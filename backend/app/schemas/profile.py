"""Profile and Correction API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.facts import FactSource


class ProfileField(BaseModel):
    concept: str
    label: str
    status: str
    value: Any = None
    values: list[Any] = Field(default_factory=list)
    confidence: float = 0.0
    is_user_confirmed: bool = False
    origin: str = "extracted"
    sensitive: bool = False
    group: str = "other"
    data_type: str = "string"
    sources: list[FactSource] = Field(default_factory=list)


class ProfileData(BaseModel):
    user_id: str
    personal: dict[str, Any] = Field(default_factory=dict)
    contact: dict[str, Any] = Field(default_factory=dict)
    address: dict[str, Any] = Field(default_factory=dict)
    education: list[dict[str, Any]] = Field(default_factory=list)
    employment: list[dict[str, Any]] = Field(default_factory=list)
    sections: dict[str, dict[str, Any]] = Field(default_factory=dict)
    fields: list[ProfileField] = Field(default_factory=list)
    groups: list[dict[str, str]] = Field(default_factory=list)
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """Either ``fields`` ({concept: value}) or the legacy personal/contact/address sections."""

    fields: dict[str, Any] | None = None
    personal: dict[str, Any] | None = None
    contact: dict[str, Any] | None = None
    address: dict[str, Any] | None = None


class ProfileUpdateResponse(BaseModel):
    updated: bool = True
    saved: int = 0


class UserMemoryCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    concept: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=10000)


class UserMemoryData(BaseModel):
    memory_id: str
    label: str
    concept: str
    value: str
    indexed: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserMemoriesData(BaseModel):
    memories: list[UserMemoryData]


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
