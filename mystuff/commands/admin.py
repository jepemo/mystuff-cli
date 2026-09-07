#!/usr/bin/env python3
"""
MyStuff CLI - Administrative curriculum review commands.
"""

import json
import os
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import typer

from mystuff.ai import (
    AgentRunnerError,
    build_codex_exec_command,
    resolve_agent_settings,
)
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
CODEX_STATUS_TAIL_BYTES = 2 * 1024 * 1024


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
    pending_lessons = [lesson for track in tracks for lesson in _pending_lessons(track)]
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


def _get_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()


def _recent_session_files(codex_home: Path, started_at: float) -> List[Path]:
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        return []

    files = []
    for path in sessions_dir.rglob("*.jsonl"):
        try:
            files.append((path.stat().st_mtime, path))
        except OSError:
            continue

    files.sort(key=lambda item: item[0], reverse=True)
    recent = [path for mtime, path in files if mtime >= started_at - 2]
    return recent or [path for _, path in files[:8]]


def _tail_text(path: Path, max_bytes: int = CODEX_STATUS_TAIL_BYTES) -> str:
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            return handle.read().decode("utf-8", errors="ignore")
    except OSError:
        return ""


def _latest_token_count_event(path: Path) -> Optional[Dict[str, Any]]:
    for line in reversed(_tail_text(path).splitlines()):
        if "token_count" not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "event_msg":
            payload = event.get("payload") or {}
            if payload.get("type") == "token_count":
                payload = dict(payload)
                payload["rate_limits"] = event.get("rate_limits") or {}
                return payload
        if event.get("type") == "token_count":
            return event

    return None


def _latest_codex_status(started_at: float) -> Optional[Dict[str, Any]]:
    for path in _recent_session_files(_get_codex_home(), started_at):
        event = _latest_token_count_event(path)
        if event:
            return event
    return None


def _format_reset_time(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError, OverflowError):
        return "unknown"


def _format_window(minutes: Any) -> str:
    try:
        total_minutes = int(minutes)
    except (TypeError, ValueError):
        return ""
    if total_minutes % 1440 == 0:
        days = total_minutes // 1440
        return f"{days}d"
    if total_minutes % 60 == 0:
        hours = total_minutes // 60
        return f"{hours}h"
    return f"{total_minutes}m"


def _print_codex_status(started_at: float) -> None:
    status = _latest_codex_status(started_at)
    if not status:
        typer.echo("Codex status unavailable.")
        return

    rate_limits = status.get("rate_limits") or {}
    typer.echo("Codex status:")
    for label in ("primary", "secondary"):
        limit = rate_limits.get(label)
        if not isinstance(limit, dict):
            continue
        used_percent = limit.get("used_percent", "unknown")
        window = _format_window(limit.get("window_minutes"))
        reset_time = _format_reset_time(limit.get("resets_at"))
        suffix = f" ({window} window)" if window else ""
        typer.echo(f"  {label}: {used_percent}% used{suffix}, resets {reset_time}")

    plan_type = rate_limits.get("plan_type")
    if plan_type:
        typer.echo(f"  plan: {plan_type}")


def _run_codex_prompt(
    prompt: str,
    *,
    codex_command: str,
    dry_run: bool,
    show_status: bool,
) -> None:
    typer.echo(f"▶ {prompt}")
    if dry_run:
        return

    try:
        settings = resolve_agent_settings(
            "learning",
            get_mystuff_dir(),
            command_override=(codex_command if codex_command != "codex" else None),
        )
    except AgentRunnerError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)
    command = build_codex_exec_command(settings, prompt, cwd=get_mystuff_dir())

    started_at = time.time()
    try:
        subprocess.run(
            command,
            cwd=get_mystuff_dir(),
            check=True,
        )
        if show_status:
            _print_codex_status(started_at)
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
    show_status: Annotated[
        bool,
        typer.Option(
            "--status/--no-status",
            help="Show best-effort Codex usage status after each prompt",
        ),
    ] = True,
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
        show_status=show_status,
    )
    _run_codex_prompt(
        f"Revisa la siguiente leccion del track {track['track_id']}.",
        codex_command=codex_command,
        dry_run=dry_run,
        show_status=show_status,
    )


@admin_app.command("review-lesson")
def review_lesson(
    track_id: Annotated[
        Optional[str],
        typer.Option(
            "--track-id", help="Track id whose next lesson should be reviewed"
        ),
    ] = None,
    codex_command: Annotated[
        str, typer.Option("--codex-command", help="Codex executable to run")
    ] = "codex",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print prompt without running Codex")
    ] = False,
    show_status: Annotated[
        bool,
        typer.Option(
            "--status/--no-status",
            help="Show best-effort Codex usage status after the prompt",
        ),
    ] = True,
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
        show_status=show_status,
    )
