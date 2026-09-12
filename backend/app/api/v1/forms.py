"""Forms APIs (Classification, Sessions, Recommendations)."""

from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
import asyncio

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.forms import (
    ClassificationOutput,
    ClassifyFieldRequest,
    ClassifyFieldsRequest,
    ClassifyFieldsResponseData,
    RecommendRequest,
    RecommendResponseData,
    BatchRecommendRequest,
    BatchRecommendResponseData,
    SessionRecommendationsData,
    RecommendationOutput,
    RecommendationProvenance,
)
from app.schemas.form_sessions import (
    FormSessionCreate,
    FormSessionCreateData,
    FormSessionResponseData,
    FormSessionAnalyzeRequest,
    FormSessionAnalyzeData,
    FormSessionCompleteRequest,
    FormSessionCompleteData,
)
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Forms"])
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/forms/classify-field", response_model=SuccessResponse[ClassificationOutput])
async def classify_single_field(
    request: Request,
    body: ClassifyFieldRequest,
    user: User,
) -> SuccessResponse[ClassificationOutput]:
    classifier = request.app.state.semantic_classifier
    result = classifier.classify_field(body.field)
    return SuccessResponse(success=True, data=result)


@router.post("/forms/classify-fields", response_model=SuccessResponse[ClassifyFieldsResponseData])
async def classify_batch_fields(
    request: Request,
    body: ClassifyFieldsRequest,
    user: User,
) -> SuccessResponse[ClassifyFieldsResponseData]:
    classifier = request.app.state.semantic_classifier
    results = classifier.classify_fields(body.fields)
    return SuccessResponse(
        success=True, data=ClassifyFieldsResponseData(classifications=results)
    )


@router.post("/forms/sessions", response_model=SuccessResponse[FormSessionCreateData])
async def create_form_session(
    request: Request,
    body: FormSessionCreate,
    user: User,
) -> SuccessResponse[FormSessionCreateData]:
    repo = request.app.state.form_sessions_repo
    doc = await repo.create_session(
        user_id=user.user_id,
        website_origin=body.website_origin,
        page_url=body.page_url,
        form_id=body.form_id
    )
    return SuccessResponse(
        success=True,
        data=FormSessionCreateData(session_id=doc["_id"], status=doc["status"])
    )


@router.get("/forms/sessions/{session_id}", response_model=SuccessResponse[FormSessionResponseData])
async def get_form_session(
    session_id: str,
    request: Request,
    user: User,
) -> SuccessResponse[FormSessionResponseData]:
    repo = request.app.state.form_sessions_repo
    doc = await repo.get_session(user_id=user.user_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")
        
    return SuccessResponse(
        success=True,
        data=FormSessionResponseData(
            session_id=doc["_id"],
            website_origin=doc["website_origin"],
            form_id=doc["form_id"],
            status=doc["status"],
            total_fields=doc.get("total_fields", 0),
            filled_fields=doc.get("filled_fields", 0),
            reviewed_fields=doc.get("reviewed_fields", 0)
        )
    )


@router.post("/forms/sessions/{session_id}/analyze", response_model=SuccessResponse[FormSessionAnalyzeData])
async def analyze_form(
    session_id: str,
    body: FormSessionAnalyzeRequest,
    request: Request,
    user: User,
    background_tasks: BackgroundTasks,
) -> SuccessResponse[FormSessionAnalyzeData]:
    repo = request.app.state.form_sessions_repo
    doc = await repo.get_session(user_id=user.user_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")
        
    await repo.update_session(user.user_id, session_id, {"status": "processing", "total_fields": len(body.fields)})
    
    agent = request.app.state.agent_graph
    
    async def process_all_fields():
        async def process_field(field):
            try:
                workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
                await agent.run({
                    "workflow_id": workflow_id,
                    "user_id": user.user_id,
                    "session_id": session_id,
                    "current_field": field.model_dump(),
                    "field_objects": [f.model_dump() for f in body.fields],
                    "page_context": {"website_origin": doc.get("website_origin", ""), "page_url": doc.get("page_url", "")}
                })
            except Exception as e:
                import logging
                logging.error(f"Error analyzing field {field.field_id}: {e}")
        await asyncio.gather(*[process_field(f) for f in body.fields])
        
    background_tasks.add_task(process_all_fields)
    
    return SuccessResponse(
        success=True,
        data=FormSessionAnalyzeData(session_id=session_id, status="processing", field_count=len(body.fields)),
        message="Form analysis started"
    )


@router.post("/forms/sessions/{session_id}/complete", response_model=SuccessResponse[FormSessionCompleteData])
async def complete_form_session(
    session_id: str,
    body: FormSessionCompleteRequest,
    request: Request,
    user: User,
) -> SuccessResponse[FormSessionCompleteData]:
    repo = request.app.state.form_sessions_repo
    doc = await repo.get_session(user_id=user.user_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")
        
    success = await repo.complete_session(
        user.user_id, session_id,
        total_fields=body.total_fields,
        filled_fields=body.filled_fields,
        reviewed_fields=body.reviewed_fields,
        failed_fields=body.failed_fields,
        submission_status=body.submission_status
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete session")
        
    final_status = "completed" if body.submission_status == "user_submitted" else "cancelled"
    return SuccessResponse(
        success=True,
        data=FormSessionCompleteData(session_id=session_id, status=final_status)
    )


@router.post("/forms/recommend", response_model=SuccessResponse[RecommendResponseData])
async def recommend_single(
    request: Request,
    body: RecommendRequest,
    user: User,
) -> SuccessResponse[RecommendResponseData]:
    # A single field recommendation, essentially running the agent inline.
    agent = request.app.state.autofill_agent
    workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
    state = await agent.run({
        "workflow_id": workflow_id,
        "user_id": user.user_id,
        "session_id": body.session_id,
        "current_field": body.field.model_dump(),
        "field_objects": [body.field.model_dump()],
        "page_context": {}
    })
    
    # We fetch the created recommendation
    rec_repo = request.app.state.recommendations_repo
    docs = await rec_repo.collection.find({"session_id": body.session_id, "field_id": body.field.field_id}).sort("created_at", -1).to_list(1)
    
    if docs:
        doc = docs[0]
        rec = RecommendResponseData(
            recommendation_id=str(doc["_id"]),
            field_id=doc["field_id"],
            concept=doc.get("concept", ""),
            recommended_value=doc.get("recommended_value"),
            confidence=doc.get("confidence", 0.0),
            retrieval_type=doc.get("retrieval_type", "structured"),
            status=doc["status"],
            provenance=[]
        )
        return SuccessResponse(success=True, data=rec)
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not generated")


@router.post("/forms/recommendations", response_model=SuccessResponse[BatchRecommendResponseData])
async def recommend_batch(
    request: Request,
    body: BatchRecommendRequest,
    user: User,
) -> SuccessResponse[BatchRecommendResponseData]:
    agent = request.app.state.autofill_agent
    
    async def process_field(field):
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        await agent.run({
            "workflow_id": workflow_id,
            "user_id": user.user_id,
            "session_id": body.session_id,
            "current_field": field.model_dump(),
            "field_objects": [f.model_dump() for f in body.fields],
            "page_context": {}
        })
        
    await asyncio.gather(*[process_field(f) for f in body.fields])
    
    rec_repo = request.app.state.recommendations_repo
    field_ids = [f.field_id for f in body.fields]
    docs = await rec_repo.collection.find({"session_id": body.session_id, "field_id": {"$in": field_ids}}).to_list(None)
    
    recs = []
    for doc in docs:
        recs.append(RecommendationOutput(
            recommendation_id=str(doc["_id"]),
            field_id=doc["field_id"],
            concept=doc.get("concept", ""),
            recommended_value=doc.get("recommended_value"),
            confidence=doc.get("confidence", 0.0),
            retrieval_type=doc.get("retrieval_type", "structured"),
            status=doc["status"],
            provenance=[]
        ))
        
    return SuccessResponse(success=True, data=BatchRecommendResponseData(recommendations=recs))


@router.get("/forms/sessions/{session_id}/recommendations", response_model=SuccessResponse[SessionRecommendationsData])
async def get_session_recommendations(
    session_id: str,
    request: Request,
    user: User,
) -> SuccessResponse[SessionRecommendationsData]:
    rec_repo = request.app.state.recommendations_repo
    docs = await rec_repo.collection.find({"session_id": session_id, "user_id": user.user_id}).to_list(None)
    
    recs = []
    for doc in docs:
        recs.append(RecommendationOutput(
            recommendation_id=str(doc["_id"]),
            field_id=doc["field_id"],
            concept=doc.get("concept", ""),
            recommended_value=doc.get("recommended_value"),
            confidence=doc.get("confidence", 0.0),
            retrieval_type=doc.get("retrieval_type", "structured"),
            status=doc["status"],
            provenance=[]
        ))
        
    return SuccessResponse(success=True, data=SessionRecommendationsData(recommendations=recs))
