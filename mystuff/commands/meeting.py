"""
Meeting command for MyStuff CLI
Manages meeting notes with Markdown files and YAML front-matter
"""
import typer
from pathlib import Path
from typing_extensions import Annotated
from typing import List, Optional
import os
import yaml
import subprocess
import re
from datetime import datetime

def get_mystuff_dir() -> Path:
    """Get the mystuff data directory from config or environment"""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home).expanduser().resolve()
    return Path.home() / ".mystuff"

def get_meetings_dir() -> Path:
    """Get the path to the meetings directory"""
    return get_mystuff_dir() / "meetings"

def ensure_meetings_dir_exists():
    """Ensure the meetings directory exists"""
    meetings_dir = get_meetings_dir()
    meetings_dir.mkdir(parents=True, exist_ok=True)

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug"""
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().replace(" ", "-")
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug

def get_meeting_filename(date: str, title: str) -> str:
    """Generate filename for a meeting note"""
    slug = slugify(title)
    return f"{date}_{slug}.md"

def parse_participants(participants_str: str) -> List[str]:
    """Parse comma-separated participants string"""
    if not participants_str:
        return []
    return [p.strip() for p in participants_str.split(",") if p.strip()]

def get_editor() -> str:
    """Get the editor from environment or config"""
    return os.getenv("EDITOR", "vim")

def load_meeting_from_file(file_path: Path) -> dict:
    """Load meeting metadata and content from a markdown file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split front-matter and body
    if content.startswith('---\n'):
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            front_matter = parts[1]
            body = parts[2].strip()
            
            # Parse YAML front-matter
            metadata = yaml.safe_load(front_matter)
            metadata['body'] = body
            metadata['file_path'] = file_path
            return metadata
    
    # No front-matter found
    return {
        'title': file_path.stem,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'participants': [],
        'tags': [],
        'body': content,
        'file_path': file_path
    }

def save_meeting_to_file(file_path: Path, title: str, date: str, participants: List[str], tags: List[str], body: str):
    """Save meeting metadata and content to a markdown file"""
    # Create front-matter
    front_matter = {
        'title': title,
        'date': date,
        'participants': participants,
        'tags': tags
    }
    
    # Write file with YAML front-matter
    with open(file_path, 'w') as f:
        f.write('---\n')
        yaml.dump(front_matter, f, default_flow_style=False)
        f.write('---\n\n')
        f.write(body)

def load_template(template_path: str) -> str:
    """Load template content from file"""
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        typer.echo(f"Template file not found: {template_path}", err=True)
        return ""
    except Exception as e:
        typer.echo(f"Error reading template: {e}", err=True)
        return ""

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

def add_meeting(
    title: Annotated[str, typer.Option("--title", help="Title of the meeting (required)")],
    date: Annotated[Optional[str], typer.Option("--date", help="Date of the meeting in YYYY-MM-DD format (defaults to today)")] = None,
    participants: Annotated[Optional[str], typer.Option("--participants", help="Comma-separated list of participants")] = None,
    body: Annotated[Optional[str], typer.Option("--body", help="Free-text content or agenda of the meeting")] = None,
    template: Annotated[Optional[str], typer.Option("--template", help="Path to a template file for pre-filling the meeting body")] = None,
    tags: Annotated[Optional[List[str]], typer.Option("--tag", help="One or more tags for categorization")] = None,
):
    """Add a new meeting note"""
    if not title:
        typer.echo("Error: Title is required", err=True)
        raise typer.Exit(code=1)
    
    ensure_meetings_dir_exists()
    
    # Set default date if not provided
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)
    
    # Parse participants
    participants_list = parse_participants(participants or "")
    
    # Set default tags if not provided
    if tags is None:
        tags = []
    
    # Generate filename
    filename = get_meeting_filename(date, title)
    file_path = get_meetings_dir() / filename
    
    # Check if file already exists
    if file_path.exists():
        typer.echo(f"Meeting note already exists: {filename}")
        if typer.confirm("Do you want to edit the existing note?"):
            if open_editor(file_path):
                typer.echo(f"✅ Meeting note updated: {title}")
        return
    
    # Load template if provided
    template_content = ""
    if template:
        template_content = load_template(template)
    
    # Use body or template or default content
    if body:
        meeting_body = body
    elif template_content:
        meeting_body = template_content
    else:
        meeting_body = f"""## Agenda

- 

## Notes

- 

## Action Items

- 
"""
    
    # Save the meeting file
    save_meeting_to_file(file_path, title, date, participants_list, tags, meeting_body)
    
    typer.echo(f"✅ Created meeting note: {title}")
    typer.echo(f"   Date: {date}")
    if participants_list:
        typer.echo(f"   Participants: {', '.join(participants_list)}")
    if tags:
        typer.echo(f"   Tags: {', '.join(tags)}")
    typer.echo(f"   File: {filename}")
    
    # Open in editor if no body was provided
    if not body:
        if typer.confirm("Do you want to edit the meeting note now?"):
            open_editor(file_path)

def list_meetings(
    search: Annotated[Optional[str], typer.Option("--search", help="Search by title, date, or participants")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by specific tag")] = None,
    date_filter: Annotated[Optional[str], typer.Option("--date", help="Filter by specific date (YYYY-MM-DD)")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Use fzf for interactive selection and preview")] = False,
):
    """List all meeting notes"""
    ensure_meetings_dir_exists()
    meetings_dir = get_meetings_dir()
    
    # Find all markdown files
    meeting_files = list(meetings_dir.glob("*.md"))
    
    if not meeting_files:
        typer.echo("No meeting notes found. Use 'mystuff meeting add --title <TITLE>' to create your first meeting note.")
        return
    
    # Load all meetings
    meetings = []
    for file_path in meeting_files:
        try:
            meeting = load_meeting_from_file(file_path)
            meetings.append(meeting)
        except Exception as e:
            typer.echo(f"Error loading {file_path}: {e}", err=True)
    
    # Filter meetings
    if search:
        search_lower = search.lower()
        meetings = [m for m in meetings if (
            search_lower in m.get('title', '').lower() or
            search_lower in m.get('date', '').lower() or
            any(search_lower in p.lower() for p in m.get('participants', []))
        )]
    
    if tag:
        meetings = [m for m in meetings if tag in m.get('tags', [])]
    
    if date_filter:
        meetings = [m for m in meetings if m.get('date') == date_filter]
    
    if not meetings:
        typer.echo("No meeting notes found matching your criteria.")
        return
    
    # Sort by date (newest first)
    meetings.sort(key=lambda m: m.get('date', ''), reverse=True)
    
    # Use fzf for interactive listing if requested and available
    if interactive and is_fzf_available():
        typer.echo("🔍 Interactive meeting browser (press Enter to view, Ctrl+C to exit):")
        selected_meeting = select_meeting_with_fzf(meetings)
        if selected_meeting:
            # Show detailed view of selected meeting
            typer.echo(f"\n📅 {selected_meeting.get('title', 'Untitled')}")
            typer.echo(f"   Date: {selected_meeting.get('date', 'Unknown')}")
            if selected_meeting.get('participants'):
                typer.echo(f"   Participants: {', '.join(selected_meeting['participants'])}")
            if selected_meeting.get('tags'):
                typer.echo(f"   Tags: {', '.join(selected_meeting['tags'])}")
            typer.echo(f"   File: {selected_meeting['file_path'].name}")
            
            # Show content preview
            body = selected_meeting.get('body', '')
            if body:
                typer.echo(f"\n📝 Content Preview:")
                # Show first few lines
                lines = body.split('\n')[:10]
                for line in lines:
                    typer.echo(f"   {line}")
                if len(body.split('\n')) > 10:
                    typer.echo("   ...")
        return
    
    # Standard listing
    for i, meeting in enumerate(meetings, 1):
        typer.echo(f"{i}. {meeting.get('title', 'Untitled')}")
        typer.echo(f"   Date: {meeting.get('date', 'Unknown')}")
        if meeting.get('participants'):
            typer.echo(f"   Participants: {', '.join(meeting['participants'])}")
        if meeting.get('tags'):
            typer.echo(f"   Tags: {', '.join(meeting['tags'])}")
        typer.echo(f"   File: {meeting['file_path'].name}")
        typer.echo()

def edit_meeting(
    title: Annotated[Optional[str], typer.Option("--title", help="Title of the meeting to edit (optional if using fzf)")] = None,
    date: Annotated[Optional[str], typer.Option("--date", help="Date of the meeting (if title is not unique)")] = None,
):
    """Edit an existing meeting note"""
    ensure_meetings_dir_exists()
    meetings_dir = get_meetings_dir()
    
    # Load all meetings
    meeting_files = list(meetings_dir.glob("*.md"))
    all_meetings = []
    
    for file_path in meeting_files:
        try:
            meeting = load_meeting_from_file(file_path)
            all_meetings.append(meeting)
        except Exception as e:
            typer.echo(f"Error loading {file_path}: {e}", err=True)
    
    if not all_meetings:
        typer.echo("No meeting notes found. Use 'mystuff meeting add --title <TITLE>' to create your first meeting note.")
        return
    
    selected_meeting = None
    
    # If no title provided and fzf is available, use fzf for selection
    if not title and is_fzf_available():
        typer.echo("🔍 Select a meeting to edit:")
        selected_meeting = select_meeting_with_fzf(all_meetings)
        if not selected_meeting:
            typer.echo("No meeting selected.")
            return
    
    # If title is provided or fzf is not available, use traditional search
    if not selected_meeting:
        if not title:
            typer.echo("Error: Title is required to identify the meeting to edit (or install fzf for interactive selection)", err=True)
            raise typer.Exit(code=1)
        
        # Find matching meetings
        matching_meetings = []
        for meeting in all_meetings:
            if meeting.get('title', '').lower() == title.lower():
                if not date or meeting.get('date') == date:
                    matching_meetings.append(meeting)
        
        if not matching_meetings:
            typer.echo(f"Meeting note not found: {title}")
            if date:
                typer.echo(f"(with date: {date})")
            raise typer.Exit(code=1)
        
        if len(matching_meetings) > 1:
            typer.echo(f"Multiple meetings found with title '{title}':")
            for i, meeting in enumerate(matching_meetings, 1):
                typer.echo(f"  {i}. {meeting['date']} - {meeting['title']}")
            typer.echo("Please specify --date to choose the correct meeting.")
            raise typer.Exit(code=1)
        
        selected_meeting = matching_meetings[0]
    
    # Edit the selected meeting
    file_path = selected_meeting['file_path']
    
    if open_editor(file_path):
        typer.echo(f"✅ Meeting note updated: {selected_meeting['title']}")
    else:
        typer.echo("Failed to open editor")
        raise typer.Exit(code=1)

def delete_meeting(
    title: Annotated[Optional[str], typer.Option("--title", help="Title of the meeting to delete (optional if using fzf)")] = None,
    date: Annotated[Optional[str], typer.Option("--date", help="Date of the meeting (if title is not unique)")] = None,
):
    """Delete a meeting note"""
    ensure_meetings_dir_exists()
    meetings_dir = get_meetings_dir()
    
    # Load all meetings
    meeting_files = list(meetings_dir.glob("*.md"))
    all_meetings = []
    
    for file_path in meeting_files:
        try:
            meeting = load_meeting_from_file(file_path)
            all_meetings.append(meeting)
        except Exception as e:
            typer.echo(f"Error loading {file_path}: {e}", err=True)
    
    if not all_meetings:
        typer.echo("No meeting notes found.")
        raise typer.Exit(code=1)
    
    selected_meeting = None
    
    # If no title provided and fzf is available, use fzf for selection
    if not title and is_fzf_available():
        typer.echo("🔍 Select a meeting to delete:")
        selected_meeting = select_meeting_with_fzf(all_meetings)
        if not selected_meeting:
            typer.echo("No meeting selected.")
            return
    
    # If title is provided or fzf is not available, use traditional search
    if not selected_meeting:
        if not title:
            typer.echo("Error: Title is required to identify the meeting to delete (or install fzf for interactive selection)", err=True)
            raise typer.Exit(code=1)
        
        # Find matching meetings
        matching_meetings = []
        for meeting in all_meetings:
            if meeting.get('title', '').lower() == title.lower():
                if not date or meeting.get('date') == date:
                    matching_meetings.append(meeting)
        
        if not matching_meetings:
            typer.echo(f"Meeting note not found: {title}")
            if date:
                typer.echo(f"(with date: {date})")
            raise typer.Exit(code=1)
        
        if len(matching_meetings) > 1:
            typer.echo(f"Multiple meetings found with title '{title}':")
            for i, meeting in enumerate(matching_meetings, 1):
                typer.echo(f"  {i}. {meeting['date']} - {meeting['title']}")
            typer.echo("Please specify --date to choose the correct meeting.")
            raise typer.Exit(code=1)
        
        selected_meeting = matching_meetings[0]
    
    # Delete the selected meeting
    file_path = selected_meeting['file_path']
    
    if typer.confirm(f"Are you sure you want to delete '{selected_meeting['title']}' ({selected_meeting['date']})?"):
        file_path.unlink()
        typer.echo(f"✅ Deleted meeting note: {selected_meeting['title']}")
    else:
        typer.echo("Deletion cancelled.")

def search_meetings(
    query: Annotated[str, typer.Argument(help="Search query")],
):
    """Search meeting notes by title, date, or participants"""
    ensure_meetings_dir_exists()
    meetings_dir = get_meetings_dir()
    
    # Find all markdown files
    meeting_files = list(meetings_dir.glob("*.md"))
    
    if not meeting_files:
        typer.echo("No meeting notes found.")
        return
    
    # Load and search meetings
    matching_meetings = []
    query_lower = query.lower()
    
    for file_path in meeting_files:
        try:
            meeting = load_meeting_from_file(file_path)
            if (query_lower in meeting.get('title', '').lower() or
                query_lower in meeting.get('date', '').lower() or
                any(query_lower in p.lower() for p in meeting.get('participants', [])) or
                query_lower in meeting.get('body', '').lower()):
                matching_meetings.append(meeting)
        except Exception:
            continue
    
    if not matching_meetings:
        typer.echo(f"No meeting notes found matching '{query}'")
        return
    
    # Sort by date (newest first)
    matching_meetings.sort(key=lambda m: m.get('date', ''), reverse=True)
    
    # Display matching meetings
    for i, meeting in enumerate(matching_meetings, 1):
        typer.echo(f"{i}. {meeting.get('title', 'Untitled')}")
        typer.echo(f"   Date: {meeting.get('date', 'Unknown')}")
        if meeting.get('participants'):
            typer.echo(f"   Participants: {', '.join(meeting['participants'])}")
        if meeting.get('tags'):
            typer.echo(f"   Tags: {', '.join(meeting['tags'])}")
        typer.echo(f"   File: {meeting['file_path'].name}")
        typer.echo()

def is_fzf_available() -> bool:
    """Check if fzf is available in the system"""
    try:
        subprocess.run(['fzf', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def select_meeting_with_fzf(meetings: List[dict]) -> Optional[dict]:
    """Use fzf to select a meeting from the list"""
    if not meetings:
        return None
    
    # Prepare the list for fzf
    fzf_input = []
    for meeting in meetings:
        title = meeting.get('title', 'Untitled')
        date = meeting.get('date', 'Unknown')
        participants = ', '.join(meeting.get('participants', []))
        tags = ', '.join(meeting.get('tags', []))
        
        # Format: "YYYY-MM-DD | Title | Participants | Tags"
        line = f"{date} | {title}"
        if participants:
            line += f" | {participants}"
        if tags:
            line += f" | [{tags}]"
        
        fzf_input.append(line)
    
    try:
        # Run fzf
        process = subprocess.run(
            ['fzf', '--prompt=Select meeting: ', '--height=40%', '--reverse'],
            input='\n'.join(fzf_input),
            text=True,
            capture_output=True,
            check=True
        )
        
        selected_line = process.stdout.strip()
        if not selected_line:
            return None
        
        # Find the corresponding meeting
        for i, line in enumerate(fzf_input):
            if line == selected_line:
                return meetings[i]
        
        return None
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

# Create the meeting subcommand app
meeting_app = typer.Typer(
    name="meeting",
    help="Manage meeting notes",
    add_completion=False,
)

meeting_app.command("add")(add_meeting)
meeting_app.command("list")(list_meetings)
meeting_app.command("edit")(edit_meeting)
meeting_app.command("delete")(delete_meeting)
meeting_app.command("search")(search_meetings)
