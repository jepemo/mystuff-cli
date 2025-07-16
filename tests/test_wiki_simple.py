#!/usr/bin/env python3

import os
import tempfile
import shutil
from pathlib import Path

def test_wiki_new_basic():
    """Test basic wiki note creation"""
    from mystuff.commands.wiki import save_wiki_to_file, load_wiki_from_file, get_wiki_filename
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir
        
        # Create wiki directory
        wiki_dir = Path(temp_dir) / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # Test data
        title = "Test Wiki Note"
        tags = ["test", "wiki"]
        aliases = ["test-note"]
        backlinks = []
        body = "This is a test wiki note."
        
        # Create file path
        filename = get_wiki_filename(title)
        file_path = wiki_dir / filename
        
        # Save wiki note
        save_wiki_to_file(file_path, title, tags, aliases, backlinks, body)
        
        # Check file exists
        assert file_path.exists(), "Wiki file should exist"
        
        # Check filename is properly slugified
        assert filename == "test-wiki-note.md", f"Expected test-wiki-note.md, got {filename}"
        
        # Load wiki note
        loaded_note = load_wiki_from_file(file_path)
        
        # Verify content
        assert loaded_note['title'] == title, f"Expected title {title}, got {loaded_note['title']}"
        assert loaded_note['tags'] == tags, f"Expected tags {tags}, got {loaded_note['tags']}"
        assert loaded_note['aliases'] == aliases, f"Expected aliases {aliases}, got {loaded_note['aliases']}"
        assert loaded_note['backlinks'] == backlinks, f"Expected backlinks {backlinks}, got {loaded_note['backlinks']}"
        assert loaded_note['body'] == body, f"Expected body {body}, got {loaded_note['body']}"
        
        print("✅ test_wiki_new_basic passed!")

def test_wiki_slugify():
    """Test title slugification"""
    from mystuff.commands.wiki import slugify, get_wiki_filename
    
    # Test various title formats
    test_cases = [
        ("Simple Title", "simple-title"),
        ("Title with Spaces", "title-with-spaces"),
        ("Title with Numbers 123", "title-with-numbers-123"),
        ("Title with Special!@#$%^&*()Characters", "title-with-specialcharacters"),
        ("Title---with---Multiple---Dashes", "title-with-multiple-dashes"),
        ("  Leading and Trailing Spaces  ", "leading-and-trailing-spaces"),
    ]
    
    for title, expected_slug in test_cases:
        result = slugify(title)
        assert result == expected_slug, f"Expected {expected_slug}, got {result} for title '{title}'"
        
        # Test filename generation
        filename = get_wiki_filename(title)
        assert filename == f"{expected_slug}.md", f"Expected {expected_slug}.md, got {filename}"
    
    print("✅ test_wiki_slugify passed!")

def test_wiki_load_without_frontmatter():
    """Test loading wiki note without YAML front-matter"""
    from mystuff.commands.wiki import load_wiki_from_file
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir
        
        # Create wiki directory
        wiki_dir = Path(temp_dir) / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file without front-matter
        file_path = wiki_dir / "test-note.md"
        body = "This is a simple wiki note without front-matter."
        
        with open(file_path, 'w') as f:
            f.write(body)
        
        # Load wiki note
        loaded_note = load_wiki_from_file(file_path)
        
        # Verify content
        assert loaded_note['title'] == "Test Note", f"Expected title 'Test Note', got {loaded_note['title']}"
        assert loaded_note['tags'] == [], f"Expected empty tags, got {loaded_note['tags']}"
        assert loaded_note['aliases'] == [], f"Expected empty aliases, got {loaded_note['aliases']}"
        assert loaded_note['backlinks'] == [], f"Expected empty backlinks, got {loaded_note['backlinks']}"
        assert loaded_note['body'] == body, f"Expected body {body}, got {loaded_note['body']}"
        
        print("✅ test_wiki_load_without_frontmatter passed!")

def test_wiki_get_all_notes():
    """Test getting all wiki notes"""
    from mystuff.commands.wiki import get_all_wiki_notes, save_wiki_to_file
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir
        
        # Create wiki directory
        wiki_dir = Path(temp_dir) / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test notes
        notes_data = [
            ("Project Overview", ["project"], ["overview"], "Overview of the project"),
            ("Team Structure", ["team"], ["structure"], "Team organization details"),
            ("Development Process", ["dev"], ["process"], "Development workflow"),
        ]
        
        for title, tags, aliases, body in notes_data:
            from mystuff.commands.wiki import get_wiki_filename
            filename = get_wiki_filename(title)
            file_path = wiki_dir / filename
            save_wiki_to_file(file_path, title, tags, aliases, [], body)
        
        # Get all notes
        all_notes = get_all_wiki_notes()
        
        # Check count
        assert len(all_notes) == 3, f"Expected 3 notes, got {len(all_notes)}"
        
        # Check sorting (by title)
        titles = [note['title'] for note in all_notes]
        expected_titles = ["Development Process", "Project Overview", "Team Structure"]
        assert titles == expected_titles, f"Expected titles {expected_titles}, got {titles}"
        
        print("✅ test_wiki_get_all_notes passed!")

def test_wiki_find_by_title_and_alias():
    """Test finding wiki notes by title or alias"""
    from mystuff.commands.wiki import find_wiki_note_by_title_or_alias, save_wiki_to_file, get_wiki_filename
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir
        
        # Create wiki directory
        wiki_dir = Path(temp_dir) / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test note
        title = "Project Overview"
        tags = ["project"]
        aliases = ["overview", "project-summary"]
        body = "Overview of the project"
        
        filename = get_wiki_filename(title)
        file_path = wiki_dir / filename
        save_wiki_to_file(file_path, title, tags, aliases, [], body)
        
        # Test finding by title
        note = find_wiki_note_by_title_or_alias("Project Overview")
        assert note is not None, "Should find note by title"
        assert note['title'] == title, f"Expected title {title}, got {note['title']}"
        
        # Test finding by alias
        note = find_wiki_note_by_title_or_alias("overview")
        assert note is not None, "Should find note by alias"
        assert note['title'] == title, f"Expected title {title}, got {note['title']}"
        
        # Test finding by another alias
        note = find_wiki_note_by_title_or_alias("project-summary")
        assert note is not None, "Should find note by second alias"
        assert note['title'] == title, f"Expected title {title}, got {note['title']}"
        
        # Test finding non-existent note
        note = find_wiki_note_by_title_or_alias("Non-existent Note")
        assert note is None, "Should not find non-existent note"
        
        print("✅ test_wiki_find_by_title_and_alias passed!")

def test_wiki_extract_links():
    """Test extracting wiki links from content"""
    from mystuff.commands.wiki import extract_wiki_links
    
    # Test content with various link formats
    content = """
    # Test Document
    
    This document links to [[Project Overview]] and [[Team Structure]].
    
    It also references [[Development Process|our dev process]] and [[Another Note]].
    
    Regular links like [external](https://example.com) should be ignored.
    
    Also [[Final Link]] at the end.
    """
    
    links = extract_wiki_links(content)
    expected_links = {"Project Overview", "Team Structure", "Development Process", "Another Note", "Final Link"}
    
    assert links == expected_links, f"Expected links {expected_links}, got {links}"
    
    # Test empty content
    empty_links = extract_wiki_links("")
    assert empty_links == set(), "Empty content should return empty set"
    
    # Test content without links
    no_links = extract_wiki_links("This is content without any wiki links.")
    assert no_links == set(), "Content without links should return empty set"
    
    print("✅ test_wiki_extract_links passed!")

def test_wiki_search():
    """Test searching wiki notes"""
    from mystuff.commands.wiki import search_notes_by_text, save_wiki_to_file, get_wiki_filename
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir
        
        # Create wiki directory
        wiki_dir = Path(temp_dir) / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test notes
        notes_data = [
            ("Python Programming", ["python", "programming"], ["py"], "Guide to Python programming"),
            ("Team Meeting", ["meeting"], ["standup"], "Meeting notes about project status"),
            ("JavaScript Guide", ["javascript", "programming"], ["js"], "JavaScript development guide"),
            ("Project Planning", ["planning"], ["roadmap"], "Planning for the next quarter"),
        ]
        
        notes = []
        for title, tags, aliases, body in notes_data:
            filename = get_wiki_filename(title)
            file_path = wiki_dir / filename
            save_wiki_to_file(file_path, title, tags, aliases, [], body)
            
            # Create note dict for search
            note = {
                'title': title,
                'tags': tags,
                'aliases': aliases,
                'body': body,
                'file_path': file_path
            }
            notes.append(note)
        
        # Search by title
        results = search_notes_by_text(notes, 'Python')
        assert len(results) == 1, f"Expected 1 result for 'Python', got {len(results)}"
        assert results[0]['title'] == 'Python Programming', f"Expected 'Python Programming', got {results[0]['title']}"
        
        # Search by tag
        results = search_notes_by_text(notes, 'programming')
        assert len(results) == 2, f"Expected 2 results for 'programming', got {len(results)}"
        titles = [result['title'] for result in results]
        assert 'Python Programming' in titles, "Should find Python Programming"
        assert 'JavaScript Guide' in titles, "Should find JavaScript Guide"
        
        # Search by alias
        results = search_notes_by_text(notes, 'js')
        assert len(results) == 1, f"Expected 1 result for 'js', got {len(results)}"
        assert results[0]['title'] == 'JavaScript Guide', f"Expected 'JavaScript Guide', got {results[0]['title']}"
        
        # Search by body content
        results = search_notes_by_text(notes, 'quarter')
        assert len(results) == 1, f"Expected 1 result for 'quarter', got {len(results)}"
        assert results[0]['title'] == 'Project Planning', f"Expected 'Project Planning', got {results[0]['title']}"
        
        # Search with no matches
        results = search_notes_by_text(notes, 'nonexistent')
        assert len(results) == 0, f"Expected 0 results for 'nonexistent', got {len(results)}"
        
        print("✅ test_wiki_search passed!")

def test_wiki_backlinks():
    """Test backlink extraction and updating"""
    from mystuff.commands.wiki import extract_wiki_links, update_backlinks, save_wiki_to_file, get_wiki_filename, get_all_wiki_notes
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        os.environ["MYSTUFF_HOME"] = temp_dir
        
        # Create wiki directory
        wiki_dir = Path(temp_dir) / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test notes with cross-references
        notes_data = [
            ("Project Overview", [], [], "This project involves [[Team Structure]] and [[Development Process]]."),
            ("Team Structure", [], [], "The team works on [[Project Overview]] using [[Development Process]]."),
            ("Development Process", [], [], "Our process supports the [[Project Overview]]."),
            ("Standalone Note", [], [], "This note doesn't link to anything."),
        ]
        
        for title, tags, aliases, body in notes_data:
            filename = get_wiki_filename(title)
            file_path = wiki_dir / filename
            save_wiki_to_file(file_path, title, tags, aliases, [], body)
        
        # Update backlinks
        update_backlinks()
        
        # Get all notes and check backlinks
        all_notes = get_all_wiki_notes()
        note_by_title = {note['title']: note for note in all_notes}
        
        # Check backlinks for each note
        project_note = note_by_title["Project Overview"]
        expected_backlinks = {"development-process", "team-structure"}
        actual_backlinks = set(project_note.get('backlinks', []))
        assert actual_backlinks == expected_backlinks, f"Expected backlinks {expected_backlinks}, got {actual_backlinks}"
        
        team_note = note_by_title["Team Structure"]
        expected_backlinks = {"project-overview"}
        actual_backlinks = set(team_note.get('backlinks', []))
        assert actual_backlinks == expected_backlinks, f"Expected backlinks {expected_backlinks}, got {actual_backlinks}"
        
        dev_note = note_by_title["Development Process"]
        expected_backlinks = {"project-overview", "team-structure"}
        actual_backlinks = set(dev_note.get('backlinks', []))
        assert actual_backlinks == expected_backlinks, f"Expected backlinks {expected_backlinks}, got {actual_backlinks}"
        
        standalone_note = note_by_title["Standalone Note"]
        assert standalone_note.get('backlinks', []) == [], "Standalone note should have no backlinks"
        
        print("✅ test_wiki_backlinks passed!")

def main():
    """Run all wiki tests"""
    print("Running Wiki tests...")
    
    test_wiki_new_basic()
    test_wiki_slugify()
    test_wiki_load_without_frontmatter()
    test_wiki_get_all_notes()
    test_wiki_find_by_title_and_alias()
    test_wiki_extract_links()
    test_wiki_search()
    test_wiki_backlinks()
    
    print("\n🎉 All wiki tests passed!")

if __name__ == "__main__":
    main()
