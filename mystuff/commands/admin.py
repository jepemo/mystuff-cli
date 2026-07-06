#!/usr/bin/env python3
"""
MyStuff CLI - Administrative curriculum review commands.
"""

import shlex
import subprocess
import os
from typing import Annotated, Any, Dict, List, Optional

import typer

from mystuff.learning_catalog import (
    LearningCatalogError,
    LearningReferenceError,
    get_lessons_dir,
    get_mystuff_dir,
    load_learning_catalog,
    resolve_track_reference,
)

admin_app = typer.Typer(help="Run administrative curriculum review workflows")

REVIEWED_STATUSES = {"reviewed", "exempt"}


def _load_catalog_or_exit() -> Dict[str, Any]:
    try:
        return load_learning_catalog()
    except LearningCatalogError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


def _inactive_tracks(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        track
        for track in catalog["tracks"]
        if str(track.get("status") or "").strip() != "active"
    ]


def _lesson_review_status(lesson: Dict[str, Any]) -> str:
    return str(lesson.get("review_status") or "pending").strip()


def _pending_lessons(track: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        lesson
        for lesson in track["lessons"]
        if _lesson_review_status(lesson) not in REVIEWED_STATUSES
    ]


def _reviewed_lesson_count(track: Dict[str, Any]) -> int:
    return sum(
        1
        for lesson in track["lessons"]
        if _lesson_review_status(lesson) in REVIEWED_STATUSES
    )


def _lesson_sort_key(lesson: Dict[str, Any]) -> tuple:
    legacy_day = lesson.get("legacy_day")
    if legacy_day is None:
        legacy_day = 10**9
    return (legacy_day, lesson["track_id"], lesson["sequence"])


def _next_pending_lesson(tracks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    pending_lessons = [
        lesson for track in tracks for lesson in _pending_lessons(track)
    ]
    if not pending_lessons:
        return None

    pending_lessons.sort(key=_lesson_sort_key)
    return pending_lessons[0]


def _resolve_track_or_exit(track_id: str, catalog: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return resolve_track_reference(track_id, catalog)
    except LearningReferenceError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


def _first_track_pending_review(catalog: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for track in _inactive_tracks(catalog):
        if _pending_lessons(track):
            return track
    return None


def _first_track_in_review(catalog: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for track in _inactive_tracks(catalog):
        if _reviewed_lesson_count(track) > 0 and _pending_lessons(track):
            return track
    return None


def _track_review_summary(track: Dict[str, Any]) -> str:
    reviewed_count = _reviewed_lesson_count(track)
    pending_count = len(_pending_lessons(track))
    total_count = len(track["lessons"])
    return (
        f"{track['track_id']} | status={track.get('status')} | "
        f"reviewed={reviewed_count}/{total_count} | pending={pending_count}"
    )


def _print_track_summaries(tracks: List[Dict[str, Any]]) -> None:
    if not tracks:
        typer.echo("No tracks found.")
        return

    for track in tracks:
        typer.echo(_track_review_summary(track))


def _print_next_pending_lesson(lesson: Dict[str, Any]) -> None:
    typer.echo(
        f"📝 Next review: {lesson['track_id']}/{lesson['sequence_label']} "
        f"[{lesson['lesson_id']}] - {lesson['title']}"
    )
    typer.echo(f"Path: {get_lessons_dir() / lesson['path']}")


def _open_lesson_path(lesson: Dict[str, Any]) -> None:
    lesson_path = get_lessons_dir() / lesson["path"]
    editor_command = None
    for env_name in ("EDITOR", "VISUAL"):
        value = os.environ.get(env_name)
        if value:
            editor_command = shlex.split(value)
            break

    if not editor_command:
        typer.echo(f"Path: {lesson_path}")
        return

    try:
        subprocess.run(editor_command + [str(lesson_path)], check=True)
    except FileNotFoundError:
        typer.echo(f"❌ Editor not found: {editor_command[0]}", err=True)
        raise typer.Exit(1)
    except subprocess.CalledProcessError as exc:
        typer.echo(f"❌ Editor exited with code {exc.returncode}", err=True)
        raise typer.Exit(exc.returncode)


def _run_codex_prompt(
    prompt: str,
    *,
    codex_command: str,
    dry_run: bool,
) -> None:
    typer.echo(f"▶ {prompt}")
    if dry_run:
        return

    command = shlex.split(codex_command)
    if not command:
        typer.echo("❌ Empty Codex command.", err=True)
        raise typer.Exit(1)

    try:
        subprocess.run(
            command + ["exec", prompt],
            cwd=get_mystuff_dir(),
            check=True,
        )
    except FileNotFoundError:
        typer.echo(f"❌ Codex command not found: {command[0]}", err=True)
        raise typer.Exit(1)
    except subprocess.CalledProcessError as exc:
        typer.echo(f"❌ Codex prompt failed with code {exc.returncode}", err=True)
        raise typer.Exit(exc.returncode)


@admin_app.command("show-tracks-pending-review")
def show_tracks_pending_review():
    """Show inactive tracks that have pending lessons and no reviewed lessons yet."""
    catalog = _load_catalog_or_exit()
    tracks = [
        track
        for track in _inactive_tracks(catalog)
        if _pending_lessons(track) and _reviewed_lesson_count(track) == 0
    ]
    _print_track_summaries(tracks)


@admin_app.command("show-tracks-in-review")
def show_tracks_in_review():
    """Show inactive tracks with some reviewed lessons and more review work pending."""
    catalog = _load_catalog_or_exit()
    tracks = [
        track
        for track in _inactive_tracks(catalog)
        if _pending_lessons(track) and _reviewed_lesson_count(track) > 0
    ]
    _print_track_summaries(tracks)


@admin_app.command("review-next")
def review_next_lesson(
    track_id: Annotated[
        Optional[str],
        typer.Option("--track-id", help="Limit the review queue to one track"),
    ] = None,
    include_active: Annotated[
        bool, typer.Option("--include-active", help="Include active tracks")
    ] = False,
    open_lesson: Annotated[
        bool, typer.Option("--open", help="Open the next pending lesson")
    ] = False,
):
    """Show the next lesson that still needs editorial review."""
    catalog = _load_catalog_or_exit()

    if track_id:
        tracks = [_resolve_track_or_exit(track_id, catalog)]
    elif include_active:
        tracks = list(catalog["tracks"])
    else:
        tracks = _inactive_tracks(catalog)

    lesson = _next_pending_lesson(tracks)
    if not lesson:
        typer.echo("✅ No pending lessons found for review.")
        return

    _print_next_pending_lesson(lesson)
    if open_lesson:
        _open_lesson_path(lesson)


@admin_app.command("review-track")
def review_track(
    track_id: Annotated[
        Optional[str],
        typer.Option("--track-id", help="Track id to plan and review"),
    ] = None,
    codex_command: Annotated[
        str, typer.Option("--codex-command", help="Codex executable to run")
    ] = "codex",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print prompts without running Codex")
    ] = False,
):
    """Plan/review a track, then ask Codex to review its next lesson."""
    catalog = _load_catalog_or_exit()
    track = (
        _resolve_track_or_exit(track_id, catalog)
        if track_id
        else _first_track_pending_review(catalog)
    )
    if not track:
        typer.echo("✅ No inactive tracks with pending lessons found.")
        return

    _run_codex_prompt(
        f"Planifica/revisa el track {track['track_id']}.",
        codex_command=codex_command,
        dry_run=dry_run,
    )
    _run_codex_prompt(
        f"Revisa la siguiente leccion del track {track['track_id']}.",
        codex_command=codex_command,
        dry_run=dry_run,
    )


@admin_app.command("review-lesson")
def review_lesson(
    track_id: Annotated[
        Optional[str],
        typer.Option("--track-id", help="Track id whose next lesson should be reviewed"),
    ] = None,
    codex_command: Annotated[
        str, typer.Option("--codex-command", help="Codex executable to run")
    ] = "codex",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print prompt without running Codex")
    ] = False,
):
    """Ask Codex to review the next lesson of a track already in review."""
    catalog = _load_catalog_or_exit()
    track = (
        _resolve_track_or_exit(track_id, catalog)
        if track_id
        else _first_track_in_review(catalog)
    )
    if not track:
        typer.echo("✅ No inactive tracks currently in review found.")
        return

    _run_codex_prompt(
        f"Revisa la siguiente leccion del track {track['track_id']}.",
        codex_command=codex_command,
        dry_run=dry_run,
    )
