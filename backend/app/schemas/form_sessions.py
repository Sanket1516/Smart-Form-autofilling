"""Schemas for form sessions, field descriptions and recommendations.

``FieldObject`` is the limited, validated description of one form control that
the extension sends. It never contains the field's current value (only whether
it has one), and every string is length-capped.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

RecommendationStatus = Literal[
    "ready",
    "needs_review",
    "missing_information",
    "security_blocked",
    "skipped",
    "error",
    "approved",
    "edited",
    "rejected",
]

_TEXT_LIMITS = {
    "label": 300,
    "question": 500,
    "name": 200,
    "id": 200,
    "placeholder": 200,
    "aria_label": 300,
    "aria_description": 300,
    "autocomplete": 100,
    "pattern": 200,
    "section": 300,
    "nearby_text": 300,
    "tag": 20,
    "input_type": 30,
}


class FormFieldOption(BaseModel):
    model_config = ConfigDict(extra="ignore")

    option_id: str = Field(default="", max_length=300)
    value: str = Field(default="", max_length=300)
    label: str = Field(default="", max_length=300)
    disabled: bool | None = None

    @field_validator("option_id", "value", "label", mode="before")
    @classmethod
    def _text(cls, value: Any) -> str:
        return "" if value is None else " ".join(str(value).split())[:300]


class FieldObject(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    field_id: str = Field(min_length=1, max_length=400)
    label: str = ""
    question: str = ""
    tag: str = "input"
    input_type: str = Field(default="text", validation_alias=AliasChoices("input_type", "type"))
    name: str = ""
    id: str = ""
    placeholder: str = ""
    aria_label: str = ""
    aria_description: str = ""
    autocomplete: str = ""
    pattern: str = ""
    section: str = Field(default="", validation_alias=AliasChoices("section", "section_context"))
    nearby_text: str = ""
    required: bool = False
    has_value: bool = False
    max_length: int | None = Field(default=None, ge=0)
    options: list[FormFieldOption] = Field(default_factory=list, max_length=500)

    @field_validator(*_TEXT_LIMITS, mode="before")
    @classmethod
    def _cap(cls, value: Any, info: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split())[: _TEXT_LIMITS[info.field_name]]

    @field_validator("input_type")
    @classmethod
    def _lower_type(cls, value: str) -> str:
        return (value or "text").lower()

    @property
    def display_label(self) -> str:
        return (
            self.question
            or self.label
            or self.aria_label
            or self.placeholder
            or self.name
            or self.field_id
        )


class FormSessionCreate(BaseModel):
    website_origin: str = Field(min_length=1, max_length=300)
    page_url: str = Field(min_length=1, max_length=2000)
    form_id: str = Field(min_length=1, max_length=300)


class FormSessionCreateData(BaseModel):
    session_id: str
    status: str


class FormSessionResponseData(BaseModel):
    session_id: str
    website_origin: str
    page_url: str = ""
    form_id: str
    status: str
    started_at: datetime | None = None
    total_fields: int = 0
    filled_fields: int = 0
    reviewed_fields: int = 0
    failed_fields: int = 0
    error: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)


class FormSessionListData(BaseModel):
    sessions: list[FormSessionResponseData]


class FormSessionAnalyzeRequest(BaseModel):
    fields: list[FieldObject] = Field(min_length=1, max_length=300)


class FormSessionAnalyzeData(BaseModel):
    session_id: str
    status: str
    field_count: int


class RecommendationSource(BaseModel):
    type: Literal["profile", "document", "memory", "user", "derived"]
    document_id: str | None = None
    document_name: str | None = None
    page: int | None = None
    snippet: str | None = None
    fact_ids: list[str] = Field(default_factory=list)


class RecommendationCandidate(BaseModel):
    value: Any
    confidence: float = 0.0
    source: RecommendationSource | None = None


class SelectedOption(BaseModel):
    label: str
    value: str


class RecommendationProvenance(BaseModel):
    document_id: str
    page: int | None = None


class RecommendationOutput(BaseModel):
    recommendation_id: str
    field_id: str
    field_label: str = ""
    input_type: str = "text"
    required: bool = False
    concept: str | None = None
    recommended_value: Any = None
    confidence: float = 0.0
    status: RecommendationStatus
    reason: str = ""
    requires_confirmation: bool = False
    origin: str | None = None
    retrieval_type: str = "none"
    source: RecommendationSource | None = None
    candidates: list[RecommendationCandidate] = Field(default_factory=list)
    options: list[SelectedOption] = Field(default_factory=list)
    selected_option: SelectedOption | None = None
    provenance: list[RecommendationProvenance] = Field(default_factory=list)
    fill_result: dict[str, Any] | None = None


class SessionRecommendationsData(BaseModel):
    session_id: str
    status: str
    recommendations: list[RecommendationOutput]


class FieldDecision(BaseModel):
    field_id: str = Field(min_length=1, max_length=400)
    decision: Literal["approve", "edit", "reject", "skip"]
    value: str | None = Field(default=None, max_length=10000)
    save_for_future: bool = False


class FieldDecisionsRequest(BaseModel):
    decisions: list[FieldDecision] = Field(min_length=1, max_length=300)


class ApprovedValueData(BaseModel):
    recommendation_id: str
    field_id: str
    concept: str | None = None
    value: str
    input_type: str = "text"
    field_label: str = ""
    selected_option: SelectedOption | None = None
    status: str


class ApprovedValuesResponseData(BaseModel):
    session_id: str
    approved_values: list[ApprovedValueData]


class AskMeAnswer(BaseModel):
    field_id: str = Field(min_length=1, max_length=400)
    value: str = Field(min_length=1, max_length=10000)
    save_for_future: bool = False


class AskMeAnswersRequest(BaseModel):
    answers: list[AskMeAnswer] = Field(min_length=1, max_length=100)


class AskMeAnswersData(BaseModel):
    session_id: str
    status: str
    saved_count: int


class FillResult(BaseModel):
    field_id: str = Field(min_length=1, max_length=400)
    applied: bool
    verified: bool
    reason: str | None = Field(default=None, max_length=300)


class FormSessionVerifyRequest(BaseModel):
    results: list[FillResult] = Field(min_length=1, max_length=300)


class FormSessionVerifyData(BaseModel):
    session_id: str
    status: str
    filled_fields: int
    failed_fields: int


class FormSessionCompleteRequest(BaseModel):
    submission_status: Literal["user_submitted", "not_submitted", "cancelled"] = "not_submitted"


class FormSessionCompleteData(BaseModel):
    session_id: str
    status: str
