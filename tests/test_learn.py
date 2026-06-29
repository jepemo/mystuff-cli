#!/usr/bin/env python3
"""Tests for the track-aware learn module."""

import datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

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
    second = runner.invoke(app, ["learn", "start", "databases"], input="n\n")

    assert first.exit_code == 0
    assert second.exit_code == 0
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "300"
    assert metadata["current_lesson_ids_by_track"] == {
        "foundations": "100",
        "databases": "300",
    }


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

    result = runner.invoke(app, ["learn", "start", "foundations"], input="n\n")

    assert result.exit_code == 0
    metadata = load_metadata()
    assert metadata["current_lesson_id"] == "100"
    assert metadata["current_lesson_ids_by_track"] == {
        "databases": "300",
        "foundations": "100",
    }


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


def test_start_rejects_unpublished_lesson(temp_learning_dir):
    lesson_path = temp_learning_dir / "lessons" / "foundations" / "002.md"
    lesson_path.write_text(
        lesson_path.read_text(encoding="utf-8").replace(
            "public: true", "public: false", 1
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "start", "foundations/002"])

    assert result.exit_code == 1
    assert "not published" in result.output
    assert load_metadata()["current_lesson_id"] is None


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
    assert "Private API" not in result.output
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


def test_unpublish_lesson_updates_public_frontmatter(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "unpublish", "foundations/001"])

    assert result.exit_code == 0
    lesson_path = temp_learning_dir / "lessons" / "foundations" / "001.md"
    assert "public: false" in lesson_path.read_text(encoding="utf-8")


def test_publish_track_updates_public_frontmatter(temp_learning_dir):
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "publish", "systems"])

    assert result.exit_code == 0
    track_path = temp_learning_dir / "lessons" / "systems" / "TRACK.md"
    assert "public: true" in track_path.read_text(encoding="utf-8")


def test_review_next_finds_pending_lesson(temp_learning_dir):
    lesson_path = temp_learning_dir / "lessons" / "systems" / "001.md"
    lesson_path.write_text(
        lesson_path.read_text(encoding="utf-8").replace(
            "review_status: reviewed", "review_status: pending"
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["learn", "review-next"])

    assert result.exit_code == 0
    assert "systems/001" in result.output
    assert "Distributed Reads" in result.output
