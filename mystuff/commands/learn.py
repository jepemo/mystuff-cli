#!/usr/bin/env python3
"""
MyStuff CLI - Learning management functionality
"""
import datetime
import os
import re
import tempfile
import webbrowser
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import markdown
import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from mystuff.learning_catalog import (
    METADATA_TEMPLATE_V2,
    LearningCatalogError,
    LearningReferenceError,
    attach_progress,
    get_all_lessons as catalog_get_all_lessons,
    get_completed_lesson_ids,
    get_current_lesson,
    get_learning_dir,
    get_lessons_dir,
    get_metadata_path,
    get_mystuff_dir,
    get_next_lesson as catalog_get_next_lesson,
    is_track_completed,
    load_learning_catalog,
    load_metadata,
    resolve_lesson_reference,
    resolve_track_reference,
    save_metadata,
    track_status_summary,
)

learn_app = typer.Typer(help="Manage learning tracks and progress")
METADATA_TEMPLATE = dict(METADATA_TEMPLATE_V2)


def load_config() -> Dict[str, Any]:
    """Load complete configuration from config.yaml."""
    mystuff_dir = get_mystuff_dir()
    config_file = mystuff_dir / "config.yaml"

    if not config_file.exists():
        typer.echo(f"❌ Configuration file not found: {config_file}", err=True)
        raise typer.Exit(1)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        typer.echo(f"❌ Error parsing config.yaml: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error reading config.yaml: {e}", err=True)
        raise typer.Exit(1)

    if not config:
        typer.echo("❌ Empty configuration file", err=True)
        raise typer.Exit(1)

    return config




def get_css_theme(theme: str = "default") -> str:
    """Get CSS styling for different themes.
    
    Args:
        theme: Theme name (default, minimal, github, dark, notion)
        
    Returns:
        CSS string for the selected theme
    """
    themes = {
        "default": """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;  /* noqa: E501 */
            line-height: 1.7;
            max-width: 900px;
            margin: 0 auto;
            padding: 3rem 2rem;
            color: #24292f;
            background: linear-gradient(to bottom, #ffffff 0%, #f6f8fa 100%);
            min-height: 100vh;
        }
        
        h1, h2, h3, h4, h5, h6 {
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 700;
            line-height: 1.3;
            color: #1a1a1a;
            letter-spacing: -0.02em;
        }
        
        h1 {
            font-size: 2.5em;
            border-bottom: 3px solid #0969da;
            padding-bottom: 0.5em;
            margin-top: 0;
            background: linear-gradient(135deg, #0969da 0%, #1f6feb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        h2 {
            font-size: 1.8em;
            border-bottom: 2px solid #d0d7de;
            padding-bottom: 0.4em;
            color: #0969da;
        }
        
        h3 { font-size: 1.4em; color: #2da44e; }
        h4 { font-size: 1.2em; }
        h5 { font-size: 1.1em; }
        h6 { font-size: 1em; color: #656d76; }
        
        p { margin: 1em 0; }
        
        code {
            background: linear-gradient(135deg, #f6f8fa 0%, #eef1f5 100%);
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 0.2em 0.5em;
            font-family: 'SF Mono', 'Monaco', 'Roboto Mono', monospace;
            font-size: 0.9em;
            color: #cf222e;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        pre {
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 1.5rem;
            overflow-x: auto;
            line-height: 1.6;
            margin: 1.5em 0;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        pre code {
            background: transparent;
            border: none;
            padding: 0;
            font-size: 0.95em;
            color: #c9d1d9;
            box-shadow: none;
        }
        
        blockquote {
            border-left: 4px solid #0969da;
            padding: 0.5em 1.5em;
            color: #656d76;
            margin: 1.5em 0;
            background: #f6f8fa;
            border-radius: 0 6px 6px 0;
            font-style: italic;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        a {
            color: #0969da;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: all 0.2s ease;
        }
        
        a:hover { color: #1f6feb; border-bottom-color: #1f6feb; }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 2em 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border-radius: 8px;
            overflow: hidden;
        }
        
        table th {
            background: linear-gradient(135deg, #0969da 0%, #1f6feb 100%);
            color: white;
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
        }
        
        table td {
            border: 1px solid #d0d7de;
            padding: 12px 16px;
            transition: background-color 0.2s ease;
        }
        
        table tr:hover td { background-color: #f6f8fa; }
        table tr:nth-child(even) { background-color: #f9fafb; }
        
        ul, ol { padding-left: 2em; margin: 1em 0; }
        li { margin: 0.5em 0; padding-left: 0.5em; }
        ul li::marker { color: #0969da; font-weight: bold; }
        ol li::marker { color: #2da44e; font-weight: bold; }
        
        hr {
            border: 0;
            height: 2px;
            background: linear-gradient(to right, transparent, #d0d7de, transparent);
            margin: 3em 0;
        }
        
        @media (prefers-color-scheme: dark) {
            body {
                background: linear-gradient(to bottom, #0d1117 0%, #010409 100%);
                color: #e6edf3;
            }
            h1, h2, h3 { color: #e6edf3; }
            h1 {
                background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                border-bottom-color: #1f6feb;
            }
            h2 { border-bottom-color: #30363d; color: #58a6ff; }
            h3 { color: #3fb950; }
            code {
                background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
                border-color: #30363d;
                color: #ff7b72;
            }
            pre { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); }
            blockquote { background: #161b22; border-left-color: #1f6feb; color: #8b949e; }
            a { color: #58a6ff; }
            a:hover { color: #79c0ff; }
            table th { background: linear-gradient(135deg, #1f6feb 0%, #58a6ff 100%); }
            table td { border-color: #30363d; }
            table tr:hover td { background-color: #161b22; }
            table tr:nth-child(even) { background-color: #0d1117; }
        }
        """,
        
        "minimal": """
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 4rem 2rem;
            color: #2c3e50;
            background: #ffffff;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 2em 0 0.5em 0;
            font-weight: 400;
            color: #1a1a1a;
        }
        
        h1 { font-size: 2.2em; font-weight: 300; }
        h2 { font-size: 1.6em; margin-top: 1.5em; }
        h3 { font-size: 1.3em; }
        
        p { margin: 1.2em 0; }
        
        code {
            background: #f5f5f5;
            padding: 0.2em 0.4em;
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 0.9em;
            color: #2c3e50;
            border-radius: 3px;
        }
        
        pre {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 1.5rem;
            border-radius: 4px;
            overflow-x: auto;
            margin: 2em 0;
        }
        
        pre code { background: transparent; padding: 0; color: #ecf0f1; }
        
        blockquote {
            border-left: 3px solid #bdc3c7;
            padding-left: 1.5em;
            color: #7f8c8d;
            margin: 2em 0;
            font-style: italic;
        }
        
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 2em 0;
        }
        
        table th, table td {
            border: 1px solid #ecf0f1;
            padding: 0.8em;
            text-align: left;
        }
        
        table th { background: #ecf0f1; font-weight: 600; }
        
        ul, ol { margin: 1.2em 0; padding-left: 2em; }
        li { margin: 0.5em 0; }
        
        hr { border: 0; border-top: 1px solid #ecf0f1; margin: 3em 0; }
        
        @media (prefers-color-scheme: dark) {
            body { background: #1a1a1a; color: #e0e0e0; }
            h1, h2, h3 { color: #ffffff; }
            code { background: #2a2a2a; color: #e0e0e0; }
            blockquote { border-left-color: #555; color: #aaa; }
            a { color: #5dade2; }
            table th { background: #2a2a2a; }
            table th, table td { border-color: #3a3a3a; }
        }
        """,
        
        "github": """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            color: #24292f;
            background-color: #ffffff;
        }
        
        h1, h2, h3, h4, h5, h6 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        
        h1 { font-size: 2em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
        h2 { font-size: 1.5em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
        h3 { font-size: 1.25em; }
        
        code {
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 0.2em 0.4em;
            font-family: 'Courier New', Courier, monospace;
            font-size: 85%;
        }
        
        pre {
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
        }
        
        pre code { background-color: transparent; padding: 0; }
        
        blockquote {
            border-left: 4px solid #d0d7de;
            padding-left: 1em;
            color: #656d76;
            margin: 1em 0;
        }
        
        a { color: #0969da; text-decoration: none; }
        a:hover { text-decoration: underline; }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }
        
        table th, table td {
            border: 1px solid #d0d7de;
            padding: 6px 13px;
        }
        
        table tr:nth-child(2n) { background-color: #f6f8fa; }
        
        ul, ol { padding-left: 2em; }
        li { margin: 0.25em 0; }
        hr { border: 0; border-top: 1px solid #d0d7de; margin: 24px 0; }
        
        @media (prefers-color-scheme: dark) {
            body { background-color: #0d1117; color: #c9d1d9; }
            h1, h2 { border-bottom-color: #21262d; }
            code { background-color: #161b22; }
            pre { background-color: #161b22; }
            blockquote { color: #8b949e; border-left-color: #3b434b; }
            a { color: #58a6ff; }
            table th, table td { border-color: #3b434b; }
            table tr:nth-child(2n) { background-color: #161b22; }
        }
        """,
        
        "dark": """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.7;
            max-width: 900px;
            margin: 0 auto;
            padding: 3rem 2rem;
            color: #e6edf3;
            background: #0d1117;
            min-height: 100vh;
        }
        
        h1, h2, h3, h4, h5, h6 {
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 700;
            color: #ffffff;
        }
        
        h1 {
            font-size: 2.5em;
            border-bottom: 3px solid #1f6feb;
            padding-bottom: 0.5em;
            color: #58a6ff;
        }
        
        h2 {
            font-size: 1.8em;
            border-bottom: 2px solid #30363d;
            padding-bottom: 0.4em;
            color: #58a6ff;
        }
        
        h3 { font-size: 1.4em; color: #3fb950; }
        
        code {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 0.2em 0.5em;
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 0.9em;
            color: #ff7b72;
        }
        
        pre {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 1.5rem;
            overflow-x: auto;
            margin: 1.5em 0;
        }
        
        pre code {
            background: transparent;
            border: none;
            padding: 0;
            color: #c9d1d9;
        }
        
        blockquote {
            border-left: 4px solid #1f6feb;
            padding: 0.5em 1.5em;
            color: #8b949e;
            margin: 1.5em 0;
            background: #161b22;
            border-radius: 0 6px 6px 0;
        }
        
        a { color: #58a6ff; text-decoration: none; transition: color 0.2s; }
        a:hover { color: #79c0ff; }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 2em 0;
            border-radius: 8px;
            overflow: hidden;
        }
        
        table th {
            background: #1f6feb;
            color: white;
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
        }
        
        table td {
            border: 1px solid #30363d;
            padding: 12px 16px;
        }
        
        table tr:nth-child(even) { background-color: #161b22; }
        table tr:hover td { background-color: #21262d; }
        
        ul, ol { padding-left: 2em; margin: 1em 0; }
        li { margin: 0.5em 0; }
        ul li::marker { color: #58a6ff; }
        ol li::marker { color: #3fb950; }
        
        hr {
            border: 0;
            height: 2px;
            background: #30363d;
            margin: 3em 0;
        }
        """,
        
        "notion": """
        body {
            font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.65;
            max-width: 900px;
            margin: 0 auto;
            padding: 5rem 4rem;
            color: #37352f;
            background: #ffffff;
        }
        
        h1, h2, h3 {
            margin: 2em 0 0.5em 0;
            font-weight: 700;
            color: #37352f;
        }
        
        h1 {
            font-size: 2.5em;
            margin-top: 0;
            padding-bottom: 0.4em;
        }
        
        h2 { font-size: 1.8em; }
        h3 { font-size: 1.3em; }
        
        p { margin: 1em 0; color: #37352f; }
        
        code {
            background: #f7f6f3;
            color: #eb5757;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.9em;
        }
        
        pre {
            background: #2f3437;
            color: #ffffff;
            padding: 1.5rem;
            border-radius: 3px;
            overflow-x: auto;
            margin: 1.5em 0;
        }
        
        pre code {
            background: transparent;
            color: #ffffff;
            padding: 0;
        }
        
        blockquote {
            border-left: 3px solid #37352f;
            padding-left: 1.2em;
            color: #37352f;
            margin: 1.5em 0;
            font-size: 1em;
        }
        
        a {
            color: #37352f;
            text-decoration: underline;
            text-decoration-color: rgba(55, 53, 47, 0.4);
            transition: all 0.2s;
        }
        
        a:hover { text-decoration-color: rgba(55, 53, 47, 1); }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 2em 0;
        }
        
        table th, table td {
            border: 1px solid #e9e9e7;
            padding: 8px 12px;
            text-align: left;
        }
        
        table th {
            background: #f7f6f3;
            font-weight: 600;
            color: #37352f;
        }
        
        ul, ol { margin: 0.5em 0; padding-left: 1.8em; }
        li { margin: 0.3em 0; }
        
        hr {
            border: 0;
            border-top: 1px solid #e9e9e7;
            margin: 2em 0;
        }
        
        @media (prefers-color-scheme: dark) {
            body { background: #191919; color: #e6e6e6; }
            h1, h2, h3 { color: #e6e6e6; }
            p { color: #e6e6e6; }
            code { background: #2f2f2f; color: #eb5757; }
            blockquote { border-left-color: #e6e6e6; color: #9b9a97; }
            a { color: #e6e6e6; }
            table th { background: #2f2f2f; color: #e6e6e6; }
            table th, table td { border-color: #2f2f2f; }
        }
        """
    }
    
    return themes.get(theme, themes["default"])


def convert_markdown_to_html(markdown_path: Path, theme: str = "default") -> str:
    """Convert a markdown file to HTML and save to a temporary file.

    Args:
        markdown_path: Path to the markdown file
        theme: CSS theme name (default, minimal, github, dark, notion)

    Returns:
        Path to the temporary HTML file
    """
    # Read markdown content
    with open(markdown_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown to HTML
    md = markdown.Markdown(extensions=["fenced_code", "tables", "codehilite"])
    html_content = md.convert(md_content)

    # Get CSS for selected theme
    css_content = get_css_theme(theme)

    # Create HTML template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{markdown_path.name}</title>
    <style>
{css_content}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(html_template)
        temp_path = temp_file.name

    return temp_path


def get_all_lessons(recursive: bool = True) -> List[Dict[str, Any]]:
    """Return all lessons in global order.

    The recursive flag is kept for backward compatibility and ignored.
    """
    _ = recursive
    return catalog_get_all_lessons()


def get_next_lesson(
    current_lesson_id: str, metadata: Dict[str, Any]
) -> Optional[str]:
    """Return the next pending lesson id within the same track."""
    next_lesson = catalog_get_next_lesson(current_lesson_id, metadata)
    return next_lesson["lesson_id"] if next_lesson else None


def _load_catalog_or_exit() -> Dict[str, Any]:
    try:
        return load_learning_catalog()
    except LearningCatalogError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


def _load_metadata_or_exit() -> Dict[str, Any]:
    try:
        return load_metadata()
    except LearningCatalogError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


def _save_metadata_or_exit(metadata: Dict[str, Any]) -> None:
    try:
        save_metadata(metadata)
    except LearningCatalogError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


def _attach_progress_or_exit(
    catalog: Dict[str, Any], metadata: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        return attach_progress(catalog, metadata)
    except LearningCatalogError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


def _track_icon(track: Dict[str, Any]) -> str:
    status = track.get("progress_status")
    if status == "done":
        return "✅"
    if status == "in_progress":
        return "🔍"
    if status == "locked":
        return "🔒"
    return "⏳"


def _lesson_icon(lesson: Dict[str, Any]) -> str:
    status = lesson.get("progress_status")
    if status == "done":
        return "✅"
    if status == "current":
        return "🔍"
    return "⏳"


def _classification_display_name(classification: Dict[str, Any]) -> str:
    return classification.get("classification_name") or classification["classification_id"]


def _track_status_badge(track: Dict[str, Any]) -> str:
    status = track.get("progress_status")
    if status == "done":
        return "[DONE]"
    if status == "in_progress":
        return "[CONTINUE]"
    if status == "locked":
        return "[LOCKED]"
    return "[START]"


def _track_difficulty_label(track: Dict[str, Any]) -> str:
    values = [
        value
        for value in [track.get("difficulty_min"), track.get("difficulty_max")]
        if value
    ]
    if not values:
        return "-"
    if len(values) == 2 and values[0] != values[1]:
        return f"{values[0]} -> {values[1]}"
    return values[0]


def _track_progress_label(track: Dict[str, Any], include_private: bool = False) -> str:
    visible_lessons = _visible_lessons(track, include_private=include_private)
    lesson_total = len(visible_lessons)
    if lesson_total == 0:
        return "0/0"
    completed_visible = sum(
        1 for lesson in visible_lessons if lesson.get("progress_status") == "done"
    )
    return f"{completed_visible}/{lesson_total}"


def _lesson_kind_badge(lesson: Dict[str, Any]) -> str:
    kind = lesson.get("lesson_kind") or "lesson"
    if kind == "lesson":
        return ""
    return f" [{kind.replace('_', ' ').upper()}]"


def _visible_tracks(
    catalog: Dict[str, Any], include_drafts: bool = False
) -> List[Dict[str, Any]]:
    tracks = catalog["tracks"]
    if include_drafts:
        return list(tracks)
    return [track for track in tracks if track["status"] != "draft"]


def _visible_lessons(
    track: Dict[str, Any], include_private: bool = False
) -> List[Dict[str, Any]]:
    lessons = track["lessons"]
    if include_private:
        return list(lessons)
    return [lesson for lesson in lessons if lesson["public"]]


def _visible_classifications(
    catalog: Dict[str, Any],
    *,
    include_drafts: bool = False,
    include_private: bool = False,
    classification_id: Optional[str] = None,
    completed: bool = False,
    pending: bool = False,
    difficulty: Optional[str] = None,
) -> List[Dict[str, Any]]:
    classifications = []
    for classification in catalog.get("classifications", []):
        if classification_id and classification["classification_id"] != classification_id:
            continue

        tracks = []
        lesson_count = 0
        for track in classification["tracks"]:
            if not include_drafts and track["status"] == "draft":
                continue
            visible_lessons = _visible_lessons(track, include_private=include_private)
            if not _track_matches_filters(
                track, visible_lessons, completed, pending, difficulty
            ):
                continue
            tracks.append(track)
            lesson_count += len(visible_lessons)

        if not tracks:
            continue

        classifications.append(
            {
                "classification_id": classification["classification_id"],
                "classification_name": _classification_display_name(classification),
                "tracks": tracks,
                "track_count": len(tracks),
                "lesson_count": lesson_count,
            }
        )

    return classifications


def _lesson_matches_filters(
    lesson: Dict[str, Any],
    completed_lesson_ids: set,
    current_lesson_id: Optional[str],
    completed: bool,
    pending: bool,
    difficulty: Optional[str],
) -> bool:
    if completed and lesson["lesson_id"] not in completed_lesson_ids:
        return False
    if pending and lesson["lesson_id"] in completed_lesson_ids:
        return False
    if difficulty and (lesson.get("difficulty") or "").lower() != difficulty.lower():
        return False
    if lesson["lesson_id"] == current_lesson_id:
        lesson["progress_status"] = "current"
    elif lesson["lesson_id"] in completed_lesson_ids:
        lesson["progress_status"] = "done"
    else:
        lesson["progress_status"] = "todo"
    return True


def _track_matches_filters(
    track: Dict[str, Any],
    visible_lessons: List[Dict[str, Any]],
    completed: bool,
    pending: bool,
    difficulty: Optional[str],
) -> bool:
    if completed and track["progress_status"] != "done":
        return False
    if pending and track["progress_status"] == "done":
        return False
    if difficulty and not any(
        (lesson.get("difficulty") or "").lower() == difficulty.lower()
        for lesson in visible_lessons
    ):
        return False
    return True


def _track_display_name(track: Dict[str, Any]) -> str:
    return f"{track['track_id']} - {track['name']}"


def _track_lock_message(track: Dict[str, Any], catalog: Dict[str, Any]) -> str:
    unresolved = [
        dependency
        for dependency in track["depends_on_tracks"]
        if dependency not in catalog.get("completed_track_ids", set())
    ]
    if not unresolved:
        return f"Track '{track['track_id']}' is not available yet."
    return (
        f"Track '{track['track_id']}' is locked. Complete these tracks first: "
        f"{', '.join(unresolved)}."
    )


def _default_start_lesson(
    catalog: Dict[str, Any], metadata: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    current = get_current_lesson(metadata, catalog)
    completed_ids = get_completed_lesson_ids(metadata)
    if current and current["lesson_id"] not in completed_ids:
        return current

    candidate_groups = [
        [
            track
            for track in catalog["tracks"]
            if track["status"] == "active" and track["is_unlocked"]
        ],
        [track for track in catalog["tracks"] if track["is_unlocked"]],
        [track for track in catalog["tracks"] if track["status"] == "active"],
        list(catalog["tracks"]),
    ]

    for group in candidate_groups:
        for track in group:
            for lesson in track["lessons"]:
                if lesson["lesson_id"] not in completed_ids:
                    return lesson
            if track["lessons"]:
                return track["lessons"][0]

    return None


def _resolve_start_target(
    reference: Optional[str], catalog: Dict[str, Any], metadata: Dict[str, Any]
) -> Dict[str, Any]:
    if not reference:
        lesson = _default_start_lesson(catalog, metadata)
        if lesson is None:
            raise LearningReferenceError(
                "No lessons found. Add track folders under learning/lessons first."
            )
        return lesson

    reference = str(reference).strip()
    if not reference:
        raise LearningReferenceError("Reference cannot be empty.")

    if reference in catalog["lessons_by_id"] or "/" in reference:
        lesson = resolve_lesson_reference(reference, catalog)
        track = catalog["tracks_by_id"][lesson["track_id"]]
        if not track["is_unlocked"]:
            raise LearningReferenceError(_track_lock_message(track, catalog))
        return lesson

    track = resolve_track_reference(reference, catalog)
    if not track["is_unlocked"]:
        raise LearningReferenceError(_track_lock_message(track, catalog))
    if not track["lessons"]:
        raise LearningReferenceError(
            f"Track '{track['track_id']}' does not contain any lessons yet."
        )

    current = get_current_lesson(metadata, catalog)
    completed_ids = get_completed_lesson_ids(metadata)
    if current and current["track_id"] == track["track_id"]:
        if current["lesson_id"] not in completed_ids:
            return current

    for lesson in track["lessons"]:
        if lesson["lesson_id"] not in completed_ids:
            return lesson

    return track["lessons"][0]


def _suggest_unlocked_tracks(
    catalog: Dict[str, Any], metadata: Dict[str, Any], exclude_track_id: Optional[str]
) -> List[Dict[str, Any]]:
    catalog = _attach_progress_or_exit(catalog, metadata)
    completed_ids = get_completed_lesson_ids(metadata)
    return [
        track
        for track in catalog["tracks"]
        if track["status"] == "active"
        and track["is_unlocked"]
        and track["track_id"] != exclude_track_id
        and not is_track_completed(track, completed_ids)
    ]


def _print_track_suggestions(tracks: List[Dict[str, Any]]) -> None:
    if not tracks:
        return

    typer.echo("🧭 Unlocked tracks you can start next:")
    for track in tracks:
        typer.echo(f"  - {track['track_id']}: {track['name']}")


def _mark_lesson_completed(
    lesson: Dict[str, Any], metadata: Dict[str, Any], catalog: Dict[str, Any]
) -> Dict[str, Any]:
    completed_lesson_ids = get_completed_lesson_ids(metadata)
    if lesson["lesson_id"] in completed_lesson_ids:
        return {
            "already_completed": True,
            "next_lesson": None,
            "track_completed": False,
            "suggested_tracks": [],
        }

    metadata.setdefault("completed_lessons", [])
    metadata["completed_lessons"].append(
        {
            "lesson_id": lesson["lesson_id"],
            "completed_at": datetime.datetime.now().isoformat(),
        }
    )

    next_lesson = None
    track_completed = False
    suggested_tracks: List[Dict[str, Any]] = []

    if metadata.get("current_lesson_id") == lesson["lesson_id"]:
        next_lesson = catalog_get_next_lesson(lesson["lesson_id"], metadata, catalog)
        if next_lesson:
            metadata["current_lesson_id"] = next_lesson["lesson_id"]
        else:
            metadata["current_lesson_id"] = None
            track_completed = True
            suggested_tracks = _suggest_unlocked_tracks(
                catalog, metadata, lesson["track_id"]
            )

    _save_metadata_or_exit(metadata)

    return {
        "already_completed": False,
        "next_lesson": next_lesson,
        "track_completed": track_completed,
        "suggested_tracks": suggested_tracks,
    }


def _open_lesson_path(lesson: Dict[str, Any], web: bool = False) -> None:
    lesson_path = get_lessons_dir() / lesson["path"]
    if not lesson_path.exists():
        typer.echo(f"❌ Lesson file not found: {lesson_path}", err=True)
        raise typer.Exit(1)

    typer.echo(
        f"📖 Opening {lesson['track_id']}/{lesson['sequence_label']} - {lesson['title']}"
    )

    if web:
        config = load_config()
        web_config = config.get("generate", {}).get("web", {})
        base_url = web_config.get("url")

        if not base_url:
            typer.echo(
                "❌ No web URL configured in config.yaml under generate.web.url",
                err=True,
            )
            raise typer.Exit(1)

        lesson_url = f"{base_url.rstrip('/')}/{lesson['url']}"
        webbrowser.open(lesson_url)
        typer.echo(f"🌐 Opened in web browser: {lesson_url}")
        return

    editor = os.getenv("EDITOR", "vim")
    os.system(f'{editor} "{lesson_path}"')



FRONTMATTER_BLOCK_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n(.*))?$", re.DOTALL)


def _rewrite_frontmatter_field(path: Path, key: str, value: Any) -> None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_BLOCK_RE.match(text)
    if not match:
        typer.echo(f"❌ Markdown file is missing YAML frontmatter: {path}", err=True)
        raise typer.Exit(1)

    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        typer.echo(f"❌ Frontmatter must be a mapping: {path}", err=True)
        raise typer.Exit(1)

    frontmatter[key] = value
    body = match.group(2) or ""
    frontmatter_text = yaml.safe_dump(frontmatter, sort_keys=False)
    path.write_text(f"---\n{frontmatter_text}---\n\n{body.lstrip()}", encoding="utf-8")


def _resolve_publication_target(reference: str, catalog: Dict[str, Any]) -> tuple[Path, str]:
    try:
        track = resolve_track_reference(reference, catalog)
        return get_lessons_dir() / track["path"], f"track {track['track_id']}"
    except LearningReferenceError:
        pass

    try:
        lesson = resolve_lesson_reference(reference, catalog)
    except LearningReferenceError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)

    return (
        get_lessons_dir() / lesson["path"],
        f"lesson {lesson['track_id']}/{lesson['sequence_label']}",
    )


def _set_public(reference: str, is_public: bool) -> None:
    catalog = _load_catalog_or_exit()
    target_path, label = _resolve_publication_target(reference, catalog)
    _rewrite_frontmatter_field(target_path, "public", is_public)
    state = "public" if is_public else "hidden"
    typer.echo(f"✅ Set {label} to {state}.")

def display_lessons_tree(
    classifications: List[Dict[str, Any]], include_private: bool = False
) -> None:
    """Display classifications, tracks, and lessons in a tree structure."""
    console = Console()

    if not classifications:
        console.print("❌ No classifications found.")
        return

    root = Tree("📚 Learning")
    for classification in classifications:
        classification_node = root.add(
            f"🗂️ {_classification_display_name(classification)}"
        )
        for track in classification["tracks"]:
            visible_lessons = _visible_lessons(track, include_private=include_private)
            summary = (
                f"{_track_icon(track)} {track['name']} "
                f"{_track_status_badge(track)} "
                f"{_track_progress_label(track, include_private=include_private)}"
            )
            if track.get("track_tier"):
                summary += f" [{track['track_tier'].upper()}]"
            track_node = classification_node.add(summary)
            for lesson in visible_lessons:
                track_node.add(
                    f"{_lesson_icon(lesson)} {lesson['sequence_label']} "
                    f"{lesson['title']}{_lesson_kind_badge(lesson)}"
                )

    console.print(root)



@learn_app.command("publish")
def publish_content(
    reference: Annotated[
        str,
        typer.Argument(help="Track id, lesson id, or track_id/NNN[.md] to publish"),
    ],
):
    """Set a track or lesson public flag to true for generated sites."""
    _set_public(reference, True)


@learn_app.command("unpublish")
def unpublish_content(
    reference: Annotated[
        str,
        typer.Argument(help="Track id, lesson id, or track_id/NNN[.md] to hide"),
    ],
):
    """Set a track or lesson public flag to false for generated sites."""
    _set_public(reference, False)


@learn_app.command("review-next")
def review_next_lesson(
    track: Annotated[
        Optional[str],
        typer.Option("--track", help="Limit the review queue to one track"),
    ] = None,
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft tracks")
    ] = False,
    open_lesson: Annotated[
        bool, typer.Option("--open", help="Open the next pending lesson")
    ] = False,
):
    """Show the next lesson that still needs editorial review."""
    catalog = _load_catalog_or_exit()

    if track:
        try:
            tracks = [resolve_track_reference(track, catalog)]
        except LearningReferenceError as exc:
            typer.echo(f"❌ {exc}", err=True)
            raise typer.Exit(1)
    else:
        tracks = _visible_tracks(catalog, include_drafts=include_drafts)

    pending_lessons = [
        lesson
        for track_item in tracks
        for lesson in track_item["lessons"]
        if (lesson.get("review_status") or "pending") not in {"reviewed", "exempt"}
    ]

    if not pending_lessons:
        typer.echo("✅ No pending lessons found for review.")
        return

    pending_lessons.sort(
        key=lambda lesson: (
            lesson.get("legacy_day") if lesson.get("legacy_day") is not None else 10**9,
            lesson["track_id"],
            lesson["sequence"],
        )
    )
    lesson = pending_lessons[0]
    typer.echo(
        f"📝 Next review: {lesson['track_id']}/{lesson['sequence_label']} "
        f"[{lesson['lesson_id']}] - {lesson['title']}"
    )
    typer.echo(f"Path: {get_lessons_dir() / lesson['path']}")

    if open_lesson:
        _open_lesson_path(lesson)

@learn_app.command("current")
def open_current_lesson(
    web: Annotated[
        bool,
        typer.Option(
            "--web", help="Open the current lesson in the generated website"
        ),
    ] = False,
):
    """Open the current lesson using the configured editor or website."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)
    current = get_current_lesson(metadata, catalog)

    if not current:
        current = _default_start_lesson(catalog, metadata)
        if not current:
            typer.echo(
                "❌ No lessons found. Add track folders under learning/lessons first."
            )
            raise typer.Exit(1)
        metadata["current_lesson_id"] = current["lesson_id"]
        typer.echo(
            f"📚 Current lesson set to: {current['track_id']}/{current['sequence_label']}"
        )

    metadata["last_opened_at"] = datetime.datetime.now().isoformat()
    _save_metadata_or_exit(metadata)
    _open_lesson_path(current, web=web)


@learn_app.command("list")
def list_lessons(
    completed: Annotated[
        bool, typer.Option("--completed", "-c", help="Show only completed items")
    ] = False,
    pending: Annotated[
        bool, typer.Option("--pending", "-p", help="Show only pending items")
    ] = False,
    tree: Annotated[
        bool, typer.Option("--tree", "-t", help="Show a track tree")
    ] = False,
    track: Annotated[
        Optional[str],
        typer.Option("--track", help="List lessons for a specific track"),
    ] = None,
    classification: Annotated[
        Optional[str],
        typer.Option("--classification", help="Filter by classification slug"),
    ] = None,
    difficulty: Annotated[
        Optional[str],
        typer.Option(
            "--difficulty",
            "-d",
            help="Filter by difficulty (beginner, intermediate, advanced)",
        ),
    ] = None,
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft tracks")
    ] = False,
    include_private: Annotated[
        bool, typer.Option("--include-private", help="Include private lessons")
    ] = False,
):
    """List tracks or lessons in the current learning catalog."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)

    if classification and classification not in catalog.get("classifications_by_id", {}):
        typer.echo(f"❌ Unknown classification: {classification}", err=True)
        raise typer.Exit(1)

    if tree:
        if track:
            try:
                selected_track = resolve_track_reference(track, catalog)
            except LearningReferenceError as exc:
                typer.echo(f"❌ {exc}", err=True)
                raise typer.Exit(1)
            classifications = [
                {
                    "classification_id": selected_track["classification"],
                    "classification_name": selected_track.get("classification_name")
                    or selected_track["classification"].replace("-", " ").title(),
                    "tracks": [selected_track],
                }
            ]
        else:
            classifications = _visible_classifications(
                catalog,
                include_drafts=include_drafts,
                include_private=include_private,
                classification_id=classification,
                completed=completed,
                pending=pending,
                difficulty=difficulty,
            )
        display_lessons_tree(classifications, include_private=include_private)
        return

    console = Console()
    completed_ids = get_completed_lesson_ids(metadata)
    current_lesson_id = metadata.get("current_lesson_id")

    if track:
        try:
            selected_track = resolve_track_reference(track, catalog)
        except LearningReferenceError as exc:
            typer.echo(f"❌ {exc}", err=True)
            raise typer.Exit(1)

        lessons = [
            lesson
            for lesson in _visible_lessons(
                selected_track, include_private=include_private
            )
            if _lesson_matches_filters(
                lesson,
                completed_ids,
                current_lesson_id,
                completed,
                pending,
                difficulty,
            )
        ]

        if not lessons:
            typer.echo("❌ No lessons matched the requested filters.")
            return

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Status", style="cyan")
        table.add_column("Seq", style="white")
        table.add_column("Lesson", style="white")
        table.add_column("Minutes", style="green")

        for lesson in lessons:
            table.add_row(
                _lesson_icon(lesson),
                lesson["sequence_label"],
                f"{lesson['title']}{_lesson_kind_badge(lesson)}",
                str(lesson.get("estimated_time") or "-"),
            )

        console.print(table)
        console.print(
            f"\n📚 {selected_track['name']} "
            f"({_classification_display_name({'classification_name': selected_track.get('classification_name'), 'classification_id': selected_track['classification']})}) "
            f"| {_track_progress_label(selected_track, include_private=include_private)} completed"
        )
        return

    classifications_to_show = _visible_classifications(
        catalog,
        include_drafts=include_drafts,
        include_private=include_private,
        classification_id=classification,
        completed=completed,
        pending=pending,
        difficulty=difficulty,
    )

    if not classifications_to_show:
        typer.echo("❌ No tracks matched the requested filters.")
        return

    for classification_item in classifications_to_show:
        console.print()
        console.print(
            f"[bold]{classification_item['classification_name']}[/bold] "
            f"({classification_item['track_count']} tracks)"
        )
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Status", style="cyan")
        table.add_column("Track", style="white")
        table.add_column("Summary", style="white")
        table.add_column("Lessons", style="green")
        table.add_column("Difficulty", style="magenta")
        table.add_column("Tier", style="yellow")

        for track_item in classification_item["tracks"]:
            table.add_row(
                _track_status_badge(track_item),
                _track_display_name(track_item),
                track_item.get("description") or "-",
                _track_progress_label(track_item, include_private=include_private),
                _track_difficulty_label(track_item),
                track_item.get("track_tier") or "-",
            )

        console.print(table)

    total_tracks = sum(
        classification_item["track_count"] for classification_item in classifications_to_show
    )
    console.print(
        "\n📊 "
        f"Classifications: {len(classifications_to_show)} | "
        f"Tracks: {total_tracks} | "
        f"Done: {sum(track['progress_status'] == 'done' for classification_item in classifications_to_show for track in classification_item['tracks'])} | "
        f"In Progress: {sum(track['progress_status'] == 'in_progress' for classification_item in classifications_to_show for track in classification_item['tracks'])}"
    )


@learn_app.command("tree")
def show_lesson_tree(
    track: Annotated[
        Optional[str],
        typer.Option("--track", help="Show only a specific track"),
    ] = None,
    classification: Annotated[
        Optional[str],
        typer.Option("--classification", help="Show only a specific classification"),
    ] = None,
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft tracks")
    ] = False,
    include_private: Annotated[
        bool, typer.Option("--include-private", help="Include private lessons")
    ] = False,
):
    """Show tracks and lessons in a tree structure."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)
    if classification and classification not in catalog.get("classifications_by_id", {}):
        typer.echo(f"❌ Unknown classification: {classification}", err=True)
        raise typer.Exit(1)

    if track:
        try:
            selected_track = resolve_track_reference(track, catalog)
        except LearningReferenceError as exc:
            typer.echo(f"❌ {exc}", err=True)
            raise typer.Exit(1)
        classifications = [
            {
                "classification_id": selected_track["classification"],
                "classification_name": selected_track.get("classification_name")
                or selected_track["classification"].replace("-", " ").title(),
                "tracks": [selected_track],
            }
        ]
    else:
        classifications = _visible_classifications(
            catalog,
            include_drafts=include_drafts,
            include_private=include_private,
            classification_id=classification,
        )

    display_lessons_tree(classifications, include_private=include_private)


@learn_app.command("complete")
def complete_lesson(
    lesson: Annotated[
        Optional[str],
        typer.Argument(
            help="Lesson reference (lesson_id or track_id/NNN[.md]) to mark as completed"
        ),
    ] = None,
):
    """Mark a lesson as completed."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)

    if not lesson:
        current = get_current_lesson(metadata, catalog)
        if not current:
            typer.echo("❌ No current lesson set. Use 'mystuff learn start' first.")
            raise typer.Exit(1)
        target_lesson = current
    else:
        try:
            target_lesson = resolve_lesson_reference(lesson, catalog)
        except LearningReferenceError as exc:
            typer.echo(f"❌ {exc}", err=True)
            raise typer.Exit(1)

    result = _mark_lesson_completed(target_lesson, metadata, catalog)
    if result["already_completed"]:
        typer.echo(
            f"ℹ️  Lesson '{target_lesson['lesson_id']}' is already marked as completed."
        )
        return

    typer.echo(
        f"✅ Marked lesson '{target_lesson['lesson_id']}' "
        f"({target_lesson['track_id']}/{target_lesson['sequence_label']}) as completed."
    )
    if result["next_lesson"]:
        next_lesson = result["next_lesson"]
        typer.echo(
            f"📚 New current lesson: {next_lesson['track_id']}/{next_lesson['sequence_label']} "
            f"- {next_lesson['title']}"
        )
    elif result["track_completed"]:
        typer.echo(f"🎉 Track completed: {target_lesson['track_id']}")
        _print_track_suggestions(result["suggested_tracks"])


@learn_app.command("next")
def next_lesson(
    web: Annotated[
        bool, typer.Option("--web", help="Open the next lesson in the website")
    ] = False,
):
    """Complete the current lesson and advance within the same track."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)
    current = get_current_lesson(metadata, catalog)

    if not current:
        typer.echo("❌ No current lesson set. Use 'mystuff learn start' first.")
        raise typer.Exit(1)

    result = _mark_lesson_completed(current, metadata, catalog)
    if result["already_completed"]:
        typer.echo(
            f"ℹ️  Lesson '{current['lesson_id']}' was already completed."
        )
        return

    typer.echo(
        f"✅ Completed {current['track_id']}/{current['sequence_label']} - {current['title']}"
    )
    if result["next_lesson"]:
        next_lesson_item = result["next_lesson"]
        typer.echo(
            f"📚 Next lesson: {next_lesson_item['track_id']}/{next_lesson_item['sequence_label']} "
            f"- {next_lesson_item['title']}"
        )
        if typer.confirm("Open the next lesson now?", default=True):
            open_current_lesson(web=web)
        return

    typer.echo(f"🎉 Track completed: {current['track_id']}")
    _print_track_suggestions(result["suggested_tracks"])


@learn_app.command("start")
def start_lesson(
    lesson: Annotated[
        Optional[str],
        typer.Argument(
            help="Track id, lesson reference (track_id/NNN[.md]), or lesson_id"
        ),
    ] = None,
    fzf: Annotated[
        bool, typer.Option("--fzf", help="Use fzf to select a lesson")
    ] = False,
):
    """Start or resume a track-aware lesson flow."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)

    if fzf:
        unlocked_tracks = [
            track_item
            for track_item in catalog["tracks"]
            if track_item["is_unlocked"] and track_item["status"] == "active"
        ]
        selectable_lessons = [
            lesson_item
            for track_item in (unlocked_tracks or catalog["tracks"])
            for lesson_item in track_item["lessons"]
        ]

        if not selectable_lessons:
            typer.echo("❌ No lessons available to select.")
            raise typer.Exit(1)

        label_to_lesson: Dict[str, Dict[str, Any]] = {}
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as temp_input:
            for lesson_item in selectable_lessons:
                label = (
                    f"{lesson_item['track_id']}/{lesson_item['sequence_label']} | "
                    f"{lesson_item['title']} [{lesson_item['lesson_id']}]"
                )
                label_to_lesson[label] = lesson_item
                temp_input.write(f"{label}\n")
            temp_input_path = temp_input.name

        output_file = tempfile.mktemp(suffix=".txt")

        try:
            cmd = (
                f"cat {temp_input_path} | fzf --height=40% --layout=reverse "
                f"--prompt='Select lesson: ' > {output_file}"
            )
            result = os.system(cmd)

            if result == 0:
                with open(output_file, "r", encoding="utf-8") as handle:
                    selected_label = handle.read().strip()
                if not selected_label:
                    typer.echo("❌ No lesson selected.")
                    raise typer.Exit(1)
                lesson = label_to_lesson[selected_label]["lesson_id"]
            else:
                typer.echo("❌ No lesson selected.")
                raise typer.Exit(1)
        except FileNotFoundError:
            typer.echo("❌ No lesson selected.")
            raise typer.Exit(1)
        finally:
            try:
                os.unlink(temp_input_path)
            except OSError:
                pass
            try:
                os.unlink(output_file)
            except OSError:
                pass

    try:
        target_lesson = _resolve_start_target(lesson, catalog, metadata)
    except LearningReferenceError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)

    metadata["current_lesson_id"] = target_lesson["lesson_id"]
    _save_metadata_or_exit(metadata)
    typer.echo(
        f"📚 Current lesson set to: {target_lesson['track_id']}/{target_lesson['sequence_label']} "
        f"- {target_lesson['title']}"
    )

    if typer.confirm("Open this lesson now?", default=True):
        open_current_lesson()


@learn_app.command("stats")
def show_stats(
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft tracks")
    ] = False,
    include_private: Annotated[
        bool, typer.Option("--include-private", help="Include private lessons")
    ] = False,
):
    """Show track and lesson progress statistics."""
    metadata = _load_metadata_or_exit()
    catalog = _attach_progress_or_exit(_load_catalog_or_exit(), metadata)
    tracks = _visible_tracks(catalog, include_drafts=include_drafts)

    if not tracks:
        typer.echo("❌ No tracks found.")
        return

    visible_lessons = [
        lesson
        for track_item in tracks
        for lesson in _visible_lessons(track_item, include_private=include_private)
    ]
    visible_classifications = _visible_classifications(
        catalog,
        include_drafts=include_drafts,
        include_private=include_private,
    )
    completed_ids = get_completed_lesson_ids(metadata)
    completed_visible_lessons = sum(
        1 for lesson in visible_lessons if lesson["lesson_id"] in completed_ids
    )
    total_visible_lessons = len(visible_lessons)
    pending_visible_lessons = total_visible_lessons - completed_visible_lessons
    completion_pct = (
        (completed_visible_lessons / total_visible_lessons) * 100
        if total_visible_lessons
        else 0
    )

    first_date = None
    last_date = None
    avg_per_day = 0.0
    completed_items = metadata.get("completed_lessons", [])
    if completed_items:
        dates = [
            datetime.datetime.fromisoformat(item["completed_at"])
            for item in completed_items
            if item.get("completed_at")
        ]
        if dates:
            first_date = min(dates).date()
            last_date = max(dates).date()
            days = (last_date - first_date).days + 1
            avg_per_day = len(dates) / days if days > 0 else len(dates)

    console = Console()
    console.print("[bold blue]📊 Learning Statistics[/bold blue]\n")
    console.print(f"🗂️  Classifications visible: {len(visible_classifications)}")
    console.print(f"🧱 Tracks visible: {len(tracks)}")
    console.print(
        "✅ Tracks done: "
        f"{sum(track['progress_status'] == 'done' for track in tracks)}"
    )
    console.print(
        "🔍 Tracks in progress: "
        f"{sum(track['progress_status'] == 'in_progress' for track in tracks)}"
    )
    console.print(
        f"🔒 Tracks locked: {sum(track['progress_status'] == 'locked' for track in tracks)}"
    )

    console.print(f"\n📚 Lessons visible: {total_visible_lessons}")
    console.print(
        f"✅ Lessons completed: {completed_visible_lessons} ({completion_pct:.1f}%)"
    )
    console.print(f"⏳ Lessons pending: {pending_visible_lessons}")

    if first_date and last_date:
        console.print(f"\n📆 First completion: {first_date}")
        console.print(f"📆 Last completion: {last_date}")
        console.print(f"⏱️  Average: {avg_per_day:.2f} lessons/day")

    current = get_current_lesson(metadata, catalog)
    if current:
        console.print(
            f"\n🔍 Current lesson: {current['track_id']}/{current['sequence_label']} "
            f"- {current['title']}"
        )
    else:
        console.print("\n❌ No current lesson set.")

    if metadata.get("last_opened_at"):
        last_opened = datetime.datetime.fromisoformat(metadata["last_opened_at"])
        console.print(f"🕒 Last opened: {last_opened.strftime('%Y-%m-%d %H:%M:%S')}")

    classification_table = Table(show_header=True, header_style="bold blue")
    classification_table.add_column("Classification", style="white")
    classification_table.add_column("Tracks", style="green")
    classification_table.add_column("Done", style="cyan")
    classification_table.add_column("In Progress", style="yellow")

    for classification_item in visible_classifications:
        classification_table.add_row(
            classification_item["classification_name"],
            str(classification_item["track_count"]),
            str(
                sum(
                    track["progress_status"] == "done"
                    for track in classification_item["tracks"]
                )
            ),
            str(
                sum(
                    track["progress_status"] == "in_progress"
                    for track in classification_item["tracks"]
                )
            ),
        )

    track_table = Table(show_header=True, header_style="bold blue")
    track_table.add_column("Track", style="white")
    track_table.add_column("Classification", style="white")
    track_table.add_column("Status", style="cyan")
    track_table.add_column("Progress", style="green")
    track_table.add_column("Tier", style="yellow")

    for track_item in tracks:
        track_table.add_row(
            track_item["name"],
            track_item.get("classification_name")
            or track_item["classification"].replace("-", " ").title(),
            track_status_summary(track_item),
            _track_progress_label(track_item, include_private=include_private),
            track_item.get("track_tier") or "-",
        )

    console.print("\n")
    console.print(classification_table)
    console.print("\n")
    console.print(track_table)


@learn_app.command("reset")
def reset_progress(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
):
    """Reset all learning progress while keeping the lessons on disk."""
    if not confirm and not typer.confirm(
        "⚠️  This will reset all your learning progress. Continue?",
        default=False,
    ):
        typer.echo("❌ Operation cancelled.")
        raise typer.Exit(0)

    _save_metadata_or_exit(dict(METADATA_TEMPLATE))
    typer.echo("✅ Learning progress has been reset.")


if __name__ == "__main__":
    learn_app()
