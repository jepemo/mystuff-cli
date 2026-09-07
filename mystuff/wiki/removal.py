"""Source-aware removal of synthesized wiki pages."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote, urlsplit

from mystuff.wiki.index import build_wiki_index
from mystuff.wiki.storage import (
    WikiPaths,
    load_markdown,
    load_source_metadata,
    source_metadata_path,
    today,
    validate_slug,
    write_markdown,
)


class WikiRemovalError(RuntimeError):
    """Raised when a wiki page cannot be removed safely."""


def _url_slug(identifier: str) -> str | None:
    parsed = urlsplit(identifier)
    if not (parsed.scheme or parsed.netloc or "/" in parsed.path):
        return None
    name = Path(unquote(parsed.path.rstrip("/"))).name
    if name.lower().endswith(".html"):
        name = name[:-5]
    try:
        return validate_slug(name)
    except ValueError:
        return None


def resolve_page_record(paths: WikiPaths, identifier: str) -> Dict[str, Any]:
    """Resolve a page by stable id, slug, or generated web URL."""
    value = identifier.strip()
    if not value:
        raise WikiRemovalError("Wiki page identifier cannot be empty")
    index = build_wiki_index(paths, write=False)
    pages = index.get("pages") or []
    record = next((page for page in pages if page.get("id") == value), None)
    if record is None:
        url_slug = _url_slug(value)
        candidate = url_slug or value
        record = next((page for page in pages if page.get("slug") == candidate), None)
    if record is None:
        raise WikiRemovalError(f"Wiki page not found: {identifier}")
    if record.get("slug") == "index":
        raise WikiRemovalError("The wiki index cannot be removed")
    return record


def _link_targets_page(link: Dict[str, str], target: Dict[str, Any]) -> bool:
    candidate = str(link.get("target") or "")
    names = {
        str(target.get("slug") or "").lower(),
        str(target.get("title") or "").lower(),
        *[str(alias).lower() for alias in target.get("aliases") or []],
    }
    return candidate.lower() in names


def _unlink_page(body: str, record: Dict[str, Any], target: Dict[str, Any]) -> str:
    lines = body.splitlines()
    for link in record.get("links") or []:
        if not _link_targets_page(link, target):
            continue
        href = str(link.get("href") or "")
        label = str(link.get("label") or target.get("title") or "")
        token = href if href.startswith("[[") else f"[{label}]({href})"
        standalone = re.compile(rf"^\s*(?:[-*+]|\d+\.)\s*{re.escape(token)}\s*$")
        lines = [
            line.replace(token, label)
            for line in lines
            if not standalone.fullmatch(line)
        ]
    return "\n".join(lines).rstrip()


def _safe_raw_directory(paths: WikiPaths, source: Dict[str, Any]) -> Path | None:
    value = str(source.get("raw_dir") or "")
    if not value:
        return None
    relative = Path(value)
    if relative.is_absolute():
        raise WikiRemovalError(
            f"Source {source.get('source_id')} has an unsafe absolute raw_dir"
        )
    destination = (paths.root / relative).resolve()
    raw_root = paths.raw.resolve()
    if destination != raw_root and raw_root not in destination.parents:
        raise WikiRemovalError(
            f"Source {source.get('source_id')} raw_dir escapes wiki/raw"
        )
    return destination


def _remove_empty_raw_parents(paths: WikiPaths, directory: Path) -> None:
    raw_root = paths.raw.resolve()
    parent = directory.parent
    while parent != raw_root and raw_root in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def plan_page_removal(paths: WikiPaths, identifier: str) -> Dict[str, Any]:
    """Describe a page removal without changing the filesystem."""
    target = resolve_page_record(paths, identifier)
    index = build_wiki_index(paths, write=False)
    remaining = [
        page for page in index.get("pages") or [] if page.get("slug") != target["slug"]
    ]
    source_users: Dict[str, List[str]] = {}
    for source_id in target.get("sources") or []:
        source_users[source_id] = sorted(
            page["slug"]
            for page in remaining
            if source_id in (page.get("sources") or [])
        )
    return {
        "id": target["id"],
        "slug": target["slug"],
        "title": target["title"],
        "sources_to_delete": sorted(
            source_id for source_id, users in source_users.items() if not users
        ),
        "shared_sources": {
            source_id: users for source_id, users in source_users.items() if users
        },
        "incoming_pages": sorted(target.get("backlinks") or []),
    }


def remove_wiki_page(paths: WikiPaths, identifier: str) -> Dict[str, Any]:
    """Remove a page, unlink references, and delete its unshared raw sources."""
    target = resolve_page_record(paths, identifier)
    plan = plan_page_removal(paths, identifier)
    index = build_wiki_index(paths, write=False)

    raw_directories: Dict[str, Path | None] = {}
    for source_id in plan["sources_to_delete"]:
        try:
            source = load_source_metadata(paths, source_id)
        except FileNotFoundError:
            raw_directories[source_id] = None
        else:
            raw_directories[source_id] = _safe_raw_directory(paths, source)

    updated_pages = []
    records = {page["slug"]: page for page in index.get("pages") or []}
    for slug in plan["incoming_pages"]:
        record = records.get(slug)
        page_path = paths.content / f"{slug}.md"
        if not record or not page_path.exists():
            continue
        page = load_markdown(page_path)
        body = _unlink_page(page["body"], record, target)
        if body == page["body"]:
            continue
        metadata = dict(page["metadata"])
        metadata["updated_at"] = today()
        write_markdown(page_path, metadata, body)
        updated_pages.append(slug)

    page_path = paths.content / f"{target['slug']}.md"
    page_path.unlink()
    for source_id, raw_directory in raw_directories.items():
        if raw_directory and raw_directory.exists():
            shutil.rmtree(raw_directory)
            _remove_empty_raw_parents(paths, raw_directory)
        source_metadata_path(paths, source_id).unlink(missing_ok=True)

    build_wiki_index(paths)
    plan["updated_pages"] = sorted(updated_pages)
    plan["deleted_raw_directories"] = sorted(
        str(path.relative_to(paths.root))
        for path in raw_directories.values()
        if path is not None
    )
    return plan
