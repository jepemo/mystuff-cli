#!/usr/bin/env python3
"""
MyStuff CLI - Learning management functionality
"""
import datetime
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from typing_extensions import Annotated

learn_app = typer.Typer(help="Manage learning materials and progress")

# Template for metadata
METADATA_TEMPLATE = {
    "current_lesson": None,
    "last_opened": None,
    "completed_lessons": [],
}


def get_mystuff_dir() -> Path:
    """Get the mystuff directory path."""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home)

    # Fallback to ~/.mystuff
    return Path.home() / ".mystuff"


def get_learning_dir() -> Path:
    """Get the learning directory path."""
    return get_mystuff_dir() / "learning"


def get_lessons_dir() -> Path:
    """Get the lessons directory path."""
    return get_learning_dir() / "lessons"


def get_metadata_path() -> Path:
    """Get the metadata file path."""
    return get_learning_dir() / "metadata.yaml"


def ensure_learning_structure() -> None:
    """Ensure learning directory structure exists."""
    learning_dir = get_learning_dir()
    lessons_dir = get_lessons_dir()

    # Create directories if they don't exist
    learning_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir.mkdir(parents=True, exist_ok=True)


def load_metadata() -> Dict[str, Any]:
    """Load learning metadata. Creates file if it doesn't exist."""
    ensure_learning_structure()
    metadata_path = get_metadata_path()

    if not metadata_path.exists():
        # Create metadata file with template
        metadata = METADATA_TEMPLATE.copy()
        save_metadata(metadata)
        return metadata

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f)

        # Ensure all required keys exist
        if metadata is None:
            metadata = {}

        for key in METADATA_TEMPLATE:
            if key not in metadata:
                metadata[key] = METADATA_TEMPLATE[key]

        return metadata
    except yaml.YAMLError as e:
        typer.echo(f"❌ Error parsing metadata.yaml: {e}", err=True)
        return METADATA_TEMPLATE.copy()
    except Exception as e:
        typer.echo(f"❌ Error reading metadata.yaml: {e}", err=True)
        return METADATA_TEMPLATE.copy()


def save_metadata(metadata: Dict[str, Any]) -> None:
    """Save learning metadata. Creates file if it doesn't exist."""
    ensure_learning_structure()
    metadata_path = get_metadata_path()

    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        typer.echo(f"❌ Error saving metadata: {e}", err=True)
        raise typer.Exit(1)


def get_all_lessons(recursive: bool = True) -> List[Dict[str, str]]:
    """Get all lessons with their metadata.

    Args:
        recursive: Whether to search recursively through subdirectories

    Returns:
        List of lesson objects with name, path, and display_name
    """
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        return []

    lessons = []

    if recursive:
        # Recursive search through all subdirectories
        for file_path in sorted(lessons_dir.glob("**/*.md")):
            if file_path.is_file():
                # Get relative path from lessons directory
                rel_path = file_path.relative_to(lessons_dir)

                # Create lesson object
                lesson = {
                    "name": str(rel_path),  # Relative path as string
                    "path": str(file_path),  # Full path as string
                    "display_name": str(rel_path),
                }
                lessons.append(lesson)
    else:
        # Only top-level lessons
        for file_path in sorted(lessons_dir.glob("*.md")):
            if file_path.is_file():
                lesson = {
                    "name": file_path.name,
                    "path": str(file_path),
                    "display_name": file_path.name,
                }
                lessons.append(lesson)

    # Sort lessons alphabetically by name
    return sorted(lessons, key=lambda l: l["name"])


def get_lesson_status(lesson_name: str, metadata: Dict[str, Any]) -> str:
    """Get the status icon for a lesson."""
    completed_names = [
        item["name"] for item in metadata.get("completed_lessons", [])
    ]
    current = metadata.get("current_lesson")

    if lesson_name in completed_names:
        return "✅"
    elif lesson_name == current:
        return "🔍"
    else:
        return "⏳"


def display_lessons_tree(
    lessons: List[Dict[str, str]], metadata: Dict[str, Any]
) -> None:
    """Display lessons in a tree structure."""
    console = Console()

    if not lessons:
        console.print("❌ No lessons found.")
        return

    # Group lessons by directory
    lesson_tree: Dict[str, List[Dict[str, str]]] = {}
    for lesson in lessons:
        parts = lesson["name"].split("/")

        if len(parts) == 1:
            # Top-level lesson
            if "_root" not in lesson_tree:
                lesson_tree["_root"] = []
            lesson_tree["_root"].append(lesson)
        else:
            # Nested lesson - group by parent directory
            directory = "/".join(parts[:-1])
            if directory not in lesson_tree:
                lesson_tree[directory] = []
            lesson_tree[directory].append(lesson)

    # Create tree
    root = Tree("📚 Lessons")

    # Add top-level lessons
    if "_root" in lesson_tree:
        for lesson in lesson_tree["_root"]:
            status = get_lesson_status(lesson["name"], metadata)
            root.add(f"{status} {lesson['name']}")

    # Add directories and their lessons
    for directory, dir_lessons in sorted(lesson_tree.items()):
        if directory == "_root":
            continue

        # Create directory node
        dir_node = root.add(f"📁 {directory}")

        # Add lessons in this directory
        for lesson in sorted(dir_lessons, key=lambda l: l["name"]):
            name = lesson["name"].split("/")[-1]  # Just the filename
            status = get_lesson_status(lesson["name"], metadata)
            dir_node.add(f"{status} {name}")

    console.print(root)


def get_next_lesson(
    current_lesson: str, metadata: Dict[str, Any]
) -> Optional[str]:
    """Get the next uncompleted lesson after the current one."""
    all_lessons = get_all_lessons()
    completed_names = [
        item["name"] for item in metadata.get("completed_lessons", [])
    ]

    # Find current lesson index
    current_index = next(
        (i for i, lesson in enumerate(all_lessons) if lesson["name"] == current_lesson),
        -1,
    )

    if current_index == -1:
        return None

    # Look for the next uncompleted lesson
    for i in range(current_index + 1, len(all_lessons)):
        if all_lessons[i]["name"] not in completed_names:
            return all_lessons[i]["name"]

    # If we've reached the end, look from beginning
    for i in range(0, current_index):
        if all_lessons[i]["name"] not in completed_names:
            return all_lessons[i]["name"]

    return None  # No uncompleted lessons found


@learn_app.command("current")
def open_current_lesson():
    """Open the current lesson in progress using the configured editor."""
    metadata = load_metadata()
    current = metadata.get("current_lesson")

    if not current:
        lessons = get_all_lessons()
        if not lessons:
            typer.echo("❌ No lessons found. Create some in the lessons directory first.")
            raise typer.Exit(1)

        # Set the first lesson as current
        current = lessons[0]["name"]
        metadata["current_lesson"] = current
        save_metadata(metadata)
        typer.echo(f"📚 Set first lesson as current: {current}")

    # Update last opened timestamp
    metadata["last_opened"] = datetime.datetime.now().isoformat()
    save_metadata(metadata)

    # Open the lesson in the editor
    lesson_path = get_lessons_dir() / current
    if not lesson_path.exists():
        typer.echo(f"❌ Current lesson file not found: {lesson_path}")
        raise typer.Exit(1)

    editor = os.getenv("EDITOR", "vim")
    typer.echo(f"📖 Opening lesson: {current}")
    os.system(f'{editor} "{lesson_path}"')


@learn_app.command("list")
def list_lessons(
    all_lessons_flag: Annotated[
        bool, typer.Option("--all", "-a", help="Show all lessons")
    ] = False,
    completed: Annotated[
        bool, typer.Option("--completed", "-c", help="Show only completed lessons")
    ] = False,
    pending: Annotated[
        bool, typer.Option("--pending", "-p", help="Show only pending lessons")
    ] = False,
    tree: Annotated[
        bool, typer.Option("--tree", "-t", help="Show as tree structure")
    ] = False,
    flat: Annotated[
        bool, typer.Option("--flat", "-f", help="Don't search subdirectories")
    ] = False,
):
    """List lessons with their status."""
    metadata = load_metadata()
    all_lessons = get_all_lessons(recursive=not flat)

    if not all_lessons:
        typer.echo("❌ No lessons found. Create some in the lessons directory first.")
        return

    # Determine which lessons to show
    completed_names = [
        item["name"] for item in metadata.get("completed_lessons", [])
    ]
    current = metadata.get("current_lesson")

    if completed:
        lessons_to_show = [
            l for l in all_lessons if l["name"] in completed_names
        ]
    elif pending:
        lessons_to_show = [
            l for l in all_lessons if l["name"] not in completed_names
        ]
    else:
        lessons_to_show = all_lessons

    if tree:
        # Show as tree structure
        display_lessons_tree(lessons_to_show, metadata)
    else:
        # Show as table
        console = Console()
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Status", style="cyan")
        table.add_column("Lesson", style="white")
        table.add_column("Directory", style="dim")
        table.add_column("Completed At", style="green")

        for lesson in lessons_to_show:
            name = lesson["name"]
            parts = name.split("/")

            if len(parts) > 1:
                filename = parts[-1]
                directory = "/".join(parts[:-1])
            else:
                filename = name
                directory = ""

            if name in completed_names:
                status = "✅"
                completed_at = next(
                    (
                        item["completed_at"]
                        for item in metadata.get("completed_lessons", [])
                        if item["name"] == name
                    ),
                    "",
                )
            elif name == current:
                status = "🔍"
                completed_at = ""
            else:
                status = "⏳"
                completed_at = ""

            table.add_row(status, filename, directory, completed_at)

        console.print(table)

        # Summary
        total = len(all_lessons)
        completed_count = len(completed_names)
        pending_count = total - completed_count
        console.print(
            f"\n📊 Total: {total} | ✅ Completed: {completed_count} | ⏳ Pending: {pending_count}"
        )


@learn_app.command("tree")
def show_lesson_tree():
    """Show lessons in a tree structure."""
    metadata = load_metadata()
    all_lessons = get_all_lessons(recursive=True)

    if not all_lessons:
        typer.echo("❌ No lessons found. Create some in the lessons directory first.")
        return

    display_lessons_tree(all_lessons, metadata)


@learn_app.command("complete")
def complete_lesson(
    lesson: Annotated[
        Optional[str],
        typer.Argument(help="Name of the lesson to mark as completed"),
    ] = None,
):
    """Mark a lesson as completed."""
    metadata = load_metadata()

    # If no lesson specified, use current
    if not lesson:
        lesson = metadata.get("current_lesson")
        if not lesson:
            typer.echo("❌ No current lesson set. Use 'mystuff learn start' to set one.")
            raise typer.Exit(1)

    # Verify the lesson exists
    lesson_path = get_lessons_dir() / lesson
    if not lesson_path.exists():
        typer.echo(f"❌ Lesson file not found: {lesson}")
        raise typer.Exit(1)

    # Check if already completed
    completed_names = [
        item["name"] for item in metadata.get("completed_lessons", [])
    ]
    if lesson in completed_names:
        typer.echo(f"ℹ️  Lesson '{lesson}' is already marked as completed.")
        return

    # Add to completed lessons
    if "completed_lessons" not in metadata:
        metadata["completed_lessons"] = []

    metadata["completed_lessons"].append(
        {"name": lesson, "completed_at": datetime.datetime.now().isoformat()}
    )

    # If this was the current lesson, find the next one
    if lesson == metadata.get("current_lesson"):
        next_lesson = get_next_lesson(lesson, metadata)

        if next_lesson:
            metadata["current_lesson"] = next_lesson
            typer.echo(f"✅ Marked lesson '{lesson}' as completed!")
            typer.echo(f"📚 New current lesson: {next_lesson}")
        else:
            metadata["current_lesson"] = None
            typer.echo(f"✅ Marked lesson '{lesson}' as completed!")
            typer.echo("🎉 Congratulations! You've completed all lessons.")
    else:
        typer.echo(f"✅ Marked lesson '{lesson}' as completed!")

    save_metadata(metadata)


@learn_app.command("next")
def next_lesson():
    """Complete current lesson and move to the next one."""
    metadata = load_metadata()
    current = metadata.get("current_lesson")

    if not current:
        typer.echo("❌ No current lesson set. Use 'mystuff learn start' to set one.")
        raise typer.Exit(1)

    # Mark current as complete
    complete_lesson(current)

    # Open the new current lesson if available
    if metadata.get("current_lesson"):
        if typer.confirm("Open the next lesson now?", default=True):
            open_current_lesson()
    else:
        typer.echo("🎉 No more lessons to complete!")


@learn_app.command("start")
def start_lesson(
    lesson: Annotated[
        Optional[str], typer.Argument(help="Name of the lesson to set as current")
    ] = None,
    fzf: Annotated[
        bool, typer.Option("--fzf", help="Use fzf to select a lesson")
    ] = False,
    directory: Annotated[
        Optional[str],
        typer.Option("--dir", "-d", help="Filter by directory"),
    ] = None,
):
    """Set a specific lesson as the current one."""
    metadata = load_metadata()
    all_lessons = get_all_lessons(recursive=True)

    if not all_lessons:
        typer.echo("❌ No lessons found. Create some in the lessons directory first.")
        raise typer.Exit(1)

    # Filter by directory if specified
    if directory:
        all_lessons = [
            l for l in all_lessons if l["name"].startswith(f"{directory}/")
        ]

        if not all_lessons:
            typer.echo(f"❌ No lessons found in directory: {directory}")
            raise typer.Exit(1)

    if fzf:
        # Use fzf to select a lesson
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as temp_input:
            for l_item in all_lessons:
                temp_input.write(f"{l_item['name']}\n")
            temp_input_path = temp_input.name

        output_file = tempfile.mktemp(suffix=".txt")

        try:
            # Run fzf
            cmd = (
                f"cat {temp_input_path} | fzf --height=40% --layout=reverse "
                f"--prompt='Select lesson: ' > {output_file}"
            )
            result = os.system(cmd)

            if result == 0:
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        selected = f.read().strip()

                    if selected:
                        lesson = selected
                    else:
                        typer.echo("❌ No lesson selected.")
                        raise typer.Exit(1)
                except FileNotFoundError:
                    typer.echo("❌ No lesson selected.")
                    raise typer.Exit(1)
            else:
                typer.echo("❌ No lesson selected.")
                raise typer.Exit(1)

        finally:
            # Clean up temp files
            try:
                os.unlink(temp_input_path)
            except OSError:
                pass
            try:
                os.unlink(output_file)
            except OSError:
                pass

    # Verify the lesson exists if specified
    if lesson:
        lesson_path = get_lessons_dir() / lesson
        if not lesson_path.exists():
            typer.echo(f"❌ Lesson file not found: {lesson}")
            raise typer.Exit(1)
    else:
        # Select first uncompleted lesson
        completed_names = [
            item["name"] for item in metadata.get("completed_lessons", [])
        ]
        uncompleted = [
            l for l in all_lessons if l["name"] not in completed_names
        ]

        if uncompleted:
            lesson = uncompleted[0]["name"]
        else:
            lesson = all_lessons[0]["name"]
            typer.echo("ℹ️  All lessons are completed. Starting from the first one.")

    # Update current lesson
    metadata["current_lesson"] = lesson
    save_metadata(metadata)
    typer.echo(f"📚 Current lesson set to: {lesson}")

    # Ask if user wants to open it
    if typer.confirm("Open this lesson now?", default=True):
        open_current_lesson()


@learn_app.command("stats")
def show_stats():
    """Show learning statistics."""
    metadata = load_metadata()
    all_lessons = get_all_lessons()

    if not all_lessons:
        typer.echo("❌ No lessons found. Create some in the lessons directory first.")
        return

    completed = metadata.get("completed_lessons", [])

    # Calculate statistics
    total_lessons = len(all_lessons)
    completed_count = len(completed)
    pending_count = total_lessons - completed_count
    completion_pct = (
        (completed_count / total_lessons) * 100 if total_lessons > 0 else 0
    )

    # Get first and last completion dates
    first_date = None
    last_date = None
    days = 0
    avg_per_day = 0

    if completed:
        dates = [
            datetime.datetime.fromisoformat(item["completed_at"])
            for item in completed
            if "completed_at" in item
        ]
        if dates:
            first_date = min(dates).date()
            last_date = max(dates).date()

            # Calculate average lessons per day
            days = (last_date - first_date).days + 1
            avg_per_day = completed_count / days if days > 0 else completed_count

    # Display statistics
    console = Console()
    console.print("[bold blue]📊 Learning Statistics[/bold blue]\n")

    console.print(f"📚 Total lessons: {total_lessons}")
    console.print(f"✅ Completed: {completed_count} ({completion_pct:.1f}%)")
    console.print(f"⏳ Pending: {pending_count}")

    if first_date:
        console.print(f"\n📆 First completion: {first_date}")
        console.print(f"📆 Last completion: {last_date}")
        console.print(
            f"⏱️  Average: {avg_per_day:.2f} lessons/day over {days} days"
        )

    if metadata.get("current_lesson"):
        console.print(f"\n🔍 Current lesson: {metadata['current_lesson']}")
    else:
        console.print("\n❌ No current lesson set.")

    # Show last opened
    if metadata.get("last_opened"):
        last_opened = datetime.datetime.fromisoformat(metadata["last_opened"])
        console.print(f"🕒 Last opened: {last_opened.strftime('%Y-%m-%d %H:%M:%S')}")


@learn_app.command("reset")
def reset_progress(
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Skip confirmation prompt"
        ),
    ] = False,
):
    """Reset all learning progress (keeps lessons, clears metadata)."""
    if not confirm:
        if not typer.confirm(
            "⚠️  This will reset all your learning progress. Continue?",
            default=False,
        ):
            typer.echo("❌ Operation cancelled.")
            raise typer.Exit(0)

    # Reset metadata to template
    metadata = METADATA_TEMPLATE.copy()
    save_metadata(metadata)

    typer.echo("✅ Learning progress has been reset.")


if __name__ == "__main__":
    learn_app()
