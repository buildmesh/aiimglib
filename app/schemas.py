"""Pydantic schemas for API payloads."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field


PromptMetaType = Union[dict, list, str, None]


class TagRead(BaseModel):
    id: int
    name: str


class ImageBase(BaseModel):
    file_name: str
    prompt_text: str
    prompt_meta: PromptMetaType = None
    ai_model: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=0, le=5)
    captured_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class ImageCreate(ImageBase):
    """Schema for creating a new image entry."""


class ImageUpdate(BaseModel):
    prompt_text: Optional[str] = None
    prompt_meta: PromptMetaType = None
    ai_model: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=0, le=5)
    captured_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


class ImageRead(ImageBase):
    id: str
    created_at: datetime
    updated_at: datetime
    tags: List[TagRead] = Field(default_factory=list)
