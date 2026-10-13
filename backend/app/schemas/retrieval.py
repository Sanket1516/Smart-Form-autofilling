"""RAG retrieval and answer schemas."""

from typing import Literal

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


class RAGAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class RAGAnswerSource(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str = ""
    page_number: int = 1
    similarity: float
    snippet: str


class RAGAnswerData(BaseModel):
    answer: str
    status: Literal["answered", "insufficient_evidence"]
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[RAGAnswerSource] = Field(default_factory=list)


class StructuredRetrievalRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=160)
    verified_only: bool = False


class StructuredRetrievalData(BaseModel):
    results: list[dict] = Field(default_factory=list)
