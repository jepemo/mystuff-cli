"""
Test cases for the journal command functionality
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import typer

from mystuff.commands.journal import (
    filter_entries_by_date_range,
    get_all_journal_entries,
    get_journal_dir,
    get_journal_filename,
    get_mystuff_dir,
    load_journal_from_file,
    parse_date_range,
    save_journal_to_file,
    search_entries_by_text,
)


@pytest.fixture
def temp_mystuff_dir():
    """Create a temporary mystuff directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["MYSTUFF_HOME"] = temp_dir
        yield Path(temp_dir)
        # Clean up environment variable
        if "MYSTUFF_HOME" in os.environ:
            del os.environ["MYSTUFF_HOME"]


def test_get_mystuff_dir_with_env(temp_mystuff_dir):
    """Test getting mystuff directory from environment variable"""
    assert get_mystuff_dir().resolve() == temp_mystuff_dir.resolve()


def test_get_mystuff_dir_default():
    """Test getting default mystuff directory"""
    if "MYSTUFF_HOME" in os.environ:
        del os.environ["MYSTUFF_HOME"]
    expected = Path.home() / ".mystuff"
    assert get_mystuff_dir() == expected


def test_get_journal_dir(temp_mystuff_dir):
    """Test getting journal directory"""
    expected = temp_mystuff_dir / "journal"
    assert get_journal_dir().resolve() == expected.resolve()


def test_get_journal_filename():
    """Test generating journal filename"""
    date = "2023-10-05"
    expected = "2023-10-05.md"
    assert get_journal_filename(date) == expected


def test_save_and_load_journal_entry(temp_mystuff_dir):
    """Test saving and loading a journal entry"""
    # Create journal directory
    journal_dir = temp_mystuff_dir / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)

    # Test data
    date = "2023-10-05"
    tags = ["personal", "reflection"]
    body = "Today was a good day. I learned a lot about Python."

    # Create file path
    file_path = journal_dir / "2023-10-05.md"

    # Save journal entry
    save_journal_to_file(file_path, date, tags, body)

    # Check file exists
    assert file_path.exists()

    # Load journal entry
    loaded_entry = load_journal_from_file(file_path)

    # Verify content
    assert loaded_entry["date"] == date
    assert loaded_entry["tags"] == tags
    assert loaded_entry["body"] == body
    assert loaded_entry["file_path"] == file_path


def test_load_journal_without_frontmatter(temp_mystuff_dir):
    """Test loading a journal entry without YAML front-matter"""
    # Create journal directory
    journal_dir = temp_mystuff_dir / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)

    # Create file without front-matter
    file_path = journal_dir / "2023-10-05.md"
    body = "This is a simple journal entry without front-matter."

    with open(file_path, "w") as f:
        f.write(body)

    # Load journal entry
    loaded_entry = load_journal_from_file(file_path)

    # Verify content
    assert loaded_entry["date"] == "2023-10-05"  # From filename
    assert loaded_entry["tags"] == []
    assert loaded_entry["body"] == body
    assert loaded_entry["file_path"] == file_path


def test_get_all_journal_entries(temp_mystuff_dir):
    """Test getting all journal entries"""
    # Create journal directory
    journal_dir = temp_mystuff_dir / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)

    # Create test entries
    entries_data = [
        ("2023-10-01", ["work"], "First entry"),
        ("2023-10-02", ["personal"], "Second entry"),
        ("2023-10-03", ["learning"], "Third entry"),
    ]

    for date, tags, body in entries_data:
        file_path = journal_dir / f"{date}.md"
        save_journal_to_file(file_path, date, tags, body)

    # Get all entries
    all_entries = get_all_journal_entries()

    # Check count
    assert len(all_entries) == 3

    # Check sorting (newest first)
    dates = [entry["date"] for entry in all_entries]
    assert dates == ["2023-10-03", "2023-10-02", "2023-10-01"]


def test_get_all_journal_entries_empty_dir(temp_mystuff_dir):
    """Test getting all journal entries from empty directory"""
    # Don't create journal directory
    entries = get_all_journal_entries()
    assert entries == []


def test_parse_date_range():
    """Test parsing date range strings"""
    # Single date
    start, end = parse_date_range("2023-10-05")
    assert start == "2023-10-05"
    assert end == "2023-10-05"

    # Date range
    start, end = parse_date_range("2023-10-01:2023-10-05")
    assert start == "2023-10-01"
    assert end == "2023-10-05"


def test_parse_date_range_invalid():
    """Test parsing invalid date range"""
    with pytest.raises(typer.Exit):
        parse_date_range("invalid-date")


def test_filter_entries_by_date_range():
    """Test filtering entries by date range"""
    # Create test entries
    entries = [
        {"date": "2023-10-01", "body": "First entry"},
        {"date": "2023-10-02", "body": "Second entry"},
        {"date": "2023-10-03", "body": "Third entry"},
        {"date": "2023-10-04", "body": "Fourth entry"},
        {"date": "2023-10-05", "body": "Fifth entry"},
    ]

    # Filter by range
    filtered = filter_entries_by_date_range(entries, "2023-10-02", "2023-10-04")

    # Check results
    assert len(filtered) == 3
    dates = [entry["date"] for entry in filtered]
    assert dates == ["2023-10-02", "2023-10-03", "2023-10-04"]


def test_search_entries_by_text():
    """Test searching entries by text content"""
    # Create test entries
    entries = [
        {
            "date": "2023-10-01",
            "body": "Today I learned Python programming",
            "tags": ["learning"],
        },
        {
            "date": "2023-10-02",
            "body": "Had a great meeting with the team",
            "tags": ["work"],
        },
        {
            "date": "2023-10-03",
            "body": "Spent time reading about JavaScript",
            "tags": ["learning", "javascript"],
        },
        {
            "date": "2023-10-04",
            "body": "Relaxing day with family",
            "tags": ["personal"],
        },
    ]

    # Search by body content
    results = search_entries_by_text(entries, "Python")
    assert len(results) == 1
    assert results[0]["date"] == "2023-10-01"

    # Search by tag
    results = search_entries_by_text(entries, "learning")
    assert len(results) == 2
    dates = [entry["date"] for entry in results]
    assert "2023-10-01" in dates
    assert "2023-10-03" in dates

    # Search case insensitive
    results = search_entries_by_text(entries, "TEAM")
    assert len(results) == 1
    assert results[0]["date"] == "2023-10-02"

    # Search with no matches
    results = search_entries_by_text(entries, "nonexistent")
    assert len(results) == 0


def test_journal_filename_validation():
    """Test that journal filenames are valid"""
    # Valid date
    filename = get_journal_filename("2023-10-05")
    assert filename == "2023-10-05.md"

    # Test with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    filename = get_journal_filename(today)
    assert filename == f"{today}.md"
