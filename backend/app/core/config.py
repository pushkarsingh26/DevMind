from pathlib import Path
import tempfile
from typing import List, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Central application configuration.

    Every module should import only:
        from app.core.config import settings
    """

    PROJECT_NAME: str = "DevMind"
    API_V1_STR: str = "/api"

    DEBUG: bool = False

    DATABASE_URL: str

    ALLOWED_ORIGINS: Any = [
        "http://localhost:5173",
    ]

    WORKSPACE_ROOT: Path = (
        Path(tempfile.gettempdir()) / "devmind-workspaces"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value):
        """
        Allow comma-separated origins inside .env

        Example

        ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]

        return value

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()