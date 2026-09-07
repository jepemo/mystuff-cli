#!/usr/bin/env python3
"""Tests for the track-aware learn module."""

import datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import mystuff.commands.admin as admin_command
import mystuff.commands.learn as learn_command
from mystuff.cli import app
from mystuff.commands.learn import (
    convert_markdown_to_html,
    get_all_lessons,
    get_learning_dir,
    get_lessons_dir,
    get_metadata_path,
    get_next_lesson,
    load_metadata,
    save_metadata,
)
from mystuff.learning_catalog import (
    LearningCatalogError,
    LearningMetadataError,
    load_learning_catalog,
)


def write_markdown_with_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    payload = "---\n"
    payload += yaml.safe_dump(frontmatter, sort_keys=False)
    payload += "---\n"
    payload += body
    path.write_text(payload, encoding="utf-8")


def create_track(
    lessons_dir: Path,
    track_id: str,
    *,
    name: str,
    description: str,
    classification: str,
    depends_on_tracks: list[str],
    status: str,
    lessons: list[dict],
    public: bool = True,
    track_metadata: dict = None,
) -> None:
    track_dir = lessons_dir / track_id
    track_dir.mkdir(parents=True)

    track_frontmatter = {
        "track_id": track_id,
        "name": name,
        "description": description,
        "classification": classification,
        "track_tier": "core",
        "target_lesson_count": len(lessons),
        "depends_on_tracks": depends_on_tracks,
        "status": status,
        "public": public,
        "lesson_count": len(lessons),
        "difficulty_min": "beginner",
        "difficulty_max": "advanced",
        "capstone_policy": "embedded",
        "legacy_source_ranges": ["001-010"],
    }
    if track_metadata:
        track_frontmatter.update(track_metadata)
    write_markdown_with_frontmatter(
        track_dir / "TRACK.md",
        track_frontmatter,
        f"# {name}\n\nTrack overview.\n",
    )

    for lesson in lessons:
        lesson_frontmatter = {
            "lesson_id": lesson["lesson_id"],
            "title": lesson["title"],
            "track_id": track_id,
            "classification": lesson.get("classification", classification),
            "sequence": lesson["sequence"],
            "difficulty": lesson.get("difficulty", "beginner"),
            "estimated_time": lesson.get("estimated_time", 20),
            "public": lesson.get("public", True),
            "review_status": lesson.get("review_status", "reviewed"),
            "lesson_kind": lesson.get("lesson_kind", "lesson"),
            "capstone_scope": lesson.get("capstone_scope", "track"),
            "depends_on_tracks": lesson.get("depends_on_tracks", depends_on_tracks),
            "legacy_day": lesson.get("legacy_day"),
            "legacy_path": lesson.get("legacy_path"),
        }
        write_markdown_with_frontmatter(
            track_dir / f"{lesson['sequence']:03d}.md",
            lesson_frontmatter,
            lesson.get("body", f"# {lesson['title']}\n\nLesson body.\n"),
        )


@pytest.fixture
def temp_learning_dir(tmp_path, monkeypatch):
    """Create a temporary track-based learning directory."""
    mystuff_dir = tmp_path / "mystuff"
    learning_dir = mystuff_dir / "learning"
    lessons_dir = learning_dir / "lessons"
    lessons_dir.mkdir(parents=True)
    monkeypatch.setenv("MYSTUFF_HOME", str(mystuff_dir))

    create_track(
        lessons_dir,
        "foundations",
        name="Foundations",
        description="Core concepts.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        lessons=[
            {
                "lesson_id": "100",
                "sequence": 1,
                "title": "Intro to Foundations",
                "difficulty": "beginner",
                "legacy_day": 100,
                "legacy_path": "10/01.md",
                "body": "# Intro\n\n[Next](002.md)\n",
            },
            {
                "lesson_id": "101",
                "sequence": 2,
                "title": "Capstone Foundations",
                "difficulty": "intermediate",
                "lesson_kind": "capstone",
                "legacy_day": 101,
                "legacy_path": "10/02.md",
                "body": "# Capstone\n\n[Back](001.md)\n",
            },
        ],
    )
    create_track(
        lessons_dir,
        "systems",
        name="Systems",
        description="Distributed systems.",
        classification="complexity-and-dynamics",
        depends_on_tracks=["foundations"],
        status="active",
        lessons=[
            {
                "lesson_id": "200",
                "sequence": 1,
                "title": "Distributed Reads",
                "difficulty": "intermediate",
                "legacy_day": 200,
                "legacy_path": "20/01.md",
            },
            {
                "lesson_id": "201",
                "sequence": 2,
                "title": "Replication Internals",
                "difficulty": "advanced",
                "public": False,
                "legacy_day": 201,
                "legacy_path": "20/02.md",
            },
        ],
    )
    create_track(
        lessons_dir,
        "ai-lab",
        name="AI Lab",
        description="Draft work.",
        classification="complexity-and-dynamics",
        depends_on_tracks=["systems"],
        status="draft",
        lessons=[],
    )

    (lessons_dir / "README.md").write_text("# Global index\n", encoding="utf-8")
    return learning_dir


def test_get_learning_dir(temp_learning_dir):
    assert get_learning_dir() == temp_learning_dir
    assert get_learning_dir().exists()


def test_get_lessons_dir(temp_learning_dir):
    lessons_dir = get_lessons_dir()
    assert lessons_dir.exists()
    assert lessons_dir.name == "lessons"


def test_get_metadata_path(temp_learning_dir):
    metadata_path = get_metadata_path()
    assert metadata_path.parent == temp_learning_dir
    assert metadata_path.name == "metadata.yaml"


def test_load_metadata_creates_v2_file(temp_learning_dir):
    metadata = load_metadata()

    assert metadata["schema_version"] == 2
    assert metadata["current_lesson_id"] is None
    assert metadata["current_lesson_ids_by_track"] == {}
    assert metadata["last_opened_at"] is None
    assert metadata["completed_lessons"] == []


def test_load_metadata_rejects_legacy_file(temp_learning_dir):
    metadata_path = get_metadata_path()
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "current_lesson": "foundations/001.md",
                "last_opened": "2025-10-01T12:00:00",
                "completed_lessons": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(LearningMetadataError):
        load_metadata()


def test_get_all_lessons_discovers_track_layout_only(temp_learning_dir):
    lessons = get_all_lessons()

    assert [lesson["lesson_id"] for lesson in lessons] == ["100", "101", "200", "201"]
    assert all(lesson["path"].count("/") == 1 for lesson in lessons)
    assert "README.md" not in {lesson["path"] for lesson in lessons}


def test_load_learning_catalog_parses_track_metadata(temp_learning_dir):
    lessons_dir = get_lessons_dir()
    create_track(
        lessons_dir,
        "metadata-track",
        name="Metadata Track",
        description="Metadata-rich track.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Metadata Intro",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
        track_metadata={
            "macro_area": "software-systems",
            "track_type": "foundations",
            "learning_role": "core",
            "canonical_question": "How do these metadata fields guide learning?",
            "scope": {
                "includes": ["navigation signals", "editorial scope"],
                "excludes": "deep specialization",
            },
            "continues_to": "systems",
            "related_tracks": [
                {"id": "foundations", "relationship": "prepares"},
                "systems",
            ],
            "tags": ["metadata", "navigation"],
            "needs_metadata_review": "yes",
        },
    )

    catalog = load_learning_catalog()
    track = catalog["tracks_by_id"]["metadata-track"]
    foundations = catalog["tracks_by_id"]["foundations"]

    assert track["macro_area"] == "software-systems"
    assert track["track_type"] == "foundations"
    assert track["learning_role"] == "core"
    assert track["canonical_question"] == "How do these metadata fields guide learning?"
    assert track["scope"] == {
        "includes": ["navigation signals", "editorial scope"],
        "excludes": ["deep specialization"],
    }
    assert track["continues_to"] == ["systems"]
    assert track["related_tracks"] == [
        {"id": "foundations", "relationship": "prepares"},
        {"id": "systems", "relationship": ""},
    ]
    assert track["tags"] == ["metadata", "navigation"]
    assert track["needs_metadata_review"] is True
    assert foundations["scope"] == {"includes": [], "excludes": []}
    assert foundations["continues_to"] == []
    assert foundations["related_tracks"] == []
    assert foundations["tags"] == []
    assert foundations["needs_metadata_review"] is False


def test_get_next_lesson_wraps_within_track(temp_learning_dir):
    metadata = {
        "schema_version": 2,
        "current_lesson_id": "101",
        "last_opened_at": None,
        "completed_lessons": [
            {"lesson_id": "101", "completed_at": "2026-04-01T10:00:00"}
        ],
    }

    next_lesson_id = get_next_lesson("101", metadata)

    assert next_lesson_id == "100"


def test_learn_without_subcommand_shows_summary(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn"])

    assert result.exit_code == 0
    assert "Learning Summary" in result.output
    assert "Tracks available" in result.output
    assert "Current lesson" in result.output


def test_start_track_sets_first_pending_lesson(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start", "foundations"], input="n\n")

    assert result.exit_code == 0
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "100"
    assert metadata["current_lesson_ids_by_track"] == {"foundations": "100"}


def test_start_track_preserves_other_started_tracks(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "databases",
        name="Databases",
        description="Storage basics.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Database Basics",
                "difficulty": "beginner",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    runner = CliRunner()

    first = runner.invoke(app, ["learn", "start", "foundations"], input="n\n")
    second = runner.invoke(app, ["learn", "start", "databases"], input="y\nn\n")

    assert first.exit_code == 0
    assert second.exit_code == 0
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "300"
    assert metadata["current_lesson_ids_by_track"] == {"databases": "300"}


def test_start_track_preserves_legacy_global_current_lesson(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "databases",
        name="Databases",
        description="Storage basics.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Database Basics",
                "difficulty": "beginner",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "300",
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start", "foundations"], input="y\nn\n")

    assert result.exit_code == 0
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "100"
    assert metadata["current_lesson_ids_by_track"] == {"foundations": "100"}


def test_start_rejects_unpublished_track(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "private-api",
        name="Private API",
        description="Unpublished work.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        public=False,
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Private API Draft",
                "difficulty": "beginner",
            }
        ],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start", "private-api"])

    assert result.exit_code == 1
    assert "not published" in result.output
    assert load_metadata()["current_lesson_id"] is None


def test_start_with_private_lesson_reference_starts_at_first_pending_lesson(
    temp_learning_dir,
):
    lesson_path = temp_learning_dir / "lessons" / "foundations" / "002.md"
    lesson_path.write_text(
        lesson_path.read_text(encoding="utf-8").replace(
            "public: true", "public: false", 1
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start", "foundations/002"], input="n\n")

    assert result.exit_code == 0
    assert load_metadata()["current_lesson_id"] == "100"


def test_start_without_argument_selects_unstarted_track(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "private-api",
        name="Private API",
        description="Unpublished work.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        public=False,
        lessons=[
            {
                "lesson_id": "050",
                "sequence": 1,
                "title": "Private API Draft",
                "difficulty": "beginner",
            }
        ],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start"], input="1\nn\n")

    assert result.exit_code == 0
    assert "Start track" in result.output
    assert "Private API" in result.output
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "100"


def test_track_without_argument_selects_active_track(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "track"], input="1\n")

    assert result.exit_code == 0
    assert "Select track" in result.output
    assert "Intro to Foundations" in result.output
    assert "todo    001 Intro to Foundations" in result.output
    assert "Status" not in result.output
    assert "Minutes" not in result.output
    assert "┏" not in result.output


def test_track_outputs_plain_lesson_list_without_header(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "track", "foundations"])

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        "todo    001 Intro to Foundations",
        "todo    002 Capstone Foundations [CAPSTONE]",
    ]


def test_track_list_outputs_published_tracks_as_plain_text(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "private-api",
        name="Private API",
        description="Unpublished work.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        public=False,
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Private API Draft",
                "difficulty": "beginner",
            }
        ],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "track", "--list"])

    assert result.exit_code == 0
    assert "foundations - Foundations" in result.output
    assert "systems - Systems" in result.output
    assert "private-api" not in result.output
    assert "ai-lab" not in result.output
    assert "┏" not in result.output
    assert "Status" not in result.output


def test_track_selector_uses_published_tracks_not_private_open_tracks(
    temp_learning_dir,
):
    create_track(
        temp_learning_dir / "lessons",
        "private-api",
        name="Private API",
        description="Unpublished work.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        public=False,
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Private API Draft",
                "difficulty": "beginner",
            }
        ],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "track", "--prompt"], input="2\n")

    assert result.exit_code == 0
    assert "Select track" in result.output
    assert "systems - Systems" in result.output
    assert "Private API" not in result.output
    assert "Distributed Reads" in result.output


def test_current_without_argument_selects_active_lesson(temp_learning_dir, monkeypatch):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )
    opened = []

    def fake_open_lesson(lesson, web=False):
        opened.append((lesson["lesson_id"], web))

    monkeypatch.setattr(learn_command, "_open_lesson_path", fake_open_lesson)
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "current"], input="1\n")

    assert result.exit_code == 0
    assert "Select active lesson" in result.output
    assert opened == [("100", False)]
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "100"
    assert metadata["current_lesson_ids_by_track"] == {"foundations": "100"}
    assert metadata["last_opened_at"]


def test_next_finishes_track_and_suggests_unlocked_tracks(temp_learning_dir):
    metadata = {
        "schema_version": 2,
        "current_lesson_id": "101",
        "last_opened_at": datetime.datetime.now().isoformat(),
        "completed_lessons": [
            {"lesson_id": "100", "completed_at": "2026-04-01T09:00:00"}
        ],
    }
    save_metadata(metadata)

    runner = CliRunner()
    result = runner.invoke(app, ["learn", "next"], input="1\n")

    assert result.exit_code == 0
    reloaded = load_metadata()
    assert reloaded["current_lesson_id"] is None
    assert reloaded["current_lesson_ids_by_track"] == {}
    assert "Track completed: foundations" in result.output
    assert "systems" in result.output


def test_next_prefers_valid_continues_to_suggestions(temp_learning_dir):
    lessons_dir = get_lessons_dir()
    foundations_path = lessons_dir / "foundations" / "TRACK.md"
    foundations_text = foundations_path.read_text(encoding="utf-8")
    foundations_path.write_text(
        foundations_text.replace(
            "legacy_source_ranges:\n- 001-010\n",
            (
                "legacy_source_ranges:\n"
                "- 001-010\n"
                "continues_to:\n"
                "- blocked-next\n"
                "- systems\n"
                "- private-next\n"
            ),
        ),
        encoding="utf-8",
    )
    create_track(
        lessons_dir,
        "practice",
        name="Practice",
        description="A valid fallback track.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Practice Intro",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    create_track(
        lessons_dir,
        "blocked-next",
        name="Blocked Next",
        description="Locked continuation.",
        classification="systems-thinking",
        depends_on_tracks=["missing-prereq"],
        status="active",
        lessons=[
            {
                "lesson_id": "400",
                "sequence": 1,
                "title": "Blocked Intro",
                "legacy_day": 400,
                "legacy_path": "40/01.md",
            }
        ],
    )
    create_track(
        lessons_dir,
        "private-next",
        name="Private Next",
        description="Private continuation.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="active",
        public=False,
        lessons=[
            {
                "lesson_id": "500",
                "sequence": 1,
                "title": "Private Intro",
                "legacy_day": 500,
                "legacy_path": "50/01.md",
            }
        ],
    )
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "101",
            "last_opened_at": datetime.datetime.now().isoformat(),
            "completed_lessons": [
                {"lesson_id": "100", "completed_at": "2026-04-01T09:00:00"}
            ],
        }
    )

    runner = CliRunner()
    result = runner.invoke(app, ["learn", "next"], input="1\n")

    assert result.exit_code == 0
    assert "systems: Systems" in result.output
    assert "practice" not in result.output
    assert "blocked-next" not in result.output
    assert "private-next" not in result.output


def test_list_track_hides_private_lessons_by_default(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "list", "--track", "systems"])

    assert result.exit_code == 0
    assert "Distributed" in result.output
    assert "Reads" in result.output
    assert "Replication Internals" not in result.output


def test_list_track_progress_counts_only_visible_lessons(temp_learning_dir):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [
                {"lesson_id": "201", "completed_at": "2026-04-01T10:00:00"}
            ],
        }
    )

    runner = CliRunner()
    result = runner.invoke(app, ["learn", "list", "--track", "systems"])

    assert result.exit_code == 0
    assert result.output.strip() == "todo    001 Distributed Reads"


def test_catalog_groups_tracks_by_classification(temp_learning_dir):
    catalog = load_learning_catalog()

    assert [item["classification_id"] for item in catalog["classifications"]] == [
        "systems-thinking",
        "complexity-and-dynamics",
    ]
    assert [track["track_id"] for track in catalog["classifications"][1]["tracks"]] == [
        "systems",
        "ai-lab",
    ]


def test_catalog_rejects_mismatched_lesson_classification(temp_learning_dir):
    lesson_path = temp_learning_dir / "lessons" / "foundations" / "001.md"
    content = lesson_path.read_text(encoding="utf-8")
    lesson_path.write_text(
        content.replace(
            "classification: systems-thinking", "classification: wrong-group"
        ),
        encoding="utf-8",
    )

    with pytest.raises(LearningCatalogError):
        load_learning_catalog()


def test_list_groups_tracks_by_classification(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "list"])

    assert result.exit_code == 0
    assert "Systems Thinking" in result.output
    assert "Complexity And Dynamics" in result.output
    assert "Foundations" in result.output
    assert "Systems" in result.output


def test_list_filters_by_classification(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(
        app, ["learn", "list", "--classification", "systems-thinking"]
    )

    assert result.exit_code == 0
    assert "Systems Thinking" in result.output
    assert "Foundations" in result.output
    assert "Complexity And Dynamics" not in result.output
    assert "systems - Systems" not in result.output


def test_tree_groups_by_classification(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(
        app, ["learn", "tree", "--classification", "complexity-and-dynamics"]
    )

    assert result.exit_code == 0
    assert "Complexity And Dynamics" in result.output
    assert "Systems" in result.output
    assert "Distributed Reads" in result.output


def test_stats_groups_output_by_classification(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "stats"])

    assert result.exit_code == 0
    assert "Classifications visible: 2" in result.output
    assert "Systems Thinking" in result.output
    assert "Complexity And Dynamics" in result.output


def test_convert_markdown_to_html(temp_learning_dir):
    lessons_dir = temp_learning_dir / "lessons" / "scratch"
    lessons_dir.mkdir()
    lesson_file = lessons_dir / "test.md"
    lesson_file.write_text(
        "# Test Lesson\n\n```python\nprint('ok')\n```\n",
        encoding="utf-8",
    )

    html_path = convert_markdown_to_html(lesson_file)

    assert Path(html_path).exists()
    html_content = Path(html_path).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "<code>" in html_content
    Path(html_path).unlink()


def test_convert_markdown_to_html_renders_generated_quote_list(temp_learning_dir):
    lessons_dir = temp_learning_dir / "lessons" / "scratch"
    lessons_dir.mkdir()
    lesson_file = lessons_dir / "quote-list.md"
    lesson_file.write_text(
        "> **By the end of this lesson, you will be able to:**\n"
        "> - identify the participants;\n"
        "> - explain the promise.\n\n"
        "> **Idea in one sentence:** Components coordinate through messages.\n",
        encoding="utf-8",
    )

    html_path = convert_markdown_to_html(lesson_file)
    html_content = Path(html_path).read_text(encoding="utf-8")

    assert "<blockquote>" in html_content
    assert "<ul>" in html_content
    assert "<li>" in html_content
    assert "identify the participants;" in html_content
    assert "explain the promise." in html_content
    Path(html_path).unlink()


def test_convert_markdown_to_html_preserves_and_loads_tex_math(temp_learning_dir):
    lessons_dir = temp_learning_dir / "lessons" / "scratch"
    lessons_dir.mkdir()
    lesson_file = lessons_dir / "math.md"
    lesson_file.write_text(
        "Inline \\(P(X)=1\\).\n\n\\[\n\\Omega = \\{A, TA, TT\\}\n\\]\n",
        encoding="utf-8",
    )

    html_path = convert_markdown_to_html(lesson_file)
    html_content = Path(html_path).read_text(encoding="utf-8")

    assert 'class="math-inline">\\(P(X)=1\\)</span>' in html_content
    assert 'class="math-display">\\[' in html_content
    assert "\\Omega = \\{A, TA, TT\\}" in html_content
    assert "https://cdn.jsdelivr.net/npm/mathjax@4.0.0/tex-chtml.js" in html_content
    Path(html_path).unlink()


def test_unpublish_rejects_a_lesson_that_would_create_a_gap(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "unpublish", "foundations/001"])

    assert result.exit_code == 1
    assert "publication gap" in result.output
    lesson_path = temp_learning_dir / "lessons" / "foundations" / "001.md"
    assert "public: true" in lesson_path.read_text(encoding="utf-8")


def test_publish_track_is_disabled_outside_the_review_gate(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "publish", "systems"])

    assert result.exit_code == 1
    assert "Manual publication is disabled" in result.output


def test_admin_review_next_finds_pending_lesson(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "draft-review",
        name="Draft Review",
        description="Draft review track.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Draft Lesson",
                "review_status": "pending",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["admin", "review-next"])

    assert result.exit_code == 0
    assert "draft-review/001" in result.output
    assert "Draft Lesson" in result.output


def test_admin_review_track_runs_plan_and_lesson_prompts(
    temp_learning_dir, tmp_path, monkeypatch
):
    create_track(
        temp_learning_dir / "lessons",
        "draft-review",
        name="Draft Review",
        description="Draft review track.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Draft Lesson",
                "review_status": "pending",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    calls = []
    codex_home = tmp_path / "codex-home"
    session_dir = codex_home / "sessions" / "2026" / "07" / "06"
    session_dir.mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    def fake_run(command, cwd=None, check=False):
        calls.append((command, cwd, check))
        status_path = session_dir / "rollout-test.jsonl"
        status_path.write_text(
            (
                '{"type":"event_msg","payload":{"type":"token_count"},'
                '"rate_limits":{"primary":{"used_percent":12.5,'
                '"window_minutes":300,"resets_at":1783350000},'
                '"secondary":{"used_percent":84.0,"window_minutes":10080,'
                '"resets_at":1783600000},"plan_type":"plus"}}\n'
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(admin_command.subprocess, "run", fake_run)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "admin",
            "review-track",
            "--track-id",
            "draft-review",
            "--codex-command",
            "fake-codex",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            [
                "fake-codex",
                "exec",
                "--cd",
                str(temp_learning_dir.parent),
                "Planifica/revisa el track draft-review.",
            ],
            temp_learning_dir.parent,
            True,
        ),
        (
            [
                "fake-codex",
                "exec",
                "--cd",
                str(temp_learning_dir.parent),
                "Revisa la siguiente leccion del track draft-review.",
            ],
            temp_learning_dir.parent,
            True,
        ),
    ]
    assert result.output.count("Codex status:") == 2
    assert "primary: 12.5% used (5h window)" in result.output
    assert "secondary: 84.0% used (7d window)" in result.output
    assert "plan: plus" in result.output


def test_admin_review_lesson_selects_track_in_review(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "unstarted-draft",
        name="Unstarted Draft",
        description="No reviewed lessons yet.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Unstarted Lesson",
                "review_status": "pending",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    create_track(
        temp_learning_dir / "lessons",
        "draft-in-review",
        name="Draft In Review",
        description="Partially reviewed track.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        lessons=[
            {
                "lesson_id": "400",
                "sequence": 1,
                "title": "Reviewed Lesson",
                "review_status": "reviewed",
                "legacy_day": 400,
                "legacy_path": "40/01.md",
            },
            {
                "lesson_id": "401",
                "sequence": 2,
                "title": "Pending Lesson",
                "review_status": "pending",
                "legacy_day": 401,
                "legacy_path": "40/02.md",
            },
        ],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["admin", "review-lesson", "--dry-run"])

    assert result.exit_code == 0
    assert "Revisa la siguiente leccion del track draft-in-review." in result.output
    assert "unstarted-draft" not in result.output


def test_admin_show_tracks_review_queues(temp_learning_dir):
    create_track(
        temp_learning_dir / "lessons",
        "unstarted-draft",
        name="Unstarted Draft",
        description="No reviewed lessons yet.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Unstarted Lesson",
                "review_status": "pending",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    create_track(
        temp_learning_dir / "lessons",
        "draft-in-review",
        name="Draft In Review",
        description="Partially reviewed track.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        lessons=[
            {
                "lesson_id": "400",
                "sequence": 1,
                "title": "Reviewed Lesson",
                "review_status": "reviewed",
                "legacy_day": 400,
                "legacy_path": "40/01.md",
            },
            {
                "lesson_id": "401",
                "sequence": 2,
                "title": "Pending Lesson",
                "review_status": "pending",
                "legacy_day": 401,
                "legacy_path": "40/02.md",
            },
        ],
    )
    runner = CliRunner()

    pending = runner.invoke(app, ["admin", "show-tracks-pending-review"])
    in_review = runner.invoke(app, ["admin", "show-tracks-in-review"])

    assert pending.exit_code == 0
    assert "unstarted-draft" in pending.output
    assert "draft-in-review" not in pending.output
    assert in_review.exit_code == 0
    assert "draft-in-review" in in_review.output
    assert "unstarted-draft" not in in_review.output


def test_metadata_v2_normalizes_multiple_cursors_to_global_current(
    temp_learning_dir,
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "200",
            "current_lesson_ids_by_track": {"foundations": "100", "systems": "200"},
            "last_opened_at": None,
            "completed_lessons": [{"lesson_id": "100", "completed_at": "2026-01-01"}],
        }
    )

    metadata = load_metadata()

    assert metadata["current_lesson_id"] == "200"
    assert metadata["current_lesson_ids_by_track"] == {"systems": "200"}
    assert metadata["completed_lessons"] == [
        {"lesson_id": "100", "completed_at": "2026-01-01"}
    ]


def test_start_plans_then_reviews_before_setting_cursor(temp_learning_dir, monkeypatch):
    lessons_dir = temp_learning_dir / "lessons"
    create_track(
        lessons_dir,
        "just-in-time",
        name="Just In Time",
        description="Prepared only when started.",
        classification="systems-thinking",
        depends_on_tracks=[],
        status="draft",
        public=True,
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Prepared Lesson",
                "public": False,
                "review_status": "pending",
            }
        ],
    )
    (temp_learning_dir / "curriculum" / "templates").mkdir(parents=True)
    write_markdown_with_frontmatter(
        temp_learning_dir / "curriculum" / "templates" / "lesson_template.md",
        {"version": 14},
        "# Template\n",
    )
    (temp_learning_dir.parent / "config.yaml").write_text(
        (
            "ai:\n  tasks:\n    learning:\n      model: gpt-5.6-sol\n"
            "      reasoning_effort: max\n"
        ),
        encoding="utf-8",
    )
    prompts = []

    def fake_agent(prompt, *, dry_run=False):
        prompts.append(prompt)
        if prompt.startswith("Planifica"):
            path = lessons_dir / "just-in-time" / "TRACK.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "status: draft", "status: active"
                ),
                encoding="utf-8",
            )
            return
        lesson_path = lessons_dir / "just-in-time" / "001.md"
        learn_command._rewrite_frontmatter_field(
            lesson_path, "review_status", "reviewed"
        )
        learn_command._rewrite_frontmatter_field(lesson_path, "version", 14)
        learn_command._rewrite_frontmatter_field(lesson_path, "public", True)

    monkeypatch.setattr(learn_command, "_run_learning_prompt", fake_agent)
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start", "just-in-time"], input="n\n")

    assert result.exit_code == 0
    assert prompts[0].startswith("Planifica/revisa el track just-in-time")
    assert prompts[1] == "Revisa la siguiente leccion del track just-in-time."
    assert load_metadata()["current_lesson_ids_by_track"] == {"just-in-time": "300"}


def test_next_leaves_cursor_unchanged_when_review_fails(temp_learning_dir, monkeypatch):
    lesson_path = temp_learning_dir / "lessons" / "foundations" / "002.md"
    learn_command._rewrite_frontmatter_field(lesson_path, "public", False)
    learn_command._rewrite_frontmatter_field(lesson_path, "review_status", "pending")
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "current_lesson_ids_by_track": {"foundations": "100"},
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    def failed_agent(prompt, *, dry_run=False):
        raise learn_command.LessonPreparationError("review failed")

    monkeypatch.setattr(learn_command, "_run_learning_prompt", failed_agent)
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "next"], input="1\n")

    assert result.exit_code == 1
    metadata = load_metadata()
    assert metadata["current_lesson_ids_by_track"] == {"foundations": "100"}
    assert metadata["completed_lessons"] == []


def test_learning_runner_uses_configured_model_reasoning_and_working_directory(
    temp_learning_dir, monkeypatch
):
    (temp_learning_dir.parent / "config.yaml").write_text(
        (
            "ai:\n  tasks:\n    learning:\n      model: gpt-5.6-sol\n"
            "      reasoning_effort: max\n"
        ),
        encoding="utf-8",
    )
    captured = {}

    class Result:
        returncode = 0

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        return Result()

    monkeypatch.setattr(learn_command.subprocess, "run", fake_run)

    learn_command._run_learning_prompt("prepare lesson")

    assert captured["command"] == [
        "codex",
        "exec",
        "--model",
        "gpt-5.6-sol",
        "--config",
        'model_reasoning_effort="max"',
        "--cd",
        str(temp_learning_dir.parent),
        "prepare lesson",
    ]
    assert captured["cwd"] == temp_learning_dir.parent
