#!/usr/bin/env python3
"""
Test for the meeting command functionality
"""
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner
import yaml
import os
from datetime import datetime

from mystuff.cli import app

def test_meeting_add_basic():
    """Test that meeting add creates a basic meeting note"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add a meeting
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Team Standup",
            "--date", "2023-10-05",
            "--participants", "Alice, Bob, Charlie",
            "--tag", "standup",
            "--tag", "team",
            "--body", "Daily standup meeting"
        ], env=env, input="n\n")  # Don't edit
        
        assert result.exit_code == 0
        assert "Created meeting note: Team Standup" in result.stdout
        
        # Check file was created
        meetings_dir = test_dir / "meetings"
        meeting_file = meetings_dir / "2023-10-05_team-standup.md"
        assert meeting_file.exists()
        
        # Check content
        with open(meeting_file, 'r') as f:
            content = f.read()
        
        assert "title: Team Standup" in content
        assert "date: '2023-10-05'" in content
        assert "participants:" in content
        assert "- Alice" in content
        assert "- Bob" in content
        assert "- Charlie" in content
        assert "tags:" in content
        assert "- standup" in content
        assert "- team" in content
        assert "Daily standup meeting" in content

def test_meeting_add_default_date():
    """Test that meeting add uses today's date by default"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add a meeting without date
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Quick Meeting",
            "--body", "Test meeting"
        ], env=env, input="n\n")  # Don't edit
        
        assert result.exit_code == 0
        assert "Created meeting note: Quick Meeting" in result.stdout
        
        # Check file was created with today's date
        meetings_dir = test_dir / "meetings"
        today = datetime.now().strftime('%Y-%m-%d')
        meeting_file = meetings_dir / f"{today}_quick-meeting.md"
        assert meeting_file.exists()

def test_meeting_add_template():
    """Test that meeting add can use a template"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        template_file = Path(temp_dir) / "template.md"
        
        # Create template file
        template_content = """## Meeting Agenda

1. Review last week's progress
2. Discuss upcoming deadlines
3. Action items

## Notes

(Add notes here)
"""
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add a meeting with template
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Weekly Review",
            "--template", str(template_file)
        ], env=env, input="n\n")  # Don't edit
        
        assert result.exit_code == 0
        assert "Created meeting note: Weekly Review" in result.stdout
        
        # Check file contains template content
        meetings_dir = test_dir / "meetings"
        today = datetime.now().strftime('%Y-%m-%d')
        meeting_file = meetings_dir / f"{today}_weekly-review.md"
        assert meeting_file.exists()
        
        with open(meeting_file, 'r') as f:
            content = f.read()
        
        assert "## Meeting Agenda" in content
        assert "Review last week's progress" in content
        assert "(Add notes here)" in content

def test_meeting_list_empty():
    """Test that meeting list shows appropriate message when no meetings exist"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # List meetings
        result = runner.invoke(app, ["meeting", "list"], env=env)
        
        assert result.exit_code == 0
        assert "No meeting notes found" in result.stdout

def test_meeting_list_with_meetings():
    """Test that meeting list shows meetings correctly"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add some meetings
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "First Meeting",
            "--date", "2023-10-01",
            "--participants", "Alice",
            "--body", "First meeting content"
        ], env=env, input="n\n")
        assert result.exit_code == 0
        
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Second Meeting",
            "--date", "2023-10-02",
            "--participants", "Bob",
            "--tag", "important",
            "--body", "Second meeting content"
        ], env=env, input="n\n")
        assert result.exit_code == 0
        
        # List meetings
        result = runner.invoke(app, ["meeting", "list"], env=env)
        
        assert result.exit_code == 0
        assert "First Meeting" in result.stdout
        assert "Second Meeting" in result.stdout
        assert "2023-10-01" in result.stdout
        assert "2023-10-02" in result.stdout
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout

def test_meeting_search():
    """Test that meeting search works correctly"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add meetings
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Python Discussion",
            "--participants", "Alice, Bob",
            "--body", "Discuss Python best practices"
        ], env=env, input="n\n")
        assert result.exit_code == 0
        
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "JavaScript Review",
            "--participants", "Charlie",
            "--body", "Review JavaScript code"
        ], env=env, input="n\n")
        assert result.exit_code == 0
        
        # Search for Python
        result = runner.invoke(app, ["meeting", "search", "python"], env=env)
        
        assert result.exit_code == 0
        assert "Python Discussion" in result.stdout
        assert "JavaScript Review" not in result.stdout

def test_meeting_delete():
    """Test that meeting delete works correctly"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add a meeting
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Meeting to Delete",
            "--date", "2023-10-05",
            "--body", "This will be deleted"
        ], env=env, input="n\n")
        assert result.exit_code == 0
        
        # Check file exists
        meetings_dir = test_dir / "meetings"
        meeting_file = meetings_dir / "2023-10-05_meeting-to-delete.md"
        assert meeting_file.exists()
        
        # Delete the meeting
        result = runner.invoke(app, [
            "meeting", "delete",
            "--title", "Meeting to Delete",
            "--date", "2023-10-05"
        ], env=env, input="y\n")  # Confirm deletion
        
        assert result.exit_code == 0
        assert "Deleted meeting note: Meeting to Delete" in result.stdout
        
        # Check file is gone
        assert not meeting_file.exists()

def test_meeting_delete_nonexistent():
    """Test that meeting delete handles non-existent meetings"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Try to delete non-existent meeting
        result = runner.invoke(app, [
            "meeting", "delete",
            "--title", "Non-existent Meeting"
        ], env=env)
        
        assert result.exit_code == 1
        assert "No meeting notes found" in result.stdout

def test_meeting_slugify():
    """Test that meeting titles are properly slugified for filenames"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add a meeting with special characters in title
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Team Meeting: Q4 Review & Planning (2023)",
            "--date", "2023-10-05",
            "--body", "Quarterly review"
        ], env=env, input="n\n")
        
        assert result.exit_code == 0
        
        # Check file was created with slugified name
        meetings_dir = test_dir / "meetings"
        meeting_file = meetings_dir / "2023-10-05_team-meeting-q4-review-planning-2023.md"
        assert meeting_file.exists()

def test_meeting_add_no_edit():
    """Test that meeting add with --no-edit doesn't prompt for editing"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Set environment for test
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Initialize directory first
        result = runner.invoke(app, ["init"], env=env)
        assert result.exit_code == 0
        
        # Add a meeting with --no-edit
        result = runner.invoke(app, [
            "meeting", "add", 
            "--title", "Team Meeting",
            "--date", "2023-10-05",
            "--no-edit"
        ], env=env)
        
        assert result.exit_code == 0
        assert "Created meeting note: Team Meeting" in result.stdout
        # Should not contain the prompt for editing
        assert "Do you want to edit the meeting note now?" not in result.stdout
        
        # Check file was created
        meetings_dir = test_dir / "meetings"
        meeting_file = meetings_dir / "2023-10-05_team-meeting.md"
        assert meeting_file.exists()

if __name__ == "__main__":
    print("Running test_meeting_add_basic...")
    test_meeting_add_basic()
    print("✅ test_meeting_add_basic passed!")
    
    print("Running test_meeting_add_default_date...")
    test_meeting_add_default_date()
    print("✅ test_meeting_add_default_date passed!")
    
    print("Running test_meeting_add_template...")
    test_meeting_add_template()
    print("✅ test_meeting_add_template passed!")
    
    print("Running test_meeting_list_empty...")
    test_meeting_list_empty()
    print("✅ test_meeting_list_empty passed!")
    
    print("Running test_meeting_list_with_meetings...")
    test_meeting_list_with_meetings()
    print("✅ test_meeting_list_with_meetings passed!")
    
    print("Running test_meeting_search...")
    test_meeting_search()
    print("✅ test_meeting_search passed!")
    
    print("Running test_meeting_delete...")
    test_meeting_delete()
    print("✅ test_meeting_delete passed!")
    
    print("Running test_meeting_delete_nonexistent...")
    test_meeting_delete_nonexistent()
    print("✅ test_meeting_delete_nonexistent passed!")
    
    print("Running test_meeting_slugify...")
    test_meeting_slugify()
    print("✅ test_meeting_slugify passed!")
    
    print("Running test_meeting_add_no_edit...")
    test_meeting_add_no_edit()
    print("✅ test_meeting_add_no_edit passed!")
    
    print("\n🎉 All meeting tests passed!")
