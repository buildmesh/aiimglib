"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings
from app.database import get_session
from app import database
from app.main import app
import app.main as app_main


@pytest.fixture()
def api_client(tmp_path: Path):
    """Provide a TestClient backed by a temporary SQLite database."""
    db_path = tmp_path / "test.db"
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    original_engine = database.engine
    original_session_local = database.SessionLocal
    original_images_dir = settings.images_dir
    original_main_engine = app_main.engine

    database.engine = engine
    database.SessionLocal = SessionLocal
    settings.images_dir = images_dir
    app_main.engine = engine

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.pop(get_session, None)
    database.engine = original_engine
    database.SessionLocal = original_session_local
    settings.images_dir = original_images_dir
    app_main.engine = original_main_engine
