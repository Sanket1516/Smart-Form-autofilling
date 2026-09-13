"""Forms APIs (Classification, Sessions, Recommendations)."""

from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
import asyncio
import json

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
from app.schemas.retrieval import RAGRetrievalRequest
from app.agents.prompts import build_bulk_fill_prompt
from app.schemas.form_sessions import (
    FormSessionCreate,
    FormSessionCreateData,
    FormSessionResponseData,
    FormSessionAnalyzeRequest,
    FormSessionAnalyzeData,
    FormSessionCompleteRequest,
    FormSessionCompleteData,
    ApprovedValueData,
    ApprovedValuesResponseData,
    FormSessionVerifyRequest,
    FormSessionVerifyData,
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
        import logging
        from datetime import datetime, UTC
        logger = logging.getLogger(__name__)
        try:
            # 1. Fetch all user data
            fact_service = request.app.state.fact_service
            discovered_repo = request.app.state.discovered_facts_repo
            
            structured_facts_resp = await fact_service.list(user_id=user.user_id)
            structured_facts = structured_facts_resp.facts
            
            discovered_facts = []
            if discovered_repo:
                discovered_facts = await discovered_repo.list(user_id=user.user_id)
            
            # 2. Format facts for the prompt
            all_facts = []
            for f in structured_facts:
                d = f.model_dump()
                d["source"] = "structured_facts"
                all_facts.append(d)
            for f in discovered_facts:
                all_facts.append({
                    "concept": f.get("ontology") or f.get("semantic_type"),
                    "value": f.get("value"),
                    "confidence": f.get("confidence", 0.5),
                    "source": "discovered_facts"
                })
                
            # 2.5 Fetch RAG Evidence
            retrieval_service = request.app.state.retrieval_service
            rag_chunks_deduped = {}
            if retrieval_service:
                for field in body.fields:
                    query = f"{field.label or ''} {field.placeholder or ''} {field.name or ''}".strip()
                    if query:
                        try:
                            rag_req = RAGRetrievalRequest(query=query, top_k=2)
                            rag_res = await retrieval_service.search(user_id=user.user_id, request=rag_req)
                            for r in rag_res.results:
                                txt = r.text.strip()
                                if txt and txt not in rag_chunks_deduped:
                                    rag_chunks_deduped[txt] = {
                                        "text": txt,
                                        "similarity": r.similarity,
                                        "document_id": r.metadata.document_id,
                                        "page": r.metadata.page_number
                                    }
                        except Exception as e:
                            logger.error(f"RAG search error for field {field.field_id}: {e}")
                            
            rag_evidence = list(rag_chunks_deduped.values())

            # 3. Generate Bulk Prompt
            field_dicts = [f.model_dump() for f in body.fields]
            prompt = build_bulk_fill_prompt(facts=all_facts, fields=field_dicts, rag_evidence=rag_evidence)
            
            # 4. Call LLM
            llm = request.app.state.llm_provider
            raw_response = llm.complete(prompt)
            
            # 5. Parse JSON
            try:
                mapping = json.loads(raw_response.strip())
            except Exception as e:
                logger.error(f"Failed to parse bulk LLM JSON: {e}. Raw: {raw_response[:200]}")
                mapping = {}
                
            # 6. Save Recommendations
            rec_repo = request.app.state.recommendations_repo
            for field in body.fields:
                field_id = field.field_id
                rec_data = mapping.get(field_id) or {}
                
                # Determine status and value
                rec_status = rec_data.get("status", "MISSING_INFORMATION")
                val = rec_data.get("value", "")
                conf = float(rec_data.get("confidence", 0.0))
                reason = str(rec_data.get("reason", "No recommendation provided."))
                
                db_status = "pending_review" if rec_status in ("REQUIRES_CONFIRMATION", "MISSING_INFORMATION") else "READY_TO_FILL"
                
                await rec_repo.create_recommendation(
                    user_id=user.user_id,
                    session_id=session_id,
                    field_id=field_id,
                    field_label=field.label or field.name or field_id,
                    concept=rec_data.get("concept", "unknown"),
                    recommended_value=val,
                    confidence=conf,
                    retrieval_type="bulk_llm",
                    source_fact_ids=[],
                    status=db_status,
                    decision_reason=reason
                )
                
        except Exception as e:
            logger.error(f"Error in bulk form analysis: {e}")
            
        # Determine final status
        rec_repo = request.app.state.recommendations_repo
        pending = await rec_repo.collection.count_documents({"session_id": session_id, "status": "pending_review"})
        final_status = "review_required" if pending > 0 else "ready"
        await repo.update_session(user.user_id, session_id, {"status": final_status})
        
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
    repo = request.app.state.form_sessions_repo
    doc = await repo.get_session(user_id=user.user_id, session_id=body.session_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")

    # A single field recommendation, essentially running the agent inline.
    agent = request.app.state.agent_graph
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
    repo = request.app.state.form_sessions_repo
    doc = await repo.get_session(user_id=user.user_id, session_id=body.session_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")

    agent = request.app.state.agent_graph
    
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


@router.get("/forms/sessions/{session_id}/approved-values", response_model=SuccessResponse[ApprovedValuesResponseData])
async def get_session_approved_values(
    session_id: str,
    request: Request,
    user: User,
) -> SuccessResponse[ApprovedValuesResponseData]:
    rec_repo = request.app.state.recommendations_repo
    
    # We fetch recommendations where status is one of the fillable statuses.
    # READY_TO_FILL: The agent confidentially recommended this.
    # approved/edited: A human explicitly confirmed/edited this during review.
    valid_statuses = ["READY_TO_FILL", "approved", "edited"]
    
    docs = await rec_repo.collection.find({
        "session_id": session_id,
        "user_id": user.user_id,
        "status": {"$in": valid_statuses}
    }).to_list(None)
    
    approved = []
    for doc in docs:
        approved.append(ApprovedValueData(
            field_id=doc["field_id"],
            concept=doc.get("concept", ""),
            value=doc.get("recommended_value", ""),
            confidence=doc.get("confidence", 0.0),
            requires_confirmation=False # Usually already confirmed if in this list
        ))
        
    return SuccessResponse(
        success=True, 
        data=ApprovedValuesResponseData(
            session_id=session_id,
            approved_values=approved
        )
    )


@router.post("/forms/sessions/{session_id}/verify", response_model=SuccessResponse[FormSessionVerifyData])
async def verify_filled_value(
    session_id: str,
    body: FormSessionVerifyRequest,
    request: Request,
    user: User,
) -> SuccessResponse[FormSessionVerifyData]:
    # This endpoint receives client-side verification outcomes.
    # In a full production system, we'd persist this in a verifications collection
    # to measure fill accuracy over time.
    repo = request.app.state.form_sessions_repo
    doc = await repo.get_session(user_id=user.user_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")

    # For now, we will log it.
    import logging
    logger = logging.getLogger(__name__)
    
    if body.match:
        logger.info(f"Session {session_id}: Field {body.field_id} successfully filled and verified.")
    else:
        logger.warning(f"Session {session_id}: Field {body.field_id} mismatch! Expected '{body.filled_value}', got '{body.actual_value}'")
        
    return SuccessResponse(
        success=True,
        data=FormSessionVerifyData(
            session_id=session_id,
            status="verified"
        )
    )

