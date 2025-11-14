"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI

from .config import settings


app = FastAPI(title=settings.app_name)


@app.get("/healthz")
def health() -> dict[str, str]:
    """Basic health endpoint for readiness checks."""
    return {"status": "ok"}
