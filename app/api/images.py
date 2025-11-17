"""Image API endpoints."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi import HTTPException
from sqlmodel import Session

from app import crud, models, schemas
from app.dependencies import PaginationParams, db_session, pagination_params
from app.services import files

router = APIRouter(prefix="/images", tags=["images"])


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="captured_at must be ISO-8601 datetime"
        ) from exc


def _parse_tags_field(raw: str | None) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(tag) for tag in parsed]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_prompt_meta(raw: str | None) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="rating must be a number") from exc


def _image_to_schema(image: models.Image) -> schemas.ImageRead:
    data = image.model_dump()
    data["tags"] = [tag.model_dump() for tag in image.tags]
    return schemas.ImageRead.model_validate(data)


def _tags_from_query(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _store_upload_or_400(upload: UploadFile, media_type: models.MediaType) -> str:
    if not files.is_allowed_upload(upload, media_type):
        allowed = ", ".join(sorted(files.allowed_content_types_for(media_type)))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid upload type. Allowed content types: {allowed}",
        )
    try:
        return files.save_upload(upload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _parse_media_type(raw: str | None) -> models.MediaType:
    if raw is None:
        return models.MediaType.IMAGE
    try:
        return models.MediaType(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid media_type") from exc


def _require_thumbnail_if_video(media_type: models.MediaType, thumbnail: UploadFile | None) -> None:
    if media_type == models.MediaType.VIDEO and thumbnail is None:
        raise HTTPException(
            status_code=400,
            detail="Video uploads require a thumbnail_file.",
        )


@router.get("/", response_model=schemas.ImageListResponse)
def list_images(
    pagination: PaginationParams = Depends(pagination_params),
    q: str | None = Query(None),
    tags: str | None = Query(None),
    rating_min: float | None = Query(None, ge=0, le=5),
    rating_max: float | None = Query(None, ge=0, le=5),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    media_type: models.MediaType | None = Query(None),
    session: Session = Depends(db_session),
):
    filters = crud.ImageFilters(
        q=q,
        tags=_tags_from_query(tags),
        rating_min=rating_min,
        rating_max=rating_max,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.page_size,
        offset=pagination.offset,
        media_type=media_type,
    )
    items, total = crud.list_images(session, filters)
    return schemas.ImageListResponse(
        total=total,
        items=[_image_to_schema(image) for image in items],
    )


@router.get("/{image_id}", response_model=schemas.ImageRead)
def retrieve_image(
    image_id: str,
    session: Session = Depends(db_session),
) -> schemas.ImageRead:
    image = crud.get_image(session, image_id)
    return _image_to_schema(image)


@router.post("/", response_model=schemas.ImageRead, status_code=status.HTTP_201_CREATED)
def create_image_endpoint(
    media_file: UploadFile = File(...),
    prompt_text: str = Form(...),
    tags: str | None = Form(None),
    rating: str | None = Form(None),
    media_type: str | None = Form("image"),
    ai_model: str | None = Form(None),
    notes: str | None = Form(None),
    captured_at: str | None = Form(None),
    prompt_meta: str | None = Form(None),
    thumbnail_file: UploadFile | None = File(None),
    session: Session = Depends(db_session),
) -> schemas.ImageRead:
    parsed_media_type = _parse_media_type(media_type)
    _require_thumbnail_if_video(parsed_media_type, thumbnail_file)

    saved_file = _store_upload_or_400(media_file, parsed_media_type)
    saved_thumbnail: str | None = None
    if thumbnail_file is not None:
        saved_thumbnail = _store_upload_or_400(thumbnail_file, models.MediaType.IMAGE)
    try:
        payload = schemas.ImageCreate(
            file_name=saved_file,
            media_type=parsed_media_type,
            prompt_text=prompt_text,
            prompt_meta=_parse_prompt_meta(prompt_meta),
            ai_model=ai_model,
            notes=notes,
            rating=_parse_optional_float(rating),
            captured_at=_parse_datetime(captured_at),
            thumbnail_file=saved_thumbnail,
            tags=_parse_tags_field(tags),
        )
        image = crud.create_image(session, payload)
        return _image_to_schema(image)
    except Exception:
        files.delete_media_files(saved_file, saved_thumbnail)
        raise


@router.put("/{image_id}", response_model=schemas.ImageRead)
def update_image_endpoint(
    image_id: str,
    payload: schemas.ImageUpdate,
    session: Session = Depends(db_session),
) -> schemas.ImageRead:
    image = crud.update_image(session, image_id, payload)
    return _image_to_schema(image)


@router.post("/{image_id}/file", response_model=schemas.ImageRead)
def replace_image_file(
    image_id: str,
    media_file: UploadFile = File(...),
    session: Session = Depends(db_session),
) -> schemas.ImageRead:
    image = crud.get_image(session, image_id)
    old_file = image.file_name
    new_file = _store_upload_or_400(media_file, image.media_type)
    try:
        image.file_name = new_file
        image.updated_at = datetime.utcnow()
        session.add(image)
        session.commit()
        session.refresh(image)
    except Exception:
        files.delete_file(new_file)
        raise
    files.delete_file(old_file)
    return _image_to_schema(image)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image_endpoint(
    image_id: str,
    session: Session = Depends(db_session),
) -> None:
    crud.delete_image(session, image_id)
