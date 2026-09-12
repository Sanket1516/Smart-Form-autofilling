"""RAG Retrieval API router (API_SPECIFICATION section 30)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.responses import SuccessResponse
from app.schemas.retrieval import (
    RAGRetrievalData,
    RAGRetrievalRequest,
    StructuredRetrievalRequest,
    StructuredRetrievalData,
)
from app.services.retrieval import RAGRetrievalService
from app.services.facts import FactService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])
User = Annotated[CurrentUser, Depends(get_current_user)]


def get_retrieval_service(request: Request) -> RAGRetrievalService:
    return request.app.state.retrieval_service

def get_fact_service(request: Request) -> FactService:
    return request.app.state.fact_service

Service = Annotated[RAGRetrievalService, Depends(get_retrieval_service)]
FactSvc = Annotated[FactService, Depends(get_fact_service)]


@router.post("/rag", response_model=SuccessResponse[RAGRetrievalData])
async def search_rag(
    request_data: RAGRetrievalRequest, user: User, service: Service
) -> SuccessResponse[RAGRetrievalData]:
    results = await service.search(user.user_id, request_data)
    return SuccessResponse(data=results)

@router.post("/structured", response_model=SuccessResponse[StructuredRetrievalData])
async def search_structured(
    request_data: StructuredRetrievalRequest, user: User, fact_service: FactSvc
) -> SuccessResponse[StructuredRetrievalData]:
    """Retrieve structured candidate facts for a specific ontology concept."""
    # List facts matching user and concept
    confirmed = True if request_data.verified_only else None
    facts_data = await fact_service.list(
        user_id=user.user_id,
        concept=request_data.concept,
        confirmed=confirmed,
    )
    return SuccessResponse(data=StructuredRetrievalData(results=facts_data.facts))
