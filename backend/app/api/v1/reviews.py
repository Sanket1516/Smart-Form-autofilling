"""Pending review queue across all form sessions (used by the dashboard)."""

from fastapi import APIRouter, Request

from app.api.v1.auth import User
from app.core.api_errors import APIError
from app.schemas.form_sessions import FieldDecision
from app.schemas.responses import SuccessResponse
from app.schemas.reviews import (
    PendingReviewItem,
    PendingReviewsResponseData,
    ReviewDecisionRequest,
    ReviewDecisionResponseData,
)

router = APIRouter(tags=["Reviews"])

_DECISIONS = {"confirm": "approve", "edit": "edit", "reject": "reject", "skip": "skip"}


@router.get("/reviews/pending", response_model=SuccessResponse[PendingReviewsResponseData])
async def get_pending_reviews(
    request: Request, user: User, session_id: str | None = None
) -> SuccessResponse[PendingReviewsResponseData]:
    docs = await request.app.state.recommendations_repo.get_pending_reviews(
        user.user_id, session_id
    )
    reviews = [
        PendingReviewItem(
            review_id=str(doc["_id"]),
            session_id=doc.get("session_id", ""),
            field_id=doc.get("field_id", ""),
            field_label=doc.get("field_label", ""),
            concept=doc.get("concept"),
            suggested_value=doc.get("recommended_value"),
            confidence=float(doc.get("confidence", 0.0)),
            reason=doc.get("reason", ""),
            requires_confirmation=bool(doc.get("requires_confirmation", False)),
            source=doc.get("source") or None,
            candidates=doc.get("candidates", []),
        )
        for doc in docs
    ]
    return SuccessResponse(data=PendingReviewsResponseData(reviews=reviews))


@router.post(
    "/reviews/{review_id}/decision", response_model=SuccessResponse[ReviewDecisionResponseData]
)
async def submit_decision(
    review_id: str, payload: ReviewDecisionRequest, request: Request, user: User
) -> SuccessResponse[ReviewDecisionResponseData]:
    record = await request.app.state.recommendations_repo.get_recommendation(
        user.user_id, review_id
    )
    if record is None:
        raise APIError("RESOURCE_NOT_FOUND", "Review not found", 404)
    if record["status"] != "needs_review":
        raise APIError("ALREADY_DECIDED", f"This review is already {record['status']}", 409)
    service = request.app.state.form_fill_service
    await service.apply_decision(
        user.user_id,
        record,
        FieldDecision(
            field_id=record["field_id"],
            decision=_DECISIONS[payload.decision],
            value=payload.value,
            save_for_future=payload.save_for_future,
        ),
    )
    status = await service.refresh_status(user.user_id, record["session_id"])
    return SuccessResponse(
        data=ReviewDecisionResponseData(
            review_id=review_id, decision=payload.decision, status=status
        )
    )
