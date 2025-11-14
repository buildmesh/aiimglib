"""Application configuration using pydantic settings."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "AI Image Library"
    database_path: Path = Path("app.db")
    images_dir: Path = Path("images")

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


settings = Settings()
