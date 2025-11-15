"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel

from .api import images_router, tags_router
from .config import settings
from .database import engine
from . import models  # noqa: F401 ensures models registered

STATIC_ROOT = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare application resources on startup."""
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(images_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.mount(
    "/images",
    StaticFiles(directory=str(settings.images_dir), check_dir=False),
    name="images",
)
app.mount(
    "/assets",
    StaticFiles(directory=str(STATIC_ROOT / "assets"), check_dir=False),
    name="frontend-assets",
)


@app.get("/healthz")
def health() -> dict[str, str]:
    """Basic health endpoint for readiness checks."""
    return {"status": "ok"}


@app.get("/")
def frontend_index() -> FileResponse:
    """Serve the built frontend bundle."""
    return FileResponse(STATIC_ROOT / "index.html")
