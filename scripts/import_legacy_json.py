"""Import legacy JSON metadata into the SQLite database."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

from datetime import datetime

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
    if not isinstance(data, list):
        msg = "Legacy JSON must be a list of image entries."
        raise ValueError(msg)
    return data


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


def parse_datetime(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def import_entries(entries: list[dict], dry_run: bool = False) -> None:
    with session_scope() as session:
        for entry in entries:
            tags = ensure_tags(session, entry.get("tags", []))
            image = models.Image(
                file_name=entry["file_name"],
                prompt_text=entry.get("prompt_text", ""),
                prompt_meta=entry.get("prompt_meta"),
                ai_model=entry.get("ai_model"),
                notes=entry.get("notes"),
                rating=entry.get("rating"),
                captured_at=parse_datetime(entry.get("captured_at")),
                tags=tags,
            )
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
