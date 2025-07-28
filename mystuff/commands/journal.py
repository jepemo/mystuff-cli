"""
Journal command for MyStuff CLI
Manages daily journal entries with Markdown files and YAML front-matter
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
import yaml
from typing_extensions import Annotated


def get_mystuff_dir() -> Path:
    """Get the mystuff data directory from config or environment"""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home).expanduser().resolve()
    return Path.home() / ".mystuff"


def get_journal_dir() -> Path:
    """Get the path to the journal directory"""
    return get_mystuff_dir() / "journal"


def ensure_journal_dir_exists():
    """Ensure the journal directory exists"""
    journal_dir = get_journal_dir()
    journal_dir.mkdir(parents=True, exist_ok=True)


def get_journal_filename(date: str) -> str:
    """Generate filename for a journal entry"""
    return f"{date}.md"


def get_editor() -> str:
    """Get the editor from environment or config"""
    return os.getenv("EDITOR", "vim")


def is_fzf_available() -> bool:
    """Check if fzf is available on the system"""
    try:
        subprocess.run(["fzf", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def load_journal_from_file(file_path: Path) -> dict:
    """Load journal metadata and content from a markdown file"""
    with open(file_path, "r") as f:
        content = f.read()

    # Split front-matter and body
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            front_matter = parts[1]
            body = parts[2].strip()

            # Parse YAML front-matter
            metadata = yaml.safe_load(front_matter)
            metadata["body"] = body
            metadata["file_path"] = file_path
            return metadata

    # No front-matter found
    return {"date": file_path.stem, "tags": [], "body": content, "file_path": file_path}


def save_journal_to_file(file_path: Path, date: str, tags: List[str], body: str):
    """Save journal metadata and content to a markdown file"""
    # Create front-matter
    front_matter = {"date": date, "tags": tags}

    # Write file with YAML front-matter
    with open(file_path, "w") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, default_flow_style=False)
        f.write("---\n\n")
        f.write(body)


def open_editor(file_path: Path) -> bool:
    """Open file in the default editor"""
    editor = get_editor()
    try:
        subprocess.run([editor, str(file_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        typer.echo(f"Error opening editor: {editor}")
        return False
    except FileNotFoundError:
        typer.echo(f"Editor not found: {editor}")
        return False


def get_all_journal_entries() -> List[dict]:
    """Get all journal entries from the journal directory"""
    journal_dir = get_journal_dir()
    if not journal_dir.exists():
        return []

    entries = []
    for file_path in journal_dir.glob("*.md"):
        try:
            entry = load_journal_from_file(file_path)
            entries.append(entry)
        except Exception as e:
            typer.echo(f"Error loading journal entry {file_path}: {e}", err=True)

    # Sort by date (newest first)
    entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    return entries


def display_journal_entry(entry: dict):
    """Display a single journal entry in detail"""
    date = entry.get("date", "Unknown date")
    tags = entry.get("tags", [])
    body = entry.get("body", "")

    typer.echo(f"📅 Date: {date}")

    if tags:
        tags_str = ", ".join(tags)
        typer.echo(f"🏷️  Tags: {tags_str}")

    if body:
        typer.echo("\n📝 Content:")
        typer.echo(body)
    else:
        typer.echo("\n📝 Content: (empty)")

    typer.echo()  # Add blank line for spacing


def select_journal_with_fzf(entries: List[dict]) -> Optional[dict]:
    """Use fzf to select a journal entry interactively"""
    if not entries:
        return None

    # Create options for fzf
    options = []
    for entry in entries:
        date = entry.get("date", "")
        tags_str = f"[{', '.join(entry.get('tags', []))}]" if entry.get("tags") else ""
        # Show first line of content as preview
        body_preview = entry.get("body", "").split("\n")[0][:50]
        if len(body_preview) == 50:
            body_preview += "..."

        option = f"{date} {tags_str} {body_preview}"
        options.append(option)

    # Create a temporary file with the options
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ) as temp_file:
        for option in options:
            temp_file.write(option + "\n")
        temp_file_path = temp_file.name

    try:
        # Use os.system to allow fzf to control the terminal directly
        # Redirect the selected option to a temporary output file
        output_file = tempfile.mktemp(suffix=".txt")

        cmd = (
            f"cat {temp_file_path} | fzf --height=40% --layout=reverse "
            f"--prompt='Select journal entry: ' > {output_file}"
        )
        result = os.system(cmd)

        if result == 0:  # Success
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    selected_line = f.read().strip()

                if selected_line:
                    # Find the corresponding entry
                    for i, option in enumerate(options):
                        if option == selected_line:
                            return entries[i]
            except FileNotFoundError:
                pass  # No selection made
            finally:
                # Clean up output file
                try:
                    os.unlink(output_file)
                except OSError:
                    pass

        return None
    except Exception as e:
        typer.echo(f"Error running fzf: {e}", err=True)
        return None
    finally:
        # Clean up temporary input file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass


def parse_date_range(range_str: str) -> tuple[str, str]:
    """Parse date range string in format YYYY-MM-DD:YYYY-MM-DD"""
    if ":" not in range_str:
        # Single date - validate format
        try:
            datetime.strptime(range_str, "%Y-%m-%d")
        except ValueError:
            typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
            raise typer.Exit(code=1)
        return range_str, range_str

    parts = range_str.split(":", 1)
    start_date = parts[0].strip()
    end_date = parts[1].strip()

    # Validate date format
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        typer.echo(
            "Error: Date range must be in YYYY-MM-DD:YYYY-MM-DD format", err=True
        )
        raise typer.Exit(code=1)

    return start_date, end_date


def filter_entries_by_date_range(
    entries: List[dict], start_date: str, end_date: str
) -> List[dict]:
    """Filter entries by date range"""
    filtered_entries = []
    for entry in entries:
        entry_date = entry.get("date", "")
        if start_date <= entry_date <= end_date:
            filtered_entries.append(entry)
    return filtered_entries


def search_entries_by_text(entries: List[dict], search_text: str) -> List[dict]:
    """Search entries by full-text content"""
    search_lower = search_text.lower()
    filtered_entries = []

    for entry in entries:
        # Search in body content
        body = entry.get("body", "").lower()
        if search_lower in body:
            filtered_entries.append(entry)
            continue

        # Search in tags
        tags = entry.get("tags", [])
        for tag in tags:
            if search_lower in tag.lower():
                filtered_entries.append(entry)
                break

    return filtered_entries


def add_journal_entry(
    date: Annotated[
        Optional[str],
        typer.Option(
            "--date",
            help="Date for the journal entry in YYYY-MM-DD format (defaults to today)",
        ),
    ] = None,
    body: Annotated[
        Optional[str],
        typer.Option("--body", help="Free-text content for the journal entry"),
    ] = None,
    tags: Annotated[
        Optional[List[str]],
        typer.Option("--tag", help="One or more tags for categorization"),
    ] = None,
    no_edit: Annotated[
        bool,
        typer.Option(
            "--no-edit", help="Don't prompt to edit the journal entry after creation"
        ),
    ] = False,
):
    """Add a new journal entry"""
    ensure_journal_dir_exists()

    # Set default date if not provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)

    # Set default tags if not provided
    if tags is None:
        tags = []

    # Generate filename
    filename = get_journal_filename(date)
    file_path = get_journal_dir() / filename

    # Check if file already exists
    if file_path.exists():
        typer.echo(f"Journal entry already exists for {date}")
        if not no_edit and typer.confirm("Do you want to edit the existing entry?"):
            if open_editor(file_path):
                typer.echo(f"✅ Journal entry updated for {date}")
        return

    # Use body or default content
    if body:
        journal_body = body
    else:
        journal_body = """## Journal Entry

Today I...

## Reflections

-

## Tomorrow's Goals

-
"""

    # Save the journal file
    save_journal_to_file(file_path, date, tags, journal_body)

    typer.echo(f"✅ Journal entry created for {date}")

    # Open in editor if not disabled
    if not no_edit:
        if open_editor(file_path):
            typer.echo(f"✅ Journal entry saved for {date}")


def list_journal_entries(
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Limit the number of entries to display"),
    ] = None,
    date_range: Annotated[
        Optional[str],
        typer.Option("--range", help="Filter by date range (YYYY-MM-DD:YYYY-MM-DD)"),
    ] = None,
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """List all journal entries"""
    entries = get_all_journal_entries()

    if not entries:
        typer.echo("No journal entries found.")
        return

    # Filter by date range if specified
    if date_range:
        start_date, end_date = parse_date_range(date_range)
        entries = filter_entries_by_date_range(entries, start_date, end_date)

    # Apply limit if specified
    if limit:
        entries = entries[:limit]

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_entry = select_journal_with_fzf(entries)
        if selected_entry:
            # Display the selected entry
            display_journal_entry(selected_entry)
        return

    # Display entries
    for entry in entries:
        date = entry.get("date", "")
        tags_str = f"[{', '.join(entry.get('tags', []))}]" if entry.get("tags") else ""

        # Show first line of content as preview
        body_preview = entry.get("body", "").split("\n")[0][:50]
        if len(body_preview) == 50:
            body_preview += "..."

        typer.echo(f"{date} {tags_str} {body_preview}")


def edit_journal_entry(
    date: Annotated[
        Optional[str],
        typer.Option(
            "--date", help="Date of the journal entry to edit (defaults to today)"
        ),
    ] = None,
):
    """Edit an existing journal entry"""
    # Set default date if not provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)

    # Check if entry exists
    filename = get_journal_filename(date)
    file_path = get_journal_dir() / filename

    if not file_path.exists():
        typer.echo(f"Journal entry not found for {date}")
        if typer.confirm("Do you want to create a new entry?"):
            # Create new entry
            save_journal_to_file(
                file_path,
                date,
                [],
                """## Journal Entry

Today I...

## Reflections

-

## Tomorrow's Goals

-
""",
            )
            typer.echo(f"✅ Journal entry created for {date}")
        else:
            return

    # Open in editor
    if open_editor(file_path):
        typer.echo(f"✅ Journal entry updated for {date}")


def search_journal_entries(
    query: Annotated[str, typer.Argument(help="Search query for journal entries")],
    date_range: Annotated[
        Optional[str],
        typer.Option("--range", help="Filter by date range (YYYY-MM-DD:YYYY-MM-DD)"),
    ] = None,
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """Search journal entries by full-text or date range"""
    entries = get_all_journal_entries()

    if not entries:
        typer.echo("No journal entries found.")
        return

    # Filter by date range if specified
    if date_range:
        start_date, end_date = parse_date_range(date_range)
        entries = filter_entries_by_date_range(entries, start_date, end_date)

    # Search by text content
    filtered_entries = search_entries_by_text(entries, query)

    if not filtered_entries:
        typer.echo(f"No journal entries found matching '{query}'")
        return

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_entry = select_journal_with_fzf(filtered_entries)
        if selected_entry:
            file_path = selected_entry["file_path"]
            if open_editor(file_path):
                typer.echo(f"✅ Journal entry opened for {selected_entry['date']}")
        return

    # Display matching entries
    typer.echo(f"Found {len(filtered_entries)} journal entries matching '{query}':")
    for entry in filtered_entries:
        date = entry.get("date", "")
        tags_str = f"[{', '.join(entry.get('tags', []))}]" if entry.get("tags") else ""

        # Show first line of content as preview
        body_preview = entry.get("body", "").split("\n")[0][:50]
        if len(body_preview) == 50:
            body_preview += "..."

        typer.echo(f"{date} {tags_str} {body_preview}")


# Create the Typer app for journal commands
journal_app = typer.Typer(name="journal", help="Manage daily journal entries")

journal_app.command("add")(add_journal_entry)
journal_app.command("list")(list_journal_entries)
journal_app.command("edit")(edit_journal_entry)
journal_app.command("search")(search_journal_entries)

if __name__ == "__main__":
    journal_app()
