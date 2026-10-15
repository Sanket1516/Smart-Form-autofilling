"""Structured fact, profile-view and conflict API schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FactData(BaseModel):
    fact_id: str
    concept: str
    value: Any
    raw_value: Any = None
    value_type: str
    origin: str = "extracted"
    status: str = "active"
    source_document_id: str
    document_name: str | None = None
    source_page: int | None = None
    evidence_text: str | None = None
    extraction_method: str | None = None
    confidence: float
    provenance: dict[str, Any] = Field(default_factory=dict)
    is_user_confirmed: bool
    document_type: str | None = None
    needs_review: bool = False
    created_at: datetime
    updated_at: datetime
    source: dict[str, Any] | None = None


class FactsData(BaseModel):
    facts: list[FactData]


class FactUpdateRequest(BaseModel):
    value: Any
    is_user_confirmed: bool = True
    reason: str | None = Field(default="User fact edit", max_length=500)


class FactCreateRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=160)
    value: Any
    reason: str | None = Field(default="Added by user", max_length=500)


class FactSource(BaseModel):
    fact_id: str
    document_id: str
    document_name: str | None = None
    page: int | None = None
    evidence: str | None = None
    origin: str
    confidence: float
    is_user_confirmed: bool
    document_type: str | None = None
    needs_review: bool = False


class ConflictCandidate(BaseModel):
    value: Any
    confidence: float
    is_user_confirmed: bool
    document_id: str
    document_name: str | None = None
    page: int | None = None
    evidence: str | None = None
    sources: list[FactSource] = Field(default_factory=list)


class ConflictData(BaseModel):
    id: str
    concept: str
    ontology: str
    field: str
    semantic_type: str
    label: str
    conflict_type: Literal["CROSS_DOCUMENT", "INTRA_DOCUMENT", "VERIFIED_VS_NEW"]
    conflict_status: Literal["CONFLICT"] = "CONFLICT"
    candidates: list[ConflictCandidate]


class ConflictResolutionRequest(BaseModel):
    resolution: Literal["candidate", "candidate_a", "candidate_b", "custom", "reject"]
    candidate_index: int | None = Field(default=None, ge=0)
    custom_value: Any = None
    reason: str | None = Field(default=None, max_length=500)


class ConceptView(BaseModel):
    """The usable profile value(s) for one concept, computed from active facts."""

    concept: str
    label: str
    status: Literal["resolved", "conflict", "multiple"]
    value: Any = None
    values: list[Any] = Field(default_factory=list)
    confidence: float = 0.0
    is_user_confirmed: bool = False
    origin: str = "extracted"
    sources: list[FactSource] = Field(default_factory=list)
    candidates: list[ConflictCandidate] = Field(default_factory=list)
    # Why a value was chosen when sources disagreed (e.g. the official document won).
    note: str | None = None
