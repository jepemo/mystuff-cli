#!/usr/bin/env python3

import os
import tempfile
from datetime import datetime
from pathlib import Path


def test_journal_add_basic():
    """Test basic journal entry addition"""
    from mystuff.commands.journal import load_journal_from_file, save_journal_to_file

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir

        # Create journal directory
        journal_dir = Path(temp_dir) / "journal"
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
        assert file_path.exists(), "Journal file should exist"

        # Load journal entry
        loaded_entry = load_journal_from_file(file_path)

        # Verify content
        assert (
            loaded_entry["date"] == date
        ), f"Expected date {date}, got {loaded_entry['date']}"
        assert (
            loaded_entry["tags"] == tags
        ), f"Expected tags {tags}, got {loaded_entry['tags']}"
        assert (
            loaded_entry["body"] == body
        ), f"Expected body {body}, got {loaded_entry['body']}"
        assert (
            loaded_entry["file_path"] == file_path
        ), f"Expected file_path {file_path}, got {loaded_entry['file_path']}"

        print("✅ test_journal_add_basic passed!")


def test_journal_add_default_date():
    """Test journal entry with default date"""
    from mystuff.commands.journal import get_journal_filename

    # Test with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    filename = get_journal_filename(today)
    expected = f"{today}.md"

    assert filename == expected, f"Expected filename {expected}, got {filename}"

    print("✅ test_journal_add_default_date passed!")


def test_journal_load_without_frontmatter():
    """Test loading journal entry without YAML front-matter"""
    from mystuff.commands.journal import load_journal_from_file

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir

        # Create journal directory
        journal_dir = Path(temp_dir) / "journal"
        journal_dir.mkdir(parents=True, exist_ok=True)

        # Create file without front-matter
        file_path = journal_dir / "2023-10-05.md"
        body = "This is a simple journal entry without front-matter."

        with open(file_path, "w") as f:
            f.write(body)

        # Load journal entry
        loaded_entry = load_journal_from_file(file_path)

        # Verify content
        assert (
            loaded_entry["date"] == "2023-10-05"
        ), f"Expected date 2023-10-05, got {loaded_entry['date']}"
        assert (
            loaded_entry["tags"] == []
        ), f"Expected empty tags, got {loaded_entry['tags']}"
        assert (
            loaded_entry["body"] == body
        ), f"Expected body {body}, got {loaded_entry['body']}"
        assert (
            loaded_entry["file_path"] == file_path
        ), f"Expected file_path {file_path}, got {loaded_entry['file_path']}"

        print("✅ test_journal_load_without_frontmatter passed!")


def test_journal_get_all_entries():
    """Test getting all journal entries"""
    from mystuff.commands.journal import get_all_journal_entries, save_journal_to_file

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir

        # Create journal directory
        journal_dir = Path(temp_dir) / "journal"
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
        assert len(all_entries) == 3, f"Expected 3 entries, got {len(all_entries)}"

        # Check sorting (newest first)
        dates = [entry["date"] for entry in all_entries]
        expected_dates = ["2023-10-03", "2023-10-02", "2023-10-01"]
        assert dates == expected_dates, f"Expected dates {expected_dates}, got {dates}"

        print("✅ test_journal_get_all_entries passed!")


def test_journal_search():
    """Test searching journal entries"""
    from mystuff.commands.journal import search_entries_by_text

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir

        # Create journal directory
        journal_dir = Path(temp_dir) / "journal"
        journal_dir.mkdir(parents=True, exist_ok=True)

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
        assert len(results) == 1, f"Expected 1 result for 'Python', got {len(results)}"
        assert (
            results[0]["date"] == "2023-10-01"
        ), f"Expected date 2023-10-01, got {results[0]['date']}"

        # Search by tag
        results = search_entries_by_text(entries, "learning")
        assert (
            len(results) == 2
        ), f"Expected 2 results for 'learning', got {len(results)}"
        dates = [entry["date"] for entry in results]
        assert "2023-10-01" in dates, "Expected 2023-10-01 in results"
        assert "2023-10-03" in dates, "Expected 2023-10-03 in results"

        # Search case insensitive
        results = search_entries_by_text(entries, "TEAM")
        assert len(results) == 1, f"Expected 1 result for 'TEAM', got {len(results)}"
        assert (
            results[0]["date"] == "2023-10-02"
        ), f"Expected date 2023-10-02, got {results[0]['date']}"

        # Search with no matches
        results = search_entries_by_text(entries, "nonexistent")
        assert (
            len(results) == 0
        ), f"Expected 0 results for 'nonexistent', got {len(results)}"

        print("✅ test_journal_search passed!")


def test_journal_date_range():
    """Test date range filtering"""
    from mystuff.commands.journal import filter_entries_by_date_range, parse_date_range

    # Test single date
    start, end = parse_date_range("2023-10-05")
    assert start == "2023-10-05", f"Expected start date 2023-10-05, got {start}"
    assert end == "2023-10-05", f"Expected end date 2023-10-05, got {end}"

    # Test date range
    start, end = parse_date_range("2023-10-01:2023-10-05")
    assert start == "2023-10-01", f"Expected start date 2023-10-01, got {start}"
    assert end == "2023-10-05", f"Expected end date 2023-10-05, got {end}"

    # Test filtering
    entries = [
        {"date": "2023-10-01", "body": "First entry"},
        {"date": "2023-10-02", "body": "Second entry"},
        {"date": "2023-10-03", "body": "Third entry"},
        {"date": "2023-10-04", "body": "Fourth entry"},
        {"date": "2023-10-05", "body": "Fifth entry"},
    ]

    filtered = filter_entries_by_date_range(entries, "2023-10-02", "2023-10-04")
    assert len(filtered) == 3, f"Expected 3 filtered entries, got {len(filtered)}"

    dates = [entry["date"] for entry in filtered]
    expected_dates = ["2023-10-02", "2023-10-03", "2023-10-04"]
    assert dates == expected_dates, f"Expected dates {expected_dates}, got {dates}"

    print("✅ test_journal_date_range passed!")


def main():
    """Run all journal tests"""
    print("Running Journal tests...")

    test_journal_add_basic()
    test_journal_add_default_date()
    test_journal_load_without_frontmatter()
    test_journal_get_all_entries()
    test_journal_search()
    test_journal_date_range()

    print("\n🎉 All journal tests passed!")


if __name__ == "__main__":
    main()
