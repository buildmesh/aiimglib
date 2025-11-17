"""CRUD helpers for image metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Tuple

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app import models, schemas
from app.services import files, tags as tag_service


@dataclass
class ImageFilters:
    """Filtering options for listing images."""

    q: str | None = None
    tags: List[str] = field(default_factory=list)
    rating_min: float | None = None
    rating_max: float | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 20
    offset: int = 0
    media_type: models.MediaType | None = None


def _normalized_tags(names: Iterable[str]) -> list[str]:
    normalized = []
    for name in names:
        normalized_name = tag_service.normalize_tag(name) if isinstance(name, str) else ""
        if normalized_name:
            normalized.append(normalized_name)
    return sorted(set(normalized))


def _apply_filters(stmt, filters: ImageFilters):
    normalized_q = filters.q.strip().lower() if filters.q else None
    if normalized_q:
        like_value = f"%{normalized_q}%"
        stmt = stmt.where(
            or_(
                func.lower(models.Image.prompt_text).like(like_value),
                func.lower(models.Image.notes).like(like_value),
                func.lower(models.Image.ai_model).like(like_value),
            )
        )

    if filters.rating_min is not None:
        stmt = stmt.where(models.Image.rating >= filters.rating_min)
    if filters.rating_max is not None:
        stmt = stmt.where(models.Image.rating <= filters.rating_max)

    if filters.date_from is not None:
        stmt = stmt.where(models.Image.captured_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(models.Image.captured_at <= filters.date_to)

    normalized_tags = _normalized_tags(filters.tags)
    if normalized_tags:
        link_stmt = (
            select(models.ImageTagLink.image_id)
            .join(models.Tag, models.Tag.id == models.ImageTagLink.tag_id)
            .where(models.Tag.name.in_(normalized_tags))
            .group_by(models.ImageTagLink.image_id)
            .having(func.count(func.distinct(models.Tag.name)) == len(normalized_tags))
        )
        stmt = stmt.where(models.Image.id.in_(link_stmt))

    if filters.media_type is not None:
        stmt = stmt.where(models.Image.media_type == filters.media_type)

    return stmt


def list_images(session: Session, filters: ImageFilters | None = None) -> Tuple[list[models.Image], int]:
    """Return images that match the given filters."""
    filters = filters or ImageFilters()

    base_query = select(models.Image).options(selectinload(models.Image.tags))
    filtered_query = _apply_filters(base_query, filters)
    filtered_query = filtered_query.order_by(
        models.Image.captured_at.desc().nullslast(),
        models.Image.created_at.desc(),
    )

    count_subquery = _apply_filters(select(models.Image.id), filters).subquery()
    total_result = session.exec(select(func.count()).select_from(count_subquery)).one()
    total = total_result[0] if isinstance(total_result, tuple) else total_result

    result = session.exec(
        filtered_query.offset(filters.offset).limit(filters.limit)
    ).all()
    return result, total


def get_image(session: Session, image_id: str) -> models.Image:
    """Fetch a single image by ID or raise 404."""
    stmt = (
        select(models.Image)
        .options(selectinload(models.Image.tags))
        .where(models.Image.id == image_id)
    )
    image = session.exec(stmt).first()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


def create_image(session: Session, data: schemas.ImageCreate) -> models.Image:
    """Persist a new image record."""
    image = models.Image(
        file_name=data.file_name,
        media_type=data.media_type,
        prompt_text=data.prompt_text,
        prompt_meta=data.prompt_meta,
        ai_model=data.ai_model,
        notes=data.notes,
        rating=data.rating,
        captured_at=data.captured_at,
        thumbnail_file=data.thumbnail_file,
    )
    image.tags = tag_service.ensure_tags(session, data.tags)
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def _validate_and_normalize_updates(
    image: models.Image, updates: dict
) -> dict:
    """Run incoming updates through the shared validator for consistency."""
    validator_input = {
        "prompt_meta": updates.get("prompt_meta", image.prompt_meta),
        "rating": updates.get("rating", image.rating),
        "media_type": updates.get("media_type", image.media_type),
        "thumbnail_file": updates.get("thumbnail_file", image.thumbnail_file),
    }
    validated = models.ImageValidator.model_validate(validator_input)

    if "prompt_meta" in updates:
        updates["prompt_meta"] = validated.prompt_meta
    if "rating" in updates:
        updates["rating"] = validated.rating
    if "media_type" in updates:
        updates["media_type"] = validated.media_type
    if "thumbnail_file" in updates:
        updates["thumbnail_file"] = validated.thumbnail_file

    # Video thumbnail requirement should also trigger when media_type changes without thumbnail.
    if (
        "media_type" in updates or "thumbnail_file" in updates
    ) and validated.media_type == models.MediaType.VIDEO and not validated.thumbnail_file:
        raise ValueError("videos require thumbnail_file")
    return updates


def update_image(session: Session, image_id: str, data: schemas.ImageUpdate) -> models.Image:
    """Update an image record with new metadata."""
    image = get_image(session, image_id)
    update_payload = data.model_dump(exclude_unset=True)
    tag_names = update_payload.pop("tags", None)

    if any(
        field in update_payload
        for field in ("prompt_meta", "rating", "media_type", "thumbnail_file")
    ):
        update_payload = _validate_and_normalize_updates(image, update_payload)

    for field, value in update_payload.items():
        setattr(image, field, value)

    if tag_names is not None:
        image.tags = tag_service.ensure_tags(session, tag_names)

    image.updated_at = datetime.utcnow()
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def delete_image(session: Session, image_id: str) -> None:
    """Remove an image record."""
    image = get_image(session, image_id)
    file_name = image.file_name
    thumbnail_name = image.thumbnail_file
    session.delete(image)
    session.commit()
    files.delete_media_files(file_name, thumbnail_name)
