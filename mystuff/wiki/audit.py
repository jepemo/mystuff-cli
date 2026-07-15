"""Fast structural and provenance audit for the wiki."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set

from mystuff.wiki.index import build_wiki_index, tokenize
from mystuff.wiki.storage import WikiPaths, iso_now, json_dump, load_source_metadata


REQUIRED_FRONTMATTER = {
    "id",
    "title",
    "summary",
    "page_type",
    "aliases",
    "topics",
    "sources",
    "freshness",
    "public",
    "created_at",
    "updated_at",
}


def _finding(
    severity: str, code: str, message: str, *, page: Optional[str] = None
) -> Dict[str, Any]:
    value: Dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if page:
        value["page"] = page
    return value


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _has_shared_span(page_text: str, source_text: str, size: int = 30) -> bool:
    page_words = tokenize(page_text)
    source_words = tokenize(source_text)
    if len(page_words) < size or len(source_words) < size:
        return False
    source_spans = {
        tuple(source_words[index : index + size])
        for index in range(0, len(source_words) - size + 1)
    }
    return any(
        tuple(page_words[index : index + size]) in source_spans
        for index in range(0, len(page_words) - size + 1)
    )


def _copy_findings(
    paths: WikiPaths,
    pages: Iterable[Dict[str, Any]],
    scope: Optional[Set[str]],
) -> List[Dict[str, Any]]:
    findings = []
    for page in pages:
        slug = page["slug"]
        if scope is not None and slug not in scope:
            continue
        page_path = paths.content / f"{slug}.md"
        if not page_path.exists():
            continue
        page_text = page_path.read_text(encoding="utf-8")
        for source_id in page.get("sources") or []:
            try:
                source = load_source_metadata(paths, source_id)
            except (FileNotFoundError, ValueError):
                continue
            extracted = paths.root / str(source.get("extracted_file") or "")
            if extracted.is_file() and _has_shared_span(
                page_text, extracted.read_text(encoding="utf-8", errors="replace")
            ):
                findings.append(
                    _finding(
                        "warning",
                        "source-copy-overlap",
                        f"Page shares a 30-word span with {source_id}; rewrite or quote explicitly",
                        page=slug,
                    )
                )
                break
    return findings


def audit_wiki(
    paths: WikiPaths,
    *,
    changed_slugs: Optional[Iterable[str]] = None,
    full: bool = False,
    llm_findings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    index = build_wiki_index(paths)
    pages = index["pages"]
    by_slug = {page["slug"]: page for page in pages}
    findings: List[Dict[str, Any]] = []
    ids: Dict[str, List[str]] = defaultdict(list)
    aliases: Dict[str, List[str]] = defaultdict(list)

    for page in pages:
        slug = page["slug"]
        ids[page["id"]].append(slug)
        aliases[page["title"].lower()].append(slug)
        for alias in page["aliases"]:
            aliases[alias.lower()].append(slug)
        if page.get("load_error"):
            findings.append(
                _finding("error", "invalid-frontmatter", page["load_error"], page=slug)
            )
            continue
        path = paths.content / f"{slug}.md"
        from mystuff.wiki.storage import split_frontmatter

        metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        missing = sorted(REQUIRED_FRONTMATTER - set(metadata))
        if missing:
            findings.append(
                _finding(
                    "error",
                    "missing-frontmatter",
                    f"Missing required fields: {', '.join(missing)}",
                    page=slug,
                )
            )
        if "public" in metadata and not isinstance(metadata["public"], bool):
            findings.append(
                _finding(
                    "error",
                    "invalid-public",
                    "Frontmatter field public must be true or false",
                    page=slug,
                )
            )
        for field in ("aliases", "topics", "sources"):
            value = metadata.get(field)
            if field in metadata and (
                not isinstance(value, list)
                or not all(isinstance(item, str) for item in value)
            ):
                findings.append(
                    _finding(
                        "error",
                        "invalid-frontmatter-type",
                        f"Frontmatter field {field} must be a string list",
                        page=slug,
                    )
                )
        for source_id in page["sources"]:
            if not (paths.source_metadata / f"{source_id}.yaml").exists():
                findings.append(
                    _finding(
                        "error",
                        "missing-source",
                        f"Unknown captured source: {source_id}",
                        page=slug,
                    )
                )
        for href in page["broken_links"]:
            findings.append(
                _finding(
                    "error",
                    "broken-link",
                    f"Unresolved internal link: {href}",
                    page=slug,
                )
            )
        if slug != "index" and not page["backlinks"]:
            findings.append(
                _finding(
                    "warning",
                    "orphan-page",
                    "Page has no backlinks from the wiki",
                    page=slug,
                )
            )
        if page["public"]:
            for target in page["outgoing"]:
                if target in by_slug and not by_slug[target]["public"]:
                    findings.append(
                        _finding(
                            "warning",
                            "public-to-private-link",
                            f"Public page links to private page {target}",
                            page=slug,
                        )
                    )
        updated_at = _parse_date(page.get("updated_at"))
        freshness = page.get("freshness")
        max_age = (
            90 if freshness == "volatile" else 365 if freshness == "evolving" else None
        )
        if (
            max_age
            and updated_at
            and updated_at < date.today() - timedelta(days=max_age)
        ):
            findings.append(
                _finding(
                    "warning",
                    "stale-page",
                    f"{freshness.title()} page has not been updated in {max_age} days",
                    page=slug,
                )
            )

    for page_id, slugs in ids.items():
        if len(slugs) > 1:
            findings.append(
                _finding(
                    "error",
                    "duplicate-id",
                    f"Page id {page_id!r} is used by: {', '.join(sorted(slugs))}",
                )
            )
    for alias, slugs in aliases.items():
        unique = sorted(set(slugs))
        if alias and len(unique) > 1:
            findings.append(
                _finding(
                    "error",
                    "duplicate-alias",
                    f"Title or alias {alias!r} resolves to: {', '.join(unique)}",
                )
            )

    scope = None if full else set(changed_slugs or [])
    findings.extend(_copy_findings(paths, pages, scope))
    if llm_findings:
        for item in llm_findings:
            findings.append(
                {
                    "severity": item.get("severity", "warning"),
                    "code": f"llm-{item.get('kind', 'review')}",
                    "message": item.get("message", "LLM audit finding"),
                    "pages": item.get("pages") or [],
                }
            )

    report = {
        "schema_version": 1,
        "generated_at": iso_now(),
        "mode": "full" if full else "incremental",
        "page_count": len(pages),
        "error_count": sum(1 for item in findings if item["severity"] == "error"),
        "warning_count": sum(1 for item in findings if item["severity"] == "warning"),
        "findings": findings,
    }
    json_dump(paths.audit_cache, report)
    return report
