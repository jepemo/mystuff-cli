#!/usr/bin/env python3
"""
Test for the link command functionality
"""
import tempfile
import json
from pathlib import Path
from typer.testing import CliRunner
from datetime import datetime

from mystuff.cli import app

def test_link_add_basic():
    """Test adding a basic link"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add a link
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://example.com",
            "--title", "Example Site",
            "--description", "Test description",
            "--tag", "example",
            "--tag", "test"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "✅ Added link: Example Site" in result.stdout
        
        # Check the JSONL file
        links_file = test_dir / "links.jsonl"
        assert links_file.exists()
        
        with open(links_file, 'r') as f:
            link_data = json.loads(f.read().strip())
        
        assert link_data["url"] == "https://example.com"
        assert link_data["title"] == "Example Site"
        assert link_data["description"] == "Test description"
        assert link_data["tags"] == ["example", "test"]
        assert "timestamp" in link_data

def test_link_add_auto_title():
    """Test adding a link with auto-generated title"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add a link without title
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://github.com/example/repo"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "✅ Added link: github.com" in result.stdout
        
        # Check the JSONL file
        links_file = test_dir / "links.jsonl"
        with open(links_file, 'r') as f:
            link_data = json.loads(f.read().strip())
        
        assert link_data["title"] == "github.com"

def test_link_add_duplicate():
    """Test adding a duplicate link"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add first link
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://example.com",
            "--title", "Example Site"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        
        # Try to add duplicate
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://example.com",
            "--title", "Different Title"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "Link already exists: Example Site" in result.stdout

def test_link_list_empty():
    """Test listing links when none exist"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # List links
        result = runner.invoke(app, [
            "link", "list"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "No links found" in result.stdout

def test_link_list_with_links():
    """Test listing links with content"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add some links
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://example.com",
            "--title", "Example Site",
            "--description", "Test description"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://github.com",
            "--title", "GitHub",
            "--tag", "development"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        # List links
        result = runner.invoke(app, [
            "link", "list"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "1. Example Site" in result.stdout
        assert "2. GitHub" in result.stdout
        assert "https://example.com" in result.stdout
        assert "Test description" in result.stdout

def test_link_search():
    """Test searching links"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add some links
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://python.org",
            "--title", "Python Official",
            "--description", "Python programming language",
            "--tag", "python"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://github.com",
            "--title", "GitHub",
            "--description", "Code repository platform",
            "--tag", "development"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        # Search by title
        result = runner.invoke(app, [
            "link", "search", "python"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "Python Official" in result.stdout
        assert "GitHub" not in result.stdout
        
        # Search by description
        result = runner.invoke(app, [
            "link", "search", "repository"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "GitHub" in result.stdout
        assert "Python Official" not in result.stdout

def test_link_edit():
    """Test editing a link"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add a link
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://example.com",
            "--title", "Example Site",
            "--description", "Original description"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        # Edit the link
        result = runner.invoke(app, [
            "link", "edit",
            "--url", "https://example.com",
            "--title", "Updated Example Site",
            "--description", "Updated description",
            "--tag", "updated"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "✅ Updated link: Updated Example Site" in result.stdout
        
        # Check the update
        links_file = test_dir / "links.jsonl"
        with open(links_file, 'r') as f:
            link_data = json.loads(f.read().strip())
        
        assert link_data["title"] == "Updated Example Site"
        assert link_data["description"] == "Updated description"
        assert link_data["tags"] == ["updated"]

def test_link_delete():
    """Test deleting a link"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Add links
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://example.com",
            "--title", "Example Site"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        result = runner.invoke(app, [
            "link", "add", 
            "--url", "https://github.com",
            "--title", "GitHub"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        assert result.exit_code == 0
        
        # Delete one link
        result = runner.invoke(app, [
            "link", "delete",
            "--url", "https://example.com"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 0
        assert "✅ Deleted link: https://example.com" in result.stdout
        
        # Check that only one link remains
        links_file = test_dir / "links.jsonl"
        with open(links_file, 'r') as f:
            links = [json.loads(line.strip()) for line in f if line.strip()]
        
        assert len(links) == 1
        assert links[0]["url"] == "https://github.com"

def test_link_delete_nonexistent():
    """Test deleting a nonexistent link"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Initialize directory
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        assert result.exit_code == 0
        
        # Try to delete nonexistent link
        result = runner.invoke(app, [
            "link", "delete",
            "--url", "https://nonexistent.com"
        ], env={"MYSTUFF_HOME": str(test_dir)})
        
        assert result.exit_code == 1
        assert "No links found" in result.stdout

if __name__ == "__main__":
    print("Running test_link_add_basic...")
    test_link_add_basic()
    print("✅ test_link_add_basic passed!")
    
    print("Running test_link_add_auto_title...")
    test_link_add_auto_title()
    print("✅ test_link_add_auto_title passed!")
    
    print("Running test_link_add_duplicate...")
    test_link_add_duplicate()
    print("✅ test_link_add_duplicate passed!")
    
    print("Running test_link_list_empty...")
    test_link_list_empty()
    print("✅ test_link_list_empty passed!")
    
    print("Running test_link_list_with_links...")
    test_link_list_with_links()
    print("✅ test_link_list_with_links passed!")
    
    print("Running test_link_search...")
    test_link_search()
    print("✅ test_link_search passed!")
    
    print("Running test_link_edit...")
    test_link_edit()
    print("✅ test_link_edit passed!")
    
    print("Running test_link_delete...")
    test_link_delete()
    print("✅ test_link_delete passed!")
    
    print("Running test_link_delete_nonexistent...")
    test_link_delete_nonexistent()
    print("✅ test_link_delete_nonexistent passed!")
    
    print("\n🎉 All link tests passed!")
