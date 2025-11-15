"""CRUD-layer tests for images and tags."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
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
