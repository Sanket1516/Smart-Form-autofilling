"""Extraction data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class CandidateFact:
    """A value found in one document, before persistence.

    ``origin`` distinguishes values copied from the text (``extracted``), values
    re-formatted without changing meaning (``normalized``) and values a model or
    heuristic produced that are not literally present (``inferred``).
    """

    semantic_type: str
    field: str
    value: Any
    raw_value: Any
    data_type: str
    confidence: float
    origin: str
    method: str
    concept: str | None = None
    page: int | None = None
    evidence_text: str = ""
    entity_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class LLMAttribute(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str = Field(min_length=1, max_length=120)
    semantic_type: str = Field(min_length=1, max_length=120)
    concept: str | None = None
    value: Any
    page: int | None = None
    evidence: str = Field(default="", max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    entity_type: str | None = Field(default=None, max_length=60)


class LLMExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_type: str = Field(default="UNKNOWN", max_length=60)
    attributes: list[LLMAttribute] = Field(default_factory=list, max_length=500)
