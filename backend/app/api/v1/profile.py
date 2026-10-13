"""Profile, saved answers ("memories"), corrections and data deletion."""

from fastapi import APIRouter, Request

from app.api.v1.auth import User
from app.core.api_errors import APIError
from app.schemas.profile import (
    CorrectionsListData,
    ProfileData,
    ProfileUpdateRequest,
    ProfileUpdateResponse,
    UserMemoriesData,
    UserMemoryCreateRequest,
    UserMemoryData,
)
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Profile"])


@router.get("/profile", response_model=SuccessResponse[ProfileData])
async def get_profile(request: Request, user: User) -> SuccessResponse[ProfileData]:
    return SuccessResponse(data=await request.app.state.profile_service.get(user.user_id))


@router.put("/profile", response_model=SuccessResponse[ProfileUpdateResponse])
async def update_profile(
    request: Request, body: ProfileUpdateRequest, user: User
) -> SuccessResponse[ProfileUpdateResponse]:
    result = await request.app.state.profile_service.update(user.user_id, body)
    return SuccessResponse(data=ProfileUpdateResponse(**result), message="Profile updated")


@router.get("/profile/concepts", response_model=SuccessResponse[list[dict]])
async def list_profile_concepts(request: Request, user: User) -> SuccessResponse[list[dict]]:
    """The ontology concepts a profile value can be stored under (for editors)."""
    ontology = request.app.state.field_ontology
    concepts = [
        {
            "concept": key,
            "description": ontology.description(key),
            "data_type": ontology.data_type(key),
            "sensitive": ontology.is_sensitive(key),
            "single_valued": ontology.is_single_valued(key),
        }
        for key, _ in ontology.catalog()
    ]
    return SuccessResponse(data=concepts)


@router.get("/profile/corrections", response_model=SuccessResponse[CorrectionsListData])
async def get_profile_corrections(
    request: Request, user: User, concept: str | None = None
) -> SuccessResponse[CorrectionsListData]:
    return SuccessResponse(
        data=await request.app.state.corrections_service.list_corrections(user.user_id, concept)
    )


@router.delete("/profile/data", response_model=SuccessResponse[dict])
async def delete_profile_data(request: Request, user: User) -> SuccessResponse[dict]:
    """Delete all documents, facts, vectors, sessions and saved answers; keep the account."""
    deleted = await request.app.state.user_data_service.delete_all(user.user_id)
    return SuccessResponse(data={"deleted": deleted}, message="All your data was deleted")


@router.get("/profile/memories", response_model=SuccessResponse[UserMemoriesData])
async def list_profile_memories(request: Request, user: User) -> SuccessResponse[UserMemoriesData]:
    memories = await request.app.state.user_memory_service.list(user.user_id)
    return SuccessResponse(data=UserMemoriesData(memories=memories))


@router.post("/profile/memories", response_model=SuccessResponse[UserMemoryData], status_code=201)
async def save_profile_memory(
    body: UserMemoryCreateRequest, request: Request, user: User
) -> SuccessResponse[UserMemoryData]:
    """Save an answer only after an explicit user action.

    Answers to known profile concepts become confirmed profile facts; anything
    else is kept as a searchable saved answer.
    """
    ontology = request.app.state.field_ontology
    if ontology.is_known(body.concept) and ontology.is_fillable(body.concept):
        fact = await request.app.state.fact_service.add_user_fact(
            user.user_id, body.concept, body.value
        )
        data = UserMemoryData(
            memory_id=fact.fact_id,
            label=body.label,
            concept=body.concept,
            value=str(fact.value),
            indexed=False,
            created_at=fact.created_at,
            updated_at=fact.updated_at,
        )
        return SuccessResponse(data=data, message="Saved to your profile")
    memory = await request.app.state.user_memory_service.save(
        user.user_id, body.label, body.concept, body.value
    )
    return SuccessResponse(data=UserMemoryData(**memory), message="Saved for future forms")


@router.delete("/profile/memories/{memory_id}", response_model=SuccessResponse[dict])
async def delete_profile_memory(
    memory_id: str, request: Request, user: User
) -> SuccessResponse[dict]:
    if not await request.app.state.user_memory_service.delete(user.user_id, memory_id):
        raise APIError("RESOURCE_NOT_FOUND", "Saved answer not found", 404)
    return SuccessResponse(data={"deleted": True})
