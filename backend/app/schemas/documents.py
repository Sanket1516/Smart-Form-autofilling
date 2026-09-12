"""Document API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal[
    "uploaded", "processing", "processed", "failed", "requires_review", "deleted"
]


class DocumentData(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    document_type: str | None = None
    status: DocumentStatus
    uploaded_at: datetime
    processed_at: datetime | None = None
    page_count: int | None = None


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
