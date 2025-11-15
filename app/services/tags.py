"""Utilities for working with tags."""
from __future__ import annotations

from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session

from app import models


def normalize_tag(name: str) -> str:
    """Normalize a tag name for comparison."""
    return name.strip().lower()


def ensure_tags(session: Session, names: Iterable[str]) -> List[models.Tag]:
    """Return Tag instances for each name, creating rows as needed."""
    normalized: List[str] = []
    for name in names:
        if not isinstance(name, str):
            continue
        normalized_name = normalize_tag(name)
        if normalized_name:
            normalized.append(normalized_name)
    unique = sorted(set(normalized))

    tags: List[models.Tag] = []
    for tag_name in unique:
        stmt = sqlite_insert(models.Tag).values(name=tag_name).prefix_with("OR IGNORE")
        session.exec(stmt)
        tag = session.exec(
            select(models.Tag).where(models.Tag.name == tag_name)
        ).scalars().first()
        if tag is None:
            continue
        tags.append(tag)
    return tags
