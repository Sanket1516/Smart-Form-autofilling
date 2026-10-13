"""Form sessions: field analysis, recommendations, review decisions and fill results."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field

from app.api.v1.auth import User
from app.core.rate_limit import limiter
from app.schemas.form_sessions import (
    ApprovedValuesResponseData,
    AskMeAnswersData,
    AskMeAnswersRequest,
    FieldDecision,
    FieldDecisionsRequest,
    FieldObject,
    FormSessionAnalyzeData,
    FormSessionAnalyzeRequest,
    FormSessionCompleteData,
    FormSessionCompleteRequest,
    FormSessionCreate,
    FormSessionCreateData,
    FormSessionListData,
    FormSessionResponseData,
    FormSessionVerifyData,
    FormSessionVerifyRequest,
    RecommendationOutput,
    SessionRecommendationsData,
)
from app.schemas.responses import SuccessResponse
from app.services.form_filling import FormFillService, to_output

router = APIRouter(tags=["Forms"])


def get_form_service(request: Request) -> FormFillService:
    return request.app.state.form_fill_service


Forms = Annotated[FormFillService, Depends(get_form_service)]


# ---------------------------------------------------------------------- classification


class ClassifyFieldRequest(BaseModel):
    field: FieldObject


class ClassifyFieldsRequest(BaseModel):
    fields: list[FieldObject] = Field(min_length=1, max_length=300)


class ClassificationData(BaseModel):
    field_id: str
    concept: str | None
    confidence: float
    method: str
    narrative: bool
    error: str | None = None


async def _classify(request: Request, fields: list[FieldObject]) -> list[ClassificationData]:
    classifier = request.app.state.field_classifier
    prior = {f.field_id: classifier.classify_deterministic(f) for f in fields}
    unresolved = [f for f in fields if not classifier.is_resolved(prior[f.field_id])]
    results = await classifier.classify_with_llm(unresolved, prior) if unresolved else {}
    merged = {**prior, **results}
    return [
        ClassificationData(
            field_id=f.field_id,
            concept=merged[f.field_id].concept,
            confidence=merged[f.field_id].confidence,
            method=merged[f.field_id].method,
            narrative=merged[f.field_id].narrative,
            error=merged[f.field_id].error,
        )
        for f in fields
    ]


@router.post("/forms/classify-field", response_model=SuccessResponse[ClassificationData])
@limiter.limit("60/minute")
async def classify_single_field(
    request: Request, body: ClassifyFieldRequest, user: User
) -> SuccessResponse[ClassificationData]:
    return SuccessResponse(data=(await _classify(request, [body.field]))[0])


@router.post("/forms/classify-fields", response_model=SuccessResponse[list[ClassificationData]])
@limiter.limit("30/minute")
async def classify_batch_fields(
    request: Request, body: ClassifyFieldsRequest, user: User
) -> SuccessResponse[list[ClassificationData]]:
    return SuccessResponse(data=await _classify(request, body.fields))


# ---------------------------------------------------------------------- sessions


@router.post(
    "/forms/sessions", response_model=SuccessResponse[FormSessionCreateData], status_code=201
)
async def create_form_session(
    request: Request, body: FormSessionCreate, user: User
) -> SuccessResponse[FormSessionCreateData]:
    doc = await request.app.state.form_sessions_repo.create_session(
        user.user_id, body.website_origin, body.page_url, body.form_id
    )
    return SuccessResponse(data=FormSessionCreateData(session_id=doc["_id"], status=doc["status"]))


@router.get("/forms/sessions", response_model=SuccessResponse[FormSessionListData])
async def list_form_sessions(
    request: Request, user: User, service: Forms
) -> SuccessResponse[FormSessionListData]:
    sessions = await request.app.state.form_sessions_repo.list_sessions(user.user_id)
    return SuccessResponse(
        data=FormSessionListData(
            sessions=[await service.session_data(user.user_id, s) for s in sessions]
        )
    )


@router.get("/forms/sessions/{session_id}", response_model=SuccessResponse[FormSessionResponseData])
async def get_form_session(
    session_id: str, user: User, service: Forms
) -> SuccessResponse[FormSessionResponseData]:
    session = await service.require_session(user.user_id, session_id)
    return SuccessResponse(data=await service.session_data(user.user_id, session))


@router.post(
    "/forms/sessions/{session_id}/analyze",
    response_model=SuccessResponse[FormSessionAnalyzeData],
    status_code=202,
)
@limiter.limit("20/minute")
async def analyze_form(
    request: Request,
    session_id: str,
    body: FormSessionAnalyzeRequest,
    user: User,
    service: Forms,
    background_tasks: BackgroundTasks,
) -> SuccessResponse[FormSessionAnalyzeData]:
    await service.require_session(user.user_id, session_id)
    await request.app.state.form_sessions_repo.update_session(
        user.user_id,
        session_id,
        {"status": "processing", "total_fields": len(body.fields), "error": None},
    )
    background_tasks.add_task(service.analyze, user.user_id, session_id, body.fields)
    return SuccessResponse(
        data=FormSessionAnalyzeData(
            session_id=session_id, status="processing", field_count=len(body.fields)
        ),
        message="Form analysis started",
    )


@router.get(
    "/forms/sessions/{session_id}/recommendations",
    response_model=SuccessResponse[SessionRecommendationsData],
)
async def get_session_recommendations(
    session_id: str, user: User, service: Forms
) -> SuccessResponse[SessionRecommendationsData]:
    session = await service.require_session(user.user_id, session_id)
    return SuccessResponse(
        data=SessionRecommendationsData(
            session_id=session_id,
            status=session.get("status", "started"),
            recommendations=await service.recommendations_for(user.user_id, session_id),
        )
    )


@router.post(
    "/forms/sessions/{session_id}/decisions",
    response_model=SuccessResponse[SessionRecommendationsData],
)
async def submit_decisions(
    session_id: str, body: FieldDecisionsRequest, user: User, service: Forms
) -> SuccessResponse[SessionRecommendationsData]:
    """Approve, edit, reject or skip recommendations before anything is filled."""
    status, _ = await service.apply_decisions(user.user_id, session_id, body.decisions)
    return SuccessResponse(
        data=SessionRecommendationsData(
            session_id=session_id,
            status=status,
            recommendations=await service.recommendations_for(user.user_id, session_id),
        )
    )


@router.post(
    "/forms/sessions/{session_id}/answers", response_model=SuccessResponse[AskMeAnswersData]
)
async def submit_ask_me_answers(
    session_id: str, body: AskMeAnswersRequest, user: User, service: Forms
) -> SuccessResponse[AskMeAnswersData]:
    """Answers typed for missing fields; saved long-term only with explicit opt-in."""
    decisions = [
        FieldDecision(
            field_id=a.field_id, decision="edit", value=a.value, save_for_future=a.save_for_future
        )
        for a in body.answers
    ]
    status, saved = await service.apply_decisions(user.user_id, session_id, decisions)
    return SuccessResponse(
        data=AskMeAnswersData(session_id=session_id, status=status, saved_count=saved)
    )


@router.get(
    "/forms/sessions/{session_id}/approved-values",
    response_model=SuccessResponse[ApprovedValuesResponseData],
)
async def get_session_approved_values(
    session_id: str, user: User, service: Forms
) -> SuccessResponse[ApprovedValuesResponseData]:
    return SuccessResponse(
        data=ApprovedValuesResponseData(
            session_id=session_id,
            approved_values=await service.approved_values(user.user_id, session_id),
        )
    )


@router.post(
    "/forms/sessions/{session_id}/verify", response_model=SuccessResponse[FormSessionVerifyData]
)
async def verify_filled_values(
    session_id: str, body: FormSessionVerifyRequest, user: User, service: Forms
) -> SuccessResponse[FormSessionVerifyData]:
    """Record what the extension actually filled and verified on the page."""
    counts = await service.record_fill_results(user.user_id, session_id, body.results)
    return SuccessResponse(
        data=FormSessionVerifyData(session_id=session_id, status="filled", **counts)
    )


@router.post(
    "/forms/sessions/{session_id}/complete", response_model=SuccessResponse[FormSessionCompleteData]
)
async def complete_form_session(
    request: Request, session_id: str, body: FormSessionCompleteRequest, user: User, service: Forms
) -> SuccessResponse[FormSessionCompleteData]:
    session = await service.require_session(user.user_id, session_id)
    counts = {
        "filled_fields": session.get("filled_fields", 0),
        "failed_fields": session.get("failed_fields", 0),
    }
    await request.app.state.form_sessions_repo.complete_session(
        user.user_id, session_id, body.submission_status, counts
    )
    status = "completed" if body.submission_status == "user_submitted" else "closed"
    return SuccessResponse(data=FormSessionCompleteData(session_id=session_id, status=status))


# ---------------------------------------------------------------------- synchronous recommendations


class RecommendRequest(BaseModel):
    session_id: str
    field: FieldObject


class BatchRecommendRequest(BaseModel):
    session_id: str
    fields: list[FieldObject] = Field(min_length=1, max_length=300)


async def _recommend(
    request: Request,
    user_id: str,
    session_id: str,
    fields: list[FieldObject],
    service: FormFillService,
) -> list[RecommendationOutput]:
    await service.require_session(user_id, session_id)
    items: list[dict[str, Any]] = await request.app.state.form_fill_graph.run(
        user_id, session_id, fields
    )
    await service.refresh_status(user_id, session_id)
    return [to_output({**item, "_id": item.get("recommendation_id", "")}) for item in items]


@router.post("/forms/recommend", response_model=SuccessResponse[RecommendationOutput])
@limiter.limit("30/minute")
async def recommend_single(
    request: Request, body: RecommendRequest, user: User, service: Forms
) -> SuccessResponse[RecommendationOutput]:
    results = await _recommend(request, user.user_id, body.session_id, [body.field], service)
    return SuccessResponse(data=results[0])


@router.post("/forms/recommendations", response_model=SuccessResponse[list[RecommendationOutput]])
@limiter.limit("20/minute")
async def recommend_batch(
    request: Request, body: BatchRecommendRequest, user: User, service: Forms
) -> SuccessResponse[list[RecommendationOutput]]:
    return SuccessResponse(
        data=await _recommend(request, user.user_id, body.session_id, body.fields, service)
    )
