#!/usr/bin/env python3
"""Tests for the learn module"""

import datetime
import os
from pathlib import Path

import pytest
import yaml

from mystuff.commands.learn import (
    get_all_lessons,
    get_learning_dir,
    get_lessons_dir,
    get_metadata_path,
    get_next_lesson,
    load_metadata,
    save_metadata,
)


@pytest.fixture
def temp_learning_dir(tmp_path, monkeypatch):
    """Create a temporary learning directory for testing."""
    learning_dir = tmp_path / "learning"
    lessons_dir = learning_dir / "lessons"
    lessons_dir.mkdir(parents=True)

    # Set MYSTUFF_HOME to temp directory
    monkeypatch.setenv("MYSTUFF_HOME", str(tmp_path))

    return learning_dir


@pytest.fixture
def sample_lessons(temp_learning_dir):
    """Create sample lesson files."""
    lessons_dir = temp_learning_dir / "lessons"

    # Create flat lessons
    (lessons_dir / "01-intro.md").write_text("# Introduction")
    (lessons_dir / "02-basics.md").write_text("# Basics")

    # Create nested lessons
    python_dir = lessons_dir / "python"
    python_dir.mkdir()
    (python_dir / "01-variables.md").write_text("# Variables")
    (python_dir / "02-functions.md").write_text("# Functions")

    git_dir = lessons_dir / "git"
    git_dir.mkdir()
    (git_dir / "01-basics.md").write_text("# Git Basics")

    return lessons_dir


def test_get_learning_dir(temp_learning_dir):
    """Test getting the learning directory."""
    learning_dir = get_learning_dir()
    assert learning_dir.exists()
    assert learning_dir.name == "learning"


def test_get_lessons_dir(temp_learning_dir):
    """Test getting the lessons directory."""
    lessons_dir = get_lessons_dir()
    assert lessons_dir.exists()
    assert lessons_dir.name == "lessons"


def test_get_metadata_path(temp_learning_dir):
    """Test getting the metadata file path."""
    metadata_path = get_metadata_path()
    assert metadata_path.parent == temp_learning_dir
    assert metadata_path.name == "metadata.yaml"


def test_load_metadata_creates_file_if_not_exists(temp_learning_dir):
    """Test that load_metadata creates the file if it doesn't exist."""
    metadata_path = get_metadata_path()
    assert not metadata_path.exists()

    metadata = load_metadata()

    assert metadata_path.exists()
    assert metadata["current_lesson"] is None
    assert metadata["last_opened"] is None
    assert metadata["completed_lessons"] == []


def test_load_metadata_with_existing_file(temp_learning_dir):
    """Test loading metadata from existing file."""
    metadata_path = get_metadata_path()

    # Create a metadata file
    test_metadata = {
        "current_lesson": "01-intro.md",
        "last_opened": "2025-10-01T12:00:00",
        "completed_lessons": [
            {"name": "00-setup.md", "completed_at": "2025-09-30T10:00:00"}
        ],
    }

    with open(metadata_path, "w") as f:
        yaml.dump(test_metadata, f)

    # Load it
    metadata = load_metadata()

    assert metadata["current_lesson"] == "01-intro.md"
    assert metadata["last_opened"] == "2025-10-01T12:00:00"
    assert len(metadata["completed_lessons"]) == 1
    assert metadata["completed_lessons"][0]["name"] == "00-setup.md"


def test_save_metadata(temp_learning_dir):
    """Test saving metadata."""
    metadata = {
        "current_lesson": "02-basics.md",
        "last_opened": datetime.datetime.now().isoformat(),
        "completed_lessons": [
            {"name": "01-intro.md", "completed_at": "2025-10-01T12:00:00"}
        ],
    }

    save_metadata(metadata)

    metadata_path = get_metadata_path()
    assert metadata_path.exists()

    # Load and verify
    with open(metadata_path, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["current_lesson"] == "02-basics.md"
    assert len(loaded["completed_lessons"]) == 1


def test_get_all_lessons_flat(sample_lessons):
    """Test getting all lessons with flat structure."""
    lessons = get_all_lessons(recursive=False)

    # Should only get top-level lessons
    assert len(lessons) == 2
    assert any(l["name"] == "01-intro.md" for l in lessons)
    assert any(l["name"] == "02-basics.md" for l in lessons)


def test_get_all_lessons_recursive(sample_lessons):
    """Test getting all lessons recursively."""
    lessons = get_all_lessons(recursive=True)

    # Should get all lessons including nested ones
    # 2 top-level + 2 in python/ + 1 in git/ = 5 total
    assert len(lessons) == 5

    # Check some specific lessons
    lesson_names = [l["name"] for l in lessons]
    assert "01-intro.md" in lesson_names
    assert "python/01-variables.md" in lesson_names
    assert "git/01-basics.md" in lesson_names


def test_get_all_lessons_sorted(sample_lessons):
    """Test that lessons are returned in sorted order."""
    lessons = get_all_lessons(recursive=True)

    lesson_names = [l["name"] for l in lessons]

    # Should be sorted alphabetically
    assert lesson_names == sorted(lesson_names)


def test_get_all_lessons_empty_directory(temp_learning_dir):
    """Test getting lessons from empty directory."""
    lessons = get_all_lessons()

    assert lessons == []


def test_get_next_lesson(sample_lessons, temp_learning_dir):
    """Test getting the next uncompleted lesson."""
    metadata = {
        "current_lesson": "01-intro.md",
        "completed_lessons": [
            {"name": "01-intro.md", "completed_at": "2025-10-01T12:00:00"}
        ],
    }

    next_lesson = get_next_lesson("01-intro.md", metadata)

    # Should get the next lesson in alphabetical order
    assert next_lesson == "02-basics.md"


def test_get_next_lesson_skip_completed(sample_lessons, temp_learning_dir):
    """Test that get_next_lesson skips completed lessons."""
    metadata = {
        "current_lesson": "01-intro.md",
        "completed_lessons": [
            {"name": "01-intro.md", "completed_at": "2025-10-01T12:00:00"},
            {"name": "02-basics.md", "completed_at": "2025-10-02T12:00:00"},
        ],
    }

    next_lesson = get_next_lesson("01-intro.md", metadata)

    # Should skip 02-basics.md and get git/01-basics.md
    assert next_lesson == "git/01-basics.md"


def test_get_next_lesson_wrap_around(sample_lessons, temp_learning_dir):
    """Test that get_next_lesson wraps around to the beginning."""
    # All lessons except first are completed
    metadata = {
        "current_lesson": "python/02-functions.md",
        "completed_lessons": [
            {"name": "02-basics.md", "completed_at": "2025-10-01T12:00:00"},
            {"name": "git/01-basics.md", "completed_at": "2025-10-02T12:00:00"},
            {"name": "python/01-variables.md", "completed_at": "2025-10-03T12:00:00"},
            {"name": "python/02-functions.md", "completed_at": "2025-10-04T12:00:00"},
        ],
    }

    next_lesson = get_next_lesson("python/02-functions.md", metadata)

    # Should wrap around to the first uncompleted lesson
    assert next_lesson == "01-intro.md"


def test_get_next_lesson_all_completed(sample_lessons, temp_learning_dir):
    """Test get_next_lesson when all lessons are completed."""
    all_lessons = get_all_lessons()
    completed = [
        {"name": lesson["name"], "completed_at": "2025-10-01T12:00:00"}
        for lesson in all_lessons
    ]

    metadata = {"current_lesson": "01-intro.md", "completed_lessons": completed}

    next_lesson = get_next_lesson("01-intro.md", metadata)

    # Should return None when all lessons are completed
    assert next_lesson is None


def test_metadata_persists_across_loads(temp_learning_dir):
    """Test that metadata persists across multiple load/save cycles."""
    # Save metadata
    metadata1 = {
        "current_lesson": "test.md",
        "last_opened": "2025-10-01T12:00:00",
        "completed_lessons": [
            {"name": "intro.md", "completed_at": "2025-09-30T10:00:00"}
        ],
    }
    save_metadata(metadata1)

    # Load it
    metadata2 = load_metadata()

    assert metadata2["current_lesson"] == "test.md"
    assert len(metadata2["completed_lessons"]) == 1

    # Modify and save again
    metadata2["completed_lessons"].append(
        {"name": "test.md", "completed_at": "2025-10-01T12:00:00"}
    )
    save_metadata(metadata2)

    # Load again
    metadata3 = load_metadata()

    assert len(metadata3["completed_lessons"]) == 2


def test_lesson_paths_are_relative(sample_lessons):
    """Test that lesson names are relative paths."""
    lessons = get_all_lessons(recursive=True)

    for lesson in lessons:
        # Names should be relative, not absolute
        assert not lesson["name"].startswith("/")

        # Paths should be absolute
        assert lesson["path"].startswith("/") or lesson["path"].startswith(
            str(sample_lessons)
        )


def test_nested_directory_structure(temp_learning_dir):
    """Test handling of deeply nested directory structures."""
    lessons_dir = get_lessons_dir()

    # Create deeply nested structure
    deep_dir = lessons_dir / "level1" / "level2" / "level3"
    deep_dir.mkdir(parents=True)
    (deep_dir / "deep-lesson.md").write_text("# Deep Lesson")

    lessons = get_all_lessons(recursive=True)

    assert len(lessons) == 1
    assert lessons[0]["name"] == "level1/level2/level3/deep-lesson.md"
