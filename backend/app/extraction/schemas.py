from typing import Any, Literal
from pydantic import BaseModel, Field

class ExtractionEvidence(BaseModel):
    document_id: str
    page: int | None = None
    text: str

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
    ontology: str
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
