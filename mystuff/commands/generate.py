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
                line = line.strip()
                if line:
                    try:
                        link = json.loads(line)
                        links.append(link)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        console.print(
            f"[yellow]⚠️  Warning: Could not read links file: {e}[/yellow]"
        )
        return []
    
    return links


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
    
    # Prepare context for templates
    context = {
        "title": config.get("title", "My Knowledge Base"),
        "description": config.get("description", "Personal knowledge management"),
        "author": config.get("author", "Your Name"),
        "menu_items": config.get("menu_items", []),
        "github_username": github_username,
        "repositories": repos,
        "links_json": json.dumps(links),
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
