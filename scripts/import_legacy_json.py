"""Import legacy JSON metadata into the SQLite database."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlmodel import SQLModel

from app import models
from app.database import engine, session_scope
from app.services import files, tags as tag_service
from app.prompt_meta import (
    PromptMetaType,
    PromptMetaFormatError,
    validate_prompt_meta_structure,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import legacy image metadata JSON.")
    parser.add_argument("json_path", type=Path, help="Path to legacy JSON exports.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without writing to the database.",
    )
    return parser.parse_args()


def load_entries(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or "image" not in data:
        msg = "Legacy JSON must be an object with an 'image' list."
        raise ValueError(msg)
    entries = data["image"]
    if not isinstance(entries, list):
        msg = "'image' must contain a list of entries."
        raise ValueError(msg)
    return entries


def parse_datetime(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        iso_value = value.strip()
        if iso_value.isdigit():
            seconds = int(iso_value)
            if len(iso_value) > 10:
                divisor = 10 ** (len(iso_value) - 10)
                seconds = seconds / divisor
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        if iso_value.endswith("Z"):
            iso_value = iso_value[:-1] + "+00:00"
        return datetime.fromisoformat(iso_value)
    raise ValueError("Unsupported datetime value")


def normalize_prompt(prompt) -> Tuple[str, PromptMetaType]:
    if prompt is None:
        return "", None
    if isinstance(prompt, str):
        return prompt, prompt
    if isinstance(prompt, list):
        validated = validate_prompt_meta_structure(prompt)
        return validated[-1], validated
    if isinstance(prompt, dict):
        # Legacy dictionary metadata may contain additional details without text.
        return "", prompt
    raise PromptMetaFormatError("Unsupported prompt metadata structure")


def detect_media_type(file_name: str) -> models.MediaType:
    suffix = Path(file_name).suffix.lower()
    if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        return models.MediaType.VIDEO
    return models.MediaType.IMAGE


def sanitize_optional_thumbnail(name: str | None) -> str | None:
    if not name:
        return None
    return files.sanitize_storage_name(name)


def normalize_rating(raw_rating) -> float | None:
    if raw_rating is None:
        return None
    try:
        value = float(raw_rating)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid rating value: {raw_rating}") from exc
    if not 0 <= value <= 5:
        raise ValueError("Rating must be between 0 and 5")
    return round(value, 1)


def convert_entry(entry: dict) -> dict:
    prompt_text, prompt_meta = normalize_prompt(entry.get("prompt"))
    tags = sorted({tag.strip().lower() for tag in entry.get("tags", []) if tag.strip()})
    sanitized_name = files.sanitize_storage_name(entry["file"])
    media_type = entry.get("media_type")
    if media_type is None:
        media_type = detect_media_type(sanitized_name).value
    raw_rating = normalize_rating(entry.get("rating"))
    thumbnail_file = sanitize_optional_thumbnail(entry.get("thumbnail_file"))
    return {
        "file_name": sanitized_name,
        "prompt_text": prompt_text,
        "prompt_meta": prompt_meta,
        "ai_model": entry.get("ai_model"),
        "notes": entry.get("notes"),
        "rating": raw_rating,
        "media_type": media_type,
        "thumbnail_file": thumbnail_file,
        "captured_at": parse_datetime(entry.get("date")),
        "tags": tags,
    }


def _resolve_source_file(base_dir: Path, relative_name: str) -> Path:
    candidate = (base_dir / relative_name).resolve()
    base_dir_resolved = base_dir.resolve()
    try:
        candidate.relative_to(base_dir_resolved)
    except ValueError as exc:
        raise ValueError(f"Legacy image path {relative_name} escapes base directory") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Legacy image {relative_name} not found in {base_dir_resolved}")
    return candidate


def import_entries(entries: list[dict], source_dir: Path, dry_run: bool = False) -> None:
    with session_scope() as session:
        for entry in entries:
            converted = convert_entry(entry)
            try:
                source_file = _resolve_source_file(source_dir, entry["file"])
            except (FileNotFoundError, ValueError) as exc:
                logger.error("Skipping %s: %s", entry.get("file"), exc)
                raise

            suffix = source_file.suffix.lower()
            if suffix not in files.ALLOWED_EXTENSIONS:
                raise ValueError(f"Unsupported legacy file extension: {suffix}")

            if not dry_run:
                copied_name = files.copy_into_images(source_file, converted["file_name"])
                converted["file_name"] = copied_name

            tag_instances = tag_service.ensure_tags(session, converted.pop("tags"))
            image = models.Image(**converted, tags=tag_instances)
            session.add(image)
        if dry_run:
            session.rollback()
        else:
            session.commit()


def main() -> None:
    args = parse_args()
    entries = load_entries(args.json_path)
    SQLModel.metadata.create_all(engine)
    import_entries(entries, source_dir=args.json_path.parent, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
