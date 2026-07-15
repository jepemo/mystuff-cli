"""
Init command for MyStuff CLI
Creates the basic directory structure for mystuff data
"""

import os
from pathlib import Path
from typing import Annotated

import typer
import yaml

from mystuff.wiki.storage import ensure_wiki_layout, get_wiki_paths


def init(
    dir: Annotated[
        str,
        typer.Option(
            "--dir",
            "-d",
            help="Directory path for mystuff data "
            "(default: ~/.mystuff or $MYSTUFF_HOME)",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force creation even if directory exists"),
    ] = False,
):
    """
    Create the structure of the mystuff data directory.

    By default creates ~/.mystuff directory with the following structure:
    - links.jsonl (file for storing links)
    - meetings/ (directory for meeting notes)
    - journal/ (directory for journal entries)
    - wiki/raw/ (immutable captured sources)
    - wiki/content/ (synthesized Markdown pages)
    - wiki/metadata/ (regenerable indexes and audit state)
    - eval/ (directory for self-evaluation notes)
    - lists/ (directory for lists)
    - config.yaml (configuration file)
    """
    # Determine the target directory
    if dir is None:
        # Check for MYSTUFF_HOME environment variable first
        mystuff_home = os.getenv("MYSTUFF_HOME")
        if mystuff_home:
            base_dir = Path(mystuff_home).expanduser().resolve()
        else:
            base_dir = Path.home() / ".mystuff"
    else:
        base_dir = Path(dir).expanduser().resolve()

    # Check if directory already exists
    if base_dir.exists() and not force:
        typer.echo(f"Directory {base_dir} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    # Create base directory
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Created base directory: {base_dir}")
    except OSError as e:
        typer.echo(f"Error creating directory {base_dir}: {e}")
        raise typer.Exit(code=1)

    # Create the links.jsonl file
    links_file = base_dir / "links.jsonl"
    try:
        links_file.touch()
        typer.echo(f"Created links file: {links_file}")
    except OSError as e:
        typer.echo(f"Error creating links file: {e}")
        raise typer.Exit(code=1)

    # Create directories with .gitkeep files
    directories = ["meetings", "journal", "wiki", "eval", "lists", "learning"]

    for directory in directories:
        dir_path = base_dir / directory
        try:
            dir_path.mkdir(exist_ok=True)
            # Create .gitkeep file for empty directories
            gitkeep_file = dir_path / ".gitkeep"
            gitkeep_file.touch()
            typer.echo(f"Created directory: {dir_path}")
        except OSError as e:
            typer.echo(f"Error creating directory {dir_path}: {e}")
            raise typer.Exit(code=1)

    # Create learning subdirectories
    learning_lessons_dir = base_dir / "learning" / "lessons"
    try:
        learning_lessons_dir.mkdir(parents=True, exist_ok=True)
        # Create .gitkeep file for empty lessons directory
        gitkeep_file = learning_lessons_dir / ".gitkeep"
        gitkeep_file.touch()
        typer.echo(f"Created directory: {learning_lessons_dir}")
    except OSError as e:
        typer.echo(f"Error creating directory {learning_lessons_dir}: {e}")
        raise typer.Exit(code=1)

    # Create the compounding wiki layout and its editorial entry points.
    try:
        wiki_paths = ensure_wiki_layout(get_wiki_paths(base_dir))
        for directory in (
            wiki_paths.raw,
            wiki_paths.content,
            wiki_paths.metadata,
            wiki_paths.source_metadata,
            wiki_paths.page_metadata,
            wiki_paths.runs,
        ):
            gitkeep_file = directory / ".gitkeep"
            gitkeep_file.touch(exist_ok=True)
        typer.echo(f"Created compounding wiki layout: {wiki_paths.root}")
    except OSError as e:
        typer.echo(f"Error creating wiki layout: {e}")
        raise typer.Exit(code=1)

    # Create default config.yaml file
    config_file = base_dir / "config.yaml"
    try:
        default_config = {
            "data_directory": str(base_dir),
            "editor": os.getenv("EDITOR", "vim"),
            "pager": os.getenv("PAGER", "less"),
            "settings": {
                "default_tags": [],
                "date_format": "%Y-%m-%d",
                "time_format": "%H:%M:%S",
            },
            "ai": {
                "default_provider": "codex",
                "providers": {
                    "codex": {
                        "command": ["codex"],
                        # Null inherits the user's current Codex defaults.
                        "model": None,
                        "reasoning_effort": None,
                        "profile": None,
                    }
                },
                "tasks": {
                    "learning": {"provider": "codex"},
                    "wiki": {"provider": "codex"},
                },
            },
            "wiki": {
                "language": "English",
                "capture": {
                    "timeout_seconds": 20,
                    "max_bytes": 20_000_000,
                    "minimum_extracted_characters": 200,
                    # Add resolver URL templates here when a source such as X
                    # cannot be read directly. Supported placeholders:
                    # {url}, {username}, and {status_id}.
                    "resolvers": {"x": []},
                }
            },
            "sync": {"commands": ['echo "Sync data"']},
        }

        with open(config_file, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        typer.echo(f"Created config file: {config_file}")
    except OSError as e:
        typer.echo(f"Error creating config file: {e}")
        raise typer.Exit(code=1)

    typer.echo(f"✅ MyStuff directory structure created successfully at {base_dir}")
    typer.echo("\nDirectory structure:")
    typer.echo(f"  {base_dir}/")
    typer.echo("  ├── links.jsonl")
    for i, directory in enumerate(directories):
        if i == len(directories) - 1:
            typer.echo(f"  ├── {directory}/")
            typer.echo("  │   └── .gitkeep")
            typer.echo("  └── config.yaml")
        else:
            typer.echo(f"  ├── {directory}/")
            typer.echo("  │   └── .gitkeep")
