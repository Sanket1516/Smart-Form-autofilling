from typing import Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared evidence model
# ---------------------------------------------------------------------------

class ExtractionEvidence(BaseModel):
    document_id: str
    page: int | None = None
    text: str


# ---------------------------------------------------------------------------
# Legacy ontology-based extraction (kept for backward compat)
# ---------------------------------------------------------------------------

class ExtractedFact(BaseModel):
    ontology: str
    value: Any
    data_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    status: Literal["EXTRACTED"]


class ExtractedConflictCandidate(BaseModel):
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence


class ExtractedConflict(BaseModel):
    ontology: str | None = None
    semantic_type: str | None = None     # populated for discovered-field conflicts
    field: str | None = None
    status: Literal["CONFLICT"]
    candidates: list[ExtractedConflictCandidate]


class UnmappedExtraction(BaseModel):
    value: Any
    reason: str | None = None


class LLMExtractionOutput(BaseModel):
    document_status: Literal["PROCESSED", "FAILED", "PARTIAL"]
    facts: list[ExtractedFact] = Field(default_factory=list)
    conflicts: list[ExtractedConflict] = Field(default_factory=list)
    unmapped_items: list[UnmappedExtraction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# NEW: Document-agnostic dynamic entity discovery schemas
# ---------------------------------------------------------------------------

class DiscoveredAttribute(BaseModel):
    """A single field discovered by the LLM from any document type."""
    field: str                              # e.g. "cgpa", "account_number", "policy_number"
    semantic_type: str                      # e.g. "ACADEMIC_SCORE", "BANK_ACCOUNT_NUMBER"
    value: Any
    data_type: str = "string"              # "string" | "number" | "date" | "boolean" | "array"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    unit: str | None = None                 # e.g. "INR", "%", "years"
    currency: str | None = None             # e.g. "INR", "USD"
    date_format: str | None = None          # e.g. "DD/MM/YYYY"
    normalization: str | None = None        # normalized representation if different from raw
    entity_id: str | None = None            # which entity this attribute belongs to
    ontology: str | None = None             # optional mapping to existing ontology concept
    ontology_confidence: float | None = None  # how confident the ontology mapping is
    relationship: str | None = None


class DiscoveredEntity(BaseModel):
    """A semantic entity discovered in the document (person, org, account, etc)."""
    entity_id: str                          # e.g. "entity_1", "entity_2"
    entity_type: str                        # "PERSON", "ORGANIZATION", "FINANCIAL_ACCOUNT", "VEHICLE", etc.
    attributes: list[DiscoveredAttribute]


class DiscoveredRelationship(BaseModel):
    """A relationship between two entities discovered in the document."""
    entity_id_1: str
    entity_id_2: str
    relationship: str                       # e.g. "WORKS_AT", "ENROLLED_IN", "OWNS"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence


class DynamicExtractionOutput(BaseModel):
    """Full dynamic extraction output — document type agnostic."""
    document_id: str
    document_type: str                      # LLM-inferred e.g. "BANK_PASSBOOK", "RESUME", "INVOICE"
    document_status: Literal["PROCESSED", "FAILED", "PARTIAL"] = "PROCESSED"
    entities: list[DiscoveredEntity] = Field(default_factory=list)
    discovered_fields: list[DiscoveredAttribute] = Field(default_factory=list)
    relationships: list[DiscoveredRelationship] = Field(default_factory=list)
    conflicts: list[ExtractedConflict] = Field(default_factory=list)
    unmapped_information: list[UnmappedExtraction] = Field(default_factory=list)

