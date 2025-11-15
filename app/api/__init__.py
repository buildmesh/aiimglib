"""API routers for the AI image library."""

from .images import router as images_router
from .tags import router as tags_router

__all__ = ["images_router", "tags_router"]
