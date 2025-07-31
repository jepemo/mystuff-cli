"""
Lists command for MyStuff CLI
Manages arbitrary named lists with YAML storage and import/export functionality
"""

import csv
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from typing_extensions import Annotated


def get_mystuff_dir() -> Path:
    """Get the mystuff data directory from config or environment"""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home).expanduser().resolve()
    return Path.home() / ".mystuff"


def get_lists_dir() -> Path:
    """Get the path to the lists directory"""
    return get_mystuff_dir() / "lists"


def ensure_lists_dir_exists():
    """Ensure the lists directory exists"""
    lists_dir = get_lists_dir()
    lists_dir.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug"""
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def get_list_filename(list_name: str) -> str:
    """Generate filename for a list"""
    return f"{slugify(list_name)}.yaml"


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


def load_list_from_file(file_path: Path) -> Dict[str, Any]:
    """Load a list from a YAML file"""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data if isinstance(data, dict) else {}
    except Exception as e:
        typer.echo(f"Error loading list from {file_path}: {e}", err=True)
        return {}


def save_list_to_file(file_path: Path, list_data: Dict[str, Any]):
    """Save a list to a YAML file"""
    ensure_lists_dir_exists()

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(list_data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        typer.echo(f"Error saving list to {file_path}: {e}", err=True)
        raise typer.Exit(code=1)


def get_all_lists() -> List[Dict[str, Any]]:
    """Get all lists from the lists directory"""
    lists_dir = get_lists_dir()
    if not lists_dir.exists():
        return []

    all_lists = []
    for file_path in lists_dir.glob("*.yaml"):
        list_data = load_list_from_file(file_path)
        if list_data:
            list_data["file_path"] = file_path
            list_data["filename"] = file_path.stem
            all_lists.append(list_data)

    # Sort by name
    all_lists.sort(key=lambda x: x.get("name", "").lower())
    return all_lists


def find_list_by_name(list_name: str) -> Optional[Dict[str, Any]]:
    """Find a list by its name"""
    filename = get_list_filename(list_name)
    file_path = get_lists_dir() / filename

    list_data = load_list_from_file(file_path)
    if list_data:
        list_data["file_path"] = file_path
        list_data["filename"] = file_path.stem
        return list_data

    return None


def create_or_update_list(
    list_name: str, items: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create or update a list"""
    filename = get_list_filename(list_name)
    file_path = get_lists_dir() / filename

    # Load existing list or create new one
    list_data = load_list_from_file(file_path)

    if not list_data:
        # Create new list
        list_data = {
            "name": list_name,
            "items": items or [],
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
        }
    else:
        # Update existing list
        if items is not None:
            list_data["items"] = items
        list_data["modified"] = datetime.now().isoformat()

    # Save to file
    save_list_to_file(file_path, list_data)

    return list_data


def delete_list_file(list_name: str) -> bool:
    """Delete a list"""
    filename = get_list_filename(list_name)
    file_path = get_lists_dir() / filename

    if file_path.exists():
        try:
            file_path.unlink()
            return True
        except Exception as e:
            typer.echo(f"Error deleting list: {e}", err=True)
            return False
    return False


def add_item_to_list(list_name: str, item_text: str) -> bool:
    """Add an item to a list"""
    list_data = find_list_by_name(list_name)
    if not list_data:
        typer.echo(f"List '{list_name}' not found", err=True)
        return False

    items = list_data.get("items", [])
    new_item = {
        "text": item_text,
        "checked": False,
        "added": datetime.now().isoformat(),
    }

    items.append(new_item)
    create_or_update_list(list_name, items)
    return True


def remove_item_from_list(list_name: str, item_text: str) -> bool:
    """Remove an item from a list"""
    list_data = find_list_by_name(list_name)
    if not list_data:
        typer.echo(f"List '{list_name}' not found", err=True)
        return False

    items = list_data.get("items", [])
    original_length = len(items)

    # Remove items that match the text
    items = [item for item in items if item.get("text", "") != item_text]

    if len(items) < original_length:
        create_or_update_list(list_name, items)
        return True

    return False


def check_item_in_list(list_name: str, item_text: str, checked: bool = True) -> bool:
    """Check or uncheck an item in a list"""
    list_data = find_list_by_name(list_name)
    if not list_data:
        typer.echo(f"List '{list_name}' not found", err=True)
        return False

    items = list_data.get("items", [])
    item_found = False

    for item in items:
        if item.get("text", "") == item_text:
            item["checked"] = checked
            item["modified"] = datetime.now().isoformat()
            item_found = True
            break

    if item_found:
        create_or_update_list(list_name, items)
        return True

    return False


def select_list_with_fzf(lists: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Use fzf to select a list interactively"""
    if not lists:
        return None

    # Create options for fzf
    options = []
    for list_data in lists:
        name = list_data.get("name", "")
        items = list_data.get("items", [])
        total_items = len(items)
        checked_items = sum(1 for item in items if item.get("checked", False))

        option = f"{name} ({checked_items}/{total_items} completed)"
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
            f"--prompt='Select list: ' > {output_file}"
        )
        result = os.system(cmd)

        if result == 0:  # Success
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    selected_line = f.read().strip()

                if selected_line:
                    # Find the corresponding list
                    for i, option in enumerate(options):
                        if option == selected_line:
                            return lists[i]
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


def select_item_with_fzf(
    items: List[Dict[str, Any]], prompt: str = "Select item: "
) -> Optional[Dict[str, Any]]:
    """Use fzf to select an item interactively"""
    if not items:
        return None

    # Create options for fzf
    options = []
    for item in items:
        text = item.get("text", "")
        checked = item.get("checked", False)
        status = "✓" if checked else "○"

        option = f"{status} {text}"
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
            f"--prompt='{prompt}' > {output_file}"
        )
        result = os.system(cmd)

        if result == 0:  # Success
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    selected_line = f.read().strip()

                if selected_line:
                    # Find the corresponding item
                    for i, option in enumerate(options):
                        if option == selected_line:
                            return items[i]
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


def search_lists_by_text(
    lists: List[Dict[str, Any]], search_text: str
) -> List[Dict[str, Any]]:
    """Search lists by name or item content"""
    search_lower = search_text.lower()
    filtered_lists = []

    for list_data in lists:
        # Search in list name
        name = list_data.get("name", "").lower()
        if search_lower in name:
            filtered_lists.append(list_data)
            continue

        # Search in item text
        items = list_data.get("items", [])
        for item in items:
            item_text = item.get("text", "").lower()
            if search_lower in item_text:
                filtered_lists.append(list_data)
                break

    return filtered_lists


def export_list_to_csv(list_data: Dict[str, Any], output_file: Path):
    """Export a list to CSV format"""
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["text", "checked", "added", "modified"])

            items = list_data.get("items", [])
            for item in items:
                writer.writerow(
                    [
                        item.get("text", ""),
                        item.get("checked", False),
                        item.get("added", ""),
                        item.get("modified", ""),
                    ]
                )
    except Exception as e:
        typer.echo(f"Error exporting to CSV: {e}", err=True)
        raise typer.Exit(code=1)


def export_list_to_yaml(list_data: Dict[str, Any], output_file: Path):
    """Export a list to YAML format"""
    try:
        # Create a clean copy without the file_path and filename fields
        clean_data = {
            k: v for k, v in list_data.items() if k not in ["file_path", "filename"]
        }

        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(clean_data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        typer.echo(f"Error exporting to YAML: {e}", err=True)
        raise typer.Exit(code=1)


def import_list_from_csv(list_name: str, input_file: Path) -> bool:
    """Import a list from CSV format"""
    try:
        items = []
        with open(input_file, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                item = {
                    "text": row.get("text", ""),
                    "checked": row.get("checked", "").lower() in ("true", "1", "yes"),
                    "added": row.get("added", datetime.now().isoformat()),
                    "modified": row.get("modified", ""),
                }
                items.append(item)

        create_or_update_list(list_name, items)
        return True
    except Exception as e:
        typer.echo(f"Error importing from CSV: {e}", err=True)
        return False


def import_list_from_yaml(list_name: str, input_file: Path) -> bool:
    """Import a list from YAML format"""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict) and "items" in data:
            items = data["items"]
            create_or_update_list(list_name, items)
            return True
        else:
            typer.echo(
                "Invalid YAML format: expected a dictionary with 'items' key", err=True
            )
            return False
    except Exception as e:
        typer.echo(f"Error importing from YAML: {e}", err=True)
        return False


def create_list(
    name: Annotated[str, typer.Option("--name", help="Name of the list to create")],
):
    """Create a new list"""
    if not name:
        typer.echo("Error: List name is required", err=True)
        raise typer.Exit(code=1)

    # Check if list already exists
    existing_list = find_list_by_name(name)
    if existing_list:
        typer.echo(f"List '{name}' already exists", err=True)
        raise typer.Exit(code=1)

    # Create new list
    create_or_update_list(name)

    typer.echo(f"✅ List created: {name}")


def view_list(
    name: Annotated[str, typer.Option("--name", help="Name of the list to view")],
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """View a list"""
    if not name:
        typer.echo("Error: List name is required", err=True)
        raise typer.Exit(code=1)

    list_data = find_list_by_name(name)
    if not list_data:
        typer.echo(f"List '{name}' not found", err=True)
        raise typer.Exit(code=1)

    items = list_data.get("items", [])

    if not items:
        typer.echo(f"List '{name}' is empty")
        return

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_item = select_item_with_fzf(items, f"Items in {name}: ")
        if selected_item:
            text = selected_item.get("text", "")
            checked = selected_item.get("checked", False)
            status = "✓" if checked else "○"
            typer.echo(f"{status} {text}")
        return

    # Display all items
    typer.echo(f"List: {name}")
    typer.echo("=" * (len(name) + 6))

    for item in items:
        text = item.get("text", "")
        checked = item.get("checked", False)
        status = "✓" if checked else "○"
        typer.echo(f"{status} {text}")


def edit_list(
    name: Annotated[str, typer.Option("--name", help="Name of the list to edit")],
    item: Annotated[
        Optional[str], typer.Option("--item", help="Add an item to the list")
    ] = None,
    remove_item: Annotated[
        Optional[str],
        typer.Option("--remove-item", help="Remove an item from the list"),
    ] = None,
    check: Annotated[
        Optional[str], typer.Option("--check", help="Mark an item as checked")
    ] = None,
    uncheck: Annotated[
        Optional[str], typer.Option("--uncheck", help="Mark an item as unchecked")
    ] = None,
):
    """Edit a list"""
    if not name:
        typer.echo("Error: List name is required", err=True)
        raise typer.Exit(code=1)

    list_data = find_list_by_name(name)
    if not list_data:
        typer.echo(f"List '{name}' not found", err=True)
        raise typer.Exit(code=1)

    # Add item
    if item:
        if add_item_to_list(name, item):
            typer.echo(f"✅ Added item to {name}: {item}")
        else:
            typer.echo(f"Error adding item to {name}", err=True)
            raise typer.Exit(code=1)

    # Remove item
    if remove_item:
        if remove_item_from_list(name, remove_item):
            typer.echo(f"✅ Removed item from {name}: {remove_item}")
        else:
            typer.echo(f"Item not found in {name}: {remove_item}", err=True)

    # Check item
    if check:
        if check_item_in_list(name, check, True):
            typer.echo(f"✅ Checked item in {name}: {check}")
        else:
            typer.echo(f"Item not found in {name}: {check}", err=True)

    # Uncheck item
    if uncheck:
        if check_item_in_list(name, uncheck, False):
            typer.echo(f"✅ Unchecked item in {name}: {uncheck}")
        else:
            typer.echo(f"Item not found in {name}: {uncheck}", err=True)

    # If no operation was specified, show help
    if not any([item, remove_item, check, uncheck]):
        typer.echo(
            "No operation specified. Use --help to see available options.", err=True
        )


def delete_list(
    name: Annotated[str, typer.Option("--name", help="Name of the list to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force deletion without confirmation")
    ] = False,
):
    """Delete a list"""
    if not name:
        typer.echo("Error: List name is required", err=True)
        raise typer.Exit(code=1)

    list_data = find_list_by_name(name)
    if not list_data:
        typer.echo(f"List '{name}' not found", err=True)
        raise typer.Exit(code=1)

    # Confirm deletion
    if not force:
        items = list_data.get("items", [])
        item_count = len(items)
        if not typer.confirm(
            f"Are you sure you want to delete list '{name}' with {item_count} items?"
        ):
            typer.echo("Deletion cancelled.")
            return

    # Delete list
    if delete_list_file(name):
        typer.echo(f"✅ List deleted: {name}")
    else:
        typer.echo(f"Error deleting list: {name}", err=True)


def search_lists(
    search: Annotated[
        str,
        typer.Option("--search", help="Search for lists or items by name or content"),
    ],
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """Search lists"""
    if not search:
        typer.echo("Error: Search term is required", err=True)
        raise typer.Exit(code=1)

    all_lists = get_all_lists()
    filtered_lists = search_lists_by_text(all_lists, search)

    if not filtered_lists:
        typer.echo(f"No lists found matching '{search}'")
        return

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_list = select_list_with_fzf(filtered_lists)
        if selected_list:
            name = selected_list.get("name", "")
            items = selected_list.get("items", [])
            total_items = len(items)
            checked_items = sum(1 for item in items if item.get("checked", False))

            typer.echo(f"List: {name}")
            typer.echo(f"Items: {checked_items}/{total_items} completed")

            if items:
                typer.echo("Items:")
                for item in items:
                    text = item.get("text", "")
                    checked = item.get("checked", False)
                    status = "✓" if checked else "○"
                    typer.echo(f"  {status} {text}")
        return

    # Display search results
    typer.echo(f"Found {len(filtered_lists)} lists matching '{search}':")
    for list_data in filtered_lists:
        name = list_data.get("name", "")
        items = list_data.get("items", [])
        total_items = len(items)
        checked_items = sum(1 for item in items if item.get("checked", False))

        typer.echo(f"  {name} ({checked_items}/{total_items} completed)")


def export_list(
    name: Annotated[str, typer.Option("--name", help="Name of the list to export")],
    export: Annotated[
        str,
        typer.Option(
            "--export", help="Export the list to a file in CSV or YAML format"
        ),
    ],
):
    """Export a list to a file"""
    if not name:
        typer.echo("Error: List name is required", err=True)
        raise typer.Exit(code=1)

    if not export:
        typer.echo("Error: Export filename is required", err=True)
        raise typer.Exit(code=1)

    list_data = find_list_by_name(name)
    if not list_data:
        typer.echo(f"List '{name}' not found", err=True)
        raise typer.Exit(code=1)

    export_path = Path(export)
    extension = export_path.suffix.lower()

    if extension == ".csv":
        export_list_to_csv(list_data, export_path)
        typer.echo(f"✅ List exported to CSV: {export_path}")
    elif extension in [".yaml", ".yml"]:
        export_list_to_yaml(list_data, export_path)
        typer.echo(f"✅ List exported to YAML: {export_path}")
    else:
        typer.echo(
            "Error: Export format must be CSV (.csv) or YAML (.yaml/.yml)", err=True
        )
        raise typer.Exit(code=1)


def import_list(
    name: Annotated[str, typer.Option("--name", help="Name of the list to import to")],
    import_file: Annotated[
        str, typer.Option("--import", help="Import a list from a CSV or YAML file")
    ],
):
    """Import a list from a file"""
    if not name:
        typer.echo("Error: List name is required", err=True)
        raise typer.Exit(code=1)

    if not import_file:
        typer.echo("Error: Import filename is required", err=True)
        raise typer.Exit(code=1)

    import_path = Path(import_file)
    if not import_path.exists():
        typer.echo(f"Error: Import file not found: {import_path}", err=True)
        raise typer.Exit(code=1)

    extension = import_path.suffix.lower()

    if extension == ".csv":
        if import_list_from_csv(name, import_path):
            typer.echo(f"✅ List imported from CSV: {name}")
        else:
            raise typer.Exit(code=1)
    elif extension in [".yaml", ".yml"]:
        if import_list_from_yaml(name, import_path):
            typer.echo(f"✅ List imported from YAML: {name}")
        else:
            raise typer.Exit(code=1)
    else:
        typer.echo(
            "Error: Import format must be CSV (.csv) or YAML (.yaml/.yml)", err=True
        )
        raise typer.Exit(code=1)


def list_all_lists(
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="Disable interactive selection even if fzf is available",
        ),
    ] = False,
):
    """List all available lists"""
    all_lists = get_all_lists()

    if not all_lists:
        typer.echo("No lists found.")
        return

    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_list = select_list_with_fzf(all_lists)
        if selected_list:
            name = selected_list.get("name", "")
            items = selected_list.get("items", [])
            total_items = len(items)
            checked_items = sum(1 for item in items if item.get("checked", False))

            typer.echo(f"List: {name}")
            typer.echo(f"Items: {checked_items}/{total_items} completed")

            if items:
                typer.echo("Items:")
                for item in items:
                    text = item.get("text", "")
                    checked = item.get("checked", False)
                    status = "✓" if checked else "○"
                    typer.echo(f"  {status} {text}")
        return

    # Display all lists
    typer.echo("Available lists:")
    for list_data in all_lists:
        name = list_data.get("name", "")
        items = list_data.get("items", [])
        total_items = len(items)
        checked_items = sum(1 for item in items if item.get("checked", False))

        typer.echo(f"  {name} ({checked_items}/{total_items} completed)")


# Create the Typer app for list commands
list_app = typer.Typer(name="list", help="Manage arbitrary named lists")

list_app.command("create")(create_list)
list_app.command("view")(view_list)
list_app.command("edit")(edit_list)
list_app.command("delete")(delete_list)
list_app.command("search")(search_lists)
list_app.command("export")(export_list)
list_app.command("import")(import_list)
list_app.command("list")(list_all_lists)

if __name__ == "__main__":
    list_app()
