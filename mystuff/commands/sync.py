#!/usr/bin/env python3
"""
MyStuff CLI - Sync commands functionality
"""
import typer
import yaml
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from typing_extensions import Annotated

sync_app = typer.Typer(help="Execute custom sync commands from configuration")


def get_mystuff_dir() -> Optional[Path]:
    """Get the mystuff directory by looking for config.yaml."""
    current = Path.cwd()
    
    # Look for config.yaml in current directory and parent directories
    while current != current.parent:
        config_file = current / "config.yaml"
        if config_file.exists():
            return current
        current = current.parent
    
    return None


def load_sync_config(mystuff_dir: Path) -> Dict[str, Any]:
    """Load sync configuration from config.yaml."""
    config_file = mystuff_dir / "config.yaml"
    
    if not config_file.exists():
        typer.echo(f"❌ Configuration file not found: {config_file}", err=True)
        raise typer.Exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
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
    
    # Get sync configuration
    sync_config = config.get('sync', {})
    if not sync_config:
        typer.echo("❌ No 'sync' section found in config.yaml", err=True)
        raise typer.Exit(1)
    
    return sync_config


def execute_sync_commands(
    commands: List[str], 
    mystuff_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
    continue_on_error: bool = False
) -> bool:
    """Execute a list of sync commands."""
    if not commands:
        typer.echo("ℹ️  No commands to execute")
        return True
    
    success = True
    
    for i, command in enumerate(commands, 1):
        if verbose or dry_run:
            typer.echo(f"[{i}/{len(commands)}] {command}")
        
        if dry_run:
            continue
        
        try:
            # Execute command in the mystuff directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=mystuff_dir,
                capture_output=not verbose,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = f"❌ Command failed (exit code {result.returncode}): {command}"
                if result.stderr and not verbose:
                    error_msg += f"\nError: {result.stderr.strip()}"
                
                typer.echo(error_msg, err=True)
                success = False
                
                if not continue_on_error:
                    break
            else:
                if verbose:
                    typer.echo(f"✅ Command completed successfully")
                elif not dry_run:
                    typer.echo(".", nl=False)  # Progress indicator
                    
        except Exception as e:
            error_msg = f"❌ Error executing command: {command}\nError: {e}"
            typer.echo(error_msg, err=True)
            success = False
            
            if not continue_on_error:
                break
    
    if not dry_run and not verbose:
        typer.echo()  # New line after progress dots
    
    return success


@sync_app.command()
def run(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Show commands that would be executed without running them"
        )
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed output during execution"
        )
    ] = False,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            "-c",
            help="Continue executing remaining commands even if one fails"
        )
    ] = False,
):
    """Execute all sync commands defined in config.yaml."""
    # Get mystuff directory
    mystuff_dir = get_mystuff_dir()
    if not mystuff_dir:
        typer.echo("❌ No mystuff directory found. Run 'mystuff init' first.", err=True)
        raise typer.Exit(1)
    
    # Load sync configuration
    sync_config = load_sync_config(mystuff_dir)
    
    # Get commands
    commands = sync_config.get('commands', [])
    if not commands:
        typer.echo("ℹ️  No sync commands defined in config.yaml")
        return
    
    if not isinstance(commands, list):
        typer.echo("❌ 'sync.commands' must be a list in config.yaml", err=True)
        raise typer.Exit(1)
    
    # Show what we're about to do
    if dry_run:
        typer.echo(f"🔍 Dry run mode - showing {len(commands)} commands that would be executed:")
    else:
        typer.echo(f"🚀 Executing {len(commands)} sync commands...")
    
    # Execute commands
    success = execute_sync_commands(
        commands=commands,
        mystuff_dir=mystuff_dir,
        dry_run=dry_run,
        verbose=verbose,
        continue_on_error=continue_on_error
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
    commands = sync_config.get('commands', [])
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
