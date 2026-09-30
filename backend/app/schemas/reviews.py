from pydantic import BaseModel, Field
from typing import Any


class ReviewSource(BaseModel):
    document_id: str


class PendingReviewItem(BaseModel):
    review_id: str
    session_id: str
    field_id: str
    concept: str
    suggested_value: str
    confidence: float
    reason: str
    sources: list[ReviewSource]


class PendingReviewsResponseData(BaseModel):
    reviews: list[PendingReviewItem]


class PendingReviewsResponse(BaseModel):
    success: bool = True
    data: PendingReviewsResponseData


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(confirm|edit|reject|skip)$")
    value: str | None = None
    save_for_future: bool = False


class ReviewDecisionResponseData(BaseModel):
    review_id: str
    decision: str
    status: str


class ReviewDecisionResponse(BaseModel):
    success: bool = True
    data: ReviewDecisionResponseData
