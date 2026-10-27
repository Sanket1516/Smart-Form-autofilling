"""Environment-based application configuration.

Every setting can be supplied through an environment variable of the same name
(upper-case) or through a ``.env`` file in the working directory or its parent.
"""

import ipaddress
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_LLM_PROVIDERS = ("google", "openai", "anthropic", "ollama", "mock")
_KEYLESS_PROVIDERS = ("mock", "ollama")
_PLACEHOLDER_SECRETS = {
    "replace_this_with_a_long_random_string_at_least_32_chars",
    "change-me",
    "changeme",
    "secret",
}
_ALLOWED_JWT_ALGORITHMS = ("HS256", "HS384", "HS512")


class Settings(BaseSettings):
    """Validated application settings."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Application
    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Smart Form Auto-Filling System"
    app_version: str = "0.2.0"
    log_level: str = "INFO"

    # MongoDB (source of truth for structured data)
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "smart_form_db"
    mongodb_server_selection_timeout_ms: int = Field(default=1500, ge=100)

    # ChromaDB (vector store for document chunks)
    chromadb_url: str = "http://localhost:8001"
    chromadb_collection: str = "user_document_chunks_v2"
    chromadb_tenant: str = "default_tenant"
    chromadb_database: str = "default_database"
    chromadb_timeout_seconds: int = Field(default=30, ge=1, le=300)

    # LLM provider
    llm_provider: str = "mock"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: int = Field(default=60, ge=5, le=300)
    llm_max_output_tokens: int = Field(default=4096, ge=256, le=32768)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    # Base URL for self-hosted providers (ollama); ignored by hosted APIs.
    llm_base_url: str = "http://localhost:11434"
    # Optional second provider used when the primary fails (e.g. a local Ollama model).
    llm_fallback_provider: str = ""
    llm_fallback_model: str = ""
    llm_fallback_api_key: str = ""
    llm_fallback_base_url: str = "http://localhost:11434"

    # Embeddings
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = Field(default=384, gt=0)

    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, gt=0, le=24 * 60)
    auth_login_rate_limit_attempts: int = Field(default=5, gt=0)
    auth_login_rate_limit_window_seconds: int = Field(default=60, gt=0)
    rate_limit_storage_uri: str = ""
    app_domain: str = ""

    # CORS: dashboard origins only. The extension reaches the API through its
    # host permission and authenticates with a bearer token.
    cors_origins: str = "http://localhost:5173"

    # Uploads and storage
    max_upload_size_mb: int = Field(default=10, gt=0, le=100)
    storage_provider: Literal["local", "cloudinary"] = "local"
    storage_root: str = "./uploads"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Document processing
    processing_mode: Literal["inline", "celery"] = "inline"
    redis_url: str = "redis://localhost:6379/0"
    processing_max_retries: int = Field(default=2, ge=0, le=5)
    processing_stale_after_minutes: int = Field(default=15, ge=1)
    # rapidocr: PP-OCR English models on ONNX Runtime (default, ~0.45 GB per page);
    # paddle: PaddlePaddle inference (~2.5 GB per page); none: scanned pages need review.
    ocr_engine: Literal["rapidocr", "paddle", "none"] = "rapidocr"
    # auto: upscale/contrast/orientation/deskew only when a page needs it; none: read as-is.
    ocr_preprocess: Literal["auto", "none"] = "auto"
    ocr_language: str = "en"
    ocr_resolution: int = Field(default=150, ge=72, le=300)
    llm_extraction_max_chars: int = Field(default=18000, ge=1000, le=200000)

    # RAG
    rag_chunk_size: int = Field(default=500, ge=50, le=2000)
    rag_chunk_overlap: int = Field(default=50, ge=0, le=500)
    rag_top_k: int = Field(default=4, ge=1, le=20)
    rag_min_similarity: float = Field(default=0.35, ge=0.0, le=1.0)

    # Form-filling decisions
    classifier_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    autofill_min_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    sensitive_field_concepts: str = (
        "identity.passport_number,identity.pan_number,identity.aadhaar_number,"
        "identity.national_id,financial.account_number,financial.routing_number,"
        "financial.tax_id,financial.cif_number"
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def _strong_secret(cls, value: str) -> str:
        if value.strip().lower() in _PLACEHOLDER_SECRETS:
            raise ValueError("JWT_SECRET_KEY is still a placeholder; generate a random secret")
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def _allowed_algorithm(cls, value: str) -> str:
        if value not in _ALLOWED_JWT_ALGORITHMS:
            raise ValueError(f"JWT_ALGORITHM must be one of {', '.join(_ALLOWED_JWT_ALGORITHMS)}")
        return value

    @field_validator("llm_provider")
    @classmethod
    def _known_provider(cls, value: str) -> str:
        provider = (value or "").strip().lower()
        if provider == "gemini":
            provider = "google"
        if provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER must be one of {', '.join(SUPPORTED_LLM_PROVIDERS)} (got {value!r})"
            )
        return provider

    @field_validator("llm_fallback_provider")
    @classmethod
    def _known_fallback(cls, value: str) -> str:
        provider = (value or "").strip().lower()
        if provider == "gemini":
            provider = "google"
        if provider and provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"LLM_FALLBACK_PROVIDER must be empty or one of {', '.join(SUPPORTED_LLM_PROVIDERS)}"
            )
        return provider

    @model_validator(mode="after")
    def _provider_has_key(self) -> "Settings":
        if self.llm_provider not in _KEYLESS_PROVIDERS and not self.llm_api_key.strip():
            raise ValueError(f"LLM_API_KEY is required when LLM_PROVIDER={self.llm_provider}")
        if self.llm_provider not in ("mock",) and not self.llm_model.strip():
            raise ValueError(f"LLM_MODEL is required when LLM_PROVIDER={self.llm_provider}")
        if self.llm_fallback_provider:
            if (
                self.llm_fallback_provider not in _KEYLESS_PROVIDERS
                and not self.llm_fallback_api_key.strip()
            ):
                raise ValueError(
                    "LLM_FALLBACK_API_KEY is required when "
                    f"LLM_FALLBACK_PROVIDER={self.llm_fallback_provider}"
                )
            if self.llm_fallback_provider != "mock" and not self.llm_fallback_model.strip():
                raise ValueError("LLM_FALLBACK_MODEL is required with LLM_FALLBACK_PROVIDER")
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        if self.storage_provider == "cloudinary" and not (
            self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret
        ):
            raise ValueError("Cloudinary storage requires CLOUDINARY_* credentials")
        if self.app_env == "production":
            self._validate_production_settings()
        return self

    def _validate_production_settings(self) -> None:
        """Refuse the development defaults that would make a public deploy unsafe."""
        if self.llm_provider == "mock" or self.llm_fallback_provider == "mock":
            raise ValueError("APP_ENV=production requires a real LLM provider")
        if not self.rate_limit_storage_uri.startswith(("redis://", "rediss://")):
            raise ValueError("APP_ENV=production requires RATE_LIMIT_STORAGE_URI using Redis")

        domain = self.app_domain.strip().lower().rstrip(".")
        parsed_domain = urlsplit(f"https://{domain}") if domain else None
        try:
            ipaddress.ip_address(domain)
            is_ip_address = True
        except ValueError:
            is_ip_address = False
        if (
            not domain
            or parsed_domain is None
            or parsed_domain.hostname != domain
            or is_ip_address
            or domain in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("APP_ENV=production requires APP_DOMAIN to be a public DNS name")
        public_origin = f"https://{domain}"
        origins = self.cors_origin_list
        if public_origin not in origins or any(
            not origin.startswith(("https://", "chrome-extension://")) for origin in origins
        ):
            raise ValueError(
                "Production CORS_ORIGINS must include https://APP_DOMAIN and use HTTPS"
            )

        mongo = urlsplit(self.mongodb_url)
        mongo_password = mongo.password or ""
        if (
            mongo.scheme not in {"mongodb", "mongodb+srv"}
            or not mongo.hostname
            or mongo.hostname in {"localhost", "127.0.0.1", "::1"}
            or len(mongo_password) < 32
            or mongo_password == "local_development_only"
        ):
            raise ValueError(
                "Production MONGODB_URL must use a non-local MongoDB host and a unique "
                "password of at least 32 characters"
            )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sensitive_concepts_list(self) -> list[str]:
        return [c.strip().lower() for c in self.sensitive_field_concepts.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
