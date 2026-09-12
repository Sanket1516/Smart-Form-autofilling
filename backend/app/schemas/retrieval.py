"""RAG Retrieval API schemas (API_SPECIFICATION section 30)."""

from typing import Any

from pydantic import BaseModel, Field


class RAGFilters(BaseModel):
    document_type: str | None = None
    language: str | None = None


class RAGRetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: RAGFilters | None = None


class RAGChunkMetadata(BaseModel):
    document_id: str
    page_number: int
    language: str


class RAGSearchResult(BaseModel):
    chunk_id: str
    text: str
    similarity: float
    metadata: RAGChunkMetadata | dict[str, Any]


class RAGRetrievalData(BaseModel):
    results: list[RAGSearchResult]


class StructuredRetrievalRequest(BaseModel):
    concept: str = Field(min_length=1, description="Ontology concept to search for")
    verified_only: bool = Field(default=False, description="Whether to return only verified canonical facts")


class StructuredRetrievalData(BaseModel):
    results: list[Any] = Field(description="List of FactData objects")
