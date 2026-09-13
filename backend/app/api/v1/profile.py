"""Profile API routes (GET /profile, PUT /profile, GET /profile/corrections)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.profile import (
    CorrectionsListData,
    ProfileData,
    ProfileUpdateRequest,
    ProfileUpdateResponse,
)
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Profile"])
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/profile", response_model=SuccessResponse[ProfileData])
async def get_profile(
    request: Request,
    user: User,
) -> SuccessResponse[ProfileData]:
    profile_service = request.app.state.profile_service
    profile_data = await profile_service.get(user.user_id)
    return SuccessResponse(success=True, data=profile_data)


@router.put("/profile", response_model=SuccessResponse[ProfileUpdateResponse])
async def update_profile(
    request: Request,
    body: ProfileUpdateRequest,
    user: User,
) -> SuccessResponse[ProfileUpdateResponse]:
    profile_service = request.app.state.profile_service
    result = await profile_service.update(user.user_id, body)
    return SuccessResponse(
        success=True,
        data=ProfileUpdateResponse(updated=result.get("updated", True)),
        message="Profile updated successfully",
    )


@router.get("/profile/corrections", response_model=SuccessResponse[CorrectionsListData])
async def get_profile_corrections(
    request: Request,
    user: User,
    concept: str | None = None,
) -> SuccessResponse[CorrectionsListData]:
    corrections_service = request.app.state.corrections_service
    corrections = await corrections_service.list_corrections(user.user_id, concept)
    return SuccessResponse(success=True, data=corrections)

@router.delete("/profile/data", response_model=SuccessResponse[dict])
async def delete_profile_data(
    request: Request,
    user: User,
) -> SuccessResponse[dict]:
    profile_service = request.app.state.profile_service
    await profile_service.delete_all_data(user.user_id)
    return SuccessResponse(success=True, data={"deleted": True}, message="Data deleted successfully")
