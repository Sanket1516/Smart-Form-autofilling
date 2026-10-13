"""Validated MongoDB document models.

These models describe what the application writes. `docs/DATABASE_SCHEMA.md`
documents the same shapes; keep the two in sync.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

FactOrigin = Literal["extracted", "normalized", "inferred", "derived", "user_provided"]
FactStatus = Literal["active", "superseded", "rejected"]


class MongoDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserDocument(MongoDocument):
    full_name: str = Field(min_length=1)
    email: EmailStr
    password_hash: str = Field(min_length=1)
    status: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class DocumentRecord(MongoDocument):
    user_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    file_type: str = Field(min_length=1)
    file_size: int = Field(ge=0)
    storage_reference: str = Field(min_length=1)
    document_type: str | None = None
    language: str | None = None
    status: Literal["uploaded", "processing", "processed", "failed", "requires_review", "deleted"]
    uploaded_at: datetime
    processed_at: datetime | None = None
    processing_started_at: datetime | None = None
    page_count: int | None = Field(default=None, ge=0)
    checksum: str = Field(min_length=64, max_length=64)
    current_stage: str | None = None
    progress: int = Field(default=0, ge=0, le=100)
    processing_error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    normalized_reference: str | None = None
    fact_count: int = Field(default=0, ge=0)
    index_status: Literal["pending", "indexed", "failed", "empty"] = "pending"
    chunk_count: int = Field(default=0, ge=0)
    index_error: str | None = None


class StructuredFact(MongoDocument):
    """One ontology-concept value from one source (a document or the user).

    Facts are never merged across sources: each document contributes its own
    records so provenance survives and deleting a document removes exactly its
    facts. The profile view and conflicts are computed from active facts.
    """

    user_id: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    value: Any
    raw_value: Any = None
    value_type: str = Field(min_length=1)
    origin: FactOrigin = "extracted"
    status: FactStatus = "active"
    source_document_id: str = Field(min_length=1)  # document id, or "user"
    document_name: str | None = None
    source_page: int | None = None
    evidence_text: str | None = None
    extraction_method: str = "deterministic"
    confidence: float = Field(ge=0, le=1)
    provenance: dict[str, Any] = Field(default_factory=dict)
    is_user_confirmed: bool = False
    created_at: datetime
    updated_at: datetime


class DiscoveredFact(BaseModel):
    """Every attribute the extractors found in one document, mapped or not."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_page: int | None = None
    entity_type: str | None = None
    field: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    value: Any
    data_type: str = "string"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str = ""
    ontology: str | None = None
    origin: FactOrigin = "extracted"
    extraction_method: str = "llm"
    document_type: str | None = None
    created_at: datetime
    updated_at: datetime


class Correction(MongoDocument):
    user_id: str = Field(min_length=1)
    session_id: str | None = None
    field_id: str | None = None
    concept: str = Field(min_length=1)
    original_value: Any = None
    corrected_value: Any = None
    reason: str = Field(min_length=1)
    created_at: datetime


class ProcessingRecord(MongoDocument):
    user_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    status: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    retry_count: int = Field(default=0, ge=0)
    error: str | None = None
