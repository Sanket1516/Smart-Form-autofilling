from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based application configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Smart Form Auto-Filling System"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "smart_form_db"
    mongodb_server_selection_timeout_ms: int = 1500
    chromadb_url: str = "http://localhost:8001"
    chromadb_collection: str = "user_document_chunks"
    chromadb_tenant: str = "default_tenant"
    chromadb_database: str = "default_database"
    chromadb_timeout_seconds: int = 2
    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    embedding_model: str = ""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, gt=0)
    auth_login_rate_limit_attempts: int = Field(default=5, gt=0)
    auth_login_rate_limit_window_seconds: int = Field(default=60, gt=0)
    cors_origins: str = "http://localhost:5173,chrome-extension://*"
    cors_origin_regex: str = r"chrome-extension://[a-p]{32}"
    max_upload_size_mb: int = Field(default=10, gt=0)
    high_confidence_threshold: float = Field(default=0.90, ge=0, le=1)
    medium_confidence_threshold: float = Field(default=0.70, ge=0, le=1)
    
    storage_provider: str = "local"
    storage_root: str = "./uploads"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    
    redis_url: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False
    processing_max_retries: int = Field(default=2, ge=0, le=5)
    ocr_language: str = "en"
    ocr_resolution: int = Field(default=150, ge=72, le=300)
    extraction_min_confidence: float = Field(default=0.50, ge=0, le=1)
    classifier_confidence_threshold: float = Field(default=0.50, ge=0, le=1)
    embedding_model_name: str = "BAAI/bge-m3"
    rag_chunk_size: int = Field(default=500, ge=50, le=2000)
    rag_chunk_overlap: int = Field(default=50, ge=0, le=500)
    llm_reasoning_timeout_seconds: int = Field(default=30, ge=5, le=120)
    llm_max_evidence_chunks: int = Field(default=5, ge=1, le=20)
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    sensitive_field_concepts: str = "ssn,credit_card,passport_number,password"

    @property
    def sensitive_concepts_list(self) -> list[str]:
        return [c.strip().lower() for c in self.sensitive_field_concepts.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
