"""File-system helpers for storing image uploads."""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]")

logger = logging.getLogger(__name__)


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_storage_name(name: str) -> str:
    """Normalize inbound filenames to prevent traversal."""
    if not name:
        raise ValueError("filename is required")
    base = Path(name).name
    sanitized = _SAFE_NAME_PATTERN.sub("_", base)
    if not sanitized or sanitized in {".", ".."}:
        raise ValueError("invalid filename")
    return sanitized


def _resolve_images_path(file_name: str) -> Path:
    safe_name = sanitize_storage_name(file_name)
    images_root = settings.images_dir.resolve()
    destination = (settings.images_dir / safe_name).resolve()
    try:
        destination.relative_to(images_root)
    except ValueError as exc:  # path escapes image dir
        raise ValueError("file path escapes images directory") from exc
    _ensure_directory(images_root)
    return destination


def is_allowed_upload(upload: UploadFile) -> bool:
    """Return True if the upload's extension & content type are allowed."""
    suffix = Path(upload.filename or "").suffix.lower()
    return suffix in ALLOWED_EXTENSIONS and (
        upload.content_type in ALLOWED_CONTENT_TYPES
    )


def save_upload(upload: UploadFile) -> str:
    """Persist an uploaded file and return its relative filename."""
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("unsupported file extension")
    destination_name = f"{uuid4().hex}{suffix}"
    destination = _resolve_images_path(destination_name)
    upload.file.seek(0)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return destination_name


def copy_into_images(source: Path, target_name: str) -> str:
    """Copy an existing file into the managed images directory."""
    destination = _resolve_images_path(target_name)
    base = destination.stem
    suffix = destination.suffix
    counter = 1
    while destination.exists():
        destination = destination.with_name(f"{base}_{counter}{suffix}")
        counter += 1
    shutil.copy2(source, destination)
    return destination.name


def delete_file(file_name: str) -> None:
    """Remove a stored image if it exists."""
    try:
        path = _resolve_images_path(file_name)
    except ValueError as exc:
        logger.warning("Refused to delete invalid path '%s': %s", file_name, exc)
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        logger.warning("Failed to delete %s: %s", path, exc)
