"""Validated MongoDB document models matching DATABASE_DESIGN sections 5-14."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class MongoDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# NEW: Flexible discovered facts model (document-agnostic extraction)
# ---------------------------------------------------------------------------

class DiscoveredFact(BaseModel):
    """Stores a dynamically discovered fact from any document type.

    Schema is intentionally flexible — new semantic_types can appear
    at runtime without requiring code changes.
    """
    model_config = ConfigDict(extra="allow")   # Allow future fields without breaking

    user_id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_page: int | None = None
    entity_id: str | None = None              # e.g. "entity_1" — groups related attributes
    entity_type: str | None = None            # e.g. "PERSON", "FINANCIAL_ACCOUNT"
    field: str = Field(min_length=1)          # e.g. "account_number", "cgpa"
    semantic_type: str = Field(min_length=1)  # e.g. "BANK_ACCOUNT_NUMBER", "ACADEMIC_SCORE"
    value: Any
    data_type: str = "string"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str = ""                   # Exact text from document supporting this value
    ontology: str | None = None               # Canonical ontology concept if mapped
    ontology_confidence: float | None = None
    unit: str | None = None
    currency: str | None = None
    date_format: str | None = None
    normalization: str | None = None
    verification_status: Literal["UNVERIFIED", "VERIFIED", "REJECTED"] = "UNVERIFIED"
    conflict_status: Literal["OK", "CONFLICT", "RESOLVED"] = "OK"
    extraction_method: str = "llm_dynamic"
    document_type: str | None = None          # e.g. "BANK_PASSBOOK", "RESUME"
    created_at: datetime
    updated_at: datetime


class DiscoveredConflict(BaseModel):
    """Tracks a conflict between two or more fact values for HITL resolution."""
    model_config = ConfigDict(extra="allow")

    user_id: str = Field(min_length=1)
    field: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    ontology: str | None = None
    conflict_type: str = "CROSS_DOCUMENT"     # "INTRA_DOCUMENT" | "CROSS_DOCUMENT" | "LLM_VS_DETERMINISTIC" | "VERIFIED_VS_NEW"
    conflict_status: Literal["CONFLICT", "RESOLVED", "REJECTED"] = "CONFLICT"
    verification_status: Literal["UNVERIFIED", "VERIFIED"] = "UNVERIFIED"
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    resolved_value: Any = None
    resolved_by: str | None = None            # user_id or "system"
    resolution_reason: str | None = None
    is_verified_conflict: bool = False         # True when an existing fact was user-verified
    created_at: datetime
    updated_at: datetime


class UserDocument(MongoDocument):
    full_name: str = Field(min_length=1)
    email: EmailStr
    password_hash: str = Field(min_length=1)
    status: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class ProfileDocument(MongoDocument):
    user_id: str = Field(min_length=1)
    personal: dict[str, Any] = Field(default_factory=dict)
    contact: dict[str, Any] = Field(default_factory=dict)
    address: dict[str, Any] = Field(default_factory=dict)
    education: list[dict[str, Any]] = Field(default_factory=list)
    employment: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime


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
    page_count: int | None = Field(default=None, ge=0)
    checksum: str = Field(min_length=64, max_length=64)
    current_stage: str | None = None
    progress: int = Field(default=0, ge=0, le=100)
    processing_error: str | None = None
    normalized_reference: str | None = None


class StructuredFact(MongoDocument):
    user_id: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    value: Any = None
    value_type: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_page: int | None = None
    confidence: float = Field(ge=0, le=1)
    provenance: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="EXTRACTED") # EXTRACTED, CONFLICT, RESOLVED
    candidates: list[dict[str, Any]] = Field(default_factory=list) # Populated if status == CONFLICT
    is_user_confirmed: bool
    created_at: datetime
    updated_at: datetime


class UnmappedItem(MongoDocument):
    user_id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    value: Any
    reason: str | None = None
    created_at: datetime


class Recommendation(MongoDocument):
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    field_id: str = Field(min_length=1)
    field_label: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    recommended_value: Any
    confidence: float = Field(ge=0, le=1)
    retrieval_type: str = Field(min_length=1)
    source_fact_ids: list[str] = Field(default_factory=list)
    status: str = Field(min_length=1)
    created_at: datetime


class Correction(MongoDocument):
    user_id: str = Field(min_length=1)
    session_id: str | None = None
    field_id: str | None = None
    concept: str = Field(min_length=1)
    original_value: Any = None
    corrected_value: Any = None
    reason: str = Field(min_length=1)
    created_at: datetime


class Feedback(MongoDocument):
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    field_id: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    recommendation_id: str = Field(min_length=1)
    action: Literal["confirmed", "edited", "rejected", "skipped", "corrected"]
    original_value: Any
    final_value: Any
    feedback_type: str = Field(min_length=1)
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


class FormSession(MongoDocument):
    user_id: str = Field(min_length=1)
    website_origin: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    form_id: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    status: str = Field(min_length=1)
    total_fields: int = Field(ge=0)
    filled_fields: int = Field(ge=0)
    reviewed_fields: int = Field(ge=0)
    failed_fields: int = Field(ge=0)

    @field_validator("filled_fields", "reviewed_fields", "failed_fields")
    @classmethod
    def counts_must_fit_total(cls, value: int, info: Any) -> int:
        total = info.data.get("total_fields")
        if total is not None and value > total:
            raise ValueError("field counts cannot exceed total_fields")
        return value
