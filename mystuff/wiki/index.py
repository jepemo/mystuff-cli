"""Regenerable lexical index for wiki pages."""

from __future__ import annotations

import hashlib
import posixpath
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit

from mystuff.wiki.storage import (
    WIKI_SCHEMA_VERSION,
    WikiPaths,
    iso_now,
    json_dump,
    json_load,
    load_content_pages,
)


MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
TOKEN_RE = re.compile(r"[A-Za-z0-9À-ÖØ-öø-ÿ][A-Za-z0-9À-ÖØ-öø-ÿ_-]{2,}")

STOPWORDS = {
    "and",
    "are",
    "como",
    "con",
    "del",
    "desde",
    "esta",
    "este",
    "for",
    "from",
    "las",
    "los",
    "para",
    "por",
    "que",
    "the",
    "una",
    "uno",
    "with",
}


def tokenize(text: str) -> List[str]:
    return [
        token.lower().strip("-_")
        for token in TOKEN_RE.findall(text)
        if token.lower().strip("-_") not in STOPWORDS
    ]


def _resolve_markdown_target(source_slug: str, href: str) -> Optional[str]:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    if not parsed.path.lower().endswith(".md"):
        return None
    source_dir = posixpath.dirname(f"{source_slug}.md") or "."
    target = posixpath.normpath(posixpath.join(source_dir, parsed.path))
    if target == ".." or target.startswith("../"):
        return None
    return target.removesuffix(".md")


def extract_page_links(source_slug: str, body: str) -> List[Dict[str, str]]:
    links: List[Dict[str, str]] = []
    for label, href in MARKDOWN_LINK_RE.findall(body):
        target = _resolve_markdown_target(source_slug, href)
        if target:
            links.append({"label": label.strip(), "href": href, "target": target})
    for target in WIKILINK_RE.findall(body):
        links.append(
            {
                "label": target.strip(),
                "href": f"[[{target.strip()}]]",
                "target": target.strip(),
            }
        )
    return links


def _claim_digest(body: str, summary: str) -> List[str]:
    claims: List[str] = []
    if summary:
        claims.append(summary.strip())
    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if (
            len(paragraph) >= 50
            and not paragraph.startswith(("#", "```", "|", "- ", "* "))
            and paragraph not in claims
        ):
            claims.append(paragraph[:400])
        if len(claims) >= 6:
            break
    return claims


def _page_record(page: Dict[str, Any]) -> Dict[str, Any]:
    metadata = page.get("metadata") or {}
    body = page.get("body") or ""
    slug = page["slug"]
    title = str(metadata.get("title") or slug.replace("-", " ").title())
    summary = str(metadata.get("summary") or "").strip()
    aliases = [str(value) for value in metadata.get("aliases") or []]
    topics = [
        str(value) for value in metadata.get("topics") or metadata.get("tags") or []
    ]
    sources = [str(value) for value in metadata.get("sources") or []]
    headings = HEADING_RE.findall(body)
    tokens = tokenize(" ".join([title, summary, *aliases, *topics, *headings, body]))
    keywords = [token for token, _ in Counter(tokens).most_common(40)]
    links = extract_page_links(slug, body)
    return {
        "id": str(metadata.get("id") or f"wiki-{slug}"),
        "slug": slug,
        "path": f"{slug}.md",
        "title": title,
        "summary": summary,
        "page_type": str(metadata.get("page_type") or "concept"),
        "aliases": aliases,
        "topics": topics,
        "sources": sources,
        "freshness": str(metadata.get("freshness") or "stable"),
        "public": bool(metadata.get("public", True)),
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "content_sha256": hashlib.sha256(
            page["path"].read_bytes() if page["path"].exists() else b""
        ).hexdigest(),
        "headings": headings,
        "keywords": keywords,
        "claim_digest": _claim_digest(body, summary),
        "links": links,
        "outgoing": [],
        "backlinks": [],
        "broken_links": [],
        "load_error": page.get("load_error"),
    }


def build_wiki_index(paths: WikiPaths, *, write: bool = True) -> Dict[str, Any]:
    records = [_page_record(page) for page in load_content_pages(paths)]
    by_slug = {record["slug"]: record for record in records}
    aliases: Dict[str, str] = {}
    for record in records:
        aliases[record["title"].lower()] = record["slug"]
        for alias in record["aliases"]:
            aliases[alias.lower()] = record["slug"]

    for record in records:
        outgoing: Set[str] = set()
        broken: List[str] = []
        for link in record["links"]:
            target = link["target"]
            resolved = target if target in by_slug else aliases.get(target.lower())
            if resolved:
                outgoing.add(resolved)
            else:
                broken.append(link["href"])
        record["outgoing"] = sorted(outgoing)
        record["broken_links"] = sorted(set(broken))

    for record in records:
        for target in record["outgoing"]:
            by_slug[target]["backlinks"].append(record["slug"])
    for record in records:
        record["backlinks"] = sorted(set(record["backlinks"]))

    index = {
        "schema_version": WIKI_SCHEMA_VERSION,
        "generated_at": iso_now(),
        "page_count": len(records),
        "public_page_count": sum(1 for record in records if record["public"]),
        "pages": sorted(records, key=lambda item: item["title"].lower()),
    }
    if write:
        json_dump(paths.index_cache, index)
        expected_sidecars = set()
        for record in records:
            sidecar = paths.page_metadata / f"{record['id']}.json"
            expected_sidecars.add(sidecar.name)
            json_dump(sidecar, record)
        if paths.page_metadata.exists():
            for sidecar in paths.page_metadata.glob("*.json"):
                if sidecar.name not in expected_sidecars:
                    sidecar.unlink()
    return index


def load_wiki_index(paths: WikiPaths) -> Dict[str, Any]:
    value = json_load(paths.index_cache)
    if isinstance(value, dict):
        return value
    return build_wiki_index(paths)


def select_related_pages(
    index: Dict[str, Any], source_text: str, *, limit: int = 12
) -> List[Dict[str, Any]]:
    source_tokens = set(tokenize(source_text))
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for page in index.get("pages") or []:
        keywords = set(page.get("keywords") or [])
        title_tokens = set(tokenize(page.get("title") or ""))
        topic_tokens = set(tokenize(" ".join(page.get("topics") or [])))
        score = float(len(source_tokens & keywords))
        score += 5.0 * len(source_tokens & title_tokens)
        score += 3.0 * len(source_tokens & topic_tokens)
        if page.get("slug") == "index":
            score += 0.5
        if score > 0:
            scored.append((score, page))
    scored.sort(key=lambda item: (-item[0], item[1].get("title", "")))
    return [page for _, page in scored[:limit]]
