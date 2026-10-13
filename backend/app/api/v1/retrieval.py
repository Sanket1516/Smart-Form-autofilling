"""RAG retrieval and grounded answers over the user's own documents."""

from fastapi import APIRouter, Request

from app.api.v1.auth import User
from app.core.rate_limit import limiter
from app.schemas.responses import SuccessResponse
from app.schemas.retrieval import (
    RAGAnswerData,
    RAGAnswerRequest,
    RAGRetrievalData,
    RAGRetrievalRequest,
    StructuredRetrievalData,
    StructuredRetrievalRequest,
)

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/rag", response_model=SuccessResponse[RAGRetrievalData])
@limiter.limit("30/minute")
async def search_rag(
    request: Request, body: RAGRetrievalRequest, user: User
) -> SuccessResponse[RAGRetrievalData]:
    service = request.app.state.retrieval_service
    results = await service.search(
        user.user_id,
        body.query,
        body.top_k,
        document_type=body.filters.document_type if body.filters else None,
    )
    return SuccessResponse(
        data=RAGRetrievalData(results=results, min_similarity=service.min_similarity)
    )


@router.post("/rag/answer", response_model=SuccessResponse[RAGAnswerData])
@limiter.limit("20/minute")
async def answer_from_rag(
    request: Request, body: RAGAnswerRequest, user: User
) -> SuccessResponse[RAGAnswerData]:
    data = await request.app.state.rag_answer_service.answer(
        user.user_id, body.question, body.top_k
    )
    message = (
        "Answer generated from your documents"
        if data.status == "answered"
        else ("Your documents do not contain enough information to answer this")
    )
    return SuccessResponse(data=data, message=message)


@router.post("/structured", response_model=SuccessResponse[StructuredRetrievalData])
async def search_structured(
    request: Request, body: StructuredRetrievalRequest, user: User
) -> SuccessResponse[StructuredRetrievalData]:
    facts = await request.app.state.fact_service.list(
        user.user_id, concept=body.concept, confirmed=True if body.verified_only else None
    )
    return SuccessResponse(
        data=StructuredRetrievalData(results=[f.model_dump() for f in facts.facts])
    )
