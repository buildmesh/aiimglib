"""FastAPI dependency helpers."""
from __future__ import annotations

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from .database import get_session as db_get_session


class PaginationParams(BaseModel):
    """Pagination model for list endpoints."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginationParams:
    """Build pagination parameters from query values."""
    return PaginationParams(page=page, page_size=page_size)


def db_session(session: Session = Depends(db_get_session)) -> Session:
    """Expose the SQLModel session as a dependency."""
    return session
