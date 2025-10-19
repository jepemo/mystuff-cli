#!/usr/bin/env python3
"""
MyStuff CLI - Sync commands functionality
"""
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from typing_extensions import Annotated

sync_app = typer.Typer(help="Execute custom sync commands from configuration")


def get_mystuff_dir() -> Optional[Path]:
    """Get the mystuff directory by looking for config.yaml.
    
    Priority:
    1. Check MYSTUFF_HOME environment variable first
    2. Fall back to searching in current directory and parent directories
    """
    import os
    
    # Check MYSTUFF_HOME environment variable first
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        mystuff_path = Path(mystuff_home).expanduser().resolve()
        config_file = mystuff_path / "config.yaml"
        if config_file.exists():
            return mystuff_path
    
    # Fall back to looking for config.yaml in current directory and parent directories
    current = Path.cwd()

    # Look for config.yaml in current directory and parent directories
    while current != current.parent:
        config_file = current / "config.yaml"
        if config_file.exists():
            return current
        current = current.parent

    return None


def load_config(mystuff_dir: Path) -> Dict[str, Any]:
    """Load complete configuration from config.yaml."""
    config_file = mystuff_dir / "config.yaml"

    if not config_file.exists():
        typer.echo(f"❌ Configuration file not found: {config_file}", err=True)
        raise typer.Exit(1)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        typer.echo(f"❌ Error parsing config.yaml: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error reading config.yaml: {e}", err=True)
        raise typer.Exit(1)

    if not config:
        typer.echo("❌ Empty configuration file", err=True)
        raise typer.Exit(1)

    return config


def load_sync_config(mystuff_dir: Path) -> Dict[str, Any]:
    """Load sync configuration from config.yaml."""
    config = load_config(mystuff_dir)
    
    # Get sync configuration
    sync_config = config.get("sync", {})
    if not sync_config:
        typer.echo("❌ No 'sync' section found in config.yaml", err=True)
        raise typer.Exit(1)

    return sync_config


def execute_sync_commands(
    commands: List[str],
    mystuff_dir: Path,
    config: Dict[str, Any],
    dry_run: bool = False,
    verbose: bool = False,
    continue_on_error: bool = False,
) -> bool:
    """Execute a list of sync commands in a single shared shell session.
    
    This allows commands to share state (environment variables, working directory, etc.)
    so that operations like 'cd' persist across multiple commands.
    """
    if not commands:
        typer.echo("ℹ️  No commands to execute")
        return True

    # Prepare environment variables
    import os
    env = os.environ.copy()
    
    # Set MYSTUFF_HOME if not already set
    if "MYSTUFF_HOME" not in env:
        data_directory = config.get("data_directory")
        if data_directory:
            env["MYSTUFF_HOME"] = str(data_directory)
            if verbose:
                typer.echo(f"🔧 Setting MYSTUFF_HOME={data_directory}")
        else:
            # Fallback to mystuff_dir if no data_directory in config
            env["MYSTUFF_HOME"] = str(mystuff_dir)
            if verbose:
                typer.echo(f"🔧 Setting MYSTUFF_HOME={mystuff_dir} (fallback)")

    if verbose or dry_run:
        for i, command in enumerate(commands, 1):
            typer.echo(f"[{i}/{len(commands)}] {command}")

    if dry_run:
        return True

    try:
        # Build a single shell script that executes all commands
        # This preserves state (working directory, variables, etc.) across commands
        shell_script = "set -e\n"  # Exit on first error by default
        
        if continue_on_error:
            # When continuing on error, we still need to track if any command failed
            # Use || to continue, and track exit status with a variable
            shell_script = """
_sync_failed=0
"""
            for cmd in commands:
                shell_script += f"({cmd}) || _sync_failed=1\n"
            shell_script += "exit $_sync_failed\n"
        else:
            # Use set -e to stop on first error
            shell_script += "\n".join(commands)
        
        # Execute all commands in a single shell session
        result = subprocess.run(
            shell_script,
            shell=True,
            cwd=mystuff_dir,
            capture_output=not verbose,
            text=True,
            env=env,
            executable="/bin/bash",  # Use bash to ensure 'set -e' works
        )

        if result.returncode != 0:
            if not verbose:
                typer.echo(f"❌ Sync commands failed (exit code {result.returncode})", err=True)
                if result.stderr:
                    typer.echo(f"Error output:\n{result.stderr.strip()}", err=True)
            else:
                typer.echo(f"❌ Sync commands failed (exit code {result.returncode})", err=True)
            return False
        else:
            if not verbose:
                typer.echo(".", nl=False)  # Progress indicator
            return True

    except Exception as e:
        error_msg = f"❌ Error executing sync commands: {e}"
        typer.echo(error_msg, err=True)
        return False


@sync_app.command()
def run(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Show commands that would be executed without running them",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output during execution"),
    ] = False,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            "-c",
            help="Continue executing remaining commands even if one fails",
        ),
    ] = False,
):
    """Execute all sync commands defined in config.yaml."""
    # Get mystuff directory
    mystuff_dir = get_mystuff_dir()
    if not mystuff_dir:
        typer.echo("❌ No mystuff directory found. Run 'mystuff init' first.", err=True)
        raise typer.Exit(1)

    # Load complete configuration
    config = load_config(mystuff_dir)
    sync_config = config.get("sync", {})
    
    if not sync_config:
        typer.echo("❌ No 'sync' section found in config.yaml", err=True)
        raise typer.Exit(1)

    # Get commands
    commands = sync_config.get("commands", [])
    if not commands:
        typer.echo("ℹ️  No sync commands defined in config.yaml")
        return

    if not isinstance(commands, list):
        typer.echo("❌ 'sync.commands' must be a list in config.yaml", err=True)
        raise typer.Exit(1)

    # Show what we're about to do
    if dry_run:
        typer.echo(
            f"🔍 Dry run mode - showing {len(commands)} commands that would be executed:"
        )
    else:
        typer.echo(f"🚀 Executing {len(commands)} sync commands...")

    # Execute commands
    success = execute_sync_commands(
        commands=commands,
        mystuff_dir=mystuff_dir,
        config=config,
        dry_run=dry_run,
        verbose=verbose,
        continue_on_error=continue_on_error,
    )

    # Show final result
    if dry_run:
        typer.echo("✅ Dry run completed")
    elif success:
        typer.echo("✅ All sync commands completed successfully")
    else:
        typer.echo("❌ Some sync commands failed", err=True)
        raise typer.Exit(1)


@sync_app.command()
def list_commands():
    """List all sync commands defined in config.yaml."""
    # Get mystuff directory
    mystuff_dir = get_mystuff_dir()
    if not mystuff_dir:
        typer.echo("❌ No mystuff directory found. Run 'mystuff init' first.", err=True)
        raise typer.Exit(1)

    # Load sync configuration
    sync_config = load_sync_config(mystuff_dir)

    # Get commands
    commands = sync_config.get("commands", [])
    if not commands:
        typer.echo("ℹ️  No sync commands defined in config.yaml")
        return

    if not isinstance(commands, list):
        typer.echo("❌ 'sync.commands' must be a list in config.yaml", err=True)
        raise typer.Exit(1)

    typer.echo(f"📋 Found {len(commands)} sync commands:")
    for i, command in enumerate(commands, 1):
        typer.echo(f"  {i}. {command}")


if __name__ == "__main__":
    sync_app()
