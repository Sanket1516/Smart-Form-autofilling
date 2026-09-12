"""Pydantic schemas for Form Sessions."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FormSessionCreate(BaseModel):
    website_origin: str
    page_url: str
    form_id: str


class FormSessionCreateData(BaseModel):
    session_id: str
    status: str


class FormSessionResponseData(BaseModel):
    session_id: str
    website_origin: str
    form_id: str
    status: str
    total_fields: int
    filled_fields: int
    reviewed_fields: int


class FieldObject(BaseModel):
    field_id: str
    label: str
    name: Optional[str] = ""
    placeholder: Optional[str] = ""
    input_type: str
    section: Optional[str] = ""
    dom_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    accessibility_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class FormSessionAnalyzeRequest(BaseModel):
    fields: List[FieldObject]


class FormSessionAnalyzeData(BaseModel):
    session_id: str
    status: str
    field_count: int


class FormSessionCompleteRequest(BaseModel):
    total_fields: int
    filled_fields: int
    reviewed_fields: int
    failed_fields: int
    submission_status: str


class FormSessionCompleteData(BaseModel):
    session_id: str
    status: str
