#!/usr/bin/env python3
"""
Shared helpers for the learning catalog and progress metadata.
"""

import os
import re
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

TRACK_FILENAME = "TRACK.md"
ROOT_IGNORED_FILES = {"README.md", ".gitkeep"}
LESSON_FILENAME_RE = re.compile(r"^\d{3}\.md$")
METADATA_SCHEMA_VERSION = 2
METADATA_TEMPLATE_V2 = {
    "schema_version": METADATA_SCHEMA_VERSION,
    "current_lesson_id": None,
    "current_lesson_ids_by_track": {},
    "last_opened_at": None,
    "completed_lessons": [],
}


def fresh_metadata_template() -> Dict[str, Any]:
    """Return a fresh schema v2 metadata payload."""
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "current_lesson_id": None,
        "current_lesson_ids_by_track": {},
        "last_opened_at": None,
        "completed_lessons": [],
    }


class LearningCatalogError(Exception):
    """Raised when the learning catalog cannot be loaded."""


class LearningMetadataError(LearningCatalogError):
    """Raised when learning metadata is invalid or outdated."""


class LearningReferenceError(LearningCatalogError):
    """Raised when a lesson or track reference cannot be resolved."""


def get_mystuff_dir() -> Path:
    """Get the mystuff directory path."""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home)

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

    learning_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir.mkdir(parents=True, exist_ok=True)


def extract_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None, content

    pattern = r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n(.*))?$"
    match = re.match(pattern, content, re.DOTALL)
    if not match:
        return None, content

    frontmatter_yaml = match.group(1)
    body = match.group(2) or ""

    try:
        frontmatter = yaml.safe_load(frontmatter_yaml)
    except yaml.YAMLError as exc:
        raise LearningCatalogError(f"Invalid YAML frontmatter: {exc}") from exc

    if frontmatter is None:
        frontmatter = {}
    if not isinstance(frontmatter, dict):
        raise LearningCatalogError("Frontmatter must decode to a mapping.")

    return frontmatter, body


def _metadata_upgrade_message(metadata_path: Path) -> str:
    return (
        f"Legacy learning metadata detected at {metadata_path}. "
        "The track-based learner requires metadata schema_version: 2 and "
        "lesson_id-based progress. Run `mystuff learn reset --yes` to recreate "
        "metadata.yaml, or remove the file manually if you want to start fresh."
    )


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]

    value_str = str(value).strip()
    return [value_str] if value_str else []


def _normalize_optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None

    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1", "on"}:
        return True
    if normalized in {"false", "no", "0", "off"}:
        return False
    return default


def _humanize_slug(value: str) -> str:
    return str(value or "").replace("-", " ").strip().title()


def _validate_track_dir_files(track_dir: Path) -> None:
    for child in sorted(track_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            raise LearningCatalogError(
                f"Unexpected nested directory in track '{track_dir.name}': {child.name}. "
                "Tracks must store lessons directly as learning/lessons/<track_id>/<NNN>.md."
            )


def _load_lesson(
    file_path: Path,
    track_id: str,
    track_classification: str,
    lessons_dir: Path,
) -> Dict[str, Any]:
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LearningCatalogError(
            f"Could not read lesson file '{file_path}'."
        ) from exc

    frontmatter, body = extract_frontmatter(content)
    if frontmatter is None:
        raise LearningCatalogError(f"Lesson '{file_path}' is missing YAML frontmatter.")

    lesson_id = str(frontmatter.get("lesson_id") or "").strip()
    title = str(frontmatter.get("title") or "").strip()
    lesson_track_id = str(frontmatter.get("track_id") or "").strip()
    classification = str(frontmatter.get("classification") or "").strip()
    sequence = _normalize_optional_int(frontmatter.get("sequence"))

    if (
        not lesson_id
        or not title
        or not lesson_track_id
        or not classification
        or sequence is None
    ):
        raise LearningCatalogError(
            f"Lesson '{file_path}' must define lesson_id, title, track_id, "
            "classification, and sequence."
        )

    if lesson_track_id != track_id:
        raise LearningCatalogError(
            f"Lesson '{file_path}' declares track_id '{lesson_track_id}' "
            f"but is stored under '{track_id}'."
        )

    if classification != track_classification:
        raise LearningCatalogError(
            f"Lesson '{file_path}' declares classification '{classification}' "
            f"but track '{track_id}' uses '{track_classification}'."
        )

    file_sequence = int(file_path.stem)
    if sequence != file_sequence:
        raise LearningCatalogError(
            f"Lesson '{file_path}' has sequence '{sequence}' "
            f"but the filename encodes '{file_path.stem}'."
        )

    lesson = {
        "lesson_id": lesson_id,
        "title": title,
        "track_id": track_id,
        "classification": classification,
        "sequence": sequence,
        "sequence_label": f"{sequence:03d}",
        "difficulty": str(frontmatter.get("difficulty") or "").strip() or None,
        "estimated_time": _normalize_optional_int(frontmatter.get("estimated_time")),
        "public": _normalize_bool(frontmatter.get("public"), default=True),
        "review_status": str(frontmatter.get("review_status") or "").strip() or None,
        "lesson_kind": str(frontmatter.get("lesson_kind") or "").strip() or "lesson",
        "capstone_scope": str(frontmatter.get("capstone_scope") or "").strip() or None,
        "depends_on_tracks": _normalize_string_list(
            frontmatter.get("depends_on_tracks")
        ),
        "legacy_day": _normalize_optional_int(frontmatter.get("legacy_day")),
        "legacy_path": str(frontmatter.get("legacy_path") or "").strip() or None,
        "path": str(file_path.relative_to(lessons_dir)),
        "filename": file_path.name,
        "body_markdown": body,
        "url": f"lessons/{track_id}/{file_path.stem}.html",
    }

    return lesson


def _load_track(track_dir: Path, lessons_dir: Path) -> Dict[str, Any]:
    track_file = track_dir / TRACK_FILENAME
    if not track_file.exists():
        raise LearningCatalogError(
            f"Track directory '{track_dir.name}' is missing TRACK.md."
        )

    _validate_track_dir_files(track_dir)

    try:
        content = track_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise LearningCatalogError(
            f"Could not read track file '{track_file}'."
        ) from exc

    frontmatter, body = extract_frontmatter(content)
    if frontmatter is None:
        raise LearningCatalogError(
            f"Track file '{track_file}' is missing YAML frontmatter."
        )

    track_id = str(frontmatter.get("track_id") or "").strip()
    classification = str(frontmatter.get("classification") or "").strip()
    if not track_id:
        raise LearningCatalogError(f"Track file '{track_file}' must define track_id.")
    if not classification:
        raise LearningCatalogError(
            f"Track file '{track_file}' must define classification."
        )
    if track_id != track_dir.name:
        raise LearningCatalogError(
            f"Track file '{track_file}' declares track_id '{track_id}' "
            f"but the directory is named '{track_dir.name}'."
        )

    lessons: List[Dict[str, Any]] = []
    for file_path in sorted(track_dir.glob("*.md")):
        if file_path.name == TRACK_FILENAME or file_path.name.startswith("."):
            continue
        if not LESSON_FILENAME_RE.match(file_path.name):
            continue
        lessons.append(_load_lesson(file_path, track_id, classification, lessons_dir))

    lessons.sort(key=lambda lesson: lesson["sequence"])

    declared_lesson_count = _normalize_optional_int(frontmatter.get("lesson_count"))
    target_lesson_count = _normalize_optional_int(
        frontmatter.get("target_lesson_count")
    )
    actual_lesson_count = len(lessons)
    if (
        declared_lesson_count is not None
        and declared_lesson_count != actual_lesson_count
    ):
        warnings.warn(
            f"Track '{track_id}' declares lesson_count={declared_lesson_count}, "
            f"but {actual_lesson_count} lessons were found. Using the real count.",
            stacklevel=2,
        )
    if target_lesson_count is not None and target_lesson_count != actual_lesson_count:
        warnings.warn(
            f"Track '{track_id}' declares target_lesson_count={target_lesson_count}, "
            f"but {actual_lesson_count} lessons were found.",
            stacklevel=2,
        )

    track = {
        "track_id": track_id,
        "name": str(frontmatter.get("name") or track_id).strip(),
        "description": str(frontmatter.get("description") or "").strip(),
        "classification": classification,
        "classification_name": _humanize_slug(classification),
        "roadmap": str(frontmatter.get("roadmap") or "uncategorized").strip()
        or "uncategorized",
        "roadmap_name": _humanize_slug(frontmatter.get("roadmap") or "uncategorized"),
        "track_tier": str(frontmatter.get("track_tier") or "").strip() or None,
        "target_lesson_count": target_lesson_count,
        "depends_on_tracks": _normalize_string_list(
            frontmatter.get("depends_on_tracks")
        ),
        "status": str(frontmatter.get("status") or "active").strip() or "active",
        "public": _normalize_bool(frontmatter.get("public"), default=True),
        "lesson_count": actual_lesson_count,
        "difficulty_min": str(frontmatter.get("difficulty_min") or "").strip() or None,
        "difficulty_max": str(frontmatter.get("difficulty_max") or "").strip() or None,
        "capstone_policy": str(frontmatter.get("capstone_policy") or "").strip()
        or None,
        "legacy_source_ranges": _normalize_string_list(
            frontmatter.get("legacy_source_ranges")
        ),
        "path": str(track_file.relative_to(lessons_dir)),
        "url": f"tracks/{track_id}.html",
        "body_markdown": body,
        "body_html": None,
        "lessons": lessons,
        "unlocks": [],
        "is_unlocked": False,
        "is_publicly_visible": (
            str(frontmatter.get("status") or "active").strip() == "active"
            and _normalize_bool(frontmatter.get("public"), default=True)
        ),
    }

    return track


def _lesson_global_sort_key(lesson: Dict[str, Any]) -> tuple:
    if lesson.get("legacy_day") is not None:
        return (0, lesson["legacy_day"], lesson["track_id"], lesson["sequence"])

    lesson_id_num = _normalize_optional_int(lesson.get("lesson_id"))
    if lesson_id_num is not None:
        return (1, lesson_id_num, lesson["track_id"], lesson["sequence"])

    return (2, lesson["track_id"], lesson["sequence"])


def _track_sort_key(track: Dict[str, Any]) -> tuple:
    if track["lessons"]:
        return _lesson_global_sort_key(track["lessons"][0])
    return (3, track["track_id"])


def _build_classifications(tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    classifications_by_id: Dict[str, Dict[str, Any]] = {}
    classifications: List[Dict[str, Any]] = []

    for track in tracks:
        classification_id = track["classification"]
        classification = classifications_by_id.get(classification_id)
        if classification is None:
            classification = {
                "classification_id": classification_id,
                "classification_name": _humanize_slug(classification_id),
                "tracks": [],
                "track_count": 0,
                "lesson_count": 0,
            }
            classifications_by_id[classification_id] = classification
            classifications.append(classification)

        classification["tracks"].append(track)
        classification["track_count"] += 1
        classification["lesson_count"] += track["lesson_count"]

    return classifications


def load_learning_catalog() -> Dict[str, Any]:
    """Load the normalized learning catalog from tracks and lessons."""
    ensure_learning_structure()
    lessons_dir = get_lessons_dir()

    top_level_md_files: List[str] = []
    tracks: List[Dict[str, Any]] = []

    for child in sorted(lessons_dir.iterdir()):
        if child.is_file():
            if child.name.startswith(".") or child.name in ROOT_IGNORED_FILES:
                continue
            if child.suffix.lower() == ".md":
                top_level_md_files.append(child.name)
            continue

        if child.is_dir() and not child.name.startswith("."):
            tracks.append(_load_track(child, lessons_dir))

    if top_level_md_files:
        raise LearningCatalogError(
            "Legacy learning layout detected. Found markdown files directly under "
            f"{lessons_dir}: {', '.join(top_level_md_files)}. "
            "Tracks must now live under learning/lessons/<track_id>/ with TRACK.md."
        )

    tracks.sort(key=_track_sort_key)

    tracks_by_id = {track["track_id"]: track for track in tracks}
    for track in tracks:
        for dependency in track["depends_on_tracks"]:
            if dependency in tracks_by_id:
                tracks_by_id[dependency]["unlocks"].append(track["track_id"])

    lessons: List[Dict[str, Any]] = []
    lessons_by_id: Dict[str, Dict[str, Any]] = {}
    lessons_by_path: Dict[str, Dict[str, Any]] = {}

    for track in tracks:
        for lesson in track["lessons"]:
            if lesson["lesson_id"] in lessons_by_id:
                raise LearningCatalogError(
                    f"Duplicate lesson_id detected: {lesson['lesson_id']}."
                )
            lessons.append(lesson)
            lessons_by_id[lesson["lesson_id"]] = lesson
            lessons_by_path[lesson["path"]] = lesson

    lessons.sort(key=_lesson_global_sort_key)
    classifications = _build_classifications(tracks)
    classifications_by_id = {
        classification["classification_id"]: classification
        for classification in classifications
    }

    return {
        "tracks": tracks,
        "tracks_by_id": tracks_by_id,
        "classifications": classifications,
        "classifications_by_id": classifications_by_id,
        "lessons": lessons,
        "lessons_by_id": lessons_by_id,
        "lessons_by_path": lessons_by_path,
    }


def load_metadata() -> Dict[str, Any]:
    """Load learning progress metadata, creating schema v2 when missing."""
    ensure_learning_structure()
    metadata_path = get_metadata_path()

    if not metadata_path.exists():
        metadata = fresh_metadata_template()
        save_metadata(metadata)
        return metadata

    try:
        with open(metadata_path, "r", encoding="utf-8") as handle:
            raw_metadata = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise LearningMetadataError(f"Error parsing metadata.yaml: {exc}") from exc
    except OSError as exc:
        raise LearningMetadataError(f"Error reading metadata.yaml: {exc}") from exc

    if raw_metadata is None:
        metadata = fresh_metadata_template()
        save_metadata(metadata)
        return metadata

    if not isinstance(raw_metadata, dict):
        raise LearningMetadataError(
            f"Invalid metadata format in {metadata_path}. Expected a mapping."
        )

    if any(key in raw_metadata for key in ("current_lesson", "last_opened")):
        raise LearningMetadataError(_metadata_upgrade_message(metadata_path))

    if "schema_version" not in raw_metadata:
        if raw_metadata:
            raise LearningMetadataError(_metadata_upgrade_message(metadata_path))
        metadata = fresh_metadata_template()
        save_metadata(metadata)
        return metadata

    if raw_metadata.get("schema_version") != METADATA_SCHEMA_VERSION:
        raise LearningMetadataError(
            f"Unsupported learning metadata schema_version="
            f"{raw_metadata.get('schema_version')}. Expected {METADATA_SCHEMA_VERSION}."
        )

    completed_raw = raw_metadata.get("completed_lessons") or []
    if not isinstance(completed_raw, list):
        raise LearningMetadataError("completed_lessons must be a list.")

    normalized_completed = []
    for item in completed_raw:
        if not isinstance(item, dict):
            raise LearningMetadataError(_metadata_upgrade_message(metadata_path))
        if "lesson_id" not in item:
            raise LearningMetadataError(_metadata_upgrade_message(metadata_path))

        lesson_id = str(item.get("lesson_id") or "").strip()
        completed_at = str(item.get("completed_at") or "").strip()
        if not lesson_id or not completed_at:
            raise LearningMetadataError(
                "Each completed_lessons item must define lesson_id and completed_at."
            )
        normalized_completed.append(
            {"lesson_id": lesson_id, "completed_at": completed_at}
        )

    current_by_track_raw = raw_metadata.get("current_lesson_ids_by_track") or {}
    if not isinstance(current_by_track_raw, dict):
        raise LearningMetadataError("current_lesson_ids_by_track must be a mapping.")

    current_lesson_ids_by_track = {
        str(track_id).strip(): str(lesson_id).strip()
        for track_id, lesson_id in current_by_track_raw.items()
        if str(track_id).strip() and str(lesson_id).strip()
    }

    metadata = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "current_lesson_id": (
            str(raw_metadata.get("current_lesson_id")).strip()
            if raw_metadata.get("current_lesson_id") is not None
            else None
        ),
        "current_lesson_ids_by_track": current_lesson_ids_by_track,
        "last_opened_at": (
            str(raw_metadata.get("last_opened_at")).strip()
            if raw_metadata.get("last_opened_at")
            else None
        ),
        "completed_lessons": normalized_completed,
    }

    return metadata


def save_metadata(metadata: Dict[str, Any]) -> None:
    """Save schema v2 learning metadata."""
    ensure_learning_structure()
    metadata_path = get_metadata_path()

    payload = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "current_lesson_id": metadata.get("current_lesson_id"),
        "current_lesson_ids_by_track": metadata.get("current_lesson_ids_by_track", {}),
        "last_opened_at": metadata.get("last_opened_at"),
        "completed_lessons": metadata.get("completed_lessons", []),
    }

    try:
        with open(metadata_path, "w", encoding="utf-8") as handle:
            yaml.dump(payload, handle, default_flow_style=False, sort_keys=False)
    except OSError as exc:
        raise LearningMetadataError(f"Error saving metadata: {exc}") from exc


def get_all_lessons(catalog: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Return all lessons in global order."""
    if catalog is None:
        catalog = load_learning_catalog()
    return list(catalog["lessons"])


def get_completed_lesson_ids(metadata: Dict[str, Any]) -> set:
    """Return the set of completed lesson IDs."""
    return {
        str(item["lesson_id"])
        for item in metadata.get("completed_lessons", [])
        if item.get("lesson_id")
    }


def get_current_lesson_ids_by_track(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Return current lesson ids keyed by track id."""
    raw_current = metadata.get("current_lesson_ids_by_track") or {}
    if not isinstance(raw_current, dict):
        return {}
    return {
        str(track_id).strip(): str(lesson_id).strip()
        for track_id, lesson_id in raw_current.items()
        if str(track_id).strip() and str(lesson_id).strip()
    }


def is_track_completed(track: Dict[str, Any], completed_lesson_ids: set) -> bool:
    """Return whether all lessons in the track have been completed."""
    lesson_ids = [lesson["lesson_id"] for lesson in track["lessons"]]
    if not lesson_ids:
        return False
    return all(lesson_id in completed_lesson_ids for lesson_id in lesson_ids)


def _completed_track_ids(
    tracks: List[Dict[str, Any]], completed_lesson_ids: set
) -> set:
    return {
        track["track_id"]
        for track in tracks
        if is_track_completed(track, completed_lesson_ids)
    }


def attach_progress(
    catalog: Dict[str, Any], metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Attach progress fields to tracks and lessons."""
    completed_lesson_ids = get_completed_lesson_ids(metadata)
    completed_track_ids = _completed_track_ids(catalog["tracks"], completed_lesson_ids)
    current_lesson_ids_by_track = get_current_lesson_ids_by_track(metadata)
    # Schema v2 initially stored a single global cursor.  Honour it only for
    # old metadata that has not acquired a per-track cursor yet; once a track
    # cursor exists it is the source of truth.
    if not current_lesson_ids_by_track and metadata.get("current_lesson_id"):
        legacy_current_lesson = catalog["lessons_by_id"].get(
            str(metadata["current_lesson_id"])
        )
        if legacy_current_lesson:
            current_lesson_ids_by_track[legacy_current_lesson["track_id"]] = (
                legacy_current_lesson["lesson_id"]
            )

    current_lesson_ids = set(current_lesson_ids_by_track.values())

    for lesson in catalog["lessons"]:
        if (
            lesson["lesson_id"] in current_lesson_ids
            and lesson["lesson_id"] not in completed_lesson_ids
        ):
            lesson["progress_status"] = "current"
        elif lesson["lesson_id"] in completed_lesson_ids:
            lesson["progress_status"] = "done"
        else:
            lesson["progress_status"] = "todo"

    for track in catalog["tracks"]:
        track_completed_count = sum(
            1
            for lesson in track["lessons"]
            if lesson["lesson_id"] in completed_lesson_ids
        )
        track_current_lesson_id = current_lesson_ids_by_track.get(track["track_id"])
        current_in_track = next(
            (
                lesson
                for lesson in track["lessons"]
                if lesson["lesson_id"] == track_current_lesson_id
                and lesson["lesson_id"] not in completed_lesson_ids
            ),
            None,
        )
        is_unlocked = all(
            dependency in completed_track_ids
            for dependency in track["depends_on_tracks"]
        )

        if is_track_completed(track, completed_lesson_ids):
            progress_status = "done"
        elif current_in_track or track_completed_count > 0:
            progress_status = "in_progress"
        elif is_unlocked:
            progress_status = "not_started"
        else:
            progress_status = "locked"

        track["completed_count"] = track_completed_count
        track["current_lesson_id"] = (
            current_in_track["lesson_id"] if current_in_track else None
        )
        track["is_unlocked"] = is_unlocked
        track["progress_status"] = progress_status

    catalog["completed_lesson_ids"] = completed_lesson_ids
    catalog["completed_track_ids"] = completed_track_ids
    return catalog


def resolve_track_reference(reference: str, catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a track by track_id."""
    normalized = str(reference or "").strip()
    if normalized in catalog["tracks_by_id"]:
        return catalog["tracks_by_id"][normalized]

    raise LearningReferenceError(f"Unknown track: {reference}")


def resolve_lesson_reference(reference: str, catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a lesson by lesson_id or track-relative path."""
    normalized = str(reference or "").strip()
    if not normalized:
        raise LearningReferenceError("Lesson reference cannot be empty.")

    if normalized in catalog["lessons_by_id"]:
        return catalog["lessons_by_id"][normalized]

    path_reference = normalized
    if "/" in normalized and not normalized.endswith(".md"):
        track_id, sequence = normalized.split("/", 1)
        if sequence.isdigit():
            path_reference = f"{track_id}/{int(sequence):03d}.md"
    elif normalized.endswith(".md"):
        path_reference = normalized

    if path_reference in catalog["lessons_by_path"]:
        return catalog["lessons_by_path"][path_reference]

    raise LearningReferenceError(f"Unknown lesson: {reference}")


def get_current_lesson(
    metadata: Dict[str, Any], catalog: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Get the current lesson object from metadata."""
    current_lesson_id = metadata.get("current_lesson_id")
    if not current_lesson_id:
        return None
    return catalog["lessons_by_id"].get(str(current_lesson_id))


def get_next_lesson(
    current_lesson_id: str,
    metadata: Dict[str, Any],
    catalog: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Get the next pending lesson within the current track."""
    if catalog is None:
        catalog = load_learning_catalog()

    current_lesson = catalog["lessons_by_id"].get(str(current_lesson_id))
    if not current_lesson:
        return None

    completed_lesson_ids = get_completed_lesson_ids(metadata)
    track = catalog["tracks_by_id"][current_lesson["track_id"]]
    lessons = track["lessons"]
    current_index = next(
        (
            index
            for index, lesson in enumerate(lessons)
            if lesson["lesson_id"] == current_lesson["lesson_id"]
        ),
        -1,
    )
    if current_index == -1:
        return None

    for lesson in lessons[current_index + 1 :]:
        if lesson["lesson_id"] not in completed_lesson_ids:
            return lesson

    for lesson in lessons[:current_index]:
        if lesson["lesson_id"] not in completed_lesson_ids:
            return lesson

    return None


def track_status_summary(track: Dict[str, Any]) -> str:
    """Return a user-facing progress summary label for a track."""
    status = track.get("progress_status")
    if status == "done":
        return "DONE"
    if status == "in_progress":
        return "IN PROGRESS"
    if status == "locked":
        return "LOCKED"
    return "NOT STARTED"
