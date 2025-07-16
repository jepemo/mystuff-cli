#!/usr/bin/env python3
"""
MyStuff CLI - Personal knowledge management tool
"""
import typer
from pathlib import Path
from typing_extensions import Annotated

from mystuff.commands.init import init
from mystuff.commands.link import link_app
from mystuff.commands.meeting import meeting_app
from mystuff.commands.journal import journal_app
from mystuff.commands.wiki import wiki_app
from mystuff.commands.eval import eval_app
from mystuff.commands.lists import list_app

app = typer.Typer(
    name="mystuff",
    help="Personal knowledge management CLI tool",
    add_completion=False,
)

# Add the init command
app.command()(init)

# Add the link command group
app.add_typer(link_app, name="link")

# Add the meeting command group
app.add_typer(meeting_app, name="meeting")

# Add the journal command group
app.add_typer(journal_app, name="journal")

# Add the wiki command group
app.add_typer(wiki_app, name="wiki")

# Add the eval command group
app.add_typer(eval_app, name="eval")

# Add the list command group
app.add_typer(list_app, name="list")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool, 
        typer.Option(
            "--version", 
            "-v", 
            help="Show version and exit"
        )
    ] = False,
):
    """
    MyStuff CLI - Personal knowledge management tool
    """
    if version:
        typer.echo("mystuff 0.6.0")
        raise typer.Exit()
    
    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


if __name__ == "__main__":
    app()
