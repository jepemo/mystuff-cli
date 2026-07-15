"""Orchestration and transactional application for wiki ingestion."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from mystuff.ai import load_mystuff_config, resolve_agent_settings
from mystuff.wiki.agent import FRESHNESS_TYPES, PAGE_TYPES, synthesize_sources
from mystuff.wiki.audit import audit_wiki
from mystuff.wiki.capture import capture_local_file, capture_url
from mystuff.wiki.index import build_wiki_index, select_related_pages
from mystuff.wiki.storage import (
    WikiPaths,
    ensure_wiki_layout,
    iso_now,
    json_dump,
    json_load,
    load_markdown,
    load_source_metadata,
    save_source_metadata,
    today,
    validate_slug,
    write_markdown,
)


class WikiPipelineError(RuntimeError):
    """Raised when an ingestion change set is unsafe or invalid."""


def _validate_page_change(
    paths: WikiPaths,
    change: Dict[str, Any],
    source_ids: Iterable[str],
) -> Dict[str, Any]:
    action = change.get("action")
    if action not in {"create", "update"}:
        raise WikiPipelineError(f"Unsupported page action: {action!r}")
    try:
        slug = validate_slug(str(change.get("slug") or ""))
    except ValueError as exc:
        raise WikiPipelineError(str(exc)) from exc
    destination = paths.content / f"{slug}.md"
    if action == "create" and destination.exists():
        raise WikiPipelineError(f"Cannot create existing wiki page: {slug}")
    if action == "update" and not destination.exists():
        raise WikiPipelineError(f"Cannot update missing wiki page: {slug}")

    frontmatter = change.get("frontmatter")
    if not isinstance(frontmatter, dict):
        raise WikiPipelineError(f"Page {slug} frontmatter must be an object")
    frontmatter = dict(frontmatter)
    existing_metadata: Dict[str, Any] = {}
    if destination.exists():
        existing_metadata = load_markdown(destination)["metadata"]
    frontmatter["id"] = existing_metadata.get("id") or f"wiki-{slug}"
    frontmatter.setdefault("title", slug.replace("-", " ").title())
    frontmatter.setdefault("summary", "")
    frontmatter.setdefault("page_type", "concept")
    frontmatter.setdefault("aliases", [])
    frontmatter.setdefault("topics", [])
    frontmatter.setdefault("sources", [])
    frontmatter.setdefault("freshness", "stable")
    frontmatter["public"] = existing_metadata.get(
        "public", frontmatter.get("public", True)
    )
    frontmatter["created_at"] = existing_metadata.get(
        "created_at", frontmatter.get("created_at", today())
    )
    frontmatter["updated_at"] = today()
    if frontmatter["page_type"] not in PAGE_TYPES:
        raise WikiPipelineError(
            f"Page {slug} has unsupported page_type {frontmatter['page_type']!r}"
        )
    if frontmatter["freshness"] not in FRESHNESS_TYPES:
        raise WikiPipelineError(
            f"Page {slug} has unsupported freshness {frontmatter['freshness']!r}"
        )
    if not isinstance(frontmatter["public"], bool):
        raise WikiPipelineError(f"Page {slug} public must be true or false")
    for field in ("aliases", "topics", "sources"):
        if not isinstance(frontmatter[field], list) or not all(
            isinstance(value, str) for value in frontmatter[field]
        ):
            raise WikiPipelineError(f"Page {slug} field {field} must be a string list")
        # Validation must not mutate the agent plan stored in the run record.
        frontmatter[field] = list(frontmatter[field])
    if slug == "index":
        # The map is derived navigation, not another material claim page.
        frontmatter["sources"] = []
    else:
        if not frontmatter["sources"]:
            raise WikiPipelineError(f"Page {slug} must cite at least one source")
        current_source_ids = set(source_ids)
        if not current_source_ids.intersection(frontmatter["sources"]):
            raise WikiPipelineError(
                f"Page {slug} must cite at least one source from the current run"
            )
    for source_id in frontmatter["sources"]:
        if not (paths.source_metadata / f"{source_id}.yaml").exists():
            raise WikiPipelineError(
                f"Page {slug} refers to uncaptured source {source_id!r}"
            )

    body = str(change.get("body") or "").strip()
    if not body:
        raise WikiPipelineError(f"Page {slug} body cannot be empty")
    if body.startswith("---"):
        raise WikiPipelineError(f"Page {slug} body must not contain frontmatter")
    return {
        "action": action,
        "slug": slug,
        "destination": destination,
        "frontmatter": frontmatter,
        "body": body,
        "reason": str(change.get("reason") or ""),
    }


def validate_change_set(
    paths: WikiPaths, plan: Dict[str, Any], source_ids: Iterable[str]
) -> List[Dict[str, Any]]:
    pages = plan.get("pages")
    if not isinstance(pages, list):
        raise WikiPipelineError("Agent change set field 'pages' must be a list")
    validated = [
        _validate_page_change(paths, change, source_ids)
        for change in pages
        if isinstance(change, dict)
    ]
    if len(validated) != len(pages):
        raise WikiPipelineError("Every page change must be an object")
    slugs = [change["slug"] for change in validated]
    if len(slugs) != len(set(slugs)):
        raise WikiPipelineError("A change set cannot modify the same page twice")
    return validated


def apply_change_set(
    paths: WikiPaths, plan: Dict[str, Any], source_ids: Iterable[str]
) -> List[str]:
    validated = validate_change_set(paths, plan, source_ids)
    if not validated:
        return []

    originals: Dict[Path, Optional[bytes]] = {
        item["destination"]: (
            item["destination"].read_bytes() if item["destination"].exists() else None
        )
        for item in validated
    }
    with tempfile.TemporaryDirectory(dir=paths.root, prefix=".wiki-apply-") as name:
        staging = Path(name)
        staged_paths = []
        for item in validated:
            staged = staging / f"{item['slug']}.md"
            write_markdown(staged, item["frontmatter"], item["body"])
            staged_paths.append((staged, item["destination"]))
        try:
            for staged, destination in staged_paths:
                destination.parent.mkdir(parents=True, exist_ok=True)
                staged.replace(destination)
        except OSError as exc:
            for destination, original in originals.items():
                if original is None:
                    destination.unlink(missing_ok=True)
                else:
                    destination.write_bytes(original)
            raise WikiPipelineError(f"Could not apply wiki change set: {exc}") from exc
    return [item["slug"] for item in validated]


def _source_text(paths: WikiPaths, source_ids: Iterable[str]) -> str:
    chunks = []
    for source_id in source_ids:
        source = load_source_metadata(paths, source_id)
        extracted = paths.root / source["extracted_file"]
        if extracted.is_file():
            chunks.append(extracted.read_text(encoding="utf-8", errors="replace"))
    return "\n\n".join(chunks)


def ingest_url(
    paths: WikiPaths,
    url: str,
    *,
    capture_only: bool = False,
    dry_run: bool = False,
    reprocess: bool = False,
    command_override: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_wiki_layout(paths)
    config = load_mystuff_config(paths.mystuff)
    source = capture_url(paths, url, config=config)
    return _process_captured_sources(
        paths,
        [source],
        urls=[url],
        config=config,
        capture_only=capture_only,
        dry_run=dry_run,
        reprocess=reprocess,
        command_override=command_override,
    )


def process_source(
    paths: WikiPaths,
    source_id: str,
    *,
    dry_run: bool = False,
    reprocess: bool = False,
    command_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Process an existing immutable capture without downloading it again."""
    return process_sources(
        paths,
        [source_id],
        dry_run=dry_run,
        reprocess=reprocess,
        command_override=command_override,
    )


def process_sources(
    paths: WikiPaths,
    source_ids: List[str],
    *,
    dry_run: bool = False,
    reprocess: bool = False,
    command_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Process related immutable captures in one coherent synthesis run."""
    if not source_ids:
        raise WikiPipelineError("At least one wiki source id is required")
    if len(source_ids) != len(set(source_ids)):
        raise WikiPipelineError("A wiki source batch cannot contain duplicate ids")
    ensure_wiki_layout(paths)
    sources = [load_source_metadata(paths, source_id) for source_id in source_ids]
    config = load_mystuff_config(paths.mystuff)
    return _process_captured_sources(
        paths,
        sources,
        urls=[
            str(source.get("original_url") or source["source_id"]) for source in sources
        ],
        config=config,
        capture_only=False,
        dry_run=dry_run,
        reprocess=reprocess,
        command_override=command_override,
    )


def _process_captured_sources(
    paths: WikiPaths,
    sources: List[Dict[str, Any]],
    *,
    urls: List[str],
    config: Dict[str, Any],
    capture_only: bool,
    dry_run: bool,
    reprocess: bool,
    command_override: Optional[str],
) -> Dict[str, Any]:
    source = sources[0]
    agent_settings = (
        None
        if capture_only
        else resolve_agent_settings(
            "wiki", paths.mystuff, command_override=command_override
        )
    )
    timestamp = iso_now().replace(":", "").replace("+00:00", "Z")
    run_id = f"run-{timestamp}-{source['source_id'][-6:]}-{uuid.uuid4().hex[:6]}"
    run_path = paths.runs / f"{run_id}.json"
    run: Dict[str, Any] = {
        "schema_version": 2,
        "run_id": run_id,
        "started_at": iso_now(),
        "primary_source_id": source["source_id"],
        "source_ids": [item["source_id"] for item in sources],
        "urls": urls,
        "mode": "capture-only" if capture_only else "dry-run" if dry_run else "apply",
        "agent": (
            {
                "provider": agent_settings.provider,
                "model": agent_settings.model,
                "profile": agent_settings.profile,
                "reasoning_effort": agent_settings.reasoning_effort,
            }
            if agent_settings
            else None
        ),
        "status": "captured" if capture_only else "running",
        "changed_pages": [],
        "plan": None,
        "audit": None,
        "error": None,
    }
    json_dump(run_path, run)
    if capture_only:
        run["finished_at"] = iso_now()
        json_dump(run_path, run)
        return run
    if all(item.get("status") == "processed" for item in sources) and not reprocess:
        run["status"] = "already-processed"
        run["finished_at"] = iso_now()
        json_dump(run_path, run)
        return run

    try:
        index = build_wiki_index(paths)
        related = select_related_pages(index, _source_text(paths, run["source_ids"]))
        plan = synthesize_sources(
            paths,
            run["source_ids"],
            related,
            command_override=command_override,
        )
        requested = plan.get("additional_sources") or []
        if requested:
            for item in requested[:5]:
                extra_url = str(item.get("url") or "")
                if not extra_url:
                    continue
                extra = capture_url(paths, extra_url, config=config)
                if extra["source_id"] not in run["source_ids"]:
                    run["source_ids"].append(extra["source_id"])
            index = build_wiki_index(paths)
            related = select_related_pages(
                index, _source_text(paths, run["source_ids"])
            )
            plan = synthesize_sources(
                paths,
                run["source_ids"],
                related,
                command_override=command_override,
            )
            if plan.get("additional_sources"):
                raise WikiPipelineError(
                    "Agent still requires additional sources after one capture round"
                )

        run["plan"] = plan
        validate_change_set(paths, plan, run["source_ids"])
        if dry_run:
            run["status"] = "planned"
            for source_id in run["source_ids"]:
                source_record = load_source_metadata(paths, source_id)
                if source_record.get("status") != "processed":
                    source_record["status"] = "pending"
                source_record["error"] = None
                save_source_metadata(paths, source_record)
            run["finished_at"] = iso_now()
            json_dump(run_path, run)
            return run

        changed = apply_change_set(paths, plan, run["source_ids"])
        report = audit_wiki(
            paths,
            changed_slugs=changed,
            llm_findings=plan.get("audit_findings") or [],
        )
        run["changed_pages"] = changed
        run["audit"] = {
            "error_count": report["error_count"],
            "warning_count": report["warning_count"],
        }
        run["status"] = (
            "completed" if report["error_count"] == 0 else "completed-with-errors"
        )
        for source_id in run["source_ids"]:
            source_record = load_source_metadata(paths, source_id)
            source_record["status"] = "processed"
            source_record["processed_at"] = iso_now()
            source_record["run_id"] = run_id
            source_record["error"] = None
            save_source_metadata(paths, source_record)
    except Exception as exc:
        run["status"] = "failed"
        run["error"] = str(exc)
        for source_id in run["source_ids"]:
            source_record = load_source_metadata(paths, source_id)
            source_record["status"] = "error"
            source_record["error"] = str(exc)
            save_source_metadata(paths, source_record)
        raise
    finally:
        run["finished_at"] = iso_now()
        json_dump(run_path, run)
    return run


def migrate_legacy_sources(paths: WikiPaths) -> List[Dict[str, Any]]:
    """Capture legacy wiki files without moving or deleting the originals."""
    ensure_wiki_layout(paths)
    excluded = {paths.raw.resolve(), paths.content.resolve(), paths.metadata.resolve()}
    candidates = []
    for path in paths.root.rglob("*"):
        if not path.is_file() or path == paths.editorial_guide:
            continue
        resolved = path.resolve()
        if any(root == resolved or root in resolved.parents for root in excluded):
            continue
        if path.name == ".gitkeep":
            continue
        candidates.append(path)
    return [capture_local_file(paths, path) for path in sorted(candidates)]


def _recover_pre_v2_sources(
    recorded_sources: List[str], batch_sources: List[str]
) -> List[str]:
    """Undo the pre-v2 validator that appended every batch source in place."""
    for prefix_length in range(len(recorded_sources) + 1):
        prefix = recorded_sources[:prefix_length]
        polluted = prefix + [item for item in batch_sources if item not in prefix]
        if polluted == recorded_sources:
            return recorded_sources[: max(1, prefix_length)]
    return recorded_sources


def repair_legacy_batch_provenance(paths: WikiPaths) -> List[str]:
    """Repair page source lists written by schema-v1 batch runs."""
    desired: Dict[str, List[str]] = {}
    for run_path in sorted(paths.runs.glob("*.json")):
        run = json_load(run_path, {})
        if not isinstance(run, dict) or run.get("schema_version") != 1:
            continue
        if run.get("status") not in {"completed", "completed-with-errors"}:
            continue
        batch_sources = run.get("source_ids") or []
        pages = (run.get("plan") or {}).get("pages") or []
        if not isinstance(batch_sources, list) or not isinstance(pages, list):
            continue
        for change in pages:
            if not isinstance(change, dict):
                continue
            slug = str(change.get("slug") or "")
            frontmatter = change.get("frontmatter") or {}
            recorded = frontmatter.get("sources") or []
            if slug == "index":
                desired[slug] = []
            elif isinstance(recorded, list) and all(
                isinstance(item, str) for item in recorded
            ):
                desired[slug] = _recover_pre_v2_sources(recorded, batch_sources)

    changed = []
    for slug, sources in desired.items():
        page_path = paths.content / f"{slug}.md"
        if not page_path.exists():
            continue
        page = load_markdown(page_path)
        metadata = dict(page["metadata"])
        if metadata.get("sources") == sources:
            continue
        metadata["sources"] = sources
        write_markdown(page_path, metadata, page["body"])
        changed.append(slug)
    if changed:
        build_wiki_index(paths)
    return changed
