"""Review (human-in-the-loop) schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.form_sessions import RecommendationCandidate, RecommendationSource


class PendingReviewItem(BaseModel):
    review_id: str
    session_id: str
    field_id: str
    field_label: str = ""
    concept: str | None = None
    suggested_value: Any = None
    confidence: float
    reason: str
    requires_confirmation: bool = False
    source: RecommendationSource | None = None
    candidates: list[RecommendationCandidate] = Field(default_factory=list)


class PendingReviewsResponseData(BaseModel):
    reviews: list[PendingReviewItem]


class ReviewDecisionRequest(BaseModel):
    decision: Literal["confirm", "edit", "reject", "skip"]
    value: str | None = Field(default=None, max_length=10000)
    save_for_future: bool = False


class ReviewDecisionResponseData(BaseModel):
    review_id: str
    decision: str
    status: str
