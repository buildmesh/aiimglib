"""SQLModel declarative models."""
from datetime import datetime
from typing import List, Optional, Union
from uuid import uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel


class ImageTagLink(SQLModel, table=True):
    """Association table linking images and tags."""

    image_id: str = Field(foreign_key="image.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


class Image(SQLModel, table=True):
    """Image metadata persisted in SQLite."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    file_name: str
    prompt_text: str
    prompt_meta: Union[dict, list, str, None] = Field(default=None, sa_column=Column(JSON))
    ai_model: str | None = None
    notes: str | None = None
    rating: int | None = Field(default=None, ge=0, le=5)
    captured_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    tags: List["Tag"] = Relationship(back_populates="images", link_model=ImageTagLink)


class Tag(SQLModel, table=True):
    """Tag taxonomy for image search filters."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    images: List[Image] = Relationship(back_populates="tags", link_model=ImageTagLink)
