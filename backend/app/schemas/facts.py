"""Structured fact API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FactData(BaseModel):
    fact_id: str
    concept: str
    value: Any
    value_type: str
    source_document_id: str
    source_page: int
    confidence: float
    provenance: dict[str, Any]
    is_user_confirmed: bool
    created_at: datetime
    updated_at: datetime
    source: dict[str, Any] | None = None


class FactsData(BaseModel):
    facts: list[FactData]


class FactUpdateRequest(BaseModel):
    value: Any
    is_user_confirmed: bool = True
    reason: str | None = "User fact edit"
