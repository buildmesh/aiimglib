"""File-system helpers for storing image uploads."""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload(upload: UploadFile) -> str:
    """Persist an uploaded file and return its relative filename."""
    _ensure_directory(settings.images_dir)
    suffix = Path(upload.filename).suffix if upload.filename else ""
    file_name = f"{uuid4().hex}{suffix}"
    destination = settings.images_dir / file_name
    upload.file.seek(0)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return file_name


def delete_file(file_name: str) -> None:
    """Remove a stored image if it exists."""
    path = settings.images_dir / file_name
    try:
        path.unlink()
    except FileNotFoundError:
        return
