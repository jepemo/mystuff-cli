"""CLI for the compounding MyStuff wiki.

The new wiki is source-driven and stores generated pages under ``wiki/content``.
The small legacy helpers remain available so existing notes and callers can be
read while users migrate them into immutable raw captures.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Set

import typer
import yaml

from mystuff.ai import AgentRunnerError
from mystuff.wiki.audit import audit_wiki
from mystuff.wiki.capture import CaptureError, reextract_source
from mystuff.wiki.index import build_wiki_index
from mystuff.wiki.pipeline import (
    WikiPipelineError,
    ingest_url,
    migrate_legacy_sources,
    process_source,
    process_sources,
    repair_legacy_batch_provenance,
)
from mystuff.wiki.removal import (
    WikiRemovalError,
    plan_page_removal,
    remove_wiki_page,
)
from mystuff.wiki.storage import (
    ensure_wiki_layout,
    get_wiki_paths,
    iter_source_metadata,
    load_markdown,
    today,
    write_markdown,
)


def get_wiki_dir() -> Path:
    return get_wiki_paths().root


def get_wiki_content_dir() -> Path:
    return get_wiki_paths().content


def ensure_wiki_dir_exists() -> None:
    ensure_wiki_layout(get_wiki_paths())


def slugify(text: str) -> str:
    slug = text.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def get_wiki_filename(title: str) -> str:
    return f"{slugify(title)}.md"


def get_editor() -> str:
    return os.getenv("EDITOR", "vim")


def open_editor(file_path: Path) -> bool:
    command = shlex.split(get_editor())
    if not command:
        typer.echo("Editor command is empty", err=True)
        return False
    try:
        subprocess.run(command + [str(file_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        typer.echo(f"Error opening editor: {command[0]}", err=True)
    except FileNotFoundError:
        typer.echo(f"Editor not found: {command[0]}", err=True)
    return False


def load_wiki_from_file(file_path: Path) -> Dict:
    """Load both new wiki pages and legacy frontmatter."""
    page = load_markdown(file_path)
    metadata = dict(page["metadata"])
    metadata.setdefault("tags", metadata.get("topics", []))
    metadata.setdefault("aliases", [])
    metadata.setdefault("backlinks", [])
    metadata["body"] = page["body"]
    metadata["file_path"] = file_path
    return metadata


def save_wiki_to_file(
    file_path: Path,
    title: str,
    tags: List[str],
    aliases: List[str],
    backlinks: List[str],
    body: str,
) -> None:
    """Compatibility writer for legacy notes.

    New generated pages use :func:`mystuff.wiki.storage.write_markdown` and do
    not persist derived backlinks in frontmatter.
    """
    metadata = {
        "title": title,
        "tags": tags,
        "aliases": aliases,
        "backlinks": backlinks,
    }
    file_path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.safe_dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    file_path.write_text(
        f"---\n{frontmatter}\n---\n\n{body.rstrip()}", encoding="utf-8"
    )


def _wiki_note_paths() -> List[Path]:
    paths = get_wiki_paths()
    content_paths = sorted(paths.content.glob("*.md")) if paths.content.exists() else []
    # Before migration, keep reading root-level notes exactly as the old CLI did.
    return content_paths or sorted(paths.root.glob("*.md"))


def get_all_wiki_notes() -> List[Dict]:
    notes = []
    for path in _wiki_note_paths():
        try:
            notes.append(load_wiki_from_file(path))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            typer.echo(f"Error loading wiki note {path}: {exc}", err=True)
    return sorted(notes, key=lambda note: str(note.get("title") or "").lower())


def find_wiki_note_by_title_or_alias(title: str) -> Optional[Dict]:
    expected = title.lower()
    for note in get_all_wiki_notes():
        if str(note.get("title") or "").lower() == expected:
            return note
        if any(str(alias).lower() == expected for alias in note.get("aliases", [])):
            return note
        if note["file_path"].stem == slugify(title):
            return note
    return None


def extract_wiki_links(content: str) -> Set[str]:
    return set(re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content))


def update_backlinks() -> None:
    """Update legacy backlinks or rebuild the derived index for new pages."""
    notes = get_all_wiki_notes()
    if not notes:
        return
    paths = get_wiki_paths()
    if all(note["file_path"].parent == paths.content for note in notes):
        build_wiki_index(paths)
        return

    title_to_file: Dict[str, Path] = {}
    for note in notes:
        title_to_file[str(note.get("title") or "").lower()] = note["file_path"]
        for alias in note.get("aliases", []):
            title_to_file[str(alias).lower()] = note["file_path"]
    backlinks = {note["file_path"]: set() for note in notes}
    for note in notes:
        for link in extract_wiki_links(note.get("body", "")):
            target = title_to_file.get(link.lower())
            if target:
                backlinks[target].add(note["file_path"].stem)
    for note in notes:
        new_backlinks = sorted(backlinks[note["file_path"]])
        if new_backlinks != sorted(note.get("backlinks", [])):
            save_wiki_to_file(
                note["file_path"],
                note.get("title", "Untitled"),
                note.get("tags", []),
                note.get("aliases", []),
                new_backlinks,
                note.get("body", ""),
            )


def search_notes_by_text(notes: List[Dict], search_text: str) -> List[Dict]:
    expected = search_text.lower()
    results = []
    for note in notes:
        values = [
            str(note.get("title") or ""),
            str(note.get("body") or ""),
            *[str(value) for value in note.get("tags", [])],
            *[str(value) for value in note.get("topics", [])],
            *[str(value) for value in note.get("aliases", [])],
        ]
        if any(expected in value.lower() for value in values):
            results.append(note)
    return results


def generate_ascii_graph(note: Dict, max_depth: int = 2) -> str:
    del max_depth  # Kept for compatibility with the old public helper.
    backlinks = note.get("backlinks", [])
    if not backlinks:
        return f"{note.get('title', 'Untitled')}\n  (no backlinks)"
    lines = [str(note.get("title") or "Untitled")]
    for index, backlink in enumerate(backlinks):
        prefix = "└── " if index == len(backlinks) - 1 else "├── "
        lines.append(f"  {prefix}{str(backlink).replace('-', ' ').title()}")
    return "\n".join(lines)


def new_wiki_note(
    title: Annotated[str, typer.Argument(help="Title of the wiki page")],
    tags: Annotated[Optional[List[str]], typer.Option("--tag")] = None,
    aliases: Annotated[Optional[List[str]], typer.Option("--alias")] = None,
    body: Annotated[Optional[str], typer.Option("--body")] = None,
    no_edit: Annotated[bool, typer.Option("--no-edit")] = False,
    public: Annotated[
        bool, typer.Option("--public/--private", help="Publish this page on the web")
    ] = True,
) -> None:
    """Create a manually authored page in the new wiki."""
    if not title.strip():
        typer.echo("Error: Title is required", err=True)
        raise typer.Exit(1)
    paths = ensure_wiki_layout(get_wiki_paths())
    slug = slugify(title)
    if not slug:
        typer.echo("Error: Title does not produce a valid slug", err=True)
        raise typer.Exit(1)
    destination = paths.content / f"{slug}.md"
    if destination.exists():
        typer.echo(f"Wiki page already exists: {title}")
        return
    page_body = body or (
        f"# {title}\n\n"
        "Start with the concrete question or confusion this page should resolve.\n"
    )
    metadata = {
        "id": f"wiki-{slug}",
        "title": title,
        "summary": "",
        "page_type": "concept",
        "aliases": aliases or [],
        "topics": tags or [],
        "sources": [],
        "freshness": "stable",
        "public": public,
        "created_at": today(),
        "updated_at": today(),
    }
    write_markdown(destination, metadata, page_body)
    build_wiki_index(paths)
    typer.echo(f"✅ Wiki page created: {title}")
    if not no_edit:
        open_editor(destination)


def view_wiki_note(
    title: Annotated[str, typer.Argument(help="Title, alias, or slug")],
    graph: Annotated[bool, typer.Option("--graph")] = False,
) -> None:
    note = find_wiki_note_by_title_or_alias(title)
    if not note:
        typer.echo(f"Wiki page not found: {title}")
        raise typer.Exit(1)
    if graph:
        paths = get_wiki_paths()
        index = build_wiki_index(paths, write=False)
        record = next(
            (page for page in index["pages"] if page["slug"] == note["file_path"].stem),
            None,
        )
        if record:
            note = dict(note)
            note["backlinks"] = record["backlinks"]
        typer.echo(generate_ascii_graph(note))
        return
    typer.echo(note.get("body", ""))


def edit_wiki_note(
    title: Annotated[str, typer.Argument(help="Title, alias, or slug")],
) -> None:
    note = find_wiki_note_by_title_or_alias(title)
    if not note:
        typer.echo(f"Wiki page not found: {title}")
        raise typer.Exit(1)
    if open_editor(note["file_path"]):
        update_backlinks()
        typer.echo(f"✅ Wiki page updated: {note.get('title', 'Untitled')}")


def delete_wiki_note(
    title: Annotated[str, typer.Argument(help="Title, alias, or slug")],
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
) -> None:
    note = find_wiki_note_by_title_or_alias(title)
    if not note:
        typer.echo(f"Wiki page not found: {title}")
        raise typer.Exit(1)
    if not force and not typer.confirm(f"Delete '{note.get('title', title)}'?"):
        typer.echo("Deletion cancelled.")
        return
    note["file_path"].unlink()
    update_backlinks()
    typer.echo(f"✅ Wiki page deleted: {note.get('title', title)}")


def remove_synthesized_wiki_page(
    identifier: Annotated[
        str, typer.Argument(help="Page id, slug, or generated wiki URL")
    ],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip the confirmation prompt")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be removed")
    ] = False,
) -> None:
    """Remove a page and any captured sources no other page still uses."""
    paths = ensure_wiki_layout(get_wiki_paths())
    try:
        plan = plan_page_removal(paths, identifier)
    except (WikiRemovalError, OSError, ValueError) as exc:
        typer.echo(f"❌ Wiki removal failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Page: {plan['id']} ({plan['slug']})")
    typer.echo(f"Raw sources to delete: {len(plan['sources_to_delete'])}")
    if plan["shared_sources"]:
        typer.echo(f"Shared sources preserved: {len(plan['shared_sources'])}")
        for source_id, users in plan["shared_sources"].items():
            typer.echo(f"  {source_id}: used by {', '.join(users)}")
    if plan["incoming_pages"]:
        typer.echo(f"Incoming links to unwrap: {len(plan['incoming_pages'])}")
    if dry_run:
        typer.echo("Status: dry-run")
        return
    if not force and not typer.confirm(
        f"Remove '{plan['title']}' and unused raw data?"
    ):
        typer.echo("Removal cancelled.")
        return
    try:
        result = remove_wiki_page(paths, identifier)
    except (WikiRemovalError, OSError, ValueError) as exc:
        typer.echo(f"❌ Wiki removal failed: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✅ Removed wiki page: {result['title']}")
    if result["updated_pages"]:
        typer.echo("Updated links in: " + ", ".join(result["updated_pages"]))
    if result["sources_to_delete"]:
        typer.echo("Deleted sources: " + ", ".join(result["sources_to_delete"]))


def list_wiki_notes(
    no_interactive: Annotated[bool, typer.Option("--no-interactive")] = False,
) -> None:
    del no_interactive
    notes = get_all_wiki_notes()
    if not notes:
        typer.echo("No wiki pages found.")
        return
    for note in notes:
        visibility = "public" if note.get("public", True) else "private"
        typer.echo(f"{note.get('title', 'Untitled')} [{visibility}]")


def search_wiki_notes(
    query: Annotated[str, typer.Argument(help="Text to find")],
    graph: Annotated[bool, typer.Option("--graph")] = False,
    no_interactive: Annotated[bool, typer.Option("--no-interactive")] = False,
) -> None:
    del no_interactive
    matches = search_notes_by_text(get_all_wiki_notes(), query)
    if not matches:
        typer.echo(f"No wiki pages found matching '{query}'")
        return
    for note in matches:
        typer.echo(
            generate_ascii_graph(note) if graph else note.get("title", "Untitled")
        )


def ingest_wiki_source(
    url: Annotated[str, typer.Argument(help="URL to capture and synthesize")],
    capture_only: Annotated[
        bool,
        typer.Option("--capture-only", help="Capture raw content without running AI"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Generate and validate a plan without applying it"
        ),
    ] = False,
    reprocess: Annotated[
        bool,
        typer.Option(
            "--reprocess", help="Run synthesis again for an already processed source"
        ),
    ] = False,
    codex_command: Annotated[
        Optional[str],
        typer.Option("--codex-command", help="Override configured Codex command"),
    ] = None,
) -> None:
    """Capture a URL, synthesize wiki pages, and audit the changed neighborhood."""
    try:
        run = ingest_url(
            get_wiki_paths(),
            url,
            capture_only=capture_only,
            dry_run=dry_run,
            reprocess=reprocess,
            command_override=codex_command,
        )
    except (
        CaptureError,
        AgentRunnerError,
        WikiPipelineError,
        OSError,
        ValueError,
    ) as exc:
        typer.echo(f"❌ Wiki ingestion failed: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Source: {run['primary_source_id']}")
    typer.echo(f"Status: {run['status']}")
    if run.get("changed_pages"):
        typer.echo("Changed pages: " + ", ".join(run["changed_pages"]))
    if run.get("audit"):
        typer.echo(
            "Audit: "
            f"{run['audit']['error_count']} errors, "
            f"{run['audit']['warning_count']} warnings"
        )


def wiki_status() -> None:
    """Show captured sources and whether they have been processed."""
    paths = ensure_wiki_layout(get_wiki_paths())
    sources = list(iter_source_metadata(paths))
    if not sources:
        typer.echo("No captured wiki sources.")
        return
    counts: Dict[str, int] = {}
    for source in sources:
        status = str(source.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
        typer.echo(
            f"{source.get('source_id')} | {status} | "
            f"{source.get('title') or source.get('original_url')}"
        )
    typer.echo(
        "Summary: "
        + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    )


def process_wiki_source(
    source_id: Annotated[
        str, typer.Argument(help="Captured source id shown by `wiki status`")
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Generate and validate a plan without applying it"
        ),
    ] = False,
    reprocess: Annotated[
        bool,
        typer.Option("--reprocess", help="Run synthesis again for a processed source"),
    ] = False,
    codex_command: Annotated[
        Optional[str],
        typer.Option("--codex-command", help="Override configured Codex command"),
    ] = None,
) -> None:
    """Process an existing immutable source capture by id."""
    try:
        run = process_source(
            get_wiki_paths(),
            source_id,
            dry_run=dry_run,
            reprocess=reprocess,
            command_override=codex_command,
        )
    except (
        AgentRunnerError,
        WikiPipelineError,
        OSError,
        ValueError,
    ) as exc:
        typer.echo(f"❌ Wiki processing failed: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Source: {run['primary_source_id']}")
    typer.echo(f"Status: {run['status']}")
    if run.get("changed_pages"):
        typer.echo("Changed pages: " + ", ".join(run["changed_pages"]))
    if run.get("audit"):
        typer.echo(
            "Audit: "
            f"{run['audit']['error_count']} errors, "
            f"{run['audit']['warning_count']} warnings"
        )


def process_wiki_source_batch(
    source_ids: Annotated[
        List[str],
        typer.Argument(help="Related captured source ids to synthesize together"),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Generate and validate a plan without applying it"
        ),
    ] = False,
    reprocess: Annotated[
        bool,
        typer.Option("--reprocess", help="Include already processed sources again"),
    ] = False,
    codex_command: Annotated[
        Optional[str],
        typer.Option("--codex-command", help="Override configured Codex command"),
    ] = None,
) -> None:
    """Process related immutable sources as one coherent batch."""
    try:
        run = process_sources(
            get_wiki_paths(),
            source_ids,
            dry_run=dry_run,
            reprocess=reprocess,
            command_override=codex_command,
        )
    except (
        AgentRunnerError,
        WikiPipelineError,
        OSError,
        ValueError,
    ) as exc:
        typer.echo(f"❌ Wiki batch processing failed: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Sources: {', '.join(run['source_ids'])}")
    typer.echo(f"Status: {run['status']}")
    if run.get("changed_pages"):
        typer.echo("Changed pages: " + ", ".join(run["changed_pages"]))
    if run.get("audit"):
        typer.echo(
            "Audit: "
            f"{run['audit']['error_count']} errors, "
            f"{run['audit']['warning_count']} warnings"
        )


def audit_wiki_command(
    full: Annotated[
        bool, typer.Option("--full", help="Also compare source overlap for every page")
    ] = False,
) -> None:
    """Audit schema, links, provenance, privacy boundaries, and staleness."""
    paths = ensure_wiki_layout(get_wiki_paths())
    report = audit_wiki(paths, full=full)
    for finding in report["findings"]:
        page = f" [{finding['page']}]" if finding.get("page") else ""
        typer.echo(
            f"{finding['severity'].upper()} {finding['code']}{page}: "
            f"{finding['message']}"
        )
    typer.echo(
        f"Audit: {report['error_count']} errors, "
        f"{report['warning_count']} warnings across {report['page_count']} pages"
    )
    if report["error_count"]:
        raise typer.Exit(1)


def rebuild_wiki_index() -> None:
    """Regenerate all machine metadata from wiki content."""
    paths = ensure_wiki_layout(get_wiki_paths())
    index = build_wiki_index(paths)
    typer.echo(
        f"✅ Indexed {index['page_count']} pages "
        f"({index['public_page_count']} public)"
    )


def reextract_wiki_source(
    source_id: Annotated[str, typer.Argument(help="Captured source id")],
) -> None:
    """Regenerate extracted text without changing the captured original."""
    try:
        source = reextract_source(get_wiki_paths(), source_id)
    except (CaptureError, OSError, ValueError) as exc:
        typer.echo(f"❌ Wiki extraction failed: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✅ Re-extracted {source['source_id']} as {source['content_type']}")


def migrate_legacy_wiki() -> None:
    """Capture old wiki files as immutable legacy sources without deleting them."""
    paths = ensure_wiki_layout(get_wiki_paths())
    sources = migrate_legacy_sources(paths)
    typer.echo(f"✅ Captured {len(sources)} legacy wiki files")
    if sources:
        typer.echo(
            "Original files were preserved. Process them with `wiki process SOURCE_ID`."
        )


def repair_wiki_provenance() -> None:
    """Repair source lists produced by the pre-v2 batch validator."""
    paths = ensure_wiki_layout(get_wiki_paths())
    changed = repair_legacy_batch_provenance(paths)
    typer.echo(f"✅ Repaired provenance for {len(changed)} wiki pages")


wiki_app = typer.Typer(
    name="wiki", help="Capture, synthesize, and audit a compounding wiki"
)
wiki_app.command("new")(new_wiki_note)
wiki_app.command("view")(view_wiki_note)
wiki_app.command("edit")(edit_wiki_note)
wiki_app.command("delete")(delete_wiki_note)
wiki_app.command("remove")(remove_synthesized_wiki_page)
wiki_app.command("list")(list_wiki_notes)
wiki_app.command("search")(search_wiki_notes)
wiki_app.command("ingest")(ingest_wiki_source)
wiki_app.command("process")(process_wiki_source)
wiki_app.command("process-batch")(process_wiki_source_batch)
wiki_app.command("status")(wiki_status)
wiki_app.command("audit")(audit_wiki_command)
wiki_app.command("rebuild-index")(rebuild_wiki_index)
wiki_app.command("reextract")(reextract_wiki_source)
wiki_app.command("migrate-legacy")(migrate_legacy_wiki)
wiki_app.command("repair-provenance")(repair_wiki_provenance)


if __name__ == "__main__":
    wiki_app()
