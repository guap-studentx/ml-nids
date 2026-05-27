from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ML-NIDS"
    api_v1_prefix: str = "/api/v1"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")

    database_url: str = "postgresql+asyncpg://nids:nids@localhost:5432/nids"
    secret_key: str = Field(default="change-me-in-env", min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    admin_username: str = "admin"
    admin_password: str = "admin"

    models_dir: Path = Path("../artifacts")
    uploads_dir: Path = Path("../uploads")
    reports_dir: Path = Path("../reports")
    captures_dir: Path = Path("../captures")
    default_model_id: str = "xgboost"
    agent_offline_after_seconds: int = 30

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
