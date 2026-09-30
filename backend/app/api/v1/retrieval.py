"""RAG Retrieval API router (API_SPECIFICATION section 30)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.responses import SuccessResponse
from app.schemas.retrieval import (
    RAGAnswerData,
    RAGAnswerRequest,
    RAGAnswerSource,
    RAGRetrievalData,
    RAGRetrievalRequest,
    StructuredRetrievalRequest,
    StructuredRetrievalData,
)
from app.services.retrieval import RAGRetrievalService
from app.services.facts import FactService
from app.agents.prompts import EVIDENCE_INSUFFICIENT, build_rag_answer_prompt
import json
import logging

logger = logging.getLogger(__name__)

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


@router.post("/rag/answer", response_model=SuccessResponse[RAGAnswerData])
async def answer_from_rag(
    request_data: RAGAnswerRequest,
    request: Request,
    user: User,
    service: Service,
) -> SuccessResponse[RAGAnswerData]:
    """Answer a personal-history question from the authenticated user's evidence."""
    query = f"{request_data.question} personal profile experience education projects achievements"
    retrieved = await service.search(
        user.user_id,
        RAGRetrievalRequest(query=query, top_k=request_data.top_k),
    )
    chunks = [result.model_dump() for result in retrieved.results]
    prompt = build_rag_answer_prompt(request_data.question, chunks)
    if prompt == EVIDENCE_INSUFFICIENT:
        return SuccessResponse(
            data=RAGAnswerData(answer="", confidence=0.0, sources=[]),
            message="No matching personal evidence was found",
        )

    try:
        raw = request.app.state.llm_provider.complete(prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        answer = str(parsed.get("answer") or "")[:10000]
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.0))))
    except Exception:
        logger.warning("rag_answer_generation_failed")
        answer, confidence = "", 0.0

    sources = [
        RAGAnswerSource(
            document_id=result.metadata.document_id,
            page_number=result.metadata.page_number,
            similarity=result.similarity,
        )
        for result in retrieved.results
    ]
    return SuccessResponse(
        data=RAGAnswerData(answer=answer, confidence=confidence, sources=sources),
        message="Answer generated from retrieved user evidence" if answer else "Evidence was insufficient",
    )

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
