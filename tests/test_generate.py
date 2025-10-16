#!/usr/bin/env python3
"""Tests for the generate module"""

import os
from pathlib import Path

import pytest
import yaml

from mystuff.commands.generate import (
    copy_static_files,
    ensure_output_structure,
    extract_lesson_title,
    generate_static_web,
    get_generate_config,
    load_learning_data,
    render_template,
)


@pytest.fixture
def temp_mystuff_dir(tmp_path, monkeypatch):
    """Create a temporary mystuff directory for testing."""
    mystuff_dir = tmp_path / "mystuff"
    mystuff_dir.mkdir()

    # Set MYSTUFF_HOME to temp directory
    monkeypatch.setenv("MYSTUFF_HOME", str(mystuff_dir))

    return mystuff_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory for testing."""
    output_dir = tmp_path / "output"
    return output_dir


@pytest.fixture
def sample_config(temp_mystuff_dir):
    """Create a sample config file."""
    config_path = temp_mystuff_dir / "config.yaml"

    config = {
        "generate": {
            "web": {
                "output": str(temp_mystuff_dir / "web"),
                "title": "Test Site",
                "description": "Test description",
                "author": "Test Author",
                "menu_items": [
                    {"name": "Home", "url": "/"},
                    {"name": "About", "url": "/about"},
                    {"name": "GitHub", "url": "https://github.com/test"},
                ],
            }
        }
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


def test_get_generate_config_default(temp_mystuff_dir):
    """Test getting default generate config when no config exists."""
    config = get_generate_config()

    assert "output" in config
    assert "title" in config
    assert "description" in config
    assert "author" in config
    assert "menu_items" in config
    assert config["title"] == "My Knowledge Base"


def test_get_generate_config_custom(sample_config):
    """Test getting custom generate config from config file."""
    config = get_generate_config()

    assert config["title"] == "Test Site"
    assert config["description"] == "Test description"
    assert config["author"] == "Test Author"
    assert len(config["menu_items"]) == 3


def test_ensure_output_structure(temp_output_dir):
    """Test creating output directory structure."""
    ensure_output_structure(temp_output_dir)

    assert temp_output_dir.exists()
    assert (temp_output_dir / "css").exists()
    assert (temp_output_dir / "js").exists()


def test_ensure_output_structure_existing(temp_output_dir):
    """Test that ensure_output_structure works with existing directory."""
    # Create directory first
    temp_output_dir.mkdir()
    (temp_output_dir / "css").mkdir()

    # Should not raise error
    ensure_output_structure(temp_output_dir)

    assert temp_output_dir.exists()
    assert (temp_output_dir / "css").exists()


def test_copy_static_files_creates_structure(temp_output_dir, monkeypatch):
    """Test that copy_static_files handles missing static dir gracefully."""
    ensure_output_structure(temp_output_dir)

    # Mock get_static_dir to return non-existent path
    def mock_get_static_dir():
        return Path("/nonexistent/path")

    monkeypatch.setattr(
        "mystuff.commands.generate.get_static_dir", mock_get_static_dir
    )

    # Should not raise error, just skip copying
    copy_static_files(temp_output_dir)

    assert (temp_output_dir / "css").exists()
    assert (temp_output_dir / "js").exists()


def test_render_template_basic(temp_output_dir, tmp_path, monkeypatch):
    """Test basic template rendering."""
    # Create a simple template
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    template_content = """<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body><h1>{{ title }}</h1></body>
</html>"""

    (templates_dir / "test.html").write_text(template_content)

    # Mock get_templates_dir
    def mock_get_templates_dir():
        return templates_dir

    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", mock_get_templates_dir
    )

    # Render template
    context = {"title": "Test Page"}
    output_path = temp_output_dir / "test.html"
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template("test.html", context, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "Test Page" in content
    assert "<h1>Test Page</h1>" in content


def test_render_template_with_menu_items(temp_output_dir, tmp_path, monkeypatch):
    """Test template rendering with menu items."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    template_content = """<ul>
{% for item in menu_items %}
<li><a href="{{ item.url }}">{{ item.name }}</a></li>
{% endfor %}
</ul>"""

    (templates_dir / "menu.html").write_text(template_content)

    def mock_get_templates_dir():
        return templates_dir

    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", mock_get_templates_dir
    )

    context = {
        "menu_items": [
            {"name": "Home", "url": "/"},
            {"name": "About", "url": "/about"},
        ]
    }
    output_path = temp_output_dir / "menu.html"
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    render_template("menu.html", context, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "Home" in content
    assert "About" in content
    assert 'href="/"' in content
    assert 'href="/about"' in content


def test_generate_static_web_creates_files(
    temp_output_dir, sample_config, tmp_path, monkeypatch
):
    """Test that generate_static_web creates all necessary files."""
    # Create mock templates
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    (templates_dir / "index.html").write_text(
        "<html><head><title>{{ title }}</title></head></html>"
    )

    # Create mock static dir
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "css").mkdir()
    (static_dir / "css" / "style.css").write_text("body { margin: 0; }")

    def mock_get_templates_dir():
        return templates_dir

    def mock_get_static_dir():
        return static_dir

    monkeypatch.setattr(
        "mystuff.commands.generate.get_templates_dir", mock_get_templates_dir
    )
    monkeypatch.setattr(
        "mystuff.commands.generate.get_static_dir", mock_get_static_dir
    )

    config = get_generate_config()
    generate_static_web(temp_output_dir, config)

    # Check structure
    assert (temp_output_dir / "css").exists()
    assert (temp_output_dir / "js").exists()
    assert (temp_output_dir / "index.html").exists()

    # Check CSS was copied
    assert (temp_output_dir / "css" / "style.css").exists()

    # Check index.html content
    index_content = (temp_output_dir / "index.html").read_text()
    assert config["title"] in index_content


def test_config_merge_with_defaults(temp_mystuff_dir):
    """Test that partial config merges with defaults."""
    config_path = temp_mystuff_dir / "config.yaml"

    # Only set title
    config = {"generate": {"web": {"title": "Custom Title"}}}

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    result = get_generate_config()

    # Custom value
    assert result["title"] == "Custom Title"

    # Default values still present
    assert "output" in result
    assert "description" in result
    assert "author" in result
    assert "menu_items" in result


def test_output_directory_expansion(temp_output_dir):
    """Test that output paths with ~ are expanded."""
    # This is more of an integration test, but we can test the logic
    path_with_tilde = Path("~/test_output")
    expanded = path_with_tilde.expanduser()

    assert str(expanded) != str(path_with_tilde)
    assert "~" not in str(expanded)


def test_load_learning_data_no_metadata(temp_mystuff_dir):
    """Test load_learning_data when no metadata file exists."""
    result = load_learning_data()
    assert result is None


def test_load_learning_data_no_current_lesson(temp_mystuff_dir):
    """Test load_learning_data when metadata exists but no current lesson."""
    learning_dir = temp_mystuff_dir / "learning"
    learning_dir.mkdir()
    
    metadata_path = learning_dir / "metadata.yaml"
    metadata = {
        "current_lesson": None,
        "last_opened": None,
        "completed_lessons": []
    }
    
    with open(metadata_path, "w") as f:
        yaml.dump(metadata, f)
    
    result = load_learning_data()
    assert result is None


def test_load_learning_data_with_current_lesson(temp_mystuff_dir):
    """Test load_learning_data when current lesson exists with Day/Topic format."""
    learning_dir = temp_mystuff_dir / "learning"
    learning_dir.mkdir()
    lessons_dir = learning_dir / "lessons"
    lessons_dir.mkdir()
    
    # Create a lesson file with Day/Topic format
    lesson_file = lessons_dir / "01-introduction.md"
    lesson_file.write_text("""# Day 001: Getting Started with Python

# Topic: Python Basics

This is the introduction.""")
    
    metadata_path = learning_dir / "metadata.yaml"
    metadata = {
        "current_lesson": "01-introduction.md",
        "last_opened": "2025-10-14T10:00:00",
        "completed_lessons": []
    }
    
    with open(metadata_path, "w") as f:
        yaml.dump(metadata, f)
    
    result = load_learning_data()
    
    assert result is not None
    assert result["current_lesson"] == "01-introduction.md"
    assert result["title"] == "Day 001: Getting Started with Python (Python Basics)"
    assert result["last_opened"] == "2025-10-14T10:00:00"


def test_load_learning_data_nested_lesson(temp_mystuff_dir):
    """Test load_learning_data with nested lesson path."""
    learning_dir = temp_mystuff_dir / "learning"
    learning_dir.mkdir()
    lessons_dir = learning_dir / "lessons"
    lessons_dir.mkdir()
    
    # Create nested directory structure
    python_dir = lessons_dir / "python"
    python_dir.mkdir()
    
    # Create a lesson file with Day/Topic format
    lesson_file = python_dir / "02-functions.md"
    lesson_file.write_text("""# Day 042: Advanced Functions in Python

# Topic: Lambda and Closures

Learn about lambda, closures, and decorators.""")
    
    metadata_path = learning_dir / "metadata.yaml"
    metadata = {
        "current_lesson": "python/02-functions.md",
        "last_opened": "2025-10-14T10:00:00",
        "completed_lessons": []
    }
    
    with open(metadata_path, "w") as f:
        yaml.dump(metadata, f)
    
    result = load_learning_data()
    
    assert result is not None
    assert result["current_lesson"] == "python/02-functions.md"
    assert result["title"] == "Day 042: Advanced Functions in Python (Lambda and Closures)"


def test_load_learning_data_fallback_to_filename(temp_mystuff_dir):
    """Test load_learning_data falls back to filename when file doesn't exist or has no heading."""
    learning_dir = temp_mystuff_dir / "learning"
    learning_dir.mkdir()
    
    metadata_path = learning_dir / "metadata.yaml"
    metadata = {
        "current_lesson": "01-introduction.md",
        "last_opened": "2025-10-14T10:00:00",
        "completed_lessons": []
    }
    
    with open(metadata_path, "w") as f:
        yaml.dump(metadata, f)
    
    result = load_learning_data()
    
    assert result is not None
    assert result["current_lesson"] == "01-introduction.md"
    # Should fall back to filename-based title
    assert result["title"] == "Introduction"


def test_extract_lesson_title_full_format():
    """Test extract_lesson_title with full Day + Topic format."""
    content = """# Day 012: Adaptive Systems and Self-Organization

# Topic: Adaptive systems

This is the content of the lesson.
"""
    result = extract_lesson_title(content)
    assert result == "Day 012: Adaptive Systems and Self-Organization (Adaptive systems)"


def test_extract_lesson_title_only_day():
    """Test extract_lesson_title with only Day format."""
    content = """# Day 005: Introduction to Python

This is the content without a topic.
"""
    result = extract_lesson_title(content)
    assert result == "Day 005: Introduction to Python"


def test_extract_lesson_title_only_topic():
    """Test extract_lesson_title with only Topic format."""
    content = """# Topic: Machine Learning Basics

This is the content without a day.
"""
    result = extract_lesson_title(content)
    assert result == "Machine Learning Basics"


def test_extract_lesson_title_case_insensitive():
    """Test extract_lesson_title is case-insensitive."""
    content = """# day 001: Testing Case Sensitivity

# topic: Test Topic

Content here.
"""
    result = extract_lesson_title(content)
    assert result == "Day 001: Testing Case Sensitivity (Test Topic)"


def test_extract_lesson_title_with_extra_spaces():
    """Test extract_lesson_title handles extra spaces."""
    content = """#   Day   123:   Title With Spaces   

#   Topic:   Topic With Spaces   

Content here.
"""
    result = extract_lesson_title(content)
    assert result == "Day 123: Title With Spaces (Topic With Spaces)"


def test_extract_lesson_title_no_match():
    """Test extract_lesson_title returns None when format doesn't match."""
    content = """# Just a Regular Title

This doesn't match the expected format.
"""
    result = extract_lesson_title(content)
    assert result is None


def test_extract_lesson_title_empty_content():
    """Test extract_lesson_title with empty content."""
    result = extract_lesson_title("")
    assert result is None
