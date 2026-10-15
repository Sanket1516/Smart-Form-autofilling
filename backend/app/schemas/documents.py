"""Document API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal[
    "uploaded", "processing", "processed", "failed", "requires_review", "deleted"
]
IndexStatus = Literal["pending", "indexed", "failed", "empty"]


class DocumentData(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    file_size: int = 0
    document_type: str | None = None
    document_type_confidence: float | None = None
    status: DocumentStatus
    current_stage: str | None = None
    progress: int = 0
    processing_error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    uploaded_at: datetime
    processed_at: datetime | None = None
    page_count: int | None = None
    fact_count: int = 0
    index_status: IndexStatus = "pending"
    chunk_count: int = 0
    index_error: str | None = None


class DocumentListData(BaseModel):
    documents: list[DocumentData]
    page: int
    limit: int
    total: int


class ProcessingData(BaseModel):
    document_id: str
    processing_status: Literal["processing"] = "processing"


class ProcessingStatusData(BaseModel):
    document_id: str
    status: DocumentStatus
    current_stage: str | None = None
    progress: int = Field(ge=0, le=100)
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    fact_count: int = 0
    index_status: IndexStatus = "pending"
    index_error: str | None = None
