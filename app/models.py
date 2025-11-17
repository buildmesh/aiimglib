"""SQLModel declarative models."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import Column, Float, JSON
from sqlmodel import Field, Relationship, SQLModel

from app.prompt_meta import PromptMetaType, validate_prompt_meta_structure


class ImageTagLink(SQLModel, table=True):
    """Association table linking images and tags."""

    image_id: str = Field(foreign_key="image.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


class MediaType(str, Enum):
    """Supported media types for gallery assets."""

    IMAGE = "image"
    VIDEO = "video"


class ImageValidator(BaseModel):
    """Pydantic helper ensuring prompt metadata + rating are valid."""

    model_config = ConfigDict(extra="allow")

    prompt_meta: PromptMetaType = None
    rating: float | None = None

    @field_validator("prompt_meta", mode="before")
    @classmethod
    def _validate_prompt_meta(cls, value: PromptMetaType) -> PromptMetaType:
        return validate_prompt_meta_structure(value)

    @field_validator("rating", mode="before")
    @classmethod
    def _validate_rating(cls, value):
        if value is None:
            return None
        try:
            rating = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("rating must be numeric") from exc
        if not 0 <= rating <= 5:
            raise ValueError("rating must be between 0 and 5")
        return round(rating, 1)


class Image(SQLModel, table=True):
    """Image metadata persisted in SQLite."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    file_name: str
    media_type: MediaType = Field(default=MediaType.IMAGE, index=True)
    prompt_text: str
    prompt_meta: PromptMetaType = Field(default=None, sa_column=Column(JSON))
    ai_model: str | None = None
    notes: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5, sa_column=Column(Float))
    thumbnail_file: str | None = None
    captured_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    tags: List["Tag"] = Relationship(back_populates="images", link_model=ImageTagLink)

    def __init__(self, **data):
        validated = ImageValidator.model_validate(data)
        data["prompt_meta"] = validated.prompt_meta
        data["rating"] = validated.rating
        super().__init__(**data)


class Tag(SQLModel, table=True):
    """Tag taxonomy for image search filters."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    images: List[Image] = Relationship(back_populates="tags", link_model=ImageTagLink)
