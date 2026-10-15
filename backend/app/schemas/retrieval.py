"""RAG retrieval and answer schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class RAGFilters(BaseModel):
    document_type: str | None = None


class RAGRetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: RAGFilters | None = None


class RAGChunkMetadata(BaseModel):
    document_id: str
    document_name: str = ""
    document_type: str = "UNKNOWN"
    source_type: str = "document"
    page_number: int = 1
    chunk_index: int = 0


class RAGSearchResult(BaseModel):
    chunk_id: str
    text: str
    similarity: float
    metadata: RAGChunkMetadata


class RAGRetrievalData(BaseModel):
    results: list[RAGSearchResult]
    min_similarity: float


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RAGAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    # Restrict the answer to these documents (all processed documents when omitted).
    document_ids: list[str] | None = Field(default=None, max_length=50)
    # Earlier turns of this conversation, oldest first, for follow-up questions.
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)
    # Exam or form the question is about (e.g. NEET_UG); detected from the question otherwise.
    exam_id: str | None = Field(default=None, max_length=40)


class RAGAnswerSource(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str = ""
    document_type: str = "UNKNOWN"
    page_number: int = 1
    similarity: float
    snippet: str


class AnswerFact(BaseModel):
    """A stored value used in the answer, with where it came from."""

    fact_id: str = ""
    concept: str
    label: str
    value: Any
    status: Literal["verified", "extracted", "needs_review"]
    document_id: str | None = None
    document_name: str | None = None
    document_type: str | None = None
    page: int | None = None
    evidence: str | None = None
    confidence: float = 0.0


class AnswerDerived(BaseModel):
    """A value calculated by code from stored facts (never by the model)."""

    label: str
    value: str
    method: str
    inputs: list[str] = Field(default_factory=list)


class AnswerMissing(BaseModel):
    concept: str
    label: str
    reason: str
    suggested_documents: list[str] = Field(default_factory=list)


class AnswerConflictValue(BaseModel):
    value: Any
    document_name: str | None = None
    page: int | None = None


class AnswerConflict(BaseModel):
    concept: str
    label: str
    values: list[AnswerConflictValue]


class AnswerRequirement(BaseModel):
    """An external rule (exam requirement or eligibility criterion) and how it was checked."""

    label: str
    outcome: Literal["met", "not_met", "unknown", "needs_confirmation", "info"]
    detail: str
    source: str


class DocumentConsidered(BaseModel):
    document_id: str
    document_name: str
    document_type: str | None = None
    status: str
    searched: bool


QuestionType = Literal[
    "exact_lookup",
    "document_lookup",
    "multi_document",
    "comparison",
    "eligibility",
    "requirements",
    "missing_info",
    "fillability",
    "provenance",
    "external",
    "contextual",
]


class RAGAnswerData(BaseModel):
    answer: str
    status: Literal[
        "answered", "partial", "insufficient_evidence", "no_documents", "documents_not_ready"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[RAGAnswerSource] = Field(default_factory=list)
    question_type: QuestionType = "contextual"
    # structured: built from stored facts by code; generated: written by the model from
    # cited evidence; evidence_only: the model was unavailable, evidence is listed instead.
    answer_mode: Literal["structured", "generated", "evidence_only", "none"] = "none"
    facts: list[AnswerFact] = Field(default_factory=list)
    derived: list[AnswerDerived] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    missing: list[AnswerMissing] = Field(default_factory=list)
    conflicts: list[AnswerConflict] = Field(default_factory=list)
    requirements: list[AnswerRequirement] = Field(default_factory=list)
    documents: list[DocumentConsidered] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StructuredRetrievalRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=160)
    verified_only: bool = False


class StructuredRetrievalData(BaseModel):
    results: list[dict] = Field(default_factory=list)
