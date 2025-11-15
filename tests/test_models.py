"""SQLModel model integration tests."""
from __future__ import annotations

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
