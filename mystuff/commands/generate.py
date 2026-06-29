#!/usr/bin/env python3
"""
MyStuff CLI - Generate static content functionality
"""
import json
import os
import posixpath
import shutil
import urllib.request
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import jinja2
import markdown
import typer
import yaml
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from rich.console import Console

from mystuff.learning_catalog import (
    LearningCatalogError,
    attach_progress,
    get_completed_lesson_ids,
    get_current_lesson,
    load_learning_catalog,
    load_metadata,
)
from mystuff.markdown_utils import normalize_lesson_markdown

console = Console()

generate_app = typer.Typer(help="Generate static content from mystuff data")


def rewrite_lesson_markdown_link(
    href: str, source_lesson_path: Path, known_lesson_paths: set[str]
) -> str:
    """Rewrite relative lesson markdown links to the published HTML path."""
    parsed = urlsplit(href)

    # Keep external, absolute, fragment-only, and non-markdown links unchanged.
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return href

    if not parsed.path.lower().endswith(".md"):
        return href

    source_rel_path = source_lesson_path.as_posix()
    source_rel_dir = posixpath.dirname(source_rel_path) or "."
    resolved_target = posixpath.normpath(posixpath.join(source_rel_dir, parsed.path))

    # Ignore paths that escape the lessons tree or do not map to a generated lesson.
    if resolved_target == ".." or resolved_target.startswith("../"):
        return href

    if resolved_target not in known_lesson_paths:
        return href

    current_output_dir = (
        posixpath.dirname(source_rel_path.removesuffix(".md") + ".html") or "."
    )
    target_output_path = resolved_target.removesuffix(".md") + ".html"
    relative_output_path = posixpath.relpath(
        target_output_path, start=current_output_dir
    )

    return urlunsplit(("", "", relative_output_path, parsed.query, parsed.fragment))


class LessonLinkRewriteTreeprocessor(Treeprocessor):
    """Rewrite lesson-to-lesson markdown links in emitted HTML anchors."""

    def __init__(
        self, md, source_lesson_path: Path, known_lesson_paths: set[str]
    ) -> None:
        super().__init__(md)
        self.source_lesson_path = source_lesson_path
        self.known_lesson_paths = known_lesson_paths

    def run(self, root):
        for element in root.iter("a"):
            href = element.get("href")
            if not href:
                continue

            element.set(
                "href",
                rewrite_lesson_markdown_link(
                    href, self.source_lesson_path, self.known_lesson_paths
                ),
            )

        return root


class LessonLinkRewriteExtension(Extension):
    """Markdown extension that rewrites internal lesson links to HTML pages."""

    def __init__(
        self, *, source_lesson_path: Path, known_lesson_paths: set[str], **kwargs
    ) -> None:
        self.source_lesson_path = source_lesson_path
        self.known_lesson_paths = known_lesson_paths
        super().__init__(**kwargs)

    def extendMarkdown(self, md) -> None:
        md.treeprocessors.register(
            LessonLinkRewriteTreeprocessor(
                md, self.source_lesson_path, self.known_lesson_paths
            ),
            "lesson_link_rewrite",
            15,
        )


def rewrite_track_markdown_link(
    href: str, track_id: str, known_lesson_paths: set[str]
) -> str:
    """Rewrite lesson markdown links from a track page to published lesson pages."""
    parsed = urlsplit(href)

    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return href

    if not parsed.path.lower().endswith(".md"):
        return href

    resolved_target = posixpath.normpath(posixpath.join(track_id, parsed.path))
    if resolved_target == ".." or resolved_target.startswith("../"):
        return href

    if resolved_target not in known_lesson_paths:
        return href

    return urlunsplit(
        (
            "",
            "",
            f"../lessons/{resolved_target.removesuffix('.md')}.html",
            parsed.query,
            parsed.fragment,
        )
    )


class TrackLinkRewriteTreeprocessor(Treeprocessor):
    """Rewrite track-to-lesson markdown links in emitted HTML anchors."""

    def __init__(self, md, track_id: str, known_lesson_paths: set[str]) -> None:
        super().__init__(md)
        self.track_id = track_id
        self.known_lesson_paths = known_lesson_paths

    def run(self, root):
        for element in root.iter("a"):
            href = element.get("href")
            if not href:
                continue

            element.set(
                "href",
                rewrite_track_markdown_link(
                    href, self.track_id, self.known_lesson_paths
                ),
            )

        return root


class TrackLinkRewriteExtension(Extension):
    """Markdown extension that rewrites internal lesson links from track pages."""

    def __init__(
        self, *, track_id: str, known_lesson_paths: set[str], **kwargs
    ) -> None:
        self.track_id = track_id
        self.known_lesson_paths = known_lesson_paths
        super().__init__(**kwargs)

    def extendMarkdown(self, md) -> None:
        md.treeprocessors.register(
            TrackLinkRewriteTreeprocessor(md, self.track_id, self.known_lesson_paths),
            "track_link_rewrite",
            15,
        )


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

    lines = lesson_content.strip().split("\n")

    day_title = None
    topic = None

    for line in lines:
        line = line.strip()

        # Match "# Day XXX: Title"
        day_match = re.match(r"^#\s+Day\s+(\d+):\s*(.+)$", line, re.IGNORECASE)
        if day_match and not day_title:
            day_number = day_match.group(1)
            title = day_match.group(2).strip()
            day_title = f"Day {day_number}: {title}"

        # Match "# Topic: Topic Name"
        topic_match = re.match(r"^#\s+Topic:\s*(.+)$", line, re.IGNORECASE)
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

    lines = lesson_content.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Match "# Topic: Topic Name"
        topic_match = re.match(r"^#\s+Topic:\s*(.+)$", line, re.IGNORECASE)
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
    if not content.startswith("---"):
        return None, content

    # Find the closing delimiter
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
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


def fetch_github_repo_details(
    username: str, repo_names: List[str]
) -> List[Dict[str, Any]]:
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
                "language": repo_data.get("language"),
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


def _load_catalog_with_progress() -> tuple[Dict[str, Any], Dict[str, Any]]:
    catalog = load_learning_catalog()
    metadata = load_metadata()
    return attach_progress(catalog, metadata), metadata


def _public_tracks(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [track for track in catalog["tracks"] if _is_track_published(track)]


def _is_track_published(track: Dict[str, Any]) -> bool:
    return track["status"] == "active" and track.get("public", True)


def _public_lessons(track: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [lesson for lesson in track["lessons"] if lesson["public"]]


def _public_lesson_status(
    lesson: Dict[str, Any], completed_ids: set, current_lesson_ids: set
) -> str:
    if lesson["lesson_id"] in completed_ids:
        return "done"
    if lesson["lesson_id"] in current_lesson_ids:
        return "current"
    return "todo"


def load_learning_data() -> Optional[Dict[str, Any]]:
    """Load current published learning state for the home page."""
    try:
        catalog, metadata = _load_catalog_with_progress()
    except LearningCatalogError as exc:
        console.print(
            f"[yellow]⚠️  Warning: Could not load learning data: {exc}[/yellow]"
        )
        return None

    current_lesson = get_current_lesson(metadata, catalog)
    if not current_lesson:
        return None

    track = catalog["tracks_by_id"][current_lesson["track_id"]]
    if (
        track["status"] != "active"
        or not track.get("public", True)
        or not current_lesson["public"]
    ):
        return None

    return {
        "current_lesson_id": current_lesson["lesson_id"],
        "lesson_title": current_lesson["title"],
        "lesson_url": current_lesson["url"],
        "track_id": track["track_id"],
        "track_name": track["name"],
        "track_url": track["url"],
        "classification_id": track["classification"],
        "classification_name": track.get("classification_name")
        or track["classification"].replace("-", " ").title(),
        "classification_url": f"classifications/{track['classification']}.html",
        "last_opened_at": metadata.get("last_opened_at"),
    }


def _first_open_lesson(track: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    current_lesson = next(
        (
            lesson
            for lesson in track["lessons"]
            if (lesson.get("status") or lesson.get("progress_status")) == "current"
        ),
        None,
    )
    if current_lesson:
        return current_lesson

    return next(
        (
            lesson
            for lesson in track["lessons"]
            if (lesson.get("status") or lesson.get("progress_status")) != "done"
        ),
        None,
    )


def load_active_learning_data() -> List[Dict[str, Any]]:
    """Load compact current/open learning items for the home page."""
    try:
        catalog, metadata = _load_catalog_with_progress()
    except LearningCatalogError as exc:
        console.print(
            f"[yellow]⚠️  Warning: Could not load learning data: {exc}[/yellow]"
        )
        return []

    # Progress comes from the catalog's per-track cursor.  The legacy global
    # cursor may be used only while attaching progress for old metadata.
    learning_items: List[Dict[str, Any]] = []
    for track in catalog["tracks"]:
        if track["status"] != "active" or track.get("progress_status") != "in_progress":
            continue

        lesson = _first_open_lesson(track)
        if not lesson:
            continue

        is_published = track.get("public", True) and lesson.get("public", True)
        learning_items.append(
            {
                "current_lesson_id": lesson["lesson_id"],
                "lesson_title": lesson["title"],
                "lesson_url": lesson["url"] if is_published else None,
                "track_id": track["track_id"],
                "track_name": track["name"],
                "track_description": track.get("description", ""),
                "track_url": track["url"] if track.get("public", True) else None,
                "classification_id": track["classification"],
                "classification_name": track.get("classification_name")
                or track["classification"].replace("-", " ").title(),
                "classification_url": (
                    f"classifications/{track['classification']}.html"
                    if track.get("public", True)
                    else None
                ),
                "last_opened_at": None,
                "is_current": lesson.get("progress_status") == "current",
            }
        )

    learning_items.sort(key=lambda item: (not item["is_current"], item["track_id"]))
    return learning_items


def load_all_tracks_with_status() -> List[Dict[str, Any]]:
    """Load all tracks for catalog display, linking only published tracks."""
    catalog, metadata = _load_catalog_with_progress()
    completed_ids = get_completed_lesson_ids(metadata)

    tracks: List[Dict[str, Any]] = []
    for track in catalog["tracks"]:
        is_published = _is_track_published(track)
        public_lessons = []
        completed_public_count = 0
        if is_published:
            for lesson in _public_lessons(track):
                lesson_copy = dict(lesson)
                lesson_copy["status"] = _public_lesson_status(
                    lesson_copy,
                    completed_ids,
                    {track["current_lesson_id"]}
                    if track.get("current_lesson_id")
                    else set(),
                )
                lesson_copy["display_title"] = (
                    f"{lesson_copy['sequence_label']}. {lesson_copy['title']}"
                )
                lesson_copy["track_page_url"] = f"../tracks/{track['track_id']}.html"
                if lesson_copy["status"] == "done":
                    completed_public_count += 1
                public_lessons.append(lesson_copy)

        if not is_published:
            public_progress_status = (
                "draft" if track["status"] == "draft" else "unpublished"
            )
        elif public_lessons:
            if completed_public_count == len(public_lessons):
                public_progress_status = "done"
            elif any(lesson["status"] == "current" for lesson in public_lessons):
                public_progress_status = "current"
            elif completed_public_count > 0:
                public_progress_status = "in_progress"
            elif track["is_unlocked"]:
                public_progress_status = "not_started"
            else:
                public_progress_status = "locked"
        else:
            public_progress_status = track["progress_status"]

        track_copy = dict(track)
        track_copy["lessons"] = public_lessons
        track_copy["is_published"] = is_published
        track_copy["track_url"] = track["url"] if is_published else None
        track_copy["display_lesson_count"] = track["lesson_count"]
        track_copy["public_lesson_count"] = len(public_lessons)
        track_copy["completed_public_count"] = completed_public_count
        track_copy["public_progress_status"] = public_progress_status
        tracks.append(track_copy)

    return tracks


def group_tracks_by_classification(
    tracks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Group already-filtered tracks by classification for rendering."""
    classifications_by_id: Dict[str, Dict[str, Any]] = {}
    classifications: List[Dict[str, Any]] = []

    for track in tracks:
        classification_id = track["classification"]
        classification = classifications_by_id.get(classification_id)
        if classification is None:
            classification = {
                "classification_id": classification_id,
                "classification_name": track.get("classification_name")
                or classification_id.replace("-", " ").title(),
                "url": f"classifications/{classification_id}.html",
                "tracks": [],
                "track_count": 0,
                "lesson_count": 0,
            }
            classifications_by_id[classification_id] = classification
            classifications.append(classification)

        classification["tracks"].append(track)
        classification["track_count"] += 1
        classification["lesson_count"] += track["display_lesson_count"]

    return classifications


def group_tracks_by_roadmap(tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group already-loaded tracks by roadmap for rendering."""
    roadmaps_by_id: Dict[str, Dict[str, Any]] = {}
    roadmaps: List[Dict[str, Any]] = []

    for track in tracks:
        roadmap_id = track.get("roadmap") or "uncategorized"
        roadmap = roadmaps_by_id.get(roadmap_id)
        if roadmap is None:
            roadmap = {
                "roadmap_id": roadmap_id,
                "roadmap_name": track.get("roadmap_name")
                or roadmap_id.replace("-", " ").title(),
                "url": f"roadmaps/{roadmap_id}.html",
                "tracks": [],
                "track_count": 0,
                "lesson_count": 0,
            }
            roadmaps_by_id[roadmap_id] = roadmap
            roadmaps.append(roadmap)

        roadmap["tracks"].append(track)
        roadmap["track_count"] += 1
        roadmap["lesson_count"] += track["display_lesson_count"]

    return roadmaps


def load_all_lessons_with_status() -> List[Dict[str, Any]]:
    """Load all public lessons with status information."""
    lessons: List[Dict[str, Any]] = []
    for track in load_all_tracks_with_status():
        if not track["is_published"]:
            continue
        for lesson in track["lessons"]:
            lesson_copy = dict(lesson)
            lesson_copy["track_name"] = track["name"]
            lesson_copy["track_id"] = track["track_id"]
            lessons.append(lesson_copy)

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

    # Copy the active brutalist stylesheet only. Legacy CSS snapshots are kept
    # in the package for reference but should not be published as site assets.
    css_src = static_dir / "css"
    css_dest = output_dir / "css"

    for legacy_css in ("normalize.css", "style_old.css"):
        legacy_path = css_dest / legacy_css
        if legacy_path.exists():
            legacy_path.unlink()
            console.print(f"  🧹 Removed legacy {legacy_css}")

    css_file = css_src / "style.css"
    if css_file.exists():
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
        console.print(f"[red]❌ Template not found: {template_name}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error rendering template {template_name}: {e}[/red]")
        raise typer.Exit(1)


def _render_lesson_markdown(
    lesson: Dict[str, Any], known_lesson_paths: set[str]
) -> str:
    lesson_path = get_mystuff_dir() / "learning" / "lessons" / lesson["path"]
    with open(lesson_path, "r", encoding="utf-8") as handle:
        md_content = handle.read()

    _, content_without_frontmatter = extract_frontmatter(md_content)
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            "codehilite",
            LessonLinkRewriteExtension(
                source_lesson_path=Path(lesson["path"]),
                known_lesson_paths=known_lesson_paths,
            ),
        ],
        tab_length=2,
    )
    return md.convert(normalize_lesson_markdown(content_without_frontmatter))


def _relative_output_path(source_path: str) -> str:
    return source_path.replace(".md", ".html")


def _relative_link_between(source_path: str, target_path: str) -> str:
    source_html = _relative_output_path(source_path)
    target_html = _relative_output_path(target_path)
    source_dir = posixpath.dirname(source_html) or "."
    return posixpath.relpath(target_html, start=source_dir)


def generate_classification_pages(
    output_dir: Path,
    config: Dict[str, Any],
    generated_at: str,
    classifications: List[Dict[str, Any]],
) -> None:
    """Generate one public page per classification."""
    if not classifications:
        console.print(
            "  ℹ️  No public classifications found, skipping classification pages"
        )
        return

    classifications_output = output_dir / "classifications"
    classifications_output.mkdir(exist_ok=True)

    console.print(f"  🗂️  Generating {len(classifications)} classification pages...")
    for classification in classifications:
        output_path = (
            classifications_output / f"{classification['classification_id']}.html"
        )
        context = {
            "title": config.get("title", "My Knowledge Base"),
            "description": config.get("description", "Personal knowledge management"),
            "author": config.get("author", "Your Name"),
            "menu_items": config.get("menu_items", []),
            "classification": classification,
            "tracks": classification["tracks"],
            "relative_root": "../",
            "generated_at": generated_at,
        }
        render_template("classification.html", context, output_path)

    console.print(f"  ✅ Generated {len(classifications)} classification pages")


def generate_roadmap_pages(
    output_dir: Path,
    config: Dict[str, Any],
    generated_at: str,
    roadmaps: List[Dict[str, Any]],
) -> None:
    """Generate one catalog page per roadmap."""
    if not roadmaps:
        console.print("  ℹ️  No roadmaps found, skipping roadmap pages")
        return

    roadmaps_output = output_dir / "roadmaps"
    roadmaps_output.mkdir(exist_ok=True)

    console.print(f"  🗺️  Generating {len(roadmaps)} roadmap pages...")
    for roadmap in roadmaps:
        output_path = roadmaps_output / f"{roadmap['roadmap_id']}.html"
        context = {
            "title": config.get("title", "My Knowledge Base"),
            "description": config.get("description", "Personal knowledge management"),
            "author": config.get("author", "Your Name"),
            "menu_items": config.get("menu_items", []),
            "roadmap": roadmap,
            "tracks": roadmap["tracks"],
            "relative_root": "../",
            "generated_at": generated_at,
        }
        render_template("roadmap.html", context, output_path)

    console.print(f"  ✅ Generated {len(roadmaps)} roadmap pages")


def generate_track_pages(
    output_dir: Path,
    config: Dict[str, Any],
    generated_at: str,
    tracks: List[Dict[str, Any]],
) -> None:
    """Generate one public page per track."""
    if not tracks:
        console.print("  ℹ️  No public tracks found, skipping track pages")
        return

    tracks_output = output_dir / "tracks"
    tracks_output.mkdir(exist_ok=True)

    console.print(f"  🧱 Generating {len(tracks)} track pages...")
    for track in tracks:
        output_path = tracks_output / f"{track['track_id']}.html"
        context = {
            "title": config.get("title", "My Knowledge Base"),
            "description": config.get("description", "Personal knowledge management"),
            "author": config.get("author", "Your Name"),
            "menu_items": config.get("menu_items", []),
            "track": track,
            "classification": {
                "classification_id": track["classification"],
                "classification_name": track.get("classification_name")
                or track["classification"].replace("-", " ").title(),
                "url": f"../classifications/{track['classification']}.html",
            },
            "lessons": track["lessons"],
            "relative_root": "../",
            "generated_at": generated_at,
        }
        render_template("track.html", context, output_path)

    console.print(f"  ✅ Generated {len(tracks)} track pages")


def generate_lesson_pages(
    output_dir: Path,
    config: Dict[str, Any],
    generated_at: str,
    tracks: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Generate public HTML pages for all published lessons."""
    if tracks is None:
        tracks = load_all_tracks_with_status()

    if not tracks:
        console.print("  ℹ️  No public lessons found")
        return

    lessons_output = output_dir / "lessons"
    lessons_output.mkdir(exist_ok=True)
    all_lessons = [lesson for track in tracks for lesson in track["lessons"]]
    known_lesson_paths = {lesson["path"] for lesson in all_lessons}

    console.print(f"  📚 Generating {len(all_lessons)} lesson pages...")
    for track in tracks:
        track_lessons = track["lessons"]
        for index, lesson in enumerate(track_lessons):
            lesson_html = _render_lesson_markdown(lesson, known_lesson_paths)
            prev_lesson_data = track_lessons[index - 1] if index > 0 else None
            next_lesson_data = (
                track_lessons[index + 1] if index < len(track_lessons) - 1 else None
            )

            relative_root = "../" * len(Path(lesson["path"]).parts)
            prev_lesson = None
            if prev_lesson_data:
                prev_lesson = {
                    "url": _relative_link_between(
                        lesson["path"], prev_lesson_data["path"]
                    ),
                    "title": prev_lesson_data["title"],
                }

            next_lesson = None
            if next_lesson_data:
                next_lesson = {
                    "url": _relative_link_between(
                        lesson["path"], next_lesson_data["path"]
                    ),
                    "title": next_lesson_data["title"],
                }

            context = {
                "title": config.get("title", "My Knowledge Base"),
                "description": config.get(
                    "description", "Personal knowledge management"
                ),
                "author": config.get("author", "Your Name"),
                "menu_items": config.get("menu_items", []),
                "lesson": lesson,
                "track": track,
                "classification": {
                    "classification_id": track["classification"],
                    "classification_name": track.get("classification_name")
                    or track["classification"].replace("-", " ").title(),
                    "url": f"{relative_root}classifications/{track['classification']}.html",
                },
                "lesson_title": lesson["title"],
                "lesson_content": lesson_html,
                "prev_lesson": prev_lesson,
                "next_lesson": next_lesson,
                "track_page_url": f"{relative_root}tracks/{track['track_id']}.html",
                "classification_page_url": (
                    f"{relative_root}classifications/{track['classification']}.html"
                ),
                "relative_root": relative_root,
                "generated_at": generated_at,
            }

            output_path = lessons_output / _relative_output_path(lesson["path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            render_template("lesson.html", context, output_path)

    console.print(f"  ✅ Generated {len(all_lessons)} lesson pages")


def generate_static_web(output_dir: Path, config: Dict[str, Any]) -> None:
    """Generate a static website."""
    from datetime import datetime, timezone

    console.print("\n🚀 Generating static website...")
    console.print(f"📁 Output directory: {output_dir}\n")

    ensure_output_structure(output_dir)

    console.print("\n📦 Copying static files...")
    copy_static_files(output_dir)

    repos = []
    github_username = config.get("github_username")
    repo_names = config.get("repositories", [])
    if github_username and repo_names:
        console.print(f"\n🐙 Fetching repository details for @{github_username}...")
        repos = fetch_github_repo_details(github_username, repo_names)
        console.print(f"  ✅ Found {len(repos)} repositories")

    console.print("\n📚 Loading links...")
    links = load_mystuff_links()
    console.print(f"  ✅ Loaded {len(links)} links")

    console.print("\n📖 Loading learning data...")
    learning = load_learning_data()
    active_learning = load_active_learning_data()
    if active_learning:
        console.print(f"  ✅ Current learning entries: {len(active_learning)}")
    elif learning:
        console.print(
            f"  ✅ Current lesson: {learning['track_id']}/{learning['current_lesson_id']}"
        )
    else:
        console.print("  ℹ️  No current published lesson found")

    console.print("\n🧱 Loading tracks...")
    tracks = load_all_tracks_with_status()
    published_tracks = [track for track in tracks if track["is_published"]]
    console.print(
        f"  ✅ Found {len(tracks)} tracks ({len(published_tracks)} published)"
    )
    classifications = group_tracks_by_classification(tracks)
    console.print(f"  ✅ Grouped into {len(classifications)} classifications")
    roadmaps = group_tracks_by_roadmap(tracks)
    console.print(f"  ✅ Grouped into {len(roadmaps)} roadmaps")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    context = {
        "title": config.get("title", "My Knowledge Base"),
        "description": config.get("description", "Personal knowledge management"),
        "author": config.get("author", "Your Name"),
        "menu_items": config.get("menu_items", []),
        "github_username": github_username,
        "repositories": repos,
        "links_json": json.dumps(links),
        "learning": learning,
        "active_learning": active_learning,
        "tracks": tracks,
        "classifications": classifications,
        "roadmaps": roadmaps,
        "generated_at": generated_at,
    }

    console.print("\n📝 Generating HTML pages...")
    render_template("index.html", context, output_dir / "index.html")

    links_template = get_templates_dir() / "links.html"
    if links_template.exists():
        render_template("links.html", context, output_dir / "links.html")
    else:
        console.print("[yellow]  ⚠️  Skipping links.html (template not found)[/yellow]")

    learning_template = get_templates_dir() / "learning.html"
    if learning_template.exists():
        render_template("learning.html", context, output_dir / "learning.html")
    else:
        console.print(
            "[yellow]  ⚠️  Skipping learning.html (template not found)[/yellow]"
        )

    classification_template = get_templates_dir() / "classification.html"
    if classification_template.exists():
        generate_classification_pages(output_dir, config, generated_at, classifications)
    else:
        console.print(
            "[yellow]  ⚠️  Skipping classification pages (template not found)[/yellow]"
        )

    roadmap_template = get_templates_dir() / "roadmap.html"
    if roadmap_template.exists():
        generate_roadmap_pages(output_dir, config, generated_at, roadmaps)
    else:
        console.print(
            "[yellow]  ⚠️  Skipping roadmap pages (template not found)[/yellow]"
        )

    track_template = get_templates_dir() / "track.html"
    if track_template.exists():
        generate_track_pages(output_dir, config, generated_at, published_tracks)
    else:
        console.print("[yellow]  ⚠️  Skipping track pages (template not found)[/yellow]")

    generate_lesson_pages(output_dir, config, generated_at, tracks=published_tracks)

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
