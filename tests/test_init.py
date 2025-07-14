"""
Test for the init command functionality
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner

from mystuff.commands.init import app

def test_init_create_default_structure():
    """Test that init create creates the expected directory structure"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Run the init create command
        result = runner.invoke(app, ["create", "--dir", str(test_dir)])
        
        # Check that the command succeeded
        assert result.exit_code == 0
        assert "MyStuff directory structure created successfully" in result.stdout
        
        # Check that the directory was created
        assert test_dir.exists()
        assert test_dir.is_dir()
        
        # Check that links.jsonl was created
        links_file = test_dir / "links.jsonl"
        assert links_file.exists()
        assert links_file.is_file()
        
        # Check that all directories were created
        expected_dirs = ["meetings", "journal", "wiki", "selfeval", "lists"]
        for dir_name in expected_dirs:
            dir_path = test_dir / dir_name
            assert dir_path.exists()
            assert dir_path.is_dir()
            
            # Check that .gitkeep file was created
            gitkeep_file = dir_path / ".gitkeep"
            assert gitkeep_file.exists()
            assert gitkeep_file.is_file()

def test_init_create_existing_directory_without_force():
    """Test that init create fails when directory already exists without --force"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        test_dir.mkdir()
        
        # Run the init create command
        result = runner.invoke(app, ["create", "--dir", str(test_dir)])
        
        # Check that the command failed
        assert result.exit_code == 1
        assert "already exists" in result.stdout
        assert "Use --force to overwrite" in result.stdout

def test_init_create_existing_directory_with_force():
    """Test that init create succeeds when directory already exists with --force"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        test_dir.mkdir()
        
        # Run the init create command with --force
        result = runner.invoke(app, ["create", "--dir", str(test_dir), "--force"])
        
        # Check that the command succeeded
        assert result.exit_code == 0
        assert "MyStuff directory structure created successfully" in result.stdout
