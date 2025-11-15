"""Import legacy JSON metadata into the SQLite database."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Tuple, Union

from sqlmodel import SQLModel, select

from app import models
from app.database import engine, session_scope


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


def ensure_tags(session, names: Iterable[str]) -> List[models.Tag]:
    tags: List[models.Tag] = []
    for name in {n.strip().lower() for n in names if n.strip()}:
        existing = session.exec(select(models.Tag).where(models.Tag.name == name)).first()
        if existing:
            tags.append(existing)
        else:
            tag = models.Tag(name=name)
            session.add(tag)
            session.flush()
            tags.append(tag)
    return tags


PromptMeta = Union[dict, list, str, None]


def parse_datetime(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        iso_value = value
        if iso_value.endswith("Z"):
            iso_value = iso_value[:-1] + "+00:00"
        return datetime.fromisoformat(iso_value)
    raise ValueError("Unsupported datetime value")


def normalize_prompt(prompt) -> Tuple[str, PromptMeta]:
    if isinstance(prompt, list):
        text = next((item for item in reversed(prompt) if isinstance(item, str)), "")
        return text, prompt
    if isinstance(prompt, str):
        return prompt, prompt
    return "", None


def convert_entry(entry: dict) -> dict:
    prompt_text, prompt_meta = normalize_prompt(entry.get("prompt"))
    tags = sorted({tag.strip().lower() for tag in entry.get("tags", []) if tag.strip()})
    return {
        "file_name": entry["file"],
        "prompt_text": prompt_text,
        "prompt_meta": prompt_meta,
        "ai_model": entry.get("ai_model"),
        "notes": entry.get("notes"),
        "rating": entry.get("rating"),
        "captured_at": parse_datetime(entry.get("date")),
        "tags": tags,
    }


def import_entries(entries: list[dict], dry_run: bool = False) -> None:
    with session_scope() as session:
        for entry in entries:
            converted = convert_entry(entry)
            tag_instances = ensure_tags(session, converted.pop("tags"))
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
    import_entries(entries, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
