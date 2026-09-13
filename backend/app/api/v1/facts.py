"""Structured and discovered fact endpoints, including HITL conflict resolution."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.facts import FactData, FactsData, FactUpdateRequest
from app.schemas.responses import SuccessResponse
from app.services.facts import FactService

router = APIRouter(tags=["structured facts"])
User = Annotated[CurrentUser, Depends(get_current_user)]


def get_fact_service(request: Request) -> FactService:
    return request.app.state.fact_service


def _get_discovered_facts_repo(request: Request):
    return getattr(request.app.state, "discovered_facts_repo", None)


def _get_discovered_conflicts_repo(request: Request):
    return getattr(request.app.state, "discovered_conflicts_repo", None)


# ---------------------------------------------------------------------------
# Existing structured facts endpoints (unchanged)
# ---------------------------------------------------------------------------

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


@router.delete("/profile/facts/{fact_id}", response_model=SuccessResponse[dict])
async def delete_profile_fact(
    fact_id: str,
    user: User,
    service: Annotated[FactService, Depends(get_fact_service)],
) -> SuccessResponse[dict]:
    await service.delete(user.user_id, fact_id)
    return SuccessResponse(
        data={"deleted": True},
        message="Fact deleted successfully",
    )

# ---------------------------------------------------------------------------
# NEW: Discovered facts endpoints (document-agnostic)
# ---------------------------------------------------------------------------

@router.get("/profile/discovered-facts")
async def list_discovered_facts(
    user: User,
    req: Request,
    semantic_type: str | None = None,
    document_id: str | None = None,
    ontology: str | None = None,
) -> dict[str, Any]:
    """List dynamically discovered facts for the authenticated user.

    Filter by semantic_type, document_id, or ontology concept.
    """
    repo = _get_discovered_facts_repo(req)
    if repo is None:
        raise HTTPException(status_code=503, detail="Discovered facts service unavailable")

    if document_id:
        facts = await repo.list_for_document(user.user_id, document_id)
    elif semantic_type:
        facts = await repo.find_by_semantic_type(user.user_id, semantic_type)
    elif ontology:
        facts = await repo.find_by_ontology(user.user_id, ontology)
    else:
        facts = await repo.list(user.user_id)

    # Serialize ObjectId to str
    serialized = []
    for f in facts:
        f = dict(f)
        f["id"] = str(f.pop("_id", ""))
        serialized.append(f)

    return {"data": serialized, "total": len(serialized)}


# ---------------------------------------------------------------------------
# NEW: HITL Conflict Resolution endpoints
# ---------------------------------------------------------------------------

class ConflictResolutionRequest(BaseModel):
    resolution: Literal["candidate_a", "candidate_b", "custom", "reject"]
    custom_value: Any = None   # Required when resolution == "custom"
    reason: str | None = None


@router.get("/profile/facts/conflicts")
async def list_fact_conflicts(
    user: User,
    req: Request,
) -> dict[str, Any]:
    """List all unresolved extraction conflicts for the authenticated user.

    Each conflict has two or more candidate values discovered from different
    documents (or within the same document) that could not be automatically
    reconciled.
    """
    repo = _get_discovered_conflicts_repo(req)
    if repo is None:
        raise HTTPException(status_code=503, detail="Conflict resolution service unavailable")

    conflicts = await repo.list_unresolved(user.user_id)
    serialized = []
    for c in conflicts:
        c = dict(c)
        c["id"] = str(c.pop("_id", ""))
        serialized.append(c)

    return {"data": serialized, "total": len(serialized)}


@router.patch("/profile/facts/conflicts/{conflict_id}/resolve")
async def resolve_fact_conflict(
    conflict_id: str,
    body: ConflictResolutionRequest,
    user: User,
    req: Request,
) -> dict[str, Any]:
    """Resolve a specific extraction conflict.

    The user selects one of the candidates or provides a custom value.
    The resolved value is stored with verification_status = VERIFIED.
    """
    conflicts_repo = _get_discovered_conflicts_repo(req)
    discovered_repo = _get_discovered_facts_repo(req)

    if conflicts_repo is None:
        raise HTTPException(status_code=503, detail="Conflict resolution service unavailable")

    # Determine the resolved value
    if body.resolution == "reject":
        resolved_value = None
    elif body.resolution == "custom":
        if body.custom_value is None:
            raise HTTPException(
                status_code=400,
                detail="custom_value is required when resolution is 'custom'"
            )
        resolved_value = body.custom_value
    else:
        # candidate_a or candidate_b — look up the conflict to find the value
        conflict = await conflicts_repo.collection.find_one(
            {"_id": __import__("bson").ObjectId(conflict_id), "user_id": user.user_id}
        )
        if not conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
        candidates = conflict.get("candidates", [])
        idx = 0 if body.resolution == "candidate_a" else 1
        if idx >= len(candidates):
            raise HTTPException(status_code=400, detail=f"Candidate index {idx} not found")
        resolved_value = candidates[idx].get("value")

    # Update the conflict record
    updated = await conflicts_repo.resolve(
        user.user_id,
        conflict_id,
        resolved_value,
        body.resolution,
        body.reason,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conflict not found")

    # Propagate resolution to the corresponding discovered_fact if we have the repo
    if discovered_repo is not None and body.resolution != "reject" and resolved_value is not None:
        semantic_type = updated.get("semantic_type")
        if semantic_type:
            from datetime import UTC, datetime
            from app.models.documents import DiscoveredFact

            # Find and update the discovered fact with VERIFIED status
            existing_facts = await discovered_repo.find_by_semantic_type(user.user_id, semantic_type)
            for ef in existing_facts:
                from bson import ObjectId
                await discovered_repo.collection.update_one(
                    {"_id": ef["_id"]},
                    {
                        "$set": {
                            "value": resolved_value,
                            "verification_status": "VERIFIED",
                            "conflict_status": "RESOLVED",
                            "updated_at": datetime.now(UTC),
                        }
                    },
                )

    updated["id"] = str(updated.pop("_id", ""))
    return {
        "data": updated,
        "message": f"Conflict resolved with resolution: {body.resolution}",
    }
