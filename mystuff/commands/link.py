"""
Link command for MyStuff CLI
Manages links with JSONL storage
"""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import typer
from typing_extensions import Annotated


def get_mystuff_dir() -> Path:
    """Get the mystuff data directory from config or environment"""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home).expanduser().resolve()
    return Path.home() / ".mystuff"


def get_links_file() -> Path:
    """Get the path to the links.jsonl file"""
    return get_mystuff_dir() / "links.jsonl"


def ensure_links_file_exists():
    """Ensure the links.jsonl file exists"""
    # Check if mystuff directory exists first
    if not check_mystuff_directory_exists():
        handle_mystuff_directory_error()

    links_file = get_links_file()
    if not links_file.exists():
        links_file.touch()


def is_fzf_available() -> bool:
    """Check if fzf is available on the system"""
    try:
        subprocess.run(["fzf", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def select_link_with_fzf(links: List[dict]) -> Optional[dict]:
    """Use fzf to select a link interactively"""
    if not links:
        return None

    # Create options for fzf
    options = []
    for link in links:
        tags_str = f"[{', '.join(link.get('tags', []))}]" if link.get("tags") else ""
        timestamp = link.get("timestamp", "")
        option = f"{link['title']} | {link['url']} | {timestamp} {tags_str}"
        options.append(option)

    try:
        # Use a different approach: write to stdin and read from stdout
        import sys

        # Create the fzf process
        fzf_process = subprocess.Popen(
            ["fzf", "--prompt=Select link: ", "--height=40%"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,  # Use parent stderr
            text=True,
        )

        # Send input and get output
        selected_option, _ = fzf_process.communicate(input="\n".join(options))

        # Check if fzf was successful
        if fzf_process.returncode == 0 and selected_option:
            selected_option = selected_option.strip()
            for i, option in enumerate(options):
                if option == selected_option:
                    return links[i]

    except (subprocess.CalledProcessError, KeyboardInterrupt, FileNotFoundError):
        return None

    return None


def get_title_from_url(url: str) -> str:
    """Extract a title from URL by using the host"""
    try:
        parsed = urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url


def load_links() -> List[dict]:
    """Load all links from the JSONL file"""
    ensure_links_file_exists()
    links = []
    links_file = get_links_file()

    if links_file.exists():
        with open(links_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        links.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    return links


def save_links(links: List[dict]):
    """Save links to the JSONL file"""
    ensure_links_file_exists()
    links_file = get_links_file()

    with open(links_file, "w") as f:
        for link in links:
            f.write(json.dumps(link) + "\n")


def add_link(
    url: Annotated[
        Optional[str],
        typer.Option(
            "--url", help="Target URL (required unless importing GitHub stars)"
        ),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Human-readable title (defaults to URL host)"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="Optional free-text notes about the link"),
    ] = None,
    tags: Annotated[
        Optional[List[str]],
        typer.Option("--tag", help="One or more tags for categorization"),
    ] = None,
    open_link: Annotated[
        bool,
        typer.Option(
            "--open", help="Open the link in the default browser after adding"
        ),
    ] = False,
    github_username: Annotated[
        Optional[str],
        typer.Option(
            "--import-github-stars",
            help="Import GitHub stars for the specified username",
        ),
    ] = None,
):
    """Add a new link or import GitHub stars"""

    # Check if mystuff directory exists
    if not check_mystuff_directory_exists():
        handle_mystuff_directory_error()

    # Handle GitHub stars import
    if github_username:
        if url or title or description or tags:
            typer.echo(
                "❌ Cannot use --import-github-stars with other options", err=True
            )
            raise typer.Exit(code=1)

        imported_count = import_github_stars(github_username)
        if imported_count > 0:
            typer.echo(f"🎉 Successfully imported {imported_count} GitHub stars!")
        return

    # Regular link addition - URL is required
    if not url:
        typer.echo(
            "Error: URL is required (or use --import-github-stars USERNAME)", err=True
        )
        raise typer.Exit(code=1)

    # Set default title if not provided
    if not title:
        title = get_title_from_url(url)

    # Set default tags if not provided
    if tags is None:
        tags = []

    # Create the link entry
    link_entry = {
        "url": url,
        "title": title,
        "description": description or "",
        "tags": tags,
        "timestamp": datetime.now().isoformat(),
    }

    # Load existing links
    links = load_links()

    # Check if URL already exists
    for existing_link in links:
        if existing_link["url"] == url:
            typer.echo(f"Link already exists: {existing_link['title']}")
            if open_link:
                webbrowser.open(url)
            return

    # Add the new link
    links.append(link_entry)
    save_links(links)

    typer.echo(f"✅ Added link: {title}")
    if description:
        typer.echo(f"   Description: {description}")
    if tags:
        typer.echo(f"   Tags: {', '.join(tags)}")

    if open_link:
        webbrowser.open(url)


def list_links(
    search: Annotated[
        Optional[str],
        typer.Option("--search", help="Search by title, tags, or description"),
    ] = None,
    tag: Annotated[
        Optional[str], typer.Option("--tag", help="Filter by specific tag")
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Use fzf for interactive selection"),
    ] = False,
):
    """List all links"""
    # Check if mystuff directory exists
    if not check_mystuff_directory_exists():
        handle_mystuff_directory_error()

    links = load_links()

    if not links:
        typer.echo(
            "No links found. Use 'mystuff link add --url <URL>' to add your first link."
        )
        return

    # Filter links if search or tag is provided
    if search:
        search_lower = search.lower()
        links = [
            link
            for link in links
            if (
                search_lower in link["title"].lower()
                or search_lower in link["description"].lower()
                or any(search_lower in tag.lower() for tag in link["tags"])
            )
        ]

    if tag:
        links = [link for link in links if tag in link["tags"]]

    if not links:
        typer.echo("No links found matching your criteria.")
        return

    # Use fzf for interactive listing if requested and available
    if interactive and is_fzf_available():
        typer.echo("🔍 Interactive link browser (press Enter to view, Ctrl+C to exit):")
        selected_link = select_link_with_fzf(links)
        if selected_link:
            # Show detailed view of selected link
            typer.echo(f"\n🔗 {selected_link['title']}")
            typer.echo(f"   URL: {selected_link['url']}")
            if selected_link["description"]:
                typer.echo(f"   Description: {selected_link['description']}")
            if selected_link["tags"]:
                typer.echo(f"   Tags: {', '.join(selected_link['tags'])}")
            typer.echo(f"   Added: {selected_link['timestamp']}")

            # Ask if user wants to open the link
            if typer.confirm("Open this link in browser?"):
                webbrowser.open(selected_link["url"])
        return

    # Standard listing
    for i, link in enumerate(links, 1):
        typer.echo(f"{i}. {link['title']}")
        typer.echo(f"   URL: {link['url']}")
        if link["description"]:
            typer.echo(f"   Description: {link['description']}")
        if link["tags"]:
            typer.echo(f"   Tags: {', '.join(link['tags'])}")
        typer.echo(f"   Added: {link['timestamp']}")
        typer.echo()


def edit_link(
    url: Annotated[
        Optional[str], typer.Option("--url", help="URL of the link to edit")
    ] = None,
    title: Annotated[Optional[str], typer.Option("--title", help="New title")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", help="New description")
    ] = None,
    tags: Annotated[
        Optional[List[str]], typer.Option("--tag", help="New tags (replaces existing)")
    ] = None,
):
    """Edit an existing link"""
    # Check if mystuff directory exists
    if not check_mystuff_directory_exists():
        handle_mystuff_directory_error()

    links = load_links()

    if not links:
        typer.echo("No links found.")
        raise typer.Exit(code=1)

    # Use fzf to select link if URL not provided and fzf is available
    if not url and is_fzf_available():
        selected_link = select_link_with_fzf(links)
        if not selected_link:
            typer.echo("No link selected.")
            raise typer.Exit(code=1)
        url = selected_link["url"]

    if not url:
        typer.echo("Error: URL is required to identify the link to edit", err=True)
        raise typer.Exit(code=1)

    # Find the link to edit
    link_to_edit = None
    for link in links:
        if link["url"] == url:
            link_to_edit = link
            break

    if not link_to_edit:
        typer.echo(f"Link not found: {url}")
        raise typer.Exit(code=1)

    # Update fields if provided
    if title:
        link_to_edit["title"] = title
    if description is not None:
        link_to_edit["description"] = description
    if tags is not None:
        link_to_edit["tags"] = tags

    save_links(links)
    typer.echo(f"✅ Updated link: {link_to_edit['title']}")


def delete_link(
    url: Annotated[
        Optional[str], typer.Option("--url", help="URL of the link to delete")
    ] = None,
):
    """Delete a link"""
    # Check if mystuff directory exists
    if not check_mystuff_directory_exists():
        handle_mystuff_directory_error()

    links = load_links()

    if not links:
        typer.echo("No links found.")
        raise typer.Exit(code=1)

    # Use fzf to select link if URL not provided and fzf is available
    if not url and is_fzf_available():
        selected_link = select_link_with_fzf(links)
        if not selected_link:
            typer.echo("No link selected.")
            raise typer.Exit(code=1)
        url = selected_link["url"]

    if not url:
        typer.echo("Error: URL is required to identify the link to delete", err=True)
        raise typer.Exit(code=1)

    # Find and remove the link
    original_count = len(links)
    links = [link for link in links if link["url"] != url]

    if len(links) == original_count:
        typer.echo(f"Link not found: {url}")
        raise typer.Exit(code=1)

    save_links(links)
    typer.echo(f"✅ Deleted link: {url}")


def search_links(
    query: Annotated[str, typer.Argument(help="Search query")],
    open_link: Annotated[
        bool, typer.Option("--open", help="Open the first matching link in browser")
    ] = False,
):
    """Search links by title, tags, or description"""
    # Check if mystuff directory exists
    if not check_mystuff_directory_exists():
        handle_mystuff_directory_error()

    links = load_links()

    if not links:
        typer.echo("No links found.")
        return

    query_lower = query.lower()
    matching_links = [
        link
        for link in links
        if (
            query_lower in link["title"].lower()
            or query_lower in link["description"].lower()
            or any(query_lower in tag.lower() for tag in link["tags"])
        )
    ]

    if not matching_links:
        typer.echo(f"No links found matching '{query}'")
        return

    # Display matching links
    for i, link in enumerate(matching_links, 1):
        typer.echo(f"{i}. {link['title']}")
        typer.echo(f"   URL: {link['url']}")
        if link["description"]:
            typer.echo(f"   Description: {link['description']}")
        if link["tags"]:
            typer.echo(f"   Tags: {', '.join(link['tags'])}")
        typer.echo()

    if open_link and matching_links:
        webbrowser.open(matching_links[0]["url"])


def fetch_github_stars(username: str) -> List[dict]:
    """Fetch GitHub stars for a given username using the public API"""
    stars = []
    page = 1
    per_page = 100

    while True:
        url = (
            f"https://api.github.com/users/{username}/starred"
            f"?per_page={per_page}&page={page}"
        )

        try:
            typer.echo(f"Fetching page {page} of GitHub stars for {username}...")
            request = urllib.request.Request(url)
            request.add_header("User-Agent", "mystuff-cli")

            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read().decode())

                if not data:  # No more pages
                    break

                for repo in data:
                    star_info = {
                        "url": repo["html_url"],
                        "title": repo["full_name"],
                        "description": repo["description"] or "",
                        "tags": [username, "github"],
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                    }
                    stars.append(star_info)

                # If we got less than per_page results, we're done
                if len(data) < per_page:
                    break

                page += 1
                # Be nice to the API
                time.sleep(0.1)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                typer.echo(f"❌ User '{username}' not found on GitHub", err=True)
                return []
            elif e.code == 403:
                typer.echo(
                    "❌ GitHub API rate limit exceeded. Please try again later.",
                    err=True,
                )
                return []
            else:
                typer.echo(f"❌ Error fetching GitHub stars: {e}", err=True)
                return []
        except Exception as e:
            typer.echo(f"❌ Error fetching GitHub stars: {e}", err=True)
            return []

    return stars


def import_github_stars(username: str) -> int:
    """Import GitHub stars for a user and add them as links"""
    typer.echo(f"🌟 Importing GitHub stars for user: {username}")

    # Fetch stars from GitHub API
    stars = fetch_github_stars(username)

    if not stars:
        typer.echo("No stars found or error occurred.")
        return 0

    # Load existing links
    existing_links = load_links()
    existing_urls = {link["url"] for link in existing_links}

    # Filter out already existing URLs
    new_stars = [star for star in stars if star["url"] not in existing_urls]

    if not new_stars:
        typer.echo(f"All {len(stars)} starred repositories are already in your links.")
        return 0

    # Convert stars to link format and add them
    for star in new_stars:
        link_entry = {
            "url": star["url"],
            "title": star["title"],
            "description": star["description"],
            "tags": star["tags"],
            "timestamp": datetime.now().isoformat(),
        }
        existing_links.append(link_entry)

    # Save all links
    save_links(existing_links)

    typer.echo(
        f"✅ Imported {len(new_stars)} new GitHub stars "
        f"({len(stars) - len(new_stars)} already existed)"
    )
    return len(new_stars)


def check_mystuff_directory_exists() -> bool:
    """Check if the mystuff directory exists"""
    mystuff_dir = get_mystuff_dir()
    return mystuff_dir.exists()


def handle_mystuff_directory_error():
    """Handle the case when mystuff directory doesn't exist"""
    typer.echo("❌ MyStuff directory not found.", err=True)
    typer.echo("   Please initialize it first with: mystuff init", err=True)
    typer.echo(
        "   Or set a custom location with: export MYSTUFF_HOME=/path/to/your/mystuff",
        err=True,
    )
    raise typer.Exit(code=1)


# Create the link subcommand app
link_app = typer.Typer(
    name="link",
    help="Manage links",
    add_completion=False,
)

link_app.command("add")(add_link)
link_app.command("list")(list_links)
link_app.command("edit")(edit_link)
link_app.command("delete")(delete_link)
link_app.command("search")(search_links)
link_app.command("import_github_stars")(import_github_stars)
