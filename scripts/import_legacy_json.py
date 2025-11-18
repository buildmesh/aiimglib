"""Import legacy JSON metadata into the SQLite database."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlmodel import SQLModel, Session

from app import models
from app.database import engine, session_scope
from app.services import files, tags as tag_service
from app.prompt_meta import (
    PromptMetaType,
    PromptMetaFormatError,
    validate_prompt_meta_structure,
)

logger = logging.getLogger(__name__)


@dataclass
class ConvertedEntry:
    payload: Dict[str, Any]
    tags: List[str]
    legacy_id: str | None
    reference_dicts: List[dict]
    thumbnail_source: str | None = None


@dataclass
class ImportedRecord:
    image_id: str
    legacy_id: str | None
    reference_dicts: List[dict]
    has_explicit_thumbnail: bool
    media_type: models.MediaType


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


def normalize_prompt(prompt) -> Tuple[str, PromptMetaType, list[dict]]:
    if prompt is None:
        return "", None, []
    if isinstance(prompt, str):
        return prompt, prompt, []
    if isinstance(prompt, list):
        validated = validate_prompt_meta_structure(prompt)
        references = [
            dict(ref) for ref in validated[:-1] if isinstance(ref, dict)
        ]
        return validated[-1], validated, references
    if isinstance(prompt, dict):
        # Legacy dictionary metadata may contain additional details without text.
        return "", prompt, []
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


def convert_entry(entry: dict) -> ConvertedEntry:
    prompt_text, prompt_meta, references = normalize_prompt(entry.get("prompt"))
    tags = sorted({tag.strip().lower() for tag in entry.get("tags", []) if tag.strip()})
    sanitized_name = files.sanitize_storage_name(entry["file"])
    legacy_media_type = entry.get("media_type")
    media_type = (
        detect_media_type(sanitized_name)
        if legacy_media_type is None
        else models.MediaType(legacy_media_type)
    )
    raw_rating = normalize_rating(entry.get("rating"))
    thumbnail_source = entry.get("thumbnail_file")
    thumbnail_file = sanitize_optional_thumbnail(thumbnail_source)
    if (
        media_type == models.MediaType.VIDEO
        and thumbnail_file is None
        and not references
    ):
        raise ValueError(
            "Video entries must include a thumbnail_file or reference another asset"
        )

    payload = {
        "file_name": sanitized_name,
        "prompt_text": prompt_text,
        "prompt_meta": prompt_meta,
        "ai_model": entry.get("ai_model"),
        "notes": entry.get("notes"),
        "rating": raw_rating,
        "media_type": media_type,
        "thumbnail_file": thumbnail_file,
        "captured_at": parse_datetime(entry.get("date")),
    }
    return ConvertedEntry(
        payload=payload,
        tags=tags,
        legacy_id=entry.get("id"),
        reference_dicts=references,
        thumbnail_source=thumbnail_source if thumbnail_file else None,
    )


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
    imported_records: list[ImportedRecord] = []
    legacy_lookup: dict[str, dict[str, str | None]] = {}

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

            payload = dict(converted.payload)
            if not dry_run:
                copied_name = files.copy_into_images(source_file, payload["file_name"])
                payload["file_name"] = copied_name
                if payload.get("thumbnail_file") and converted.thumbnail_source:
                    thumb_source = _resolve_source_file(source_dir, converted.thumbnail_source)
                    copied_thumb = files.copy_into_images(thumb_source, payload["thumbnail_file"])
                    payload["thumbnail_file"] = copied_thumb

            tag_instances = tag_service.ensure_tags(session, converted.tags)
            image = models.Image(**payload, tags=tag_instances)
            session.add(image)
            session.flush()
            session.refresh(image)

            imported_records.append(
                ImportedRecord(
                    image_id=image.id,
                    legacy_id=converted.legacy_id,
                    reference_dicts=converted.reference_dicts,
                    has_explicit_thumbnail=bool(image.thumbnail_file),
                    media_type=image.media_type,
                )
            )
            if converted.legacy_id:
                legacy_lookup[converted.legacy_id] = {
                    "id": image.id,
                    "file_name": image.file_name,
                    "thumbnail_file": image.thumbnail_file,
                }

        _apply_reference_updates(session, imported_records, legacy_lookup)

        if dry_run:
            session.rollback()
        else:
            session.commit()


def _apply_reference_updates(
    session: Session,
    records: list[ImportedRecord],
    legacy_lookup: dict[str, dict[str, str | None]],
) -> None:
    for record in records:
        if not record.reference_dicts:
            continue
        image = session.get(models.Image, record.image_id)
        if image is None:
            continue

        updated_refs: list[dict] = []
        first_source: dict[str, str | None] | None = None
        for ref in record.reference_dicts:
            legacy_ref_id = ref.get("id")
            if not legacy_ref_id:
                continue
            mapped = legacy_lookup.get(legacy_ref_id)
            if not mapped:
                continue
            new_ref = dict(ref)
            new_ref["id"] = mapped["id"]
            updated_refs.append(new_ref)
            if first_source is None:
                first_source = mapped

        if not updated_refs:
            continue

        image.prompt_meta = [*updated_refs, image.prompt_text]
        if not record.has_explicit_thumbnail and first_source:
            replacement = first_source.get("thumbnail_file") or first_source.get("file_name")
            image.thumbnail_file = replacement
            if record.legacy_id and replacement:
                legacy_lookup.setdefault(
                    record.legacy_id,
                    {"id": record.image_id, "file_name": image.file_name, "thumbnail_file": None},
                )["thumbnail_file"] = replacement
        session.add(image)


def main() -> None:
    args = parse_args()
    entries = load_entries(args.json_path)
    SQLModel.metadata.create_all(engine)
    import_entries(entries, source_dir=args.json_path.parent, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
