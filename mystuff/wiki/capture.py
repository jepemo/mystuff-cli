"""Immutable source capture and normalization."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from mystuff.wiki.storage import (
    WikiPaths,
    iso_now,
    load_source_metadata,
    save_source_metadata,
    source_metadata_path,
)


class CaptureError(RuntimeError):
    """Raised when a source cannot be captured safely."""


GENERIC_TEXT_CONTENT_TYPES = {
    "application/octet-stream",
    "application/x-sh",
    "application/x-shellscript",
}


@dataclass(frozen=True)
class Download:
    requested_url: str
    resolved_url: str
    content_type: str
    body: bytes
    status: int


def _looks_like_text(body: bytes) -> bool:
    if b"\x00" in body:
        return False
    try:
        body.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


class ReadableHTMLParser(HTMLParser):
    """Small dependency-free HTML-to-text extractor.

    It intentionally favors predictable text over pixel-perfect article
    extraction. Site-specific adapters can supply richer JSON or Markdown.
    """

    BLOCK_TAGS = {
        "article",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "main",
        "p",
        "pre",
        "section",
        "tr",
    }
    SKIP_TAGS = {"script", "style", "svg", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: List[str] = []
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        self.parts.append(cleaned + " ")

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def text(self) -> str:
        lines = []
        for line in "".join(self.parts).splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if normalized and (not lines or normalized != lines[-1]):
                lines.append(normalized)
        return "\n\n".join(lines)


def _content_type(headers: Any, url: str) -> str:
    header = headers.get("Content-Type", "") if headers else ""
    value = header.split(";", 1)[0].strip().lower()
    if value:
        return value
    guessed, _ = mimetypes.guess_type(urllib.parse.urlparse(url).path)
    return guessed or "application/octet-stream"


def download_url(
    url: str, *, timeout: int = 20, max_bytes: int = 20_000_000
) -> Download:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https", "file"}:
        raise CaptureError(f"Unsupported URL scheme: {parsed.scheme or '(missing)'}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "mystuff-cli/0.7 (+local knowledge capture)",
            "Accept": "text/html,application/pdf,application/json,text/plain,*/*;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise CaptureError(
                    f"Source exceeds configured maximum of {max_bytes} bytes"
                )
            resolved_url = response.geturl()
            status = int(getattr(response, "status", None) or 200)
            return Download(
                requested_url=url,
                resolved_url=resolved_url,
                content_type=_content_type(response.headers, resolved_url),
                body=body,
                status=status,
            )
    except CaptureError:
        raise
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CaptureError(f"Could not download {url}: {exc}") from exc


def _x_url_parts(url: str) -> Dict[str, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {
        "x.com",
        "www.x.com",
        "twitter.com",
        "www.twitter.com",
    }:
        return {}
    match = re.search(r"/([^/]+)/status/(\d+)", parsed.path)
    if not match:
        return {}
    return {"username": match.group(1), "status_id": match.group(2), "url": url}


def candidate_urls(url: str, config: Dict[str, Any]) -> List[str]:
    """Return the original URL followed by configured resolver fallbacks."""
    candidates = [url]
    parts = _x_url_parts(url)
    if not parts:
        return candidates
    capture_config = (config.get("wiki") or {}).get("capture") or {}
    resolvers = (capture_config.get("resolvers") or {}).get("x") or []
    if not isinstance(resolvers, list):
        raise CaptureError("wiki.capture.resolvers.x must be a list")
    for template in resolvers:
        if not isinstance(template, str):
            continue
        try:
            resolved = template.format(**parts)
        except KeyError as exc:
            raise CaptureError(f"Unknown X resolver placeholder: {exc}") from exc
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _decode(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")


def _json_to_markdown(body: bytes) -> Tuple[str, str]:
    try:
        value = json.loads(_decode(body))
    except json.JSONDecodeError:
        return "Captured JSON", _decode(body)

    title = "Captured JSON"
    text_parts: List[str] = []
    if isinstance(value, dict):
        title = str(value.get("title") or value.get("name") or title)
        # Common thread APIs expose tweets in one of these containers.
        containers: Iterable[Any] = (
            value.get("tweets") or value.get("thread") or value.get("items") or [value]
        )
        if isinstance(containers, dict):
            containers = [containers]
        for item in containers:
            if not isinstance(item, dict):
                continue
            author = item.get("author") or item.get("user") or item.get("username")
            text = item.get("text") or item.get("content") or item.get("full_text")
            if text:
                heading = f"**{author}**\n\n" if author else ""
                text_parts.append(f"{heading}{text}")
    if not text_parts:
        text_parts.append(
            "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"
        )
    return title, "\n\n---\n\n".join(text_parts)


def extract_content(download: Download, original_path: Path) -> Tuple[str, str]:
    content_type = download.content_type
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = ReadableHTMLParser()
        parser.feed(_decode(download.body))
        title = parser.title or urllib.parse.urlparse(download.resolved_url).netloc
        return title, parser.text
    if content_type == "application/pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(original_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(value.strip() for value in pages if value.strip())
            title = "Captured PDF"
            if reader.metadata and reader.metadata.title:
                title = str(reader.metadata.title)
            if not text:
                text = (
                    "The PDF contains no extractable text. It may be a scanned "
                    "document that requires OCR before synthesis."
                )
            return title, text
        except ImportError:
            return "Captured PDF", (
                "PDF captured successfully, but the `pypdf` dependency is not installed."
            )
        except Exception as exc:
            return "Captured PDF", f"PDF captured, but text extraction failed: {exc}"
    if content_type in {"application/json", "application/ld+json"}:
        return _json_to_markdown(download.body)
    if content_type.startswith("text/"):
        return "Captured text", _decode(download.body).strip()
    return (
        "Captured binary source",
        "No textual extraction is available for this file type.",
    )


def _extension(content_type: str, url: str) -> str:
    mapping = {
        "text/html": ".html",
        "application/xhtml+xml": ".html",
        "application/pdf": ".pdf",
        "application/json": ".json",
        "application/ld+json": ".json",
        "text/markdown": ".md",
        "text/plain": ".txt",
    }
    if content_type in mapping:
        return mapping[content_type]
    suffix = Path(urllib.parse.urlparse(url).path).suffix
    return suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,8}", suffix) else ".bin"


def _source_type(url: str, content_type: str) -> str:
    if _x_url_parts(url):
        return "x-thread"
    if content_type == "application/pdf":
        return "pdf"
    if content_type in {"application/json", "application/ld+json"}:
        return "json"
    if content_type in {"text/html", "application/xhtml+xml"}:
        return "web-page"
    return "document"


def _capture_download(
    paths: WikiPaths,
    requested_url: str,
    download: Download,
    *,
    attempts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    digest = hashlib.sha256(download.body).hexdigest()
    source_id = f"src-{digest[:16]}"
    relative_dir = Path(str(now.year)) / f"{now.month:02d}" / source_id
    raw_dir = paths.raw / relative_dir
    metadata_path = source_metadata_path(paths, source_id)
    if metadata_path.exists():
        existing = load_source_metadata(paths, source_id)
        existing_raw_dir = paths.root / str(existing.get("raw_dir") or "")
        if existing_raw_dir.is_dir():
            known_urls = [
                str(existing.get("original_url") or ""),
                *(str(value) for value in existing.get("alternate_urls") or []),
            ]
            if requested_url not in known_urls:
                existing.setdefault("alternate_urls", []).append(requested_url)
                save_source_metadata(paths, existing)
            return existing

    raw_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=raw_dir.parent, prefix=f".{source_id}-"
    ) as temp_name:
        temp_dir = Path(temp_name)
        extension = _extension(download.content_type, download.resolved_url)
        original_path = temp_dir / f"original{extension}"
        original_path.write_bytes(download.body)
        title, extracted = extract_content(download, original_path)
        extracted_path = temp_dir / "extracted.md"
        extracted_path.write_text(
            f"# {title}\n\n{extracted.strip()}\n", encoding="utf-8"
        )
        if raw_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            temp_dir.rename(raw_dir)

    source = {
        "schema_version": 1,
        "source_id": source_id,
        "source_type": _source_type(requested_url, download.content_type),
        "original_url": requested_url,
        "alternate_urls": [],
        "resolved_url": download.resolved_url,
        "title": title,
        "captured_at": iso_now(),
        "content_type": download.content_type,
        "content_sha256": digest,
        "byte_size": len(download.body),
        "raw_dir": raw_dir.relative_to(paths.root).as_posix(),
        "original_file": (raw_dir / f"original{extension}")
        .relative_to(paths.root)
        .as_posix(),
        "extracted_file": (raw_dir / "extracted.md").relative_to(paths.root).as_posix(),
        "capture_attempts": attempts,
        "status": "pending",
        "processed_at": None,
        "error": None,
    }
    save_source_metadata(paths, source)
    return source


def capture_url(
    paths: WikiPaths,
    url: str,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    config = config or {}
    capture_config = (config.get("wiki") or {}).get("capture") or {}
    timeout = int(capture_config.get("timeout_seconds", 20))
    max_bytes = int(capture_config.get("max_bytes", 20_000_000))
    min_text = int(capture_config.get("minimum_extracted_characters", 200))
    attempts: List[Dict[str, Any]] = []
    best: Optional[Download] = None
    best_length = -1

    candidates = candidate_urls(url, config)
    for candidate in candidates:
        try:
            downloaded = download_url(candidate, timeout=timeout, max_bytes=max_bytes)
            # Estimate extractability without persisting candidate attempts.
            if downloaded.content_type in {"text/html", "application/xhtml+xml"}:
                parser = ReadableHTMLParser()
                parser.feed(_decode(downloaded.body))
                text_length = len(parser.text)
            else:
                text_length = len(downloaded.body)
            attempts.append(
                {
                    "url": candidate,
                    "ok": True,
                    "status": downloaded.status,
                    "content_type": downloaded.content_type,
                    "estimated_text_length": text_length,
                }
            )
            if text_length > best_length:
                best = downloaded
                best_length = text_length
            if candidate == url and (not _x_url_parts(url) or len(candidates) == 1):
                break
            if candidate != url and text_length >= min_text:
                break
        except CaptureError as exc:
            attempts.append({"url": candidate, "ok": False, "error": str(exc)})

    if best is None:
        details = "; ".join(item.get("error", "failed") for item in attempts)
        raise CaptureError(details or f"Could not capture {url}")
    return _capture_download(paths, url, best, attempts=attempts)


def capture_local_file(paths: WikiPaths, path: Path) -> Dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise CaptureError(f"Legacy source is not a file: {path}")
    body = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if content_type in GENERIC_TEXT_CONTENT_TYPES and _looks_like_text(body):
        content_type = "text/plain"
    download = Download(
        requested_url=path.as_uri(),
        resolved_url=path.as_uri(),
        content_type=content_type,
        body=body,
        status=200,
    )
    source = _capture_download(
        paths,
        path.as_uri(),
        download,
        attempts=[{"url": path.as_uri(), "ok": True, "status": 200}],
    )
    source["source_type"] = "legacy-note"
    source["legacy_path"] = str(path)
    save_source_metadata(paths, source)
    return source


def reextract_source(paths: WikiPaths, source_id: str) -> Dict[str, Any]:
    """Regenerate derived text from an immutable captured original."""
    source = load_source_metadata(paths, source_id)
    original_path = paths.root / str(source["original_file"])
    if not original_path.is_file():
        raise CaptureError(f"Captured original is missing: {original_path}")
    body = original_path.read_bytes()
    content_type = str(source.get("content_type") or "application/octet-stream")
    if content_type in GENERIC_TEXT_CONTENT_TYPES and _looks_like_text(body):
        content_type = "text/plain"
    download = Download(
        requested_url=str(source.get("original_url") or original_path.as_uri()),
        resolved_url=str(source.get("resolved_url") or original_path.as_uri()),
        content_type=content_type,
        body=body,
        status=200,
    )
    title, extracted = extract_content(download, original_path)
    extracted_path = paths.root / str(source["extracted_file"])
    extracted_path.write_text(f"# {title}\n\n{extracted.strip()}\n", encoding="utf-8")
    source["title"] = title
    source["content_type"] = content_type
    source["extracted_at"] = iso_now()
    source["error"] = None
    if source.get("status") == "error":
        source["status"] = "pending"
    save_source_metadata(paths, source)
    return source
