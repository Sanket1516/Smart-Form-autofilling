"""Review and Human-in-the-Loop endpoints (API_SPECIFICATION §34-35)."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Annotated
from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser

from app.schemas.reviews import (
    PendingReviewItem,
    PendingReviewsResponse,
    PendingReviewsResponseData,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewDecisionResponseData,
    ReviewSource,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reviews"])
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.get(
    "/reviews/pending",
    response_model=PendingReviewsResponse,
    summary="Get Pending Reviews"
)
async def get_pending_reviews(request: Request, user: User):
    user_id = user.user_id
    repo = request.app.state.recommendations_repo
    
    docs = await repo.get_pending_reviews(user_id)
    reviews = []
    for doc in docs:
        reviews.append(
            PendingReviewItem(
                review_id=doc["_id"],
                session_id=doc.get("session_id", ""),
                field_id=doc.get("field_id", ""),
                concept=doc.get("concept", ""),
                suggested_value=doc.get("recommended_value", ""),
                confidence=doc.get("confidence", 0.0),
                reason=doc.get("reason", ""),
                sources=[ReviewSource(document_id=sid) for sid in doc.get("source_fact_ids", [])]
            )
        )
        
    return PendingReviewsResponse(
        success=True,
        data=PendingReviewsResponseData(reviews=reviews)
    )


@router.post(
    "/reviews/{review_id}/decision",
    response_model=ReviewDecisionResponse,
    summary="Submit Human Review Decision"
)
async def submit_decision(review_id: str, payload: ReviewDecisionRequest, request: Request, user: User):
    user_id = user.user_id
    repo = request.app.state.recommendations_repo
    
    # 1. Fetch recommendation
    rec = await repo.get_recommendation(user_id, review_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
        
    if rec["status"] != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Review is already {rec['status']}"
        )

    # 2. Map decision to status
    decision = payload.decision
    final_status = "completed"
    if decision == "confirm":
        rec_status = "approved"
    elif decision == "edit":
        if not payload.value:
            raise HTTPException(status_code=400, detail="Value required for edit decision")
        rec_status = "edited"
    elif decision == "reject":
        rec_status = "rejected"
    elif decision == "skip":
        rec_status = "skipped"
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")
        
    # 3. Update Recommendation
    new_value = payload.value if decision == "edit" else None
    await repo.update_status(user_id, review_id, rec_status, new_value)
    
    # 4. If confirmed/edited, update profile explicitly (SRS §19.3)
    if decision in ("confirm", "edit"):
        value_to_save = new_value if decision == "edit" else rec.get("recommended_value")
        concept = rec.get("concept")
        if value_to_save and concept:
            try:
                fact_service = getattr(request.app.state, "fact_service", None)
                if fact_service and hasattr(fact_service, "repository"):
                    from datetime import datetime, UTC
                    from app.models.documents import StructuredFact
                    source_ids = rec.get("source_fact_ids", [])
                    source_doc = str(source_ids[0]) if source_ids else "hitl_override"
                    fact_doc = StructuredFact(
                        user_id=user_id,
                        concept=concept,
                        value=value_to_save,
                        value_type=type(value_to_save).__name__,
                        source_document_id=source_doc,
                        source_page=1,
                        confidence=1.0,
                        provenance={"source": "hitl_review", "decision": decision, "review_id": review_id},
                        is_user_confirmed=True,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    await fact_service.repository.create(user_id, fact_doc)
            except Exception as e:
                logger.warning(f"Failed to update profile from HITL decision: {e}")

    return ReviewDecisionResponse(
        success=True,
        data=ReviewDecisionResponseData(
            review_id=review_id,
            decision=decision,
            status=final_status
        )
    )
