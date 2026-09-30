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
    tag: Optional[str] = "input"
    name: Optional[str] = ""
    id: Optional[str] = ""
    placeholder: Optional[str] = ""
    input_type: str
    aria_label: Optional[str] = ""
    aria_description: Optional[str] = ""
    autocomplete: Optional[str] = ""
    required: bool = False
    pattern: Optional[str] = ""
    section: Optional[str] = ""
    nearby_text: Optional[str] = ""
    section_context: Optional[str] = ""
    visual_context: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None
    dom_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    accessibility_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class FormSessionAnalyzeRequest(BaseModel):
    fields: List[FieldObject]


class FormSessionAnalyzeData(BaseModel):
    session_id: str
    status: str
    field_count: int


class AskMeAnswer(BaseModel):
    field_id: str = Field(min_length=1)
    value: str = Field(min_length=1, max_length=10000)
    save_for_future: bool = False


class AskMeAnswersRequest(BaseModel):
    answers: list[AskMeAnswer] = Field(min_length=1, max_length=100)


class AskMeAnswersData(BaseModel):
    session_id: str
    status: str
    saved_count: int


class FormSessionCompleteRequest(BaseModel):
    total_fields: int
    filled_fields: int
    reviewed_fields: int
    failed_fields: int
    submission_status: str


class FormSessionCompleteData(BaseModel):
    session_id: str
    status: str


class ApprovedValueData(BaseModel):
    field_id: str
    concept: str
    value: str
    confidence: float
    requires_confirmation: bool
    field_label: str = ""
    input_type: str = "text"


class ApprovedValuesResponseData(BaseModel):
    session_id: str
    approved_values: List[ApprovedValueData]


class FormSessionVerifyRequest(BaseModel):
    field_id: str
    filled_value: str
    actual_value: str
    match: bool
    requires_correction: bool


class FormSessionVerifyData(BaseModel):
    session_id: str
    status: str
