"""User Corrections API route (POST /corrections)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.profile import CorrectionCreateRequest, CorrectionData
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Corrections"])
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/corrections", response_model=SuccessResponse[CorrectionData])
async def create_correction(
    request: Request,
    body: CorrectionCreateRequest,
    user: User,
) -> SuccessResponse[CorrectionData]:
    corrections_service = request.app.state.corrections_service
    record = await corrections_service.record_correction(user.user_id, body)
    return SuccessResponse(success=True, data=record, message="Correction recorded successfully")
