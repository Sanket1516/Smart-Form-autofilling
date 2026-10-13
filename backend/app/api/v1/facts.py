"""Structured facts, discovered facts and conflict resolution endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.auth import User
from app.schemas.facts import (
    ConceptView,
    ConflictData,
    ConflictResolutionRequest,
    FactCreateRequest,
    FactData,
    FactsData,
    FactUpdateRequest,
)
from app.schemas.responses import SuccessResponse
from app.services.facts import FactService

router = APIRouter(tags=["structured facts"])


def get_fact_service(request: Request) -> FactService:
    return request.app.state.fact_service


Facts = Annotated[FactService, Depends(get_fact_service)]


@router.get("/profile/facts", response_model=SuccessResponse[FactsData])
async def list_profile_facts(
    user: User,
    service: Facts,
    concept: Annotated[str | None, Query(max_length=160)] = None,
    source_document_id: Annotated[str | None, Query(max_length=100)] = None,
    confirmed: bool | None = None,
) -> SuccessResponse[FactsData]:
    return SuccessResponse(
        data=await service.list(user.user_id, concept, source_document_id, confirmed)
    )


@router.post("/profile/facts", response_model=SuccessResponse[FactData], status_code=201)
async def add_profile_fact(
    user: User, service: Facts, body: FactCreateRequest
) -> SuccessResponse[FactData]:
    return SuccessResponse(
        data=await service.add_user_fact(user.user_id, body.concept, body.value),
        message="Fact saved",
    )


@router.put("/profile/facts/{fact_id}", response_model=SuccessResponse[FactData])
async def update_profile_fact(
    fact_id: str, body: FactUpdateRequest, user: User, service: Facts
) -> SuccessResponse[FactData]:
    return SuccessResponse(
        data=await service.update(user.user_id, fact_id, body), message="Fact updated"
    )


@router.delete("/profile/facts/{fact_id}", response_model=SuccessResponse[dict])
async def delete_profile_fact(fact_id: str, user: User, service: Facts) -> SuccessResponse[dict]:
    await service.delete(user.user_id, fact_id)
    return SuccessResponse(data={"deleted": True}, message="Fact removed")


@router.get("/profile/facts/conflicts", response_model=SuccessResponse[list[ConflictData]])
async def list_fact_conflicts(user: User, service: Facts) -> SuccessResponse[list[ConflictData]]:
    return SuccessResponse(data=await service.list_conflicts(user.user_id))


@router.patch(
    "/profile/facts/conflicts/{conflict_id}/resolve",
    response_model=SuccessResponse[ConceptView | None],
)
async def resolve_fact_conflict(
    conflict_id: str, body: ConflictResolutionRequest, user: User, service: Facts
) -> SuccessResponse[ConceptView | None]:
    view = await service.resolve_conflict(user.user_id, conflict_id, body)
    return SuccessResponse(data=view, message="Conflict resolved")


@router.get("/profile/discovered-facts", response_model=SuccessResponse[list[dict[str, Any]]])
async def list_discovered_facts(
    user: User,
    request: Request,
    semantic_type: Annotated[str | None, Query(max_length=120)] = None,
    document_id: Annotated[str | None, Query(max_length=100)] = None,
    ontology: Annotated[str | None, Query(max_length=160)] = None,
) -> SuccessResponse[list[dict[str, Any]]]:
    """Everything the extractors found in the user's documents, including unmapped data."""
    records = await request.app.state.discovered_facts_repo.list_filtered(
        user.user_id, document_id, semantic_type, ontology
    )
    items = []
    for record in records:
        record = dict(record)
        record["id"] = str(record.pop("_id"))
        record.pop("user_id", None)
        items.append(record)
    return SuccessResponse(data=items)
