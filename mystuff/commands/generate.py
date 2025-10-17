#!/usr/bin/env python3
"""
MyStuff CLI - Generate static content functionality
"""
import json
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2
import typer
import yaml
from rich.console import Console
from typing_extensions import Annotated

console = Console()

generate_app = typer.Typer(help="Generate static content from mystuff data")


def get_mystuff_dir() -> Path:
    """Get the mystuff directory path."""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home)
    return Path.home() / ".mystuff"


def get_config_path() -> Path:
    """Get the config file path."""
    return get_mystuff_dir() / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load mystuff configuration."""
    config_path = get_config_path()
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[yellow]⚠️  Warning: Could not load config: {e}[/yellow]")
        return {}


def extract_lesson_title(lesson_content: str) -> Optional[str]:
    """
    Extract and format lesson title from markdown content.
    
    Expected format in the markdown:
        # Day XXX: Title
        # Topic: Topic Name
    
    Returns formatted as: "Day XXX: Title (Topic Name)"
    
    Args:
        lesson_content: The markdown content of the lesson
        
    Returns:
        Formatted title string or None if format doesn't match
    """
    import re
    
    lines = lesson_content.strip().split('\n')
    
    day_title = None
    topic = None
    
    for line in lines:
        line = line.strip()
        
        # Match "# Day XXX: Title"
        day_match = re.match(r'^#\s+Day\s+(\d+):\s*(.+)$', line, re.IGNORECASE)
        if day_match and not day_title:
            day_number = day_match.group(1)
            title = day_match.group(2).strip()
            day_title = f"Day {day_number}: {title}"
        
        # Match "# Topic: Topic Name"
        topic_match = re.match(r'^#\s+Topic:\s*(.+)$', line, re.IGNORECASE)
        if topic_match and not topic:
            topic = topic_match.group(1).strip()
        
        # Stop if we found both
        if day_title and topic:
            break
    
    # Format the result
    if day_title and topic:
        return f"{day_title} ({topic})"
    elif day_title:
        return day_title
    elif topic:
        return topic


def extract_lesson_topic(lesson_content: str) -> Optional[str]:
    """
    Extract only the topic from markdown content.
    
    Expected format in the markdown:
        # Topic: Topic Name
    
    Args:
        lesson_content: The markdown content of the lesson
        
    Returns:
        Topic name or None if not found
    """
    import re
    
    lines = lesson_content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Match "# Topic: Topic Name"
        topic_match = re.match(r'^#\s+Topic:\s*(.+)$', line, re.IGNORECASE)
        if topic_match:
            return topic_match.group(1).strip()
    
    return None


def extract_frontmatter(content: str) -> tuple[Optional[Dict[str, Any]], str]:
    """
    Extract YAML frontmatter from markdown content.
    
    Args:
        content: The full markdown content
        
    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)
    """
    import re
    
    # Check if content starts with frontmatter delimiter
    if not content.startswith('---'):
        return None, content
    
    # Find the closing delimiter
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return None, content
    
    frontmatter_yaml = match.group(1)
    content_without_frontmatter = match.group(2)
    
    try:
        frontmatter = yaml.safe_load(frontmatter_yaml)
        return frontmatter, content_without_frontmatter
    except yaml.YAMLError:
        return None, content
    
    return None


def get_generate_config() -> Dict[str, Any]:
    """Get generate configuration from config.yaml."""
    config = load_config()
    generate_config = config.get("generate", {}).get("web", {})
    
    # Set defaults if not configured
    defaults = {
        "output": str(Path.home() / "mystuff_web"),
        "title": "My Knowledge Base",
        "description": "Personal knowledge management",
        "author": "Your Name",
        "github_username": None,
        "repositories": [],  # List of repository names to display
        "menu_items": [
            {"name": "Home", "url": "/", "icon": "home"},
        ],
    }
    
    # Merge with user config
    for key, value in defaults.items():
        if key not in generate_config:
            generate_config[key] = value
    
    return generate_config


def fetch_github_repo_details(username: str, repo_names: List[str]) -> List[Dict[str, Any]]:
    """Fetch details for specific GitHub repositories.
    
    Uses GitHub's REST API to fetch repository information for the specified
    repository names. This works without authentication for public repositories.
    
    Args:
        username: GitHub username
        repo_names: List of repository names to fetch
        
    Returns:
        List of repository dictionaries with name, description, url, and language
    """
    if not username or not repo_names:
        return []
    
    repos = []
    
    for repo_name in repo_names:
        try:
            # GitHub REST API endpoint for a specific repository
            url = f"https://api.github.com/repos/{username}/{repo_name}"
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "mystuff-cli",
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            # Make the request
            with urllib.request.urlopen(req, timeout=10) as response:
                repo_data = json.loads(response.read().decode("utf-8"))
            
            # Extract repository information
            repo = {
                "name": repo_data["name"],
                "description": repo_data.get("description", ""),
                "url": repo_data["html_url"],
                "language": repo_data.get("language")
            }
            repos.append(repo)
            
        except urllib.error.HTTPError as e:
            if e.code == 404:
                console.print(
                    f"[yellow]⚠️  Warning: Repository '{username}/{repo_name}' not found[/yellow]"
                )
            elif e.code == 403:
                console.print(
                    f"[yellow]⚠️  Warning: GitHub API rate limit exceeded. "
                    f"Skipping remaining repositories.[/yellow]"
                )
                break
            else:
                console.print(
                    f"[yellow]⚠️  Warning: Could not fetch repo '{repo_name}' (HTTP {e.code})[/yellow]"
                )
        except Exception as e:
            console.print(
                f"[yellow]⚠️  Warning: Could not fetch repo '{repo_name}': {e}[/yellow]"
            )
    
    return repos


def load_mystuff_links() -> List[Dict[str, Any]]:
    """Load links from mystuff links.jsonl file."""
    mystuff_dir = get_mystuff_dir()
    links_file = mystuff_dir / "links.jsonl"
    
    if not links_file.exists():
        console.print(
            "[yellow]⚠️  Warning: links.jsonl not found, links page will be empty[/yellow]"
        )
        return []
    
    links = []
    try:
        with open(links_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    links.append(json.loads(line))
    except Exception as e:
        console.print(f"[yellow]⚠️  Warning: Could not load links: {e}[/yellow]")
    
    return links


def load_learning_data() -> Optional[Dict[str, Any]]:
    """Load current learning lesson from metadata."""
    import re
    
    mystuff_dir = get_mystuff_dir()
    learning_dir = mystuff_dir / "learning"
    metadata_path = learning_dir / "metadata.yaml"
    
    if not metadata_path.exists():
        return None
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f)
        
        if not metadata or not metadata.get("current_lesson"):
            return None
        
        current_lesson = metadata.get("current_lesson")
        
        # Convert to string if needed and ensure filename has .md extension
        current_lesson = str(current_lesson)
        if not current_lesson.endswith('.md'):
            current_lesson = f"{current_lesson}.md"
        
        # Try to extract title from the markdown file content
        lessons_dir = learning_dir / "lessons"
        lesson_path = lessons_dir / current_lesson
        
        title = None
        if lesson_path.exists():
            try:
                with open(lesson_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Use the specialized function to extract lesson title
                title = extract_lesson_title(content)
            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Warning: Could not read lesson file: {e}[/yellow]"
                )
        
        # Fallback: extract title from filename if we couldn't read the file
        if not title:
            lesson_name = Path(current_lesson).stem
            title = re.sub(r'^\d+-?', '', lesson_name)
            title = title.replace('-', ' ').replace('_', ' ').title()
        
        # Generate URL for the lesson page
        lesson_url = f"lessons/{current_lesson.replace('.md', '.html')}"
        
        return {
            "current_lesson": current_lesson,
            "title": title if title else Path(current_lesson).stem,
            "url": lesson_url,
            "last_opened": metadata.get("last_opened"),
        }
    except Exception as e:
        console.print(f"[yellow]⚠️  Warning: Could not load learning data: {e}[/yellow]")
        return None


def load_all_lessons_with_status() -> List[Dict[str, Any]]:
    """
    Load all lessons with their status information.
    
    Returns:
        List of lessons with status, title, and navigation info
    """
    import re
    
    mystuff_dir = get_mystuff_dir()
    learning_dir = mystuff_dir / "learning"
    lessons_dir = learning_dir / "lessons"
    metadata_path = learning_dir / "metadata.yaml"
    
    if not lessons_dir.exists():
        return []
    
    # Load metadata
    metadata = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f) or {}
        except Exception:
            pass
    
    current_lesson = metadata.get("current_lesson")
    
    # Normalize current lesson to include .md extension
    if current_lesson:
        current_lesson = str(current_lesson)
        if not current_lesson.endswith('.md'):
            current_lesson = f"{current_lesson}.md"
    
    # Handle both old format (list of strings) and new format (list of dicts)
    # Normalize all to include .md extension
    completed_raw = metadata.get("completed_lessons", [])
    if completed_raw and isinstance(completed_raw[0], dict):
        completed_lessons = set()
        for item in completed_raw:
            name = str(item["name"])
            if not name.endswith('.md'):
                name = f"{name}.md"
            completed_lessons.add(name)
    else:
        completed_lessons = set()
        for item in (completed_raw if completed_raw else []):
            name = str(item)
            if not name.endswith('.md'):
                name = f"{name}.md"
            completed_lessons.add(name)
    
    # Get all lessons with numeric format
    lessons = []
    for file_path in sorted(lessons_dir.glob("**/*.md")):
        # Check if filename has numeric format
        if not re.match(r'^\d+', file_path.name):
            continue
        
        rel_path = file_path.relative_to(lessons_dir)
        lesson_name = str(rel_path)
        
        # Determine status (lesson_name already has .md extension)
        if lesson_name in completed_lessons:
            status = "done"
        elif lesson_name == current_lesson:
            status = "current"
        else:
            status = "todo"
        
        # Extract title from file and check Reviewed attribute
        title = None
        topic = None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract frontmatter and check Reviewed attribute
            frontmatter, content_without_frontmatter = extract_frontmatter(content)
            
            # Check Reviewed attribute in frontmatter (case-insensitive)
            if frontmatter:
                # Check for both "reviewed" (lowercase) and "Reviewed" (uppercase)
                reviewed = None
                if "reviewed" in frontmatter:
                    reviewed = frontmatter["reviewed"]
                elif "Reviewed" in frontmatter:
                    reviewed = frontmatter["Reviewed"]
                
                # If reviewed exists and is false, skip this lesson
                if reviewed is False:
                    continue
                # If reviewed exists and is true, include it
                # If reviewed doesn't exist, include it (default behavior)
            
            # Extract title and topic from content (after frontmatter removal)
            title = extract_lesson_title(content_without_frontmatter)
            topic = extract_lesson_topic(content_without_frontmatter)
            
        except Exception:
            pass
        
        # Fallback title from filename
        if not title:
            lesson_stem = file_path.stem
            title = re.sub(r'^\d+-?', '', lesson_stem)
            title = title.replace('-', ' ').replace('_', ' ').title()
        
        # Generate URL for the lesson page
        lesson_url = f"lessons/{str(rel_path).replace('.md', '.html')}"
        
        lessons.append({
            "name": lesson_name,
            "title": title,
            "status": status,
            "path": str(rel_path),
            "filename": file_path.name,
            "url": lesson_url,
            "topic": topic,  # Add topic field
        })
    
    # Sort by path (preserves directory structure order: 01/01/01.md, 01/01/02.md, etc.)
    lessons.sort(key=lambda x: x["path"])
    
    return lessons


def get_templates_dir() -> Path:
    """Get the templates directory path."""
    # Templates are bundled with the package
    return Path(__file__).parent.parent / "templates"


def get_static_dir() -> Path:
    """Get the static files directory path."""
    # Static files are bundled with the package
    return Path(__file__).parent.parent / "static"


def ensure_output_structure(output_dir: Path) -> None:
    """Create the output directory structure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "css").mkdir(exist_ok=True)
    (output_dir / "js").mkdir(exist_ok=True)
    
    console.print(f"✅ Created output directory: {output_dir}")


def copy_static_files(output_dir: Path) -> None:
    """Copy static CSS and JS files to output directory."""
    static_dir = get_static_dir()
    
    if not static_dir.exists():
        console.print(
            "[yellow]⚠️  Warning: Static files directory not found, "
            "skipping copy[/yellow]"
        )
        return
    
    # Copy CSS files
    css_src = static_dir / "css"
    css_dest = output_dir / "css"
    
    if css_src.exists():
        for css_file in css_src.glob("*.css"):
            shutil.copy2(css_file, css_dest)
            console.print(f"  📄 Copied {css_file.name}")
    
    # Copy JS files if they exist
    js_src = static_dir / "js"
    js_dest = output_dir / "js"
    
    if js_src.exists():
        for js_file in js_src.glob("*.js"):
            shutil.copy2(js_file, js_dest)
            console.print(f"  📄 Copied {js_file.name}")
    
    # Copy favicon if it exists
    favicon_src = static_dir / "favicon.ico"
    if favicon_src.exists():
        shutil.copy2(favicon_src, output_dir / "favicon.ico")
        console.print(f"  📄 Copied favicon.ico")


def render_template(
    template_name: str, context: Dict[str, Any], output_path: Path
) -> None:
    """Render a Jinja2 template with given context to output path."""
    templates_dir = get_templates_dir()
    
    if not templates_dir.exists():
        raise typer.Exit(
            f"❌ Templates directory not found: {templates_dir}\n"
            "Please ensure the package is properly installed."
        )
    
    template_loader = jinja2.FileSystemLoader(searchpath=str(templates_dir))
    template_env = jinja2.Environment(loader=template_loader)
    
    try:
        template = template_env.get_template(template_name)
        output = template.render(**context)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        
        console.print(f"  ✅ Generated {output_path.name}")
    except jinja2.TemplateNotFound:
        console.print(
            f"[red]❌ Template not found: {template_name}[/red]"
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(
            f"[red]❌ Error rendering template {template_name}: {e}[/red]"
        )
        raise typer.Exit(1)


def generate_lesson_pages(output_dir: Path, config: Dict[str, Any], generated_at: str) -> None:
    """Generate HTML pages for all lessons."""
    import markdown
    
    mystuff_dir = get_mystuff_dir()
    learning_dir = mystuff_dir / "learning"
    lessons_dir = learning_dir / "lessons"
    
    if not lessons_dir.exists():
        console.print("  ℹ️  No lessons directory found, skipping lesson pages")
        return
    
    # Create lessons output directory
    lessons_output = output_dir / "lessons"
    lessons_output.mkdir(exist_ok=True)
    
    # Get all lessons with status
    all_lessons = load_all_lessons_with_status()
    
    if not all_lessons:
        console.print("  ℹ️  No lessons found")
        return
    
    console.print(f"  📚 Generating {len(all_lessons)} lesson pages...")
    
    # Generate HTML for each lesson
    for idx, lesson in enumerate(all_lessons):
        lesson_path = lessons_dir / lesson["path"]
        
        if not lesson_path.exists():
            continue
        
        # Read and process markdown
        with open(lesson_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        
        # Extract frontmatter and check Reviewed attribute
        frontmatter, content_without_frontmatter = extract_frontmatter(md_content)
        
        # Check Reviewed attribute in frontmatter (case-insensitive)
        if frontmatter:
            # Check for both "reviewed" (lowercase) and "Reviewed" (uppercase)
            reviewed = None
            if "reviewed" in frontmatter:
                reviewed = frontmatter["reviewed"]
            elif "Reviewed" in frontmatter:
                reviewed = frontmatter["Reviewed"]
            
            # If reviewed exists and is false, skip generating HTML for this lesson
            if reviewed is False:
                continue
            # If reviewed exists and is true, generate it
            # If reviewed doesn't exist, generate it (default behavior)
        
        # Convert markdown to HTML with syntax highlighting (use content without frontmatter)
        md = markdown.Markdown(
            extensions=["fenced_code", "tables", "codehilite", "nl2br"]
        )
        lesson_html = md.convert(content_without_frontmatter)
        
        # Determine prev/next lessons
        prev_lesson_data = all_lessons[idx - 1] if idx > 0 else None
        next_lesson_data = all_lessons[idx + 1] if idx < len(all_lessons) - 1 else None
        
        # Calculate relative path to root based on depth
        # The lesson will be at lessons/{path}, so we need to count all directory levels
        # For example: lessons/01/01/01.html needs ../../../ (3 levels up)
        lesson_rel_path = Path(lesson["path"])
        current_dir = lesson_rel_path.parent
        # Count directories in the relative path (excluding filename)
        depth = len(lesson_rel_path.parts) - 1
        # Add 1 for the "lessons" directory itself
        depth += 1
        relative_root = "../" * depth if depth > 0 else "./"
        
        # Calculate relative URLs for prev/next lessons
        prev_lesson = None
        if prev_lesson_data:
            prev_path = Path(prev_lesson_data["path"])
            prev_dir = prev_path.parent
            
            # If same directory, just use filename
            if current_dir == prev_dir:
                relative_prev = prev_path.name.replace(".md", ".html")
            else:
                # Calculate relative path between directories
                # Count how many levels to go up from current
                up_levels = len(current_dir.parts)
                # Then go down to target directory
                relative_prev = ("../" * up_levels) + str(prev_path).replace(".md", ".html")
            
            prev_lesson = {
                "url": relative_prev,
                "title": prev_lesson_data["title"]
            }
        
        next_lesson = None
        if next_lesson_data:
            next_path = Path(next_lesson_data["path"])
            next_dir = next_path.parent
            
            # If same directory, just use filename
            if current_dir == next_dir:
                relative_next = next_path.name.replace(".md", ".html")
            else:
                # Calculate relative path between directories
                # Count how many levels to go up from current
                up_levels = len(current_dir.parts)
                # Then go down to target directory
                relative_next = ("../" * up_levels) + str(next_path).replace(".md", ".html")
            
            next_lesson = {
                "url": relative_next,
                "title": next_lesson_data["title"]
            }
        
        # Prepare context
        context = {
            "title": config.get("title", "My Knowledge Base"),
            "description": config.get("description", "Personal knowledge management"),
            "author": config.get("author", "Your Name"),
            "menu_items": config.get("menu_items", []),
            "lesson_title": lesson["title"],
            "lesson_content": lesson_html,  # Changed from lesson_html to lesson_content
            "prev_lesson": prev_lesson,
            "next_lesson": next_lesson,
            "relative_root": relative_root,
            "generated_at": generated_at,
        }
        
        # Generate output path
        output_filename = lesson["path"].replace(".md", ".html")
        output_path = lessons_output / output_filename
        
        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Render template
        render_template("lesson.html", context, output_path)
    
    console.print(f"  ✅ Generated {len(all_lessons)} lesson pages")


def generate_static_web(output_dir: Path, config: Dict[str, Any]) -> None:
    """Generate a static website."""
    console.print("\n🚀 Generating static website...")
    console.print(f"📁 Output directory: {output_dir}\n")
    
    # Create directory structure
    ensure_output_structure(output_dir)
    
    # Copy static files
    console.print("\n📦 Copying static files...")
    copy_static_files(output_dir)
    
    # Fetch GitHub repositories if username and repo list are configured
    repos = []
    github_username = config.get("github_username")
    repo_names = config.get("repositories", [])
    
    if github_username and repo_names:
        console.print(f"\n🐙 Fetching repository details for @{github_username}...")
        repos = fetch_github_repo_details(github_username, repo_names)
        console.print(f"  ✅ Found {len(repos)} repositories")
    
    # Load links from mystuff
    console.print("\n📚 Loading links...")
    links = load_mystuff_links()
    console.print(f"  ✅ Loaded {len(links)} links")
    
    # Load learning data
    console.print("\n📖 Loading learning data...")
    learning = load_learning_data()
    if learning:
        console.print(f"  ✅ Current lesson: {learning['title']}")
    else:
        console.print("  ℹ️  No current lesson found")
    
    # Prepare context for templates
    from datetime import datetime
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    context = {
        "title": config.get("title", "My Knowledge Base"),
        "description": config.get("description", "Personal knowledge management"),
        "author": config.get("author", "Your Name"),
        "menu_items": config.get("menu_items", []),
        "github_username": github_username,
        "repositories": repos,
        "links_json": json.dumps(links),
        "learning": learning,
        "generated_at": generated_at,
    }
    
    # Generate index.html
    console.print("\n📝 Generating HTML pages...")
    render_template("index.html", context, output_dir / "index.html")
    
    # Generate links.html (if template exists)
    links_template = get_templates_dir() / "links.html"
    if links_template.exists():
        render_template("links.html", context, output_dir / "links.html")
    else:
        console.print(
            "[yellow]  ⚠️  Skipping links.html (template not found)[/yellow]"
        )
    
    # Load all lessons with status
    console.print("\n📖 Loading lessons...")
    all_lessons = load_all_lessons_with_status()
    console.print(f"  ✅ Found {len(all_lessons)} lessons")
    
    # Generate learning.html (if template exists)
    learning_template = get_templates_dir() / "learning.html"
    if learning_template.exists() and all_lessons:
        lessons_context = context.copy()
        lessons_context["lessons"] = all_lessons
        lessons_context["lessons_json"] = json.dumps(all_lessons)
        render_template("learning.html", lessons_context, output_dir / "learning.html")
        
        # Generate individual lesson pages
        generate_lesson_pages(output_dir, config, generated_at)
    else:
        if not learning_template.exists():
            console.print(
                "[yellow]  ⚠️  Skipping learning.html (template not found)[/yellow]"
            )
        if not all_lessons:
            console.print(
                "  ℹ️  No lessons to generate"
            )
    
    console.print("\n✨ Website generation complete!")
    console.print(f"\n🌐 Open {output_dir / 'index.html'} in your browser\n")


@generate_app.command("web")
def generate_web(
    type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help="Type of generation (currently only 'static_web' is supported)",
        ),
    ] = "static_web",
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            help="Output directory for generated files",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite output directory without asking",
        ),
    ] = False,
) -> None:
    """Generate a static website from mystuff data.
    
    Creates a minimal, elegant static website with a sidebar menu
    similar to https://jepemo.github.io/
    
    Examples:
        # Generate with default settings
        mystuff generate web
        
        # Generate to specific directory
        mystuff generate web --output ~/my-website
        
        # Specify type explicitly
        mystuff generate web --type static_web --output ./dist
    """
    # Validate type
    if type != "static_web":
        console.print(
            f"[red]❌ Error: Unknown type '{type}'. "
            f"Currently only 'static_web' is supported.[/red]"
        )
        raise typer.Exit(1)
    
    # Load configuration
    config = get_generate_config()
    
    # Determine output directory
    if output is None:
        output = Path(config.get("output", str(Path.home() / "mystuff_web")))
    
    # Expand user path
    output = output.expanduser().resolve()
    
    # Check if output directory exists and has content
    if output.exists() and any(output.iterdir()):
        if not force:
            if not typer.confirm(
                f"\n⚠️  Output directory '{output}' already exists and is not empty.\n"
                "Do you want to overwrite it?",
                default=False,
            ):
                console.print("\n❌ Generation cancelled.")
                raise typer.Exit(0)
    
    # Generate the website
    try:
        generate_static_web(output, config)
    except Exception as e:
        console.print(f"\n[red]❌ Error during generation: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    generate_app()
