"""Tag API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlmodel import Session

from app import models, schemas
from app.dependencies import db_session

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[schemas.TagUsage])
def list_tags(session: Session = Depends(db_session)) -> list[schemas.TagUsage]:
    stmt = (
        select(
            models.Tag.name,
            func.count(models.ImageTagLink.image_id).label("count"),
        )
        .join(
            models.ImageTagLink,
            models.Tag.id == models.ImageTagLink.tag_id,
            isouter=True,
        )
        .group_by(models.Tag.id)
        .order_by(models.Tag.name)
    )
    results = session.exec(stmt).all()
    return [schemas.TagUsage(name=row[0], count=row[1]) for row in results]
