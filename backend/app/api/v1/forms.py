"""Forms APIs (Classification, Sessions, Recommendations)."""

from typing import Any, Annotated
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
import asyncio
import json
from datetime import UTC, datetime
import re

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
from app.schemas.profile import ProfileUpdateRequest
from app.schemas.forms import FieldObject as SemanticFieldObject
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
    AskMeAnswersRequest,
    AskMeAnswersData,
)
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Forms"])
User = Annotated[CurrentUser, Depends(get_current_user)]


def _is_narrative_field(label: str, placeholder: str = "") -> bool:
    text = f"{label} {placeholder}".lower()
    return any(term in text for term in (
        "about yourself", "about me", "past experience", "work experience",
        "employment history", "career goal", "career objective", "achievement",
        "describe your", "tell us about", "project description", "strengths",
    ))


def _field_is_required(field: Any) -> bool:
    label = str(getattr(field, "label", "") or "")
    return bool(getattr(field, "required", False) or "*" in label)


def _concept_from_label(label: str, existing: str | None = None) -> str:
    concept = str(existing or "").strip().lower()
    if concept and concept not in {"unknown", "missing", "none"}:
        aliases = {
            "full_name": "personal.full_name",
            "date_of_birth": "personal.date_of_birth",
            "personal.email": "contact.email",
            "personal.phone": "contact.phone",
            "email_address": "contact.email",
            "phone_number": "contact.phone",
            "current_address": "address.current",
            "address.current_address": "address.current",
            "permanent_address": "address.permanent",
            "address.permanent_address": "address.permanent",
            "address.current": "address.current",
            "address.permanent": "address.permanent",
            "postal_code": "address.postal_code",
        }
        return aliases.get(concept, concept)

    text = re.sub(r"[^a-z0-9 ]+", " ", label.lower())
    text = " ".join(text.split())
    if "first name" in text or "given name" in text:
        return "personal.first_name"
    if "last name" in text or "surname" in text or "family name" in text:
        return "personal.last_name"
    if any(term in text for term in ("date of birth", "birth date", "birthdate", "dob")):
        return "personal.date_of_birth"
    if any(term in text for term in ("annual income", "yearly income", "family income", "income")):
        return "personal.annual_income"
    common_name = any(term in text for term in (
        "full name", "applicant name", "candidate name", "legal name", "your name"
    ))
    role_name = "name" in text and any(term in text for term in ("applicant", "candidate"))
    if common_name or role_name:
        return "personal.full_name"
    if "email" in text:
        return "contact.email"
    if any(term in text for term in ("phone", "mobile", "telephone")):
        return "contact.phone"
    if any(term in text for term in ("pincode", "pin code", "postal code", "zip code")):
        return "address.postal_code"
    if "permanent" in text and "address" in text:
        return "address.permanent"
    if "address" in text:
        return "address.current"
    if any(term in text for term in ("college", "university", "institution")):
        return "education.institution"
    if "degree" in text or "qualification" in text:
        return "education.degree"
    narrative_terms = (
        "experience", "employment history", "about yourself", "about me", "tell us about"
    )
    if any(term in text for term in narrative_terms):
        return "experience.summary"
    if "project" in text or "achievement" in text or "strength" in text or "career goal" in text:
        return "profile.narrative"
    return "profile.narrative"


def _normalize_answer(value: str, concept: str, input_type: str) -> str | int | float:
    normalized = " ".join(value.split())
    if concept == "personal.date_of_birth":
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(normalized, fmt).date().isoformat()
            except ValueError:
                continue
    if concept == "personal.annual_income":
        numeric = re.fullmatch(
            r"(?:₹|\$|Rs\.?|INR)?\s*[\d,]+(?:\.\d+)?\s*",
            normalized,
            re.IGNORECASE,
        )
        if numeric:
            numeric_value = re.sub(r"[^0-9.]", "", normalized)
            try:
                number = float(numeric_value)
                return int(number) if number.is_integer() else number
            except ValueError:
                pass
    return normalized


def _profile_target(concept: str) -> tuple[str, str] | None:
    mapping = {
        "personal.full_name": ("personal", "full_name"),
        "personal.first_name": ("personal", "first_name"),
        "personal.last_name": ("personal", "last_name"),
        "personal.date_of_birth": ("personal", "date_of_birth"),
        "personal.annual_income": ("personal", "annual_income"),
        "personal.gender": ("personal", "gender"),
        "personal.nationality": ("personal", "nationality"),
        "contact.email": ("contact", "email"),
        "contact.phone": ("contact", "phone"),
        "address.current": ("address", "current"),
        "address.permanent": ("address", "permanent"),
        "address.postal_code": ("address", "postal_code"),
        "address.city": ("address", "city"),
        "address.state": ("address", "state"),
        "address.country": ("address", "country"),
        "education.institution": ("education", "institution"),
        "education.degree": ("education", "degree"),
        "education.field_of_study": ("education", "field_of_study"),
        "employment.company": ("employment", "company"),
        "employment.job_title": ("employment", "job_title"),
    }
    return mapping.get(concept)


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

            # Explicit profile entries are also first-class structured evidence.
            profile = await request.app.state.profile_service.get(user.user_id)
            for section in ("personal", "contact", "address"):
                for key, value in getattr(profile, section).items():
                    if value not in (None, "", [], {}):
                        all_facts.append({
                            "concept": f"{section}.{key}",
                            "value": value,
                            "confidence": 1.0,
                            "source": "user_profile",
                        })
            for section in ("education", "employment"):
                for entry in getattr(profile, section):
                    if isinstance(entry, dict):
                        for key, value in entry.items():
                            if value not in (None, "", [], {}):
                                all_facts.append({
                                    "concept": f"{section}.{key}",
                                    "value": value,
                                    "confidence": 0.9,
                                    "source": "user_profile",
                                })

            # Reuse the existing semantic classifier so field labels resolve to
            # ontology concepts before fact and RAG evidence are matched.
            semantic_fields: dict[str, dict[str, Any]] = {}
            classifier = request.app.state.semantic_classifier
            for field in body.fields:
                try:
                    classification = classifier.classify_field(SemanticFieldObject(
                        field_id=field.field_id,
                        tag=field.tag,
                        type=field.input_type,
                        name=field.name,
                        id=field.id,
                        placeholder=field.placeholder,
                        label=field.label,
                        aria_label=field.aria_label,
                        aria_description=field.aria_description,
                        autocomplete=field.autocomplete,
                        required=_field_is_required(field),
                        pattern=field.pattern,
                        nearby_text=field.nearby_text,
                        section_context=field.section_context or field.section,
                        position=field.position,
                        visual_context=field.visual_context,
                    ))
                    semantic_fields[field.field_id] = {
                        "concept": classification.concept,
                        "semantic_type": classification.semantic_type,
                        "retrieval_strategy": classification.retrieval_strategy,
                        "field_type": classification.field_type,
                        "classification_status": classification.status,
                    }
                except Exception:
                    semantic_fields[field.field_id] = {}
                
            # 2.5 Fetch RAG Evidence
            retrieval_service = request.app.state.retrieval_service
            rag_chunks_deduped = {}
            if retrieval_service:
                for field in body.fields:
                    label = field.label or field.name or ""
                    narrative_hints = ""
                    semantics = semantic_fields.get(field.field_id, {})
                    if (
                        semantics.get("field_type") == "CONTEXTUAL"
                        or _is_narrative_field(label, field.placeholder or "")
                    ):
                        narrative_hints = (
                            "personal history work experience education projects achievements "
                            "strengths goals about the user"
                        )
                    query = " ".join(part for part in (
                        label,
                        str(semantics.get("concept") or ""),
                        str(semantics.get("semantic_type") or ""),
                        field.placeholder or "",
                        field.name or "",
                        field.nearby_text or "",
                        field.section or field.section_context or "",
                        narrative_hints,
                    ) if part).strip()
                    if query:
                        try:
                            rag_req = RAGRetrievalRequest(query=query, top_k=3)
                            rag_res = await retrieval_service.search(
                                user_id=user.user_id,
                                request=rag_req,
                            )
                            for r in rag_res.results:
                                txt = r.text.strip()
                                key = (field.field_id, txt)
                                if txt and key not in rag_chunks_deduped:
                                    rag_chunks_deduped[key] = {
                                        "text": txt,
                                        "similarity": r.similarity,
                                        "document_id": r.metadata.document_id,
                                        "page": r.metadata.page_number,
                                        "field_id": field.field_id,
                                        "field_label": label,
                                    }
                        except Exception:
                            logger.error("RAG search failed for a form field")
                            
            rag_evidence = list(rag_chunks_deduped.values())

            # 3. Generate Bulk Prompt
            field_dicts = [
                {**field.model_dump(), **semantic_fields.get(field.field_id, {})}
                for field in body.fields
            ]
            prompt = build_bulk_fill_prompt(
                facts=all_facts,
                fields=field_dicts,
                rag_evidence=rag_evidence,
            )
            
            # 4. Call LLM
            llm = request.app.state.llm_provider
            raw_response = llm.complete(prompt)
            
            # 5. Parse JSON
            try:
                mapping = json.loads(raw_response.strip())
                if not isinstance(mapping, dict):
                    mapping = {}
            except Exception:
                logger.error("Failed to parse bulk LLM JSON response")
                mapping = {}
                
            # 6. Save Recommendations
            rec_repo = request.app.state.recommendations_repo
            for field in body.fields:
                field_id = field.field_id
                required = _field_is_required(field)
                rec_data = mapping.get(field_id) or {}
                if not isinstance(rec_data, dict):
                    rec_data = {}
                
                # Determine status and value
                rec_status = str(rec_data.get("status", "MISSING_INFORMATION")).upper()
                val = rec_data.get("value", "")
                if not isinstance(val, (str, int, float, bool)):
                    val = ""
                has_value = val is not None and str(val).strip() != ""
                try:
                    conf = max(0.0, min(1.0, float(rec_data.get("confidence", 0.0))))
                except (TypeError, ValueError):
                    conf = 0.0
                reason = str(rec_data.get("reason", "No recommendation provided."))[:500]
                
                proposed_concept = str(rec_data.get("concept") or "").strip()[:160]
                if not proposed_concept:
                    proposed_concept = str(
                        semantic_fields.get(field_id, {}).get("concept") or ""
                    ).strip()[:160]
                concept = (
                    proposed_concept
                    if proposed_concept.lower() not in {"unknown", "missing"}
                    else _concept_from_label(field.label or field.name or "")
                )
                if semantic_fields.get(field_id, {}).get("classification_status") == "security_blocked":
                    db_status = "security_blocked"
                    val = ""
                elif not has_value or rec_status in {"MISSING_INFORMATION", "LOW_CONFIDENCE"}:
                    db_status = "missing_information" if required else "skipped"
                    if not has_value:
                        val = ""
                elif rec_status == "READY_TO_FILL" and conf >= 0.85:
                    db_status = "READY_TO_FILL"
                else:
                    db_status = "pending_review"
                
                await rec_repo.create_recommendation(
                    user_id=user.user_id,
                    session_id=session_id,
                    field_id=field_id,
                    field_label=field.label or field.name or field_id,
                    concept=concept,
                    recommended_value=val,
                    confidence=conf,
                    retrieval_type="bulk_llm",
                    source_fact_ids=[],
                    status=db_status,
                    decision_reason=reason,
                    required=required,
                    input_type=field.input_type or "text",
                )
                
        except Exception:
            logger.error("Bulk form analysis failed")
            
        # Determine final status
        rec_repo = request.app.state.recommendations_repo
        missing = await rec_repo.collection.count_documents({
            "session_id": session_id, "user_id": user.user_id,
            "status": "missing_information", "required": True,
        })
        pending = await rec_repo.collection.count_documents({
            "session_id": session_id, "user_id": user.user_id, "status": "pending_review",
        })
        if missing:
            final_status = "information_required"
        elif pending:
            final_status = "review_required"
        else:
            final_status = "ready"
        await repo.update_session(user.user_id, session_id, {"status": final_status})
        
    background_tasks.add_task(process_all_fields)
    
    return SuccessResponse(
        success=True,
        data=FormSessionAnalyzeData(
            session_id=session_id,
            status="processing",
            field_count=len(body.fields),
        ),
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
            provenance=[],
            field_label=doc.get("field_label", ""),
            required=bool(doc.get("required", False)),
            input_type=doc.get("input_type", "text"),
        ))
        
    return SuccessResponse(success=True, data=SessionRecommendationsData(recommendations=recs))


@router.post(
    "/forms/sessions/{session_id}/answers",
    response_model=SuccessResponse[AskMeAnswersData],
)
async def submit_ask_me_answers(
    session_id: str,
    body: AskMeAnswersRequest,
    request: Request,
    user: User,
) -> SuccessResponse[AskMeAnswersData]:
    """Use user answers for this form; save them long-term only on explicit opt-in."""
    session_repo = request.app.state.form_sessions_repo
    if not await session_repo.get_session(user.user_id, session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form session not found")

    rec_repo = request.app.state.recommendations_repo
    profile_values: dict[str, dict[str, object]] = {
        "personal": {}, "contact": {}, "address": {},
    }
    education_entries: list[dict[str, object]] = []
    employment_entries: list[dict[str, object]] = []
    saved_count = 0

    validated_answers: list[tuple[Any, dict[str, Any]]] = []
    seen_fields: set[str] = set()
    for answer in body.answers:
        if not answer.value.strip() or answer.field_id in seen_fields:
            raise HTTPException(status_code=422, detail="Each field needs one non-empty answer")
        seen_fields.add(answer.field_id)
        recommendation = await rec_repo.collection.find_one({
            "session_id": session_id,
            "user_id": user.user_id,
            "field_id": answer.field_id,
        })
        if not recommendation or recommendation.get("status") not in (
            "missing_information", "pending_review"
        ):
            raise HTTPException(status_code=409, detail="Answer does not match an outstanding field")

        validated_answers.append((answer, recommendation))

    for answer, recommendation in validated_answers:
        label = str(recommendation.get("field_label") or answer.field_id)
        concept = _concept_from_label(label, recommendation.get("concept"))
        value = _normalize_answer(answer.value, concept, recommendation.get("input_type", "text"))
        await rec_repo.collection.update_one(
            {"_id": recommendation["_id"], "user_id": user.user_id},
            {"$set": {
                "recommended_value": value,
                "concept": concept,
                "status": "READY_TO_FILL",
                "updated_at": datetime.now(UTC).isoformat(),
                "user_supplied": True,
            }},
        )

        if answer.save_for_future:
            target = _profile_target(concept)
            if target:
                section, key = target
                if section == "education":
                    education_entries.append({key: value})
                elif section == "employment":
                    employment_entries.append({key: value})
                else:
                    profile_values[section][key] = value

            await request.app.state.user_memory_service.save(
                user.user_id, label, concept, value
            )
            saved_count += 1

    if any(profile_values.values()) or education_entries or employment_entries:
        profile_update: dict[str, object] = {
            section: values for section, values in profile_values.items() if values
        }
        if education_entries:
            existing = await request.app.state.profile_service.get(user.user_id)
            profile_update["education"] = [*existing.education, *education_entries]
        if employment_entries:
            existing = await request.app.state.profile_service.get(user.user_id)
            profile_update["employment"] = [*existing.employment, *employment_entries]
        await request.app.state.profile_service.update(
            user.user_id, ProfileUpdateRequest(**profile_update)
        )

    missing = await rec_repo.collection.count_documents({
        "session_id": session_id, "user_id": user.user_id,
        "status": "missing_information", "required": True,
    })
    pending = await rec_repo.collection.count_documents({
        "session_id": session_id, "user_id": user.user_id, "status": "pending_review",
    })
    next_status = "information_required" if missing else "review_required" if pending else "ready"
    await session_repo.update_session(user.user_id, session_id, {"status": next_status})
    return SuccessResponse(data=AskMeAnswersData(
        session_id=session_id, status=next_status, saved_count=saved_count
    ))


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
            value=str(doc.get("recommended_value", "") or ""),
            confidence=doc.get("confidence", 0.0),
            requires_confirmation=False,  # Usually already confirmed if in this list
            field_label=doc.get("field_label", ""),
            input_type=doc.get("input_type", "text"),
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
        logger.warning("form_field_value_mismatch session_id=%s field_id=%s", session_id, body.field_id)
        
    return SuccessResponse(
        success=True,
        data=FormSessionVerifyData(
            session_id=session_id,
            status="verified"
        )
    )

