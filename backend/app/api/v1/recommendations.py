"""Single recommendation lookup."""

from fastapi import APIRouter, Request

from app.api.v1.auth import User
from app.core.api_errors import APIError
from app.schemas.form_sessions import RecommendationOutput
from app.schemas.responses import SuccessResponse
from app.services.form_filling import to_output

router = APIRouter(tags=["Recommendations"])


@router.get(
    "/recommendations/{recommendation_id}", response_model=SuccessResponse[RecommendationOutput]
)
async def get_recommendation(
    recommendation_id: str, request: Request, user: User
) -> SuccessResponse[RecommendationOutput]:
    doc = await request.app.state.recommendations_repo.get_recommendation(
        user.user_id, recommendation_id
    )
    if doc is None:
        raise APIError("RESOURCE_NOT_FOUND", "Recommendation not found", 404)
    return SuccessResponse(data=to_output(doc))
