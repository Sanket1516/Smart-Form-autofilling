"""Structured fact endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.facts import FactData, FactsData, FactUpdateRequest
from app.schemas.responses import SuccessResponse
from app.services.facts import FactService

router = APIRouter(tags=["structured facts"])
User = Annotated[CurrentUser, Depends(get_current_user)]


def get_fact_service(request: Request) -> FactService:
    return request.app.state.fact_service


@router.get("/profile/facts", response_model=SuccessResponse[FactsData])
async def list_profile_facts(
    user: User,
    service: Annotated[FactService, Depends(get_fact_service)],
    concept: str | None = None,
    source_document_id: str | None = None,
    confirmed: bool | None = Query(default=None),
) -> SuccessResponse[FactsData]:
    return SuccessResponse(
        data=await service.list(user.user_id, concept, source_document_id, confirmed)
    )


@router.put("/profile/facts/{fact_id}", response_model=SuccessResponse[FactData])
async def update_profile_fact(
    fact_id: str,
    request: FactUpdateRequest,
    user: User,
    service: Annotated[FactService, Depends(get_fact_service)],
) -> SuccessResponse[FactData]:
    return SuccessResponse(
        data=await service.update(user.user_id, fact_id, request),
        message="Fact updated successfully",
    )
