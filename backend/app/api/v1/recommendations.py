"""Recommendation endpoints (API_SPECIFICATION §36)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException, status

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.responses import SuccessResponse
from app.schemas.forms import RecommendationOutput

router = APIRouter(tags=["Recommendations"])
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/recommendations/{recommendation_id}", response_model=SuccessResponse[RecommendationOutput])
async def get_recommendation(
    recommendation_id: str,
    request: Request,
    user: User,
) -> SuccessResponse[RecommendationOutput]:
    repo = request.app.state.recommendations_repo
    doc = await repo.get_recommendation(user_id=user.user_id, rec_id=recommendation_id)
    
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
        
    rec = RecommendationOutput(
        recommendation_id=str(doc["_id"]),
        field_id=doc["field_id"],
        concept=doc.get("concept", ""),
        recommended_value=doc.get("recommended_value"),
        confidence=doc.get("confidence", 0.0),
        retrieval_type=doc.get("retrieval_type", "structured"),
        status=doc["status"],
        provenance=[]
    )
    return SuccessResponse(success=True, data=rec)
