"""Field Object and Semantic Classification API schemas per SRS §11.2, §13.6 and API_SPECIFICATION §25-26, 27-28, 31, 33."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class FieldObject(BaseModel):
    """Field Object schema per SRS §11.2."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    field_id: str = Field(min_length=1, description="Unique field identifier")
    tag: str | None = Field(default="input", description="HTML element tag (e.g. input, select, textarea)")
    type: str | None = Field(default="text", alias="input_type", description="Input type attribute")
    name: str | None = Field(default=None, description="HTML name attribute")
    id: str | None = Field(default=None, description="HTML id attribute")
    placeholder: str | None = Field(default=None, description="Placeholder text")
    label: str | None = Field(default=None, description="Visible associated label text")
    aria_label: str | None = Field(default=None, description="Accessibility aria-label attribute")
    aria_description: str | None = Field(default=None, description="Accessibility aria-description attribute")
    autocomplete: str | None = Field(default=None, description="HTML autocomplete attribute")
    required: bool = Field(default=False, description="Whether field is required")
    pattern: str | None = Field(default=None, description="Validation regex pattern")
    nearby_text: str | None = Field(default=None, description="Surrounding text or label context")
    section_context: str | None = Field(default=None, alias="section", description="Form section context")
    position: dict[str, Any] | None = Field(default=None, description="Position coordinates in layout")
    dom_context: dict[str, Any] = Field(default_factory=dict, alias="DOM_context", description="DOM tree context")
    accessibility_context: dict[str, Any] = Field(default_factory=dict, description="Accessibility tree metadata")
    visual_context: dict[str, Any] | None = Field(default=None, description="Visual bounds and layout metadata")
    concept: str | None = Field(default=None, description="Classified semantic concept")


class AlternativeConcept(BaseModel):
    concept: str
    confidence: float = Field(ge=0.0, le=1.0)


class ClassificationOutput(BaseModel):
    """Semantic Classification Agent output shape per Pipeline C."""

    field_id: str
    concept: str = Field(alias="ontology")
    # NEW: semantic type label for document-agnostic retrieval
    # e.g. "BANK_ACCOUNT_NUMBER", "ACADEMIC_SCORE", "PERSON_FULL_NAME"
    semantic_type: str = "UNKNOWN"
    field_type: str = Field(description="STRUCTURED, CONTEXTUAL, or MISSING")
    confidence: float = Field(ge=0.0, le=1.0)
    retrieval: dict[str, Any] | None = Field(default_factory=dict)
    # NEW: explicit retrieval strategy
    # "MONGODB" → structured/discovered facts | "CHROMADB" → RAG | "BOTH" | "MISSING"
    retrieval_strategy: str = "MISSING"

    # Keeping old fields with defaults for backward compatibility where needed
    alternatives: list[AlternativeConcept] = Field(default_factory=list)
    context_used: list[str] = Field(default_factory=list)
    status: str = "classified"


class ClassifyFieldRequest(BaseModel):
    field: FieldObject


class ClassifyFieldsRequest(BaseModel):
    fields: list[FieldObject]


class ClassifyFieldsResponseData(BaseModel):
    classifications: list[ClassificationOutput]


class RecommendRequest(BaseModel):
    session_id: str
    field: FieldObject


class BatchRecommendRequest(BaseModel):
    session_id: str
    fields: list[FieldObject]


class RecommendationProvenance(BaseModel):
    document_id: str
    page: int


class RecommendationOutput(BaseModel):
    recommendation_id: str
    field_id: str
    concept: str
    recommended_value: Any
    confidence: float
    retrieval_type: str = "structured"
    status: str
    provenance: list[RecommendationProvenance] = Field(default_factory=list)
    field_label: str = ""
    required: bool = False
    input_type: str = "text"


class RecommendResponseData(BaseModel):
    recommendation_id: str
    field_id: str
    concept: str
    recommended_value: Any
    confidence: float
    retrieval_type: str
    status: str
    provenance: list[RecommendationProvenance] = Field(default_factory=list)
    field_label: str = ""
    required: bool = False
    input_type: str = "text"


class BatchRecommendResponseData(BaseModel):
    recommendations: list[RecommendationOutput]


class SessionRecommendationsData(BaseModel):
    recommendations: list[RecommendationOutput]


class AgentRunRequest(BaseModel):
    session_id: str
    field: FieldObject


class AgentRunResponseData(BaseModel):
    run_id: str
    status: str


class AgentRunStatusData(BaseModel):
    run_id: str
    status: str
    current_node: str | None = None
    recommendation_id: str | None = None
