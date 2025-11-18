"""Pydantic schemas for API payloads."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models import MediaType
from app.prompt_meta import PromptMetaType, validate_prompt_meta_structure


class TagRead(BaseModel):
    id: int
    name: str


class TagUsage(BaseModel):
    name: str
    count: int


class ImageDependent(BaseModel):
    id: str
    prompt_text: str
    file_name: str
    thumbnail_file: Optional[str] = None
    media_type: MediaType
    captured_at: Optional[datetime] = None


class ImageBase(BaseModel):
    file_name: str
    media_type: MediaType = MediaType.IMAGE
    prompt_text: str
    prompt_meta: PromptMetaType = None
    ai_model: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    thumbnail_file: Optional[str] = None
    captured_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)

    @field_validator("prompt_meta", mode="before")
    @classmethod
    def _validate_prompt_meta(cls, value: PromptMetaType) -> PromptMetaType:
        return validate_prompt_meta_structure(value)


class ImageCreate(ImageBase):
    """Schema for creating a new image entry."""


class ImageUpdate(BaseModel):
    prompt_text: Optional[str] = None
    prompt_meta: PromptMetaType = None
    ai_model: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    media_type: Optional[MediaType] = None
    thumbnail_file: Optional[str] = None
    captured_at: Optional[datetime] = None
    tags: Optional[List[str]] = None

    @field_validator("prompt_meta", mode="before")
    @classmethod
    def _validate_prompt_meta(cls, value: PromptMetaType) -> PromptMetaType:
        return validate_prompt_meta_structure(value)


class ImageRead(ImageBase):
    id: str
    created_at: datetime
    updated_at: datetime
    tags: List[TagRead] = Field(default_factory=list)


class ImageListResponse(BaseModel):
    items: List[ImageRead]
    total: int


class ImageDetail(ImageRead):
    dependents: List[ImageDependent] = Field(default_factory=list)
