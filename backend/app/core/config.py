from pathlib import Path
import tempfile
from typing import List, Any, Optional

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

    # --------------------------------------------------------------------------
    # AI Engine Core Configurations
    # --------------------------------------------------------------------------
    AI_PROVIDER: str = "google"
    GOOGLE_MODEL_NAME: str = "gemini-2.5-flash"
    GROQ_MODEL_NAME: str = "moonshotai/kimi-k2-instruct"
    OPENROUTER_MODEL_NAME: str = "deepseek/deepseek-chat-v3"
    NVIDIA_MODEL_NAME: str = "meta/llama-3.3-70b-instruct"
    AI_PROVIDER_CHAIN: str = "google,groq,openrouter,nvidia"

    # API Credentials & Custom Endpoints
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    NVIDIA_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Hyperparameters & Timeouts
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 4096
    TIMEOUT: float = 30.0
    MAX_RETRIES: int = 3

    # Task-Specific Prompt Versions
    PROMPT_VERSION_REVIEW: str = "1.0.0"
    PROMPT_VERSION_EXPLAIN: str = "1.0.0"
    PROMPT_VERSION_TESTS: str = "1.0.0"
    PROMPT_VERSION_BUGS: str = "1.0.0"

    # Optimization, Cache and Logging
    RETRIEVAL_LIMIT: int = 15
    AI_CACHE_DIR: Path = Path("temp/ai_cache")
    AI_CACHE_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

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