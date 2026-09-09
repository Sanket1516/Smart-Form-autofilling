from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based application configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Smart Form Auto-Filling System"
    app_version: str = "0.1.0"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "smart_form_db"
    mongodb_server_selection_timeout_ms: int = 1500
    chromadb_url: str = "http://localhost:8001"
    chromadb_collection: str = "user_document_chunks"
    chromadb_timeout_seconds: int = 2
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()

