"""
Wiki command for MyStuff CLI
Manages topical notes with Markdown files, YAML front-matter, and backlinks
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Set

import typer
import yaml
from typing_extensions import Annotated


def get_mystuff_dir() -> Path:
    """Get the mystuff data directory from config or environment"""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home).expanduser().resolve()
    return Path.home() / ".mystuff"


def get_wiki_dir() -> Path:
    """Get the path to the wiki directory"""
    return get_mystuff_dir() / "wiki"


def ensure_wiki_dir_exists():
    """Ensure the wiki directory exists"""
    wiki_dir = get_wiki_dir()
    wiki_dir.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug"""
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().replace(" ", "-")
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def get_wiki_filename(title: str) -> str:
    """Generate filename for a wiki note"""
    return f"{slugify(title)}.md"


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


def load_wiki_from_file(file_path: Path) -> dict:
    """Load wiki note metadata and content from a markdown file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split front-matter and body
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            front_matter = parts[1]
            body = parts[2].strip()

            # Parse YAML front-matter
            metadata = yaml.safe_load(front_matter)
            if metadata is None:
                metadata = {}

            metadata["body"] = body
            metadata["file_path"] = file_path

            # Ensure required fields exist
            if "title" not in metadata:
                metadata["title"] = file_path.stem.replace("-", " ").title()
            if "tags" not in metadata:
                metadata["tags"] = []
            if "aliases" not in metadata:
                metadata["aliases"] = []
            if "backlinks" not in metadata:
                metadata["backlinks"] = []

            return metadata

    # No front-matter found
    return {
        "title": file_path.stem.replace("-", " ").title(),
        "tags": [],
        "aliases": [],
        "backlinks": [],
        "body": content,
        "file_path": file_path,
    }


def save_wiki_to_file(
    file_path: Path,
    title: str,
    tags: List[str],
    aliases: List[str],
    backlinks: List[str],
    body: str,
):
    """Save wiki note metadata and content to a markdown file"""
    # Create front-matter
    front_matter = {
        "title": title,
        "tags": tags,
        "aliases": aliases,
        "backlinks": backlinks,
    }

    # Write file with YAML front-matter
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, default_flow_style=False, allow_unicode=True)
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


def get_all_wiki_notes() -> List[dict]:
    """Get all wiki notes from the wiki directory"""
    wiki_dir = get_wiki_dir()
    if not wiki_dir.exists():
        return []

    notes = []
    for file_path in wiki_dir.glob("*.md"):
        try:
            note = load_wiki_from_file(file_path)
            notes.append(note)
        except Exception as e:
            typer.echo(f"Error loading wiki note {file_path}: {e}", err=True)

    # Sort by title
    notes.sort(key=lambda x: x.get("title", "").lower())
    return notes


def find_wiki_note_by_title_or_alias(title: str) -> Optional[dict]:
    """Find a wiki note by title or alias"""
    notes = get_all_wiki_notes()
    title_lower = title.lower()

    for note in notes:
        # Check exact title match
        if note.get("title", "").lower() == title_lower:
            return note

        # Check aliases
        for alias in note.get("aliases", []):
            if alias.lower() == title_lower:
                return note

        # Check slug match
        if note["file_path"].stem == slugify(title):
            return note

    return None


def extract_wiki_links(content: str) -> Set[str]:
    """Extract wiki-style links from content (e.g., [[Link Title]])"""
    # Pattern to match [[Link Title]] or [[Link Title|Display Text]]
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    matches = re.findall(pattern, content)
    return set(matches)


def update_backlinks():
    """Update backlinks for all wiki notes"""
    notes = get_all_wiki_notes()

    # Build a mapping of title/alias to file path
    title_to_file = {}
    for note in notes:
        title = note.get("title", "")
        file_path = note["file_path"]

        # Add title mapping
        if title:
            title_to_file[title.lower()] = file_path

        # Add alias mappings
        for alias in note.get("aliases", []):
            title_to_file[alias.lower()] = file_path

    # Track backlinks for each note
    backlinks_map = {note["file_path"]: set() for note in notes}

    # Scan all notes for wiki links
    for note in notes:
        content = note.get("body", "")
        wiki_links = extract_wiki_links(content)

        for link in wiki_links:
            target_file = title_to_file.get(link.lower())
            if target_file:
                # Add this note as a backlink to the target
                backlinks_map[target_file].add(note["file_path"].stem)

    # Update backlinks in all notes
    for note in notes:
        file_path = note["file_path"]
        current_backlinks = set(note.get("backlinks", []))
        new_backlinks = backlinks_map.get(file_path, set())

        # Only update if backlinks changed
        if current_backlinks != new_backlinks:
            note["backlinks"] = sorted(list(new_backlinks))
            save_wiki_to_file(
                file_path,
                note.get("title", ""),
                note.get("tags", []),
                note.get("aliases", []),
                note.get("backlinks", []),
                note.get("body", ""),
            )


def select_wiki_with_fzf(notes: List[dict]) -> Optional[dict]:
    """Use fzf to select a wiki note interactively"""
    if not notes:
        return None

    # Create options for fzf
    options = []
    for note in notes:
        title = note.get("title", "")
        tags_str = f"[{', '.join(note.get('tags', []))}]" if note.get("tags") else ""
        aliases_str = (
            f"({', '.join(note.get('aliases', []))})" if note.get("aliases") else ""
        )

        # Show first line of content as preview
        body_preview = note.get("body", "").split("\n")[0][:40]
        if len(body_preview) == 40:
            body_preview += "..."

        option = f"{title} {tags_str} {aliases_str} {body_preview}"
        options.append(option)

    # Run fzf
    try:
        process = subprocess.run(
            ["fzf", "--height=40%", "--layout=reverse", "--prompt=Select wiki note: "],
            input="\n".join(options),
            text=True,
            capture_output=True,
        )

        if process.returncode == 0:
            selected_line = process.stdout.strip()
            # Find the corresponding note
            for i, option in enumerate(options):
                if option == selected_line:
                    return notes[i]

        return None
    except Exception as e:
        typer.echo(f"Error running fzf: {e}", err=True)
        return None


def search_notes_by_text(notes: List[dict], search_text: str) -> List[dict]:
    """Search notes by full-text content"""
    search_lower = search_text.lower()
    filtered_notes = []

    for note in notes:
        # Search in title
        title = note.get("title", "").lower()
        if search_lower in title:
            filtered_notes.append(note)
            continue

        # Search in body content
        body = note.get("body", "").lower()
        if search_lower in body:
            filtered_notes.append(note)
            continue

        # Search in tags
        tags = note.get("tags", [])
        for tag in tags:
            if search_lower in tag.lower():
                filtered_notes.append(note)
                break
        else:
            # Search in aliases
            aliases = note.get("aliases", [])
            for alias in aliases:
                if search_lower in alias.lower():
                    filtered_notes.append(note)
                    break

    return filtered_notes


def generate_ascii_graph(note: dict, max_depth: int = 2) -> str:
    """Generate a simple ASCII graph of backlinks"""
    if not note.get("backlinks"):
        return f"{note.get('title', 'Untitled')}\n  (no backlinks)"

    graph = f"{note.get('title', 'Untitled')}\n"

    for i, backlink_slug in enumerate(note.get("backlinks", [])):
        is_last = i == len(note.get("backlinks", [])) - 1
        prefix = "└── " if is_last else "├── "

        # Try to find the actual title for this backlink
        backlink_title = backlink_slug.replace("-", " ").title()
        backlink_file = get_wiki_dir() / f"{backlink_slug}.md"

        if backlink_file.exists():
            try:
                backlink_note = load_wiki_from_file(backlink_file)
                backlink_title = backlink_note.get("title", backlink_title)
            except Exception:
                pass

        graph += f"  {prefix}{backlink_title}\n"

    return graph


def new_wiki_note(
    title: Annotated[str, typer.Argument(help="Title of the wiki note")],
    tags: Annotated[
        Optional[List[str]],
        typer.Option("--tag", help="One or more tags for categorization"),
    ] = None,
    aliases: Annotated[
        Optional[List[str]],
        typer.Option("--alias", help="One or more aliases for the note"),
    ] = None,
    body: Annotated[
        Optional[str], typer.Option("--body", help="Content for the wiki note")
    ] = None,
    no_edit: Annotated[
        bool, typer.Option("--no-edit", help="Don't open editor after creation")
    ] = False,
):
    """Create a new wiki note"""
    if not title:
        typer.echo("Error: Title is required", err=True)
        raise typer.Exit(code=1)

    ensure_wiki_dir_exists()

    # Set default values
    if tags is None:
        tags = []
    if aliases is None:
        aliases = []

    # Generate filename
    filename = get_wiki_filename(title)
    file_path = get_wiki_dir() / filename

    # Check if file already exists
    if file_path.exists():
        typer.echo(f"Wiki note already exists: {title}")
        if not no_edit and typer.confirm("Do you want to edit the existing note?"):
            if open_editor(file_path):
                typer.echo(f"✅ Wiki note updated: {title}")
                # Update backlinks after editing
                update_backlinks()
        return

    # Use body or default content
    if body:
        wiki_body = body
    else:
        wiki_body = f"""# {title}

## Overview

Brief description of {title}.

## Key Points

-

## Related Notes

-

## References

-
"""

    # Save the wiki file
    save_wiki_to_file(file_path, title, tags, aliases, [], wiki_body)

    typer.echo(f"✅ Wiki note created: {title}")

    # Open in editor if not disabled
    if not no_edit:
        if open_editor(file_path):
            typer.echo(f"✅ Wiki note saved: {title}")
            # Update backlinks after editing
            update_backlinks()


def view_wiki_note(
    title: Annotated[
        str, typer.Argument(help="Title or alias of the wiki note to view")
    ],
    graph: Annotated[
        bool, typer.Option("--graph", help="Display ASCII graph of backlinks")
    ] = False,
):
    """View a wiki note"""
    note = find_wiki_note_by_title_or_alias(title)

    if not note:
        typer.echo(f"Wiki note not found: {title}")
        return

    if graph:
        # Display ASCII graph
        typer.echo(generate_ascii_graph(note))
    else:
        # Display note content
        typer.echo(f"Title: {note.get('title', 'Untitled')}")

        tags = note.get("tags", [])
        if tags:
            typer.echo(f"Tags: {', '.join(tags)}")

        aliases = note.get("aliases", [])
        if aliases:
            typer.echo(f"Aliases: {', '.join(aliases)}")

        backlinks = note.get("backlinks", [])
        if backlinks:
            typer.echo(f"Backlinks: {', '.join(backlinks)}")

        typer.echo("\n" + "=" * 50 + "\n")
        typer.echo(note.get("body", ""))


def edit_wiki_note(
    title: Annotated[
        str, typer.Argument(help="Title or alias of the wiki note to edit")
    ],
):
    """Edit an existing wiki note"""
    note = find_wiki_note_by_title_or_alias(title)

    if not note:
        typer.echo(f"Wiki note not found: {title}")
        if typer.confirm("Do you want to create a new note?"):
            new_wiki_note(title, no_edit=False)
        return

    file_path = note["file_path"]

    # Open in editor
    if open_editor(file_path):
        typer.echo(f"✅ Wiki note updated: {note.get('title', 'Untitled')}")
        # Update backlinks after editing
        update_backlinks()


def delete_wiki_note(
    title: Annotated[
        str, typer.Argument(help="Title or alias of the wiki note to delete")
    ],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force deletion without confirmation")
    ] = False,
):
    """Delete a wiki note"""
    note = find_wiki_note_by_title_or_alias(title)

    if not note:
        typer.echo(f"Wiki note not found: {title}")
        return

    note_title = note.get("title", "Untitled")
    file_path = note["file_path"]

    # Confirm deletion
    if not force:
        if not typer.confirm(f"Are you sure you want to delete '{note_title}'?"):
            typer.echo("Deletion cancelled.")
            return

    # Delete the file
    try:
        file_path.unlink()
        typer.echo(f"✅ Wiki note deleted: {note_title}")

        # Update backlinks after deletion
        update_backlinks()
    except OSError as e:
        typer.echo(f"Error deleting wiki note: {e}", err=True)
        raise typer.Exit(code=1)


def list_wiki_notes(
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """List all wiki notes"""
    notes = get_all_wiki_notes()

    if not notes:
        typer.echo("No wiki notes found.")
        return

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_note = select_wiki_with_fzf(notes)
        if selected_note:
            file_path = selected_note["file_path"]
            if open_editor(file_path):
                typer.echo(
                    f"✅ Wiki note opened: {selected_note.get('title', 'Untitled')}"
                )
                # Update backlinks after editing
                update_backlinks()
        return

    # Display notes
    for note in notes:
        title = note.get("title", "Untitled")
        tags_str = f"[{', '.join(note.get('tags', []))}]" if note.get("tags") else ""
        aliases_str = (
            f"({', '.join(note.get('aliases', []))})" if note.get("aliases") else ""
        )

        typer.echo(f"{title} {tags_str} {aliases_str}")


def search_wiki_notes(
    query: Annotated[str, typer.Argument(help="Search query for wiki notes")],
    graph: Annotated[
        bool,
        typer.Option("--graph", help="Display ASCII graph of backlinks for results"),
    ] = False,
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """Search wiki notes by title, tags, or content"""
    notes = get_all_wiki_notes()

    if not notes:
        typer.echo("No wiki notes found.")
        return

    # Search by text content
    filtered_notes = search_notes_by_text(notes, query)

    if not filtered_notes:
        typer.echo(f"No wiki notes found matching '{query}'")
        return

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_note = select_wiki_with_fzf(filtered_notes)
        if selected_note:
            if graph:
                typer.echo(generate_ascii_graph(selected_note))
            else:
                file_path = selected_note["file_path"]
                if open_editor(file_path):
                    typer.echo(
                        f"✅ Wiki note opened: {selected_note.get('title', 'Untitled')}"
                    )
                    # Update backlinks after editing
                    update_backlinks()
        return

    # Display matching notes
    typer.echo(f"Found {len(filtered_notes)} wiki notes matching '{query}':")
    for note in filtered_notes:
        title = note.get("title", "Untitled")
        tags_str = f"[{', '.join(note.get('tags', []))}]" if note.get("tags") else ""
        aliases_str = (
            f"({', '.join(note.get('aliases', []))})" if note.get("aliases") else ""
        )

        if graph:
            typer.echo(f"\n{generate_ascii_graph(note)}")
        else:
            typer.echo(f"{title} {tags_str} {aliases_str}")


# Create the Typer app for wiki commands
wiki_app = typer.Typer(name="wiki", help="Manage topical notes with backlinks")

wiki_app.command("new")(new_wiki_note)
wiki_app.command("view")(view_wiki_note)
wiki_app.command("edit")(edit_wiki_note)
wiki_app.command("delete")(delete_wiki_note)
wiki_app.command("list")(list_wiki_notes)
wiki_app.command("search")(search_wiki_notes)

if __name__ == "__main__":
    wiki_app()
