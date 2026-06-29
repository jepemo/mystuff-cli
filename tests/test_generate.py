#!/usr/bin/env python3
"""Tests for the generate module."""

from pathlib import Path
from typing import Optional

import pytest
import yaml

from mystuff.commands.generate import (
    copy_static_files,
    ensure_output_structure,
    extract_lesson_title,
    generate_lesson_pages,
    generate_static_web,
    get_generate_config,
    group_tracks_by_classification,
    group_tracks_by_roadmap,
    load_active_learning_data,
    load_all_lessons_with_status,
    load_all_tracks_with_status,
    load_learning_data,
    render_template,
)
from mystuff.commands.learn import save_metadata


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
    roadmap: Optional[str] = None,
) -> None:
    track_dir = lessons_dir / track_id
    track_dir.mkdir(parents=True)

    track_frontmatter = {
        "track_id": track_id,
        "name": name,
        "description": description,
        "classification": classification,
        "roadmap": roadmap or classification,
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
def temp_mystuff_dir(tmp_path, monkeypatch):
    """Create a temporary mystuff directory for testing."""
    mystuff_dir = tmp_path / "mystuff"
    mystuff_dir.mkdir()
    monkeypatch.setenv("MYSTUFF_HOME", str(mystuff_dir))
    return mystuff_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    return tmp_path / "output"


@pytest.fixture
def sample_config(temp_mystuff_dir):
    config_path = temp_mystuff_dir / "config.yaml"
    config = {
        "generate": {
            "web": {
                "output": str(temp_mystuff_dir / "web"),
                "title": "Test Site",
                "description": "Test description",
                "author": "Test Author",
                "url": "https://example.com/site",
                "menu_items": [
                    {"name": "Home", "url": "/"},
                    {"name": "Docs", "url": "/docs"},
                ],
            }
        }
    }
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


@pytest.fixture
def sample_learning(temp_mystuff_dir):
    learning_dir = temp_mystuff_dir / "learning"
    lessons_dir = learning_dir / "lessons"
    lessons_dir.mkdir(parents=True)

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
                "body": "# Intro\n\n[Next](002.md)\n[External](https://example.com/doc.md)\n",
            },
            {
                "lesson_id": "101",
                "sequence": 2,
                "title": "Capstone Foundations",
                "difficulty": "intermediate",
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
        roadmap="distributed-systems",
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
        "private-api",
        name="Private API",
        description="Internal API draft.",
        classification="systems-thinking",
        roadmap="backend",
        depends_on_tracks=[],
        status="active",
        public=False,
        lessons=[
            {
                "lesson_id": "300",
                "sequence": 1,
                "title": "Private API Draft",
                "difficulty": "beginner",
                "legacy_day": 300,
                "legacy_path": "30/01.md",
            }
        ],
    )
    create_track(
        lessons_dir,
        "ai-lab",
        name="AI Lab",
        description="Draft work.",
        classification="complexity-and-dynamics",
        roadmap="ai-lab",
        depends_on_tracks=["systems"],
        status="draft",
        lessons=[],
    )

    return learning_dir


def test_get_generate_config_default(temp_mystuff_dir):
    config = get_generate_config()
    assert config["title"] == "My Knowledge Base"
    assert "output" in config


def test_get_generate_config_custom(sample_config):
    config = get_generate_config()
    assert config["title"] == "Test Site"
    assert config["author"] == "Test Author"


def test_ensure_output_structure(temp_output_dir):
    ensure_output_structure(temp_output_dir)
    assert (temp_output_dir / "css").exists()
    assert (temp_output_dir / "js").exists()


def test_copy_static_files_creates_structure(temp_output_dir, monkeypatch):
    ensure_output_structure(temp_output_dir)

    def mock_get_static_dir():
        return Path("/nonexistent/path")

    monkeypatch.setattr("mystuff.commands.generate.get_static_dir", mock_get_static_dir)

    copy_static_files(temp_output_dir)
    assert (temp_output_dir / "css").exists()


def test_render_template_basic(temp_output_dir, tmp_path, monkeypatch):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "test.html").write_text(
        "<html><body><h1>{{ title }}</h1></body></html>", encoding="utf-8"
    )

    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", lambda: templates_dir
    )

    output_path = temp_output_dir / "test.html"
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    render_template("test.html", {"title": "Hello"}, output_path)

    assert (
        output_path.read_text(encoding="utf-8")
        == "<html><body><h1>Hello</h1></body></html>"
    )


def test_load_learning_data_returns_current_public_lesson(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "last_opened_at": "2026-04-01T10:00:00",
            "completed_lessons": [],
        }
    )

    result = load_learning_data()

    assert result is not None
    assert result["track_id"] == "foundations"
    assert result["lesson_title"] == "Intro to Foundations"
    assert result["lesson_url"] == "lessons/foundations/001.html"
    assert result["classification_url"] == "classifications/systems-thinking.html"


def test_load_learning_data_ignores_private_current_lesson(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "201",
            "last_opened_at": "2026-04-01T10:00:00",
            "completed_lessons": [],
        }
    )

    result = load_learning_data()

    assert result is None


def test_load_active_learning_data_returns_open_public_lessons(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [
                {"lesson_id": "100", "completed_at": "2026-04-01T10:00:00"}
            ],
        }
    )

    result = load_active_learning_data()

    assert len(result) == 1
    assert result[0]["track_name"] == "Foundations"
    assert result[0]["track_description"] == "Core concepts."
    assert result[0]["lesson_title"] == "Capstone Foundations"
    assert result[0]["lesson_url"] == "lessons/foundations/002.html"
    assert result[0]["is_current"] is False


def test_load_active_learning_data_returns_started_tracks_without_completions(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "current_lesson_ids_by_track": {
                "foundations": "100",
                "systems": "200",
            },
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    result = load_active_learning_data()

    assert [(item["track_id"], item["current_lesson_id"]) for item in result] == [
        ("foundations", "100"),
        ("systems", "200"),
    ]


def test_load_active_learning_data_uses_track_cursor_over_legacy_global_cursor(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "current_lesson_ids_by_track": {"foundations": "101"},
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    result = load_active_learning_data()

    assert [
        (item["track_id"], item["current_lesson_id"], item["is_current"])
        for item in result
    ] == [("foundations", "101", True)]


def test_load_active_learning_data_includes_unpublished_started_track(
    sample_learning, sample_config
):
    track_path = sample_learning / "lessons" / "foundations" / "TRACK.md"
    track_path.write_text(
        track_path.read_text(encoding="utf-8").replace(
            "public: true", "public: false", 1
        ),
        encoding="utf-8",
    )
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "current_lesson_ids_by_track": {"foundations": "100"},
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    result = load_active_learning_data()

    assert len(result) == 1
    assert result[0]["track_id"] == "foundations"
    assert result[0]["lesson_title"] == "Intro to Foundations"
    assert result[0]["track_url"] is None
    assert result[0]["lesson_url"] is None


def test_load_all_tracks_with_status_includes_unpublished_tracks_without_links(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "101",
            "last_opened_at": None,
            "completed_lessons": [
                {"lesson_id": "100", "completed_at": "2026-04-01T10:00:00"}
            ],
        }
    )

    tracks = load_all_tracks_with_status()

    assert [track["track_id"] for track in tracks] == [
        "foundations",
        "systems",
        "private-api",
        "ai-lab",
    ]
    assert [lesson["lesson_id"] for lesson in tracks[1]["lessons"]] == ["200"]
    assert tracks[0]["completed_public_count"] == 1
    assert tracks[2]["track_url"] is None
    assert tracks[2]["is_published"] is False
    assert tracks[2]["public_progress_status"] == "unpublished"
    assert tracks[3]["public_progress_status"] == "draft"


def test_load_all_lessons_with_status_flattens_public_catalog(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "200",
            "last_opened_at": None,
            "completed_lessons": [
                {"lesson_id": "100", "completed_at": "2026-04-01T10:00:00"}
            ],
        }
    )

    lessons = load_all_lessons_with_status()

    assert [lesson["lesson_id"] for lesson in lessons] == ["100", "101", "200"]
    assert lessons[-1]["status"] == "current"


def test_group_tracks_by_classification_preserves_order(sample_learning, sample_config):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    classifications = group_tracks_by_classification(load_all_tracks_with_status())

    assert [item["classification_id"] for item in classifications] == [
        "systems-thinking",
        "complexity-and-dynamics",
    ]
    assert classifications[0]["track_count"] == 2
    assert [track["track_id"] for track in classifications[1]["tracks"]] == [
        "systems",
        "ai-lab",
    ]


def test_group_tracks_by_roadmap_preserves_order(sample_learning, sample_config):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    roadmaps = group_tracks_by_roadmap(load_all_tracks_with_status())

    assert [item["roadmap_id"] for item in roadmaps] == [
        "systems-thinking",
        "distributed-systems",
        "backend",
        "ai-lab",
    ]
    assert roadmaps[2]["tracks"][0]["track_id"] == "private-api"


def test_learning_template_includes_switchable_tracks_view(
    sample_learning, sample_config, temp_output_dir
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    tracks = load_all_tracks_with_status()
    classifications = group_tracks_by_classification(tracks)
    roadmaps = group_tracks_by_roadmap(tracks)
    active_learning = [
        {
            "track_name": "Foundations",
            "track_description": "Core concepts.",
            "track_url": "tracks/foundations.html",
            "lesson_title": "Capstone Foundations",
            "lesson_url": "lessons/foundations/002.html",
            "classification_name": "Systems Thinking",
            "classification_url": "classifications/systems-thinking.html",
        }
    ]
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template(
        "learning.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "learning": None,
            "active_learning": active_learning,
            "tracks": tracks,
            "classifications": classifications,
            "roadmaps": roadmaps,
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "learning.html",
    )

    html_content = (temp_output_dir / "learning.html").read_text(encoding="utf-8")

    assert "data-theme-toggle" in html_content
    assert 'data-learning-view-button="tracks"' in html_content
    assert 'data-learning-view="tracks"' in html_content
    assert 'data-learning-view-button="roadmaps"' in html_content
    assert 'data-learning-view="roadmaps"' in html_content
    assert 'class="current-learning-card"' in html_content
    assert 'href="tracks/foundations.html">Foundations' in html_content
    assert 'href="lessons/foundations/002.html">Capstone Foundations' in html_content
    assert "Open current lesson" in html_content
    assert "classifications/systems-thinking.html" in html_content
    assert (
        'classifications/systems-thinking.html">Systems Thinking</a>\n    /'
        not in html_content
    )
    assert "compact-track-group" not in html_content
    assert "compact-track-row" in html_content
    assert "Foundations" in html_content
    assert "Private API" in html_content
    assert "Systems Thinking" in html_content
    assert "Distributed Systems" in html_content
    assert "Core concepts." in html_content
    assert "lessons across this classification" not in html_content
    assert "lessons across this roadmap" not in html_content
    assert (
        'href="classifications/complexity-and-dynamics.html">Complexity And Dynamics'
        in html_content
    )
    tracks_view_start = html_content.index('data-learning-view="tracks"')
    assert html_content.index(
        'href="tracks/systems.html">Systems', tracks_view_start
    ) < html_content.index(
        'href="tracks/foundations.html">Foundations', tracks_view_start
    )
    assert 'href="tracks/private-api.html"' not in html_content
    assert 'href="roadmaps/backend.html">Backend' in html_content
    assert "Explore the curriculum by classification" not in html_content


def test_learning_template_lists_multiple_current_lessons(
    sample_learning, sample_config, temp_output_dir
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    tracks = load_all_tracks_with_status()
    classifications = group_tracks_by_classification(tracks)
    roadmaps = group_tracks_by_roadmap(tracks)
    active_learning = [
        {
            "track_name": "Foundations",
            "track_description": "Core concepts.",
            "track_url": "tracks/foundations.html",
            "lesson_title": "Capstone Foundations",
            "lesson_url": "lessons/foundations/002.html",
        },
        {
            "track_name": "Systems",
            "track_description": "Distributed systems.",
            "track_url": None,
            "lesson_title": "Distributed Reads",
            "lesson_url": None,
        },
    ]
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template(
        "learning.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "learning": None,
            "active_learning": active_learning,
            "tracks": tracks,
            "classifications": classifications,
            "roadmaps": roadmaps,
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "learning.html",
    )

    html_content = (temp_output_dir / "learning.html").read_text(encoding="utf-8")

    assert "current-learning-list-compact" in html_content
    assert "current-learning-card" not in html_content
    assert "Foundations" in html_content
    assert "Capstone Foundations" in html_content
    assert "Core concepts." in html_content
    assert "Systems" in html_content
    assert "Distributed Reads" in html_content
    assert "Distributed systems." in html_content
    assert "Open current lesson" not in html_content
    assert "Foundations</a>\n      /" not in html_content


def test_classification_template_uses_compact_track_list(
    sample_learning, sample_config, temp_output_dir
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    tracks = load_all_tracks_with_status()
    classification = group_tracks_by_classification(tracks)[0]
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template(
        "classification.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "classification": classification,
            "tracks": classification["tracks"],
            "relative_root": "../",
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "classification.html",
    )

    html_content = (temp_output_dir / "classification.html").read_text(
        encoding="utf-8"
    )

    assert 'class="compact-track-list"' in html_content
    assert 'class="compact-track-row"' in html_content
    assert "compact-track-row-minimal" not in html_content
    assert 'href="../tracks/foundations.html">Foundations' in html_content
    assert 'href="../classifications/systems-thinking.html"' in html_content
    assert "Core concepts." in html_content
    assert "Private API" in html_content
    assert 'href="../tracks/private-api.html"' not in html_content
    assert " tracks / " not in html_content
    assert " lessons" not in html_content
    assert " complete" not in html_content
    assert "Open track" not in html_content
    assert "status-badge" not in html_content
    assert 'class="track-row' not in html_content


def test_roadmap_template_uses_compact_track_list(
    sample_learning, sample_config, temp_output_dir
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    tracks = load_all_tracks_with_status()
    roadmap = group_tracks_by_roadmap(tracks)[1]
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template(
        "roadmap.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "roadmap": roadmap,
            "tracks": roadmap["tracks"],
            "relative_root": "../",
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "roadmap.html",
    )

    html_content = (temp_output_dir / "roadmap.html").read_text(encoding="utf-8")

    assert 'class="compact-track-list"' in html_content
    assert 'class="compact-track-row"' in html_content
    assert 'href="../tracks/systems.html">Systems' in html_content
    assert 'href="../classifications/complexity-and-dynamics.html"' in html_content
    assert "Distributed systems." in html_content
    assert " tracks / " not in html_content
    assert " lessons" not in html_content
    assert " complete" not in html_content
    assert "Open track" not in html_content
    assert "status-badge" not in html_content
    assert "track-row-" not in html_content


def test_index_template_omits_current_learning_card(
    temp_output_dir,
):
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    active_learning = [
        {
            "track_name": "Foundations",
            "track_url": "tracks/foundations.html",
            "lesson_title": "Capstone Foundations",
            "lesson_url": "lessons/foundations/002.html",
        },
        {
            "track_name": "Systems",
            "track_url": None,
            "lesson_title": "Distributed Reads",
            "lesson_url": None,
        },
    ]

    render_template(
        "index.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "learning": active_learning[0],
            "active_learning": active_learning,
            "classifications": [{"classification_id": "systems-thinking"}],
            "repositories": [
                {
                    "name": "mystuff-cli",
                    "description": "Personal CLI",
                    "url": "https://example.com/mystuff-cli",
                    "language": "Python",
                }
            ],
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "index.html",
    )

    html_content = (temp_output_dir / "index.html").read_text(encoding="utf-8")

    assert 'class="stack-block home-learning"' not in html_content
    assert "Current Learning" not in html_content
    assert "current-learning-list" not in html_content
    assert "Foundations" not in html_content
    assert "Capstone Foundations" not in html_content
    assert "Systems" not in html_content
    assert "Distributed Reads" not in html_content
    assert 'href="tracks/systems.html"' not in html_content
    assert 'href="lessons/systems/001.html"' not in html_content
    assert "CURRENT LEARNING" not in html_content
    assert "LEARNING HUB" not in html_content
    assert "OSS" not in html_content
    assert "Open Source" in html_content
    assert "All tracks" not in html_content
    assert "All learning" not in html_content
    assert "Continue from the current lesson" not in html_content
    assert "Last opened:" not in html_content


def test_track_template_omits_lesson_minutes(
    sample_learning, sample_config, temp_output_dir
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    track = load_all_tracks_with_status()[0]
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template(
        "track.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "track": track,
            "classification": {
                "classification_id": track["classification"],
                "classification_name": track["classification_name"],
                "url": f"../classifications/{track['classification']}.html",
            },
            "lessons": track["lessons"],
            "relative_root": "../",
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "track.html",
    )

    html_content = (temp_output_dir / "track.html").read_text(encoding="utf-8")

    assert "Intro to Foundations" in html_content
    assert "lesson-syllabus-meta" not in html_content
    assert "20 min" not in html_content


def test_lesson_template_uses_reading_layout_and_exit_link(
    sample_learning, sample_config, temp_output_dir
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )

    track = load_all_tracks_with_status()[0]
    lesson = track["lessons"][0]
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template(
        "lesson.html",
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
            "lesson": lesson,
            "track": track,
            "classification": {
                "classification_id": track["classification"],
                "classification_name": track["classification_name"],
            },
            "lesson_title": lesson["title"],
            "lesson_content": "<p>Lesson body.</p>",
            "prev_lesson": None,
            "next_lesson": {"url": "002.html", "title": "Next Lesson"},
            "track_page_url": "../tracks/foundations.html",
            "classification_page_url": "../classifications/systems-thinking.html",
            "relative_root": "../",
            "generated_at": "2026-04-02",
        },
        temp_output_dir / "lesson.html",
    )

    html_content = (temp_output_dir / "lesson.html").read_text(encoding="utf-8")

    assert '<body class="lesson-reading">' in html_content
    assert 'class="lesson-exit"' in html_content
    assert 'href="../tracks/foundations.html"' in html_content
    assert ">EXIT<" in html_content
    assert "data-read-mode-toggle" not in html_content
    assert "data-theme-toggle" in html_content
    assert 'class="stack-block lesson-content-shell"' in html_content
    assert 'class="lesson-navigation-grid lesson-page-nav"' in html_content
    assert "Back to Foundations" in html_content
    assert "Back to Systems Thinking" in html_content
    assert "Back to Learning Hub" in html_content

    css_content = (
        Path(__file__).resolve().parents[1] / "mystuff/static/css/style.css"
    ).read_text(encoding="utf-8")
    assert "body.lesson-reading .lesson-content-shell > h1:first-child" in css_content
    assert "data-read-mode" not in css_content

    script_content = (
        Path(__file__).resolve().parents[1] / "mystuff/static/js/site.js"
    ).read_text(encoding="utf-8")
    assert "mystuff-cli:read-mode" not in script_content
    assert "readModeToggle" not in script_content


def test_generate_lesson_pages_rewrites_internal_lesson_markdown_links(
    sample_learning, sample_config, temp_output_dir, tmp_path, monkeypatch
):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "lesson.html").write_text("{{ lesson_content }}", encoding="utf-8")

    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", lambda: templates_dir
    )

    temp_output_dir.mkdir()
    generate_lesson_pages(
        temp_output_dir,
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
        },
        "2026-04-02",
    )

    html_content = (temp_output_dir / "lessons" / "foundations" / "001.html").read_text(
        encoding="utf-8"
    )

    assert 'href="002.html"' in html_content
    assert 'href="https://example.com/doc.md"' in html_content


def test_generate_lesson_pages_renders_generated_quote_list(
    sample_learning, sample_config, temp_output_dir, tmp_path, monkeypatch
):
    lesson_path = sample_learning / "lessons" / "foundations" / "001.md"
    lesson_path.write_text(
        lesson_path.read_text(encoding="utf-8")
        + "\n> **By the end of this lesson, you will be able to:**\n"
        "> - identify the participants;\n"
        "> - explain the promise.\n",
        encoding="utf-8",
    )

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "lesson.html").write_text("{{ lesson_content }}", encoding="utf-8")
    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", lambda: templates_dir
    )

    temp_output_dir.mkdir()
    generate_lesson_pages(
        temp_output_dir,
        {
            "title": "Test Site",
            "description": "Test description",
            "author": "Test Author",
            "menu_items": [],
        },
        "2026-04-02",
    )

    html_content = (temp_output_dir / "lessons" / "foundations" / "001.html").read_text(
        encoding="utf-8"
    )
    assert "<blockquote>" in html_content
    assert "<ul>" in html_content
    assert "<li>" in html_content
    assert "identify the participants;" in html_content


def test_generate_static_web_creates_track_and_lesson_pages(
    sample_learning, sample_config, temp_output_dir, tmp_path, monkeypatch
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": "100",
            "last_opened_at": "2026-04-01T10:00:00",
            "completed_lessons": [],
        }
    )

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "index.html").write_text(
        "{{ learning.lesson_title if learning else 'none' }}", encoding="utf-8"
    )
    (templates_dir / "links.html").write_text("links", encoding="utf-8")
    (templates_dir / "learning.html").write_text(
        "{% for classification in classifications %}{{ classification.classification_id }}->{{ classification.url }} {% endfor %}",
        encoding="utf-8",
    )
    (templates_dir / "classification.html").write_text(
        "{{ classification.classification_name }} {% for track in tracks %}{{ track.track_id }} {% endfor %}",
        encoding="utf-8",
    )
    (templates_dir / "roadmap.html").write_text(
        "{{ roadmap.roadmap_name }} {% for track in tracks %}{{ track.track_id }} {% endfor %}",
        encoding="utf-8",
    )
    (templates_dir / "track.html").write_text(
        "{{ classification.url }} {{ track.track_id }} {{ track.name }}",
        encoding="utf-8",
    )
    (templates_dir / "lesson.html").write_text(
        "{{ classification_page_url }} {{ track.name }} {{ lesson.title }}",
        encoding="utf-8",
    )

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "css").mkdir()
    (static_dir / "css" / "style.css").write_text(
        "body { margin: 0; }", encoding="utf-8"
    )

    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", lambda: templates_dir
    )
    monkeypatch.setattr("mystuff.commands.generate.get_static_dir", lambda: static_dir)

    generate_static_web(temp_output_dir, get_generate_config())

    assert (temp_output_dir / "index.html").exists()
    assert (temp_output_dir / "learning.html").exists()
    assert (temp_output_dir / "classifications" / "systems-thinking.html").exists()
    assert (temp_output_dir / "roadmaps" / "systems-thinking.html").exists()
    assert (temp_output_dir / "tracks" / "foundations.html").exists()
    assert not (temp_output_dir / "tracks" / "private-api.html").exists()
    assert (temp_output_dir / "lessons" / "foundations" / "001.html").exists()
    assert not (temp_output_dir / "lessons" / "systems" / "002.html").exists()
    assert "systems-thinking->classifications/systems-thinking.html" in (
        temp_output_dir / "learning.html"
    ).read_text(encoding="utf-8")
    assert "Systems Thinking foundations" in (
        temp_output_dir / "classifications" / "systems-thinking.html"
    ).read_text(encoding="utf-8")
    assert "../classifications/systems-thinking.html foundations Foundations" in (
        temp_output_dir / "tracks" / "foundations.html"
    ).read_text(encoding="utf-8")
    assert (
        "../../classifications/systems-thinking.html Foundations Intro to Foundations"
        in (temp_output_dir / "lessons" / "foundations" / "001.html").read_text(
            encoding="utf-8"
        )
    )


def test_extract_lesson_title_full_format():
    content = """# Day 012: Adaptive Systems

# Topic: Resilience
"""
    assert extract_lesson_title(content) == "Day 012: Adaptive Systems (Resilience)"


def test_load_all_tracks_with_status_keeps_unpublished_track_unlinked(
    sample_learning, sample_config
):
    save_metadata(
        {
            "schema_version": 2,
            "current_lesson_id": None,
            "last_opened_at": None,
            "completed_lessons": [],
        }
    )
    track_path = sample_learning / "lessons" / "foundations" / "TRACK.md"
    track_path.write_text(
        track_path.read_text(encoding="utf-8").replace(
            "public: true", "public: false", 1
        ),
        encoding="utf-8",
    )

    tracks = load_all_tracks_with_status()

    foundations = next(track for track in tracks if track["track_id"] == "foundations")

    assert {track["track_id"] for track in tracks} >= {"foundations", "systems"}
    assert foundations["is_published"] is False
    assert foundations["track_url"] is None
    assert foundations["lessons"] == []
