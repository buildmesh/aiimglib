"""CRUD-layer tests for images and tags."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, create_engine

from app import models, schemas
from app.crud import (
    ImageFilters,
    create_image,
    delete_image,
    get_image,
    list_images,
    update_image,
)
from app.services.tags import ensure_tags


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_ensure_tags_normalizes_and_reuses(session):
    tags = ensure_tags(session, ["SciFi", "scifi", "  ", "SPACE"])
    assert [t.name for t in tags] == ["scifi", "space"]

    reused = ensure_tags(session, ["SCIFI"])
    assert reused[0].id == tags[0].id


def test_create_and_list_images_with_filters(session):
    base_time = datetime.now(tz=timezone.utc)
    create_image(
        session,
        schemas.ImageCreate(
            file_name="mars.png",
            prompt_text="Space ship above Mars",
            tags=["Space", "SciFi"],
            rating=5,
            captured_at=base_time,
        ),
    )
    create_image(
        session,
        schemas.ImageCreate(
            file_name="forest.png",
            prompt_text="Forest scene",
            tags=["nature"],
            rating=3,
            captured_at=base_time - timedelta(days=1),
        ),
    )

    filters = ImageFilters(q="space", tags=["scifi"], rating_min=4, limit=10)
    items, total = list_images(session, filters)

    assert total == 1
    assert len(items) == 1
    assert {t.name for t in items[0].tags} == {"scifi", "space"}


def test_update_image_replaces_metadata_and_tags(session):
    created = create_image(
        session,
        schemas.ImageCreate(
            file_name="edit.png",
            prompt_text="Initial prompt",
            tags=["old"],
            notes="first",
        ),
    )
    original_updated = created.updated_at

    updated = update_image(
        session,
        created.id,
        schemas.ImageUpdate(
            notes="updated",
            tags=["new", "scifi"],
            rating=4,
        ),
    )

    assert updated.notes == "updated"
    assert updated.rating == 4
    assert {t.name for t in updated.tags} == {"new", "scifi"}
    assert updated.updated_at > original_updated


def test_delete_image_removes_record(session):
    created = create_image(
        session,
        schemas.ImageCreate(file_name="delete.png", prompt_text="will go away"),
    )

    delete_image(session, created.id)

    with pytest.raises(HTTPException):
        get_image(session, created.id)


def test_create_image_persists_prompt_references(session):
    prompt_meta = [{"id": "seed-1"}, "final prompt"]
    created = create_image(
        session,
        schemas.ImageCreate(
            file_name="prompt.png",
            prompt_text="final prompt",
            prompt_meta=prompt_meta,
            tags=["test"],
        ),
    )

    assert created.prompt_meta == prompt_meta


def test_list_images_supports_decimal_rating_filters(session):
    base_time = datetime.now(tz=timezone.utc)
    create_image(
        session,
        schemas.ImageCreate(
            file_name="high.png",
            prompt_text="High rating",
            rating=4.2,
            captured_at=base_time,
        ),
    )
    create_image(
        session,
        schemas.ImageCreate(
            file_name="low.png",
            prompt_text="Low rating",
            rating=3.4,
            captured_at=base_time,
        ),
    )

    filters = ImageFilters(rating_min=4.0, rating_max=4.3, limit=10)
    items, total = list_images(session, filters)

    assert total == 1
    assert items[0].file_name == "high.png"


def test_create_video_requires_thumbnail(session):
    with pytest.raises(ValidationError):
        create_image(
            session,
            schemas.ImageCreate(
                file_name="clip.mp4",
                prompt_text="Video without thumbnail",
                media_type=models.MediaType.VIDEO,
            ),
        )


def test_delete_image_removes_primary_and_thumbnail_files(session, monkeypatch):
    deleted_files: list[str] = []

    def fake_delete(name: str | None) -> None:
        if name:
            deleted_files.append(name)

    monkeypatch.setattr("app.services.files.delete_file", fake_delete)

    created = create_image(
        session,
        schemas.ImageCreate(
            file_name="clip.mp4",
            prompt_text="Video with thumbnail",
            media_type=models.MediaType.VIDEO,
            thumbnail_file="clip-thumb.png",
        ),
    )

    delete_image(session, created.id)

    assert created.file_name in deleted_files
    assert created.thumbnail_file in deleted_files
