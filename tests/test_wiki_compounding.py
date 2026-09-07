import json

import pytest
import yaml
from typer.testing import CliRunner

from mystuff.ai import build_codex_exec_command, resolve_agent_settings
from mystuff.cli import app
from mystuff.commands.generate import (
    generate_wiki_pages,
    load_wiki_web_data,
    rewrite_wiki_markdown_links,
)
from mystuff.wiki.audit import audit_wiki
from mystuff.wiki.capture import (
    candidate_urls,
    capture_local_file,
    capture_url,
    reextract_source,
)
from mystuff.wiki.index import build_wiki_index, select_related_pages
from mystuff.wiki.pipeline import (
    apply_change_set,
    process_source,
    process_sources,
    repair_legacy_batch_provenance,
)
from mystuff.wiki.removal import (
    WikiRemovalError,
    plan_page_removal,
    remove_wiki_page,
    resolve_page_record,
)
from mystuff.wiki.storage import (
    ensure_wiki_layout,
    get_wiki_paths,
    load_markdown,
    load_source_metadata,
    source_metadata_path,
    today,
    write_markdown,
)


def page_metadata(
    slug: str,
    title: str,
    *,
    sources=None,
    public=True,
    page_type="concept",
):
    return {
        "id": f"wiki-{slug}",
        "title": title,
        "summary": f"A clear explanation of {title}.",
        "page_type": page_type,
        "aliases": [],
        "topics": ["systems"],
        "sources": sources or [],
        "freshness": "stable",
        "public": public,
        "created_at": today(),
        "updated_at": today(),
    }


def test_layout_has_separate_raw_content_and_metadata(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path))

    assert paths.raw.is_dir()
    assert paths.content.is_dir()
    assert paths.source_metadata.is_dir()
    assert paths.page_metadata.is_dir()
    assert (paths.content / "index.md").exists()
    assert paths.editorial_guide.exists()
    assert load_markdown(paths.content / "index.md")["metadata"]["public"] is True

    with pytest.raises(ValueError, match="Invalid wiki source id"):
        source_metadata_path(paths, "../../outside")


def test_capture_is_immutable_and_deduplicated(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "article.html"
    source_file.write_text(
        """<html><head><title>Why caches revalidate</title></head>
        <body><script>ignore me</script><article><h1>Cache revalidation</h1>
        <p>A client can ask whether its stored response is still current.</p>
        <p>The validator makes that question cheap.</p></article></body></html>""",
        encoding="utf-8",
    )

    first = capture_url(paths, source_file.as_uri())
    second = capture_url(paths, source_file.as_uri())
    mirror_file = tmp_path / "article-mirror.html"
    mirror_file.write_bytes(source_file.read_bytes())
    mirrored = capture_url(paths, mirror_file.as_uri())

    assert first["source_id"] == second["source_id"]
    assert first["source_id"] == mirrored["source_id"]
    assert first["status"] == "pending"
    assert (
        (paths.root / first["original_file"])
        .read_text(encoding="utf-8")
        .startswith("<html>")
    )
    extracted = (paths.root / first["extracted_file"]).read_text(encoding="utf-8")
    assert "Why caches revalidate" in extracted
    assert "ignore me" not in extracted
    assert len(list(paths.raw.rglob("original.*"))) == 1
    refreshed = load_source_metadata(paths, first["source_id"])
    assert mirror_file.as_uri() in refreshed["alternate_urls"]


def test_process_uses_an_existing_capture_without_downloading_again(
    tmp_path, monkeypatch
):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "source.md"
    source_file.write_text("# Source\n\nA useful captured idea.", encoding="utf-8")
    source = capture_local_file(paths, source_file)
    source_file.unlink()
    monkeypatch.setattr(
        "mystuff.wiki.pipeline.synthesize_sources",
        lambda *args, **kwargs: {
            "summary": "Nothing to change",
            "pages": [],
            "audit_findings": [],
            "additional_sources": [],
        },
    )

    run = process_source(paths, source["source_id"])

    assert run["status"] == "completed"
    assert run["agent"]["provider"] == "codex"
    assert load_source_metadata(paths, source["source_id"])["status"] == "processed"


def test_process_batch_synthesizes_related_sources_together(tmp_path, monkeypatch):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    first_file = tmp_path / "first.md"
    second_file = tmp_path / "second.md"
    first_file.write_text("# First\n\nOne related idea.", encoding="utf-8")
    second_file.write_text("# Second\n\nAnother related idea.", encoding="utf-8")
    first = capture_local_file(paths, first_file)
    second = capture_local_file(paths, second_file)
    observed = {}

    def synthesize(_paths, source_ids, _related, **_kwargs):
        observed["source_ids"] = source_ids
        return {
            "summary": "Nothing to change",
            "pages": [],
            "audit_findings": [],
            "additional_sources": [],
        }

    monkeypatch.setattr("mystuff.wiki.pipeline.synthesize_sources", synthesize)

    run = process_sources(paths, [first["source_id"], second["source_id"]])

    assert run["status"] == "completed"
    assert observed["source_ids"] == [first["source_id"], second["source_id"]]
    assert load_source_metadata(paths, first["source_id"])["status"] == "processed"
    assert load_source_metadata(paths, second["source_id"])["status"] == "processed"


def test_batch_keeps_selective_page_provenance(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    for source_id in ("src-first", "src-second"):
        (paths.source_metadata / f"{source_id}.yaml").write_text(
            f"source_id: {source_id}\n", encoding="utf-8"
        )
    plan = {
        "pages": [
            {
                "action": "create",
                "slug": "selective",
                "frontmatter": page_metadata(
                    "selective", "Selective", sources=["src-first"]
                ),
                "body": "# Selective\n\nOnly the first source supports this page.",
                "reason": "New durable concept",
            }
        ]
    }

    apply_change_set(paths, plan, ["src-first", "src-second"])

    assert plan["pages"][0]["frontmatter"]["sources"] == ["src-first"]
    assert load_markdown(paths.content / "selective.md")["metadata"]["sources"] == [
        "src-first"
    ]


def test_repair_legacy_batch_provenance_recovers_original_prefix(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    polluted = ["src-specific", "src-first", "src-second"]
    write_markdown(
        paths.content / "legacy-page.md",
        page_metadata("legacy-page", "Legacy Page", sources=polluted),
        "# Legacy Page\n\nA repaired page.",
    )
    (paths.runs / "old.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "completed",
                "source_ids": ["src-first", "src-second", "src-specific"],
                "plan": {
                    "pages": [
                        {
                            "slug": "legacy-page",
                            "frontmatter": {"sources": polluted},
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    assert repair_legacy_batch_provenance(paths) == ["legacy-page"]
    assert load_markdown(paths.content / "legacy-page.md")["metadata"]["sources"] == [
        "src-specific"
    ]


def test_remove_page_by_id_deletes_unshared_raw_source_and_unwraps_links(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "source.md"
    source_file.write_text("# Source\n\nDisposable evidence.", encoding="utf-8")
    source = capture_local_file(paths, source_file)
    write_markdown(
        paths.content / "disposable.md",
        page_metadata("disposable", "Disposable", sources=[source["source_id"]]),
        "# Disposable\n\nA page that can be removed.",
    )
    index_page = load_markdown(paths.content / "index.md")
    write_markdown(
        paths.content / "index.md",
        index_page["metadata"],
        "# Wiki\n\n- [Disposable](disposable.md)",
    )
    build_wiki_index(paths)
    raw_directory = paths.root / source["raw_dir"]

    result = remove_wiki_page(paths, "wiki-disposable")

    assert result["sources_to_delete"] == [source["source_id"]]
    assert result["updated_pages"] == ["index"]
    assert not (paths.content / "disposable.md").exists()
    assert not raw_directory.exists()
    assert not raw_directory.parent.exists()
    assert not source_metadata_path(paths, source["source_id"]).exists()
    assert "Disposable" not in load_markdown(paths.content / "index.md")["body"]
    assert not (paths.page_metadata / "wiki-disposable.json").exists()


def test_remove_page_by_web_url_preserves_a_source_used_by_another_page(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "shared.md"
    source_file.write_text("# Shared\n\nEvidence for two pages.", encoding="utf-8")
    source = capture_local_file(paths, source_file)
    for slug in ("first-page", "second-page"):
        write_markdown(
            paths.content / f"{slug}.md",
            page_metadata(slug, slug.title(), sources=[source["source_id"]]),
            f"# {slug.title()}\n\nA page backed by shared evidence.",
        )
    build_wiki_index(paths)

    url = "https://example.com/wiki/first-page.html?from=test#top"
    plan = plan_page_removal(paths, url)
    result = remove_wiki_page(paths, url)

    assert resolve_page_record(paths, "wiki-second-page")["slug"] == "second-page"
    assert plan["shared_sources"] == {source["source_id"]: ["second-page"]}
    assert result["sources_to_delete"] == []
    assert (paths.root / source["raw_dir"]).is_dir()
    assert source_metadata_path(paths, source["source_id"]).exists()
    assert not (paths.content / "first-page.md").exists()


def test_remove_command_supports_dry_run_and_protects_index(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    write_markdown(
        paths.content / "preview.md",
        page_metadata("preview", "Preview"),
        "# Preview\n\nA manual page without raw sources.",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["wiki", "remove", "wiki-preview", "--dry-run"],
        env={"MYSTUFF_HOME": str(paths.mystuff)},
    )

    assert result.exit_code == 0
    assert "Status: dry-run" in result.output
    assert (paths.content / "preview.md").exists()
    with pytest.raises(WikiRemovalError, match="index cannot be removed"):
        plan_page_removal(paths, "wiki-index")


def test_x_resolvers_are_configurable_and_keep_original_first():
    url = "https://x.com/example/status/123456"
    config = {
        "wiki": {
            "capture": {
                "resolvers": {
                    "x": [
                        "https://reader.example/{username}/status/{status_id}",
                        "https://archive.example/?url={url}",
                    ]
                }
            }
        }
    }

    assert candidate_urls(url, config) == [
        url,
        "https://reader.example/example/status/123456",
        "https://archive.example/?url=https://x.com/example/status/123456",
    ]


def test_extensionless_text_can_be_reextracted_without_changing_original(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "notes.livemd"
    source_file.write_text("# Live note\n\nReadable text.", encoding="utf-8")
    source = capture_local_file(paths, source_file)
    original_before = (paths.root / source["original_file"]).read_bytes()

    refreshed = reextract_source(paths, source["source_id"])

    assert refreshed["content_type"] == "text/plain"
    assert "Readable text" in (paths.root / source["extracted_file"]).read_text()
    assert (paths.root / source["original_file"]).read_bytes() == original_before

    script_file = tmp_path / "start.sh"
    script_file.write_text("#!/bin/sh\necho ready\n", encoding="utf-8")
    script = capture_local_file(paths, script_file)
    assert script["content_type"] == "text/plain"
    assert "echo ready" in (paths.root / script["extracted_file"]).read_text()


def test_index_builds_links_backlinks_and_related_candidates(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path))
    write_markdown(
        paths.content / "cache-revalidation.md",
        page_metadata("cache-revalidation", "Cache revalidation"),
        "# Cache revalidation\n\nA validator asks if cached state is current.\n\n"
        "See [HTTP validators](http-validators.md).",
    )
    write_markdown(
        paths.content / "http-validators.md",
        page_metadata("http-validators", "HTTP validators"),
        "# HTTP validators\n\nAn ETag identifies one representation version.",
    )

    index = build_wiki_index(paths)
    pages = {page["slug"]: page for page in index["pages"]}

    assert pages["cache-revalidation"]["outgoing"] == ["http-validators"]
    assert pages["http-validators"]["backlinks"] == ["cache-revalidation"]
    assert (paths.page_metadata / "wiki-http-validators.json").exists()
    related = select_related_pages(
        index, "How do HTTP cache validators and ETags work?"
    )
    assert related[0]["slug"] == "http-validators"


def test_change_set_application_keeps_source_and_preserves_index_source_boundary(
    tmp_path,
):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "source.md"
    source_file.write_text(
        "# Source\n\nA cache can revalidate stored state.", encoding="utf-8"
    )
    source = capture_local_file(paths, source_file)
    plan = {
        "summary": "Add cache revalidation",
        "pages": [
            {
                "action": "create",
                "slug": "cache-revalidation",
                "frontmatter": page_metadata(
                    "cache-revalidation",
                    "Cache revalidation",
                    sources=[source["source_id"]],
                ),
                "body": "# Cache revalidation\n\nA client checks whether stored state is current.",
                "reason": "This is a durable mechanism.",
            },
            {
                "action": "update",
                "slug": "index",
                "frontmatter": page_metadata(
                    "index",
                    "Wiki",
                    sources=[source["source_id"]],
                    page_type="map",
                ),
                "body": "# Wiki\n\n- [Cache revalidation](cache-revalidation.md)",
                "reason": "Expose the new concept from the main map.",
            },
        ],
        "audit_findings": [],
        "additional_sources": [],
    }

    changed = apply_change_set(paths, plan, [source["source_id"]])

    assert changed == ["cache-revalidation", "index"]
    cache = load_markdown(paths.content / "cache-revalidation.md")
    index = load_markdown(paths.content / "index.md")
    assert cache["metadata"]["id"] == "wiki-cache-revalidation"
    assert cache["metadata"]["sources"] == [source["source_id"]]
    assert index["metadata"]["sources"] == []


def test_change_set_preserves_identity_dates_and_private_visibility_on_update(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path / "mystuff"))
    source_file = tmp_path / "source.md"
    source_file.write_text("# Source\n\nUpdated evidence.", encoding="utf-8")
    source = capture_local_file(paths, source_file)
    metadata = page_metadata("private-page", "Private page", public=False)
    metadata["created_at"] = "2025-01-02"
    write_markdown(
        paths.content / "private-page.md",
        metadata,
        "# Private page\n\nOld explanation.",
    )
    proposed = page_metadata("private-page", "Private page", public=True)
    proposed["sources"] = [source["source_id"]]
    proposed["id"] = "agent-replaced-id"
    proposed["created_at"] = today()
    plan = {
        "summary": "Improve a private page",
        "pages": [
            {
                "action": "update",
                "slug": "private-page",
                "frontmatter": proposed,
                "body": "# Private page\n\nA clearer private explanation.",
                "reason": "New evidence",
            }
        ],
        "audit_findings": [],
        "additional_sources": [],
    }

    apply_change_set(paths, plan, [source["source_id"]])

    updated = load_markdown(paths.content / "private-page.md")["metadata"]
    assert updated["id"] == "wiki-private-page"
    assert updated["created_at"] == "2025-01-02"
    assert updated["public"] is False


def test_incremental_audit_detects_privacy_boundary_and_broken_link(tmp_path):
    paths = ensure_wiki_layout(get_wiki_paths(tmp_path))
    write_markdown(
        paths.content / "public-page.md",
        page_metadata("public-page", "Public page"),
        "# Public page\n\nSee [private details](private-page.md) and "
        "[missing details](missing-page.md).",
    )
    write_markdown(
        paths.content / "private-page.md",
        page_metadata("private-page", "Private page", public=False),
        "# Private page\n\nThis page stays local.",
    )

    report = audit_wiki(paths, changed_slugs=["public-page"])
    codes = {finding["code"] for finding in report["findings"]}

    assert "public-to-private-link" in codes
    assert "broken-link" in codes
    assert report["error_count"] == 1


def test_web_generation_excludes_private_pages_and_neutralizes_links(
    tmp_path, monkeypatch
):
    mystuff_dir = tmp_path / "mystuff"
    paths = ensure_wiki_layout(get_wiki_paths(mystuff_dir))
    monkeypatch.setenv("MYSTUFF_HOME", str(mystuff_dir))
    write_markdown(
        paths.content / "public-page.md",
        page_metadata("public-page", "Public page"),
        "# Public page\n\nRead [the private appendix](private-page.md).",
    )
    write_markdown(
        paths.content / "private-page.md",
        page_metadata("private-page", "Private page", public=False),
        "# Private page\n\nSecret details.",
    )
    write_markdown(
        paths.content / "index.md",
        page_metadata("index", "Wiki", page_type="map"),
        "# Wiki\n\nStart with [the public page](public-page.md).",
    )
    output = tmp_path / "site"
    stale_private = output / "wiki" / "private-page.html"
    stale_private.parent.mkdir(parents=True)
    stale_private.write_text("old private output", encoding="utf-8")

    wiki = load_wiki_web_data()
    generate_wiki_pages(
        output,
        {"author": "Tester", "menu_items": []},
        "2026-07-15 08:00 UTC",
        wiki,
    )

    assert [page["slug"] for page in wiki["pages"]] == ["public-page"]
    public_html = (output / "wiki" / "public-page.html").read_text(encoding="utf-8")
    index_html = (output / "wiki" / "index.html").read_text(encoding="utf-8")
    assert "the private appendix" in public_html
    assert "private-page.html" not in public_html
    assert "SUBJECT DIRECTORY" not in index_html
    assert "indexed page" not in index_html
    assert "<h1>Wiki</h1>" not in index_html
    assert "This is the navigational entry point" not in index_html
    assert "wiki-directory" in index_html
    assert "<h2>Pages</h2>" not in index_html
    assert not stale_private.exists()
    assert (output / "wiki" / "index.html").exists()


def test_rewrite_wiki_links_keeps_external_and_public_links():
    content = (
        "[Public](public.md) [Private](private.md) "
        "[External](https://example.com/doc.md)"
    )
    rewritten = rewrite_wiki_markdown_links(content, {"public"})
    assert "[Public](public.html)" in rewritten
    assert "[Private]" not in rewritten
    assert " Private " in f" {rewritten} "
    assert "https://example.com/doc.md" in rewritten


def test_agent_settings_are_shared_and_map_to_codex_flags(tmp_path):
    config = {
        "ai": {
            "default_provider": "codex",
            "providers": {
                "codex": {
                    "command": ["custom-codex"],
                    "model": "configured-model",
                    "profile": "mystuff",
                    "reasoning_effort": "medium",
                }
            },
            "tasks": {
                "wiki": {"provider": "codex", "model": "wiki-model"},
                "learning": {"provider": "codex"},
            },
        }
    }
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )

    wiki_settings = resolve_agent_settings("wiki", tmp_path)
    learning_settings = resolve_agent_settings("learning", tmp_path)
    command = build_codex_exec_command(
        wiki_settings,
        "Curate this source",
        cwd=tmp_path,
        read_only=True,
        ephemeral=True,
    )

    assert wiki_settings.model == "wiki-model"
    assert learning_settings.model == "configured-model"
    assert wiki_settings.reasoning_effort == "medium"
    assert command == [
        "custom-codex",
        "exec",
        "--model",
        "wiki-model",
        "--profile",
        "mystuff",
        "--config",
        'model_reasoning_effort="medium"',
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--cd",
        str(tmp_path),
        "Curate this source",
    ]


def test_cli_capture_only_and_legacy_migration_preserve_inputs(tmp_path):
    mystuff_dir = tmp_path / "mystuff"
    source_file = tmp_path / "article.html"
    source_file.write_text(
        "<html><head><title>Captured article</title></head>"
        "<body><p>A sufficiently useful source body for capture.</p></body></html>",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["wiki", "ingest", source_file.as_uri(), "--capture-only"],
        env={"MYSTUFF_HOME": str(mystuff_dir)},
    )
    assert result.exit_code == 0
    assert "Status: captured" in result.output

    legacy = mystuff_dir / "wiki" / "old" / "note.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("# Old note\n\nKeep me.", encoding="utf-8")
    migration = runner.invoke(
        app,
        ["wiki", "migrate-legacy"],
        env={"MYSTUFF_HOME": str(mystuff_dir)},
    )
    assert migration.exit_code == 0
    assert "Captured 1 legacy wiki files" in migration.output
    assert legacy.exists()
