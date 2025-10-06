#!/usr/bin/env python3
"""
Tests for the sync command
"""
import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mystuff.commands.sync import (
    execute_sync_commands,
    get_mystuff_dir,
    load_sync_config,
    sync_app,
)


@pytest.fixture
def temp_mystuff_dir():
    """Create a temporary mystuff directory with config.yaml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mystuff_dir = Path(temp_dir)
        config_file = mystuff_dir / "config.yaml"

        # Create a basic config with sync commands
        config = {
            "sync": {"commands": ['echo "Test command 1"', 'echo "Test command 2"']}
        }

        with open(config_file, "w") as f:
            yaml.dump(config, f)

        yield mystuff_dir


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


def test_get_mystuff_dir_with_config(temp_mystuff_dir):
    """Test finding mystuff directory with config.yaml."""
    # Change to the temp directory
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_mystuff_dir)
        mystuff_dir = get_mystuff_dir()
        # Resolve both paths to handle macOS /private/var vs /var differences
        assert mystuff_dir.resolve() == temp_mystuff_dir.resolve()
    finally:
        os.chdir(original_cwd)


def test_get_mystuff_dir_no_config():
    """Test behavior when no config.yaml is found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            mystuff_dir = get_mystuff_dir()
            assert mystuff_dir is None
        finally:
            os.chdir(original_cwd)


def test_load_sync_config_success(temp_mystuff_dir):
    """Test loading sync configuration successfully."""
    sync_config = load_sync_config(temp_mystuff_dir)

    assert "commands" in sync_config
    assert len(sync_config["commands"]) == 2
    assert 'echo "Test command 1"' in sync_config["commands"]
    assert 'echo "Test command 2"' in sync_config["commands"]


def test_load_sync_config_no_file():
    """Test loading sync config when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mystuff_dir = Path(temp_dir)

        # Should capture the typer.Exit exception which becomes click.exceptions.Exit
        try:
            load_sync_config(mystuff_dir)
            assert False, "Should have raised Exit"
        except Exception as e:
            # typer.Exit becomes click.exceptions.Exit when called
            assert "Exit" in str(type(e))


def test_load_sync_config_no_sync_section():
    """Test loading sync config when sync section doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mystuff_dir = Path(temp_dir)
        config_file = mystuff_dir / "config.yaml"

        # Create config without sync section
        config = {"other": "value"}
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        try:
            load_sync_config(mystuff_dir)
            assert False, "Should have raised Exit"
        except Exception as e:
            # typer.Exit becomes click.exceptions.Exit when called
            assert "Exit" in str(type(e))


def test_execute_sync_commands_dry_run(temp_mystuff_dir):
    """Test executing sync commands in dry run mode."""
    commands = ['echo "test1"', 'echo "test2"']
    config = {"data_directory": str(temp_mystuff_dir)}

    # Dry run should always succeed
    success = execute_sync_commands(
        commands=commands, mystuff_dir=temp_mystuff_dir, config=config, dry_run=True
    )

    assert success is True


def test_execute_sync_commands_success(temp_mystuff_dir):
    """Test executing sync commands successfully."""
    commands = ['echo "test1"', 'echo "test2"']
    config = {"data_directory": str(temp_mystuff_dir)}

    success = execute_sync_commands(
        commands=commands, mystuff_dir=temp_mystuff_dir, config=config, dry_run=False, verbose=False
    )

    assert success is True


def test_execute_sync_commands_failure(temp_mystuff_dir):
    """Test executing sync commands with failure."""
    commands = ['echo "test1"', "false", 'echo "test3"']  # false command will fail
    config = {"data_directory": str(temp_mystuff_dir)}

    success = execute_sync_commands(
        commands=commands,
        mystuff_dir=temp_mystuff_dir,
        config=config,
        dry_run=False,
        continue_on_error=False,
    )

    assert success is False


def test_execute_sync_commands_continue_on_error(temp_mystuff_dir):
    """Test executing sync commands with continue on error."""
    commands = ['echo "test1"', "false", 'echo "test3"']  # false command will fail
    config = {"data_directory": str(temp_mystuff_dir)}

    success = execute_sync_commands(
        commands=commands,
        mystuff_dir=temp_mystuff_dir,
        config=config,
        dry_run=False,
        continue_on_error=True,
    )

    assert success is False  # Still false because one command failed


def test_execute_sync_commands_empty_list(temp_mystuff_dir):
    """Test executing empty command list."""
    commands = []
    config = {"data_directory": str(temp_mystuff_dir)}

    success = execute_sync_commands(
        commands=commands, mystuff_dir=temp_mystuff_dir, config=config, dry_run=False
    )

    assert success is True


def test_sync_run_command_dry_run(runner, temp_mystuff_dir):
    """Test sync run command in dry run mode."""
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_mystuff_dir)
        result = runner.invoke(sync_app, ["run", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run mode" in result.stdout
        assert "Test command 1" in result.stdout
        assert "Test command 2" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_sync_run_command_success(runner, temp_mystuff_dir):
    """Test sync run command execution."""
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_mystuff_dir)
        result = runner.invoke(sync_app, ["run"])
        assert result.exit_code == 0
        assert "Executing 2 sync commands" in result.stdout
        assert "All sync commands completed successfully" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_sync_run_command_no_mystuff_dir(runner):
    """Test sync run command when no mystuff directory found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(sync_app, ["run"])
            assert result.exit_code == 1
            assert "No mystuff directory found" in result.output
        finally:
            os.chdir(original_cwd)


def test_sync_list_commands(runner, temp_mystuff_dir):
    """Test sync list-commands command."""
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_mystuff_dir)
        result = runner.invoke(sync_app, ["list-commands"])
        assert result.exit_code == 0
        assert "Found 2 sync commands" in result.stdout
        assert "Test command 1" in result.stdout
        assert "Test command 2" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_sync_list_commands_no_commands(runner):
    """Test sync list-commands when no commands are configured."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mystuff_dir = Path(temp_dir)
        config_file = mystuff_dir / "config.yaml"

        # Create config without sync commands
        config = {"sync": {}}
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(mystuff_dir)
            result = runner.invoke(sync_app, ["list-commands"])
            assert result.exit_code == 1  # Should exit with error when no sync section
        finally:
            os.chdir(original_cwd)


def test_sync_with_invalid_config(runner):
    """Test sync with invalid YAML config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mystuff_dir = Path(temp_dir)
        config_file = mystuff_dir / "config.yaml"

        # Create invalid YAML
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(mystuff_dir)
            result = runner.invoke(sync_app, ["run"])
            assert result.exit_code == 1
            assert "Error parsing config.yaml" in result.output
        finally:
            os.chdir(original_cwd)


def test_sync_with_non_list_commands(runner):
    """Test sync when commands is not a list."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mystuff_dir = Path(temp_dir)
        config_file = mystuff_dir / "config.yaml"

        # Create config with non-list commands
        config = {"sync": {"commands": "not a list"}}
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(mystuff_dir)
            result = runner.invoke(sync_app, ["run"])
            assert result.exit_code == 1
            assert "must be a list" in result.output
        finally:
            os.chdir(original_cwd)
