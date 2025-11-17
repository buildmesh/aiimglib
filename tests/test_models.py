"""SQLModel model integration tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, create_engine, select

from app import models


def create_in_memory_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


def test_image_model_persists_and_defaults() -> None:
    engine = create_in_memory_engine()
    with Session(engine) as session:
        image = models.Image(
            file_name="foo.png",
            prompt_text="sunset",
            prompt_meta={"seed": 1},
            ai_model="stable-diffusion",
            rating=4,
        )
        session.add(image)
        session.commit()
        session.refresh(image)

        fetched = session.get(models.Image, image.id)
        assert fetched is not None
        assert fetched.file_name == "foo.png"
        assert fetched.prompt_meta == {"seed": 1}
        assert fetched.created_at is not None
        assert fetched.updated_at is not None


def test_image_tag_relationship_round_trip() -> None:
    engine = create_in_memory_engine()
    with Session(engine) as session:
        tag = models.Tag(name="vibrant")
        image = models.Image(file_name="bar.png", prompt_text="forest", tags=[tag])

        session.add(image)
        session.commit()
        session.refresh(image)

        fetched = session.exec(
            select(models.Image).where(models.Image.id == image.id)
        ).one()
        assert fetched.tags
        assert fetched.tags[0].name == "vibrant"

        fetched_tag = session.exec(
            select(models.Tag).where(models.Tag.id == tag.id)
        ).one()
        assert fetched_tag.images
        assert fetched_tag.images[0].id == image.id


def test_image_model_persists_media_fields_and_decimal_rating() -> None:
    engine = create_in_memory_engine()
    with Session(engine) as session:
        image = models.Image(
            file_name="baz.png",
            media_type=models.MediaType.VIDEO,
            thumbnail_file="baz-thumb.png",
            prompt_text="rainy city",
            rating=4.2,
        )
        session.add(image)
        session.commit()
        session.refresh(image)

        fetched = session.get(models.Image, image.id)
        assert fetched is not None
        assert fetched.media_type == models.MediaType.VIDEO
        assert fetched.thumbnail_file == "baz-thumb.png"
        assert pytest.approx(fetched.rating, rel=0.001) == 4.2


def test_image_prompt_meta_list_requires_trailing_prompt_text() -> None:
    with pytest.raises(ValidationError):
        models.Image(
            file_name="invalid.png",
            prompt_text="ignored",
            prompt_meta=[{"id": "abc"}],
        )


def test_image_prompt_meta_references_must_be_id_only_dicts() -> None:
    with pytest.raises(ValidationError):
        models.Image(
            file_name="invalid2.png",
            prompt_text="ignored",
            prompt_meta=[{"id": "abc"}, {"not_id": "oops"}, "final prompt"],
        )


def test_image_prompt_meta_allows_extra_reference_fields() -> None:
    image = models.Image(
        file_name="ok.png",
        prompt_text="hello",
        prompt_meta=[{"id": "abc", "weight": 0.5}, "final prompt"],
    )
    assert image.prompt_meta[-1] == "final prompt"


def test_image_model_requires_thumbnail_for_videos() -> None:
    with pytest.raises(ValidationError):
        models.Image(
            file_name="clip.mp4",
            prompt_text="video",
            media_type=models.MediaType.VIDEO,
        )
