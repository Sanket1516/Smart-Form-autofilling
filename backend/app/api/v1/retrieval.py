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


_ANSWER_MESSAGES = {
    "answered": "Answer built from your documents",
    "partial": "Partial answer: some information is missing, conflicting or needs review",
    "insufficient_evidence": "Your documents do not contain enough information to answer this",
    "no_documents": "Upload documents before asking questions",
    "documents_not_ready": "Your documents are still processing or failed processing",
}


@router.post("/rag/answer", response_model=SuccessResponse[RAGAnswerData])
@limiter.limit("20/minute")
async def answer_from_rag(
    request: Request, body: RAGAnswerRequest, user: User
) -> SuccessResponse[RAGAnswerData]:
    """Ask Documents: answer from the caller's own processed documents, with sources.

    Exact values come from stored facts; text passages from metadata-filtered
    retrieval; the model only writes the answer from cited evidence. When the model
    is unavailable the response still lists the facts and passages found
    (``answer_mode=evidence_only``) instead of failing.
    """
    data = await request.app.state.document_qa_service.answer(user.user_id, body)
    return SuccessResponse(data=data, message=_ANSWER_MESSAGES.get(data.status, ""))


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
