#!/usr/bin/env python3
"""
Simple test for the init command functionality (without pytest)
"""
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner

from mystuff.cli import app

def test_init_create_default_structure():
    """Test that init creates the expected directory structure"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Run the init command
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        
        # Check that the command succeeded
        assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}: {result.stdout}"
        assert "MyStuff directory structure created successfully" in result.stdout
        
        # Check that the directory was created
        assert test_dir.exists(), f"Directory {test_dir} was not created"
        assert test_dir.is_dir(), f"{test_dir} is not a directory"
        
        # Check that links.jsonl was created
        links_file = test_dir / "links.jsonl"
        assert links_file.exists(), f"links.jsonl file was not created"
        assert links_file.is_file(), f"links.jsonl is not a file"
        
        # Check that all directories were created
        expected_dirs = ["meetings", "journal", "wiki", "eval", "lists"]
        for dir_name in expected_dirs:
            dir_path = test_dir / dir_name
            assert dir_path.exists(), f"Directory {dir_name} was not created"
            assert dir_path.is_dir(), f"{dir_name} is not a directory"
            
            # Check that .gitkeep file was created
            gitkeep_file = dir_path / ".gitkeep"
            assert gitkeep_file.exists(), f".gitkeep file was not created in {dir_name}"
            assert gitkeep_file.is_file(), f".gitkeep in {dir_name} is not a file"
        
        # Check that config.yaml was created
        config_file = test_dir / "config.yaml"
        assert config_file.exists(), f"config.yaml file was not created"
        assert config_file.is_file(), f"config.yaml is not a file"

def test_init_create_existing_directory_without_force():
    """Test that init fails when directory already exists without --force"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        test_dir.mkdir()
        
        # Run the init command
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        
        # Check that the command failed
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
        assert "already exists" in result.stdout
        assert "Use --force to overwrite" in result.stdout

def test_init_create_existing_directory_with_force():
    """Test that init succeeds when directory already exists with --force"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        test_dir.mkdir()
        
        # Run the init command with --force
        result = runner.invoke(app, ["init", "--dir", str(test_dir), "--force"])
        
        # Check that the command succeeded
        assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}: {result.stdout}"
        assert "MyStuff directory structure created successfully" in result.stdout

def test_init_with_mystuff_home_env():
    """Test that init respects MYSTUFF_HOME environment variable"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "mystuff-home"
        
        # Set MYSTUFF_HOME environment variable
        env = {"MYSTUFF_HOME": str(test_dir)}
        
        # Run the init command without --dir, should use MYSTUFF_HOME
        result = runner.invoke(app, ["init"], env=env)
        
        # Check that the command succeeded
        assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}: {result.stdout}"
        assert "MyStuff directory structure created successfully" in result.stdout
        
        # Check that the directory was created at MYSTUFF_HOME location
        assert test_dir.exists(), f"Directory {test_dir} was not created"
        assert test_dir.is_dir(), f"{test_dir} is not a directory"
        
        # Check that links.jsonl was created
        links_file = test_dir / "links.jsonl"
        assert links_file.exists(), f"links.jsonl file was not created"
        
        # Check that config.yaml was created
        config_file = test_dir / "config.yaml"
        assert config_file.exists(), f"config.yaml file was not created"

def test_init_config_yaml_content():
    """Test that config.yaml is created with proper content"""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test-mystuff"
        
        # Run the init command
        result = runner.invoke(app, ["init", "--dir", str(test_dir)])
        
        # Check that the command succeeded
        assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}: {result.stdout}"
        
        # Check that config.yaml was created and has expected content
        config_file = test_dir / "config.yaml"
        assert config_file.exists(), f"config.yaml file was not created"
        
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check that config has expected keys
        assert "data_directory" in config
        assert "editor" in config
        assert "pager" in config
        assert "settings" in config
        
        # Check that data_directory is set correctly (should be absolute path)
        # Note: Path resolution may change /tmp to /private/tmp on macOS
        assert Path(config["data_directory"]).resolve() == test_dir.resolve()

if __name__ == "__main__":
    print("Running test_init_create_default_structure...")
    test_init_create_default_structure()
    print("✅ test_init_create_default_structure passed!")
    
    print("Running test_init_create_existing_directory_without_force...")
    test_init_create_existing_directory_without_force()
    print("✅ test_init_create_existing_directory_without_force passed!")
    
    print("Running test_init_create_existing_directory_with_force...")
    test_init_create_existing_directory_with_force()
    print("✅ test_init_create_existing_directory_with_force passed!")
    
    print("Running test_init_with_mystuff_home_env...")
    test_init_with_mystuff_home_env()
    print("✅ test_init_with_mystuff_home_env passed!")
    
    print("Running test_init_config_yaml_content...")
    test_init_config_yaml_content()
    print("✅ test_init_config_yaml_content passed!")
    
    print("\n🎉 All tests passed!")
