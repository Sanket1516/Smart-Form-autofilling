"""Profile and Correction API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProfileData(BaseModel):
    user_id: str
    personal: dict[str, Any] = Field(default_factory=dict)
    contact: dict[str, Any] = Field(default_factory=dict)
    address: dict[str, Any] = Field(default_factory=dict)
    education: list[dict[str, Any]] = Field(default_factory=list)
    employment: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    personal: dict[str, Any] | None = None
    contact: dict[str, Any] | None = None
    address: dict[str, Any] | None = None
    education: list[dict[str, Any]] | None = None
    employment: list[dict[str, Any]] | None = None


class ProfileUpdateResponse(BaseModel):
    updated: bool = True


class CorrectionCreateRequest(BaseModel):
    session_id: str | None = None
    field_id: str | None = None
    concept: str
    original_value: Any = None
    corrected_value: Any = None
    reason: str = "User correction"


class CorrectionData(BaseModel):
    correction_id: str
    user_id: str
    session_id: str | None = None
    field_id: str | None = None
    concept: str
    original_value: Any = None
    corrected_value: Any = None
    reason: str
    created_at: datetime


class CorrectionsListData(BaseModel):
    corrections: list[CorrectionData]
