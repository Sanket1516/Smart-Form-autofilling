"""LangGraph state machine for the autofill agent (SRS §30.2)."""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph

from app.agents.enums import FinalResponseStatus
from app.agents.llm_provider import LLMProvider, detect_injection
from app.agents.prompts import EVIDENCE_INSUFFICIENT, build_reasoning_prompt
from app.agents.state import AgentState
from app.agents.semantic_classifier import SemanticClassifier
from app.agents.conflict_resolver import ConflictResolver
from app.db.repositories.recommendations import RecommendationsRepository
from app.schemas.forms import FieldObject
from app.schemas.retrieval import RAGRetrievalRequest
from app.services.facts import FactService

if TYPE_CHECKING:
    from app.services.retrieval import RAGRetrievalService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence thresholds (can be made settings-configurable if needed)
# ---------------------------------------------------------------------------
_HIGH_CONFIDENCE = 0.85
_MEDIUM_CONFIDENCE = 0.60


class AutofillAgent:
    """Agent orchestrator utilizing LangGraph for form autofilling."""

    def __init__(
        self,
        semantic_classifier: SemanticClassifier | None = None,
        fact_service: FactService | None = None,
        retrieval_service: "RAGRetrievalService | None" = None,
        llm_provider: LLMProvider | None = None,
        conflict_resolver: ConflictResolver | None = None,
        recommendations_repo: RecommendationsRepository | None = None,
        discovered_facts_repo: Any | None = None,   # DiscoveredFactsRepository
        max_evidence_chunks: int = 5,
    ) -> None:
        self.semantic_classifier = semantic_classifier
        self.fact_service = fact_service
        self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider
        self.conflict_resolver = conflict_resolver
        self.recommendations_repo = recommendations_repo
        self.discovered_facts_repo = discovered_facts_repo
        self.max_evidence_chunks = max_evidence_chunks
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(AgentState)

        # Add Nodes
        workflow.add_node("semantic_classification", self._node_semantic_classification)
        workflow.add_node("structured_retrieval", self._node_structured_retrieval)
        workflow.add_node("rag_retrieval", self._node_rag_retrieval)
        workflow.add_node("missing_information", self._node_missing_information)
        workflow.add_node("candidate_aggregation", self._node_candidate_aggregation)
        workflow.add_node("conflict_confidence", self._node_conflict_confidence)
        workflow.add_node("final_response", self._node_final_response)
        workflow.add_node("hitl", self._node_hitl)
        workflow.add_node("browser_fill", self._node_browser_fill)
        workflow.add_node("verify", self._node_verify)

        # Entry
        workflow.add_edge(START, "semantic_classification")

        # After classification, route to retrieval branch
        workflow.add_conditional_edges(
            "semantic_classification",
            self._route_retrieval,
        )

        # All retrieval branches converge at candidate_aggregation
        workflow.add_edge("structured_retrieval", "candidate_aggregation")
        workflow.add_edge("rag_retrieval", "candidate_aggregation")
        workflow.add_edge("missing_information", "candidate_aggregation")

        workflow.add_edge("candidate_aggregation", "conflict_confidence")

        # After reasoning, route to HITL or final response
        workflow.add_conditional_edges(
            "conflict_confidence",
            self._route_confidence,
            {
                "hitl": "hitl",
                "final_response": "final_response",
            },
        )

        workflow.add_edge("hitl", "final_response")
        workflow.add_conditional_edges(
            "final_response",
            lambda state: "browser_fill" if state.get("status") == "filling" else END,
            {
                "browser_fill": "browser_fill",
                END: END
            }
        )
        workflow.add_edge("browser_fill", "verify")
        workflow.add_edge("verify", END)

        return workflow.compile()

    # -----------------------------------------------------------------------
    # Security check — applied to ALL field/page context before it touches
    # anything that might be forwarded to the LLM (SRS §27.6).
    # -----------------------------------------------------------------------

    def _check_field_security(self, field_dict: dict[str, Any]) -> bool:
        """Return True if the field context is safe (no injection patterns)."""
        for key in ("label", "placeholder", "nearby_text", "aria_label", "name", "id"):
            val = field_dict.get(key, "") or ""
            if detect_injection(str(val)):
                return False
        return True

    # -----------------------------------------------------------------------
    # Nodes
    # -----------------------------------------------------------------------

    async def _node_semantic_classification(self, state: AgentState) -> dict[str, Any]:
        """Classifies the current field (Phase 9 reuse)."""
        logger.debug("Executing semantic_classification node")

        current_field = state.get("current_field") or {}
        semantic_result = state.get("semantic_result")

        # Security gate: check for prompt injection before any processing
        if current_field and not self._check_field_security(current_field):
            logger.warning(
                "security_blocked workflow_id=%s", state.get("workflow_id")
            )
            return {
                "status": "failed",
                "final_response_status": FinalResponseStatus.SECURITY_BLOCKED.value,
                "errors": (state.get("errors") or []) + ["Field context blocked by security heuristic"],
            }

        if current_field and self.semantic_classifier and not semantic_result:
            try:
                field_obj = FieldObject(**current_field)
                result = self.semantic_classifier.classify_field(field_obj)
                return {
                    "semantic_result": result.model_dump(),
                    "status": "routing",
                }
            except Exception as exc:
                logger.error("classification_error: %s", exc)
                return {
                    "errors": (state.get("errors") or []) + [str(exc)],
                    "status": "failed",
                    "final_response_status": FinalResponseStatus.ERROR.value,
                }

        return {"status": "routing"}

    async def _route_retrieval(self, state: AgentState) -> str:
        """Decides which retrieval branch to follow based on LLM field understanding."""
        semantic_result = state.get("semantic_result") or {}

        concept = semantic_result.get("ontology") or semantic_result.get("concept", "unknown")
        semantic_type = semantic_result.get("semantic_type", "UNKNOWN")
        field_type = semantic_result.get("field_type", "MISSING")
        retrieval_strategy = semantic_result.get("retrieval_strategy", "MISSING")

        # If classification was blocked, skip retrieval entirely
        if state.get("final_response_status") == FinalResponseStatus.SECURITY_BLOCKED.value:
            return "missing_information"

        # Primary routing: use retrieval_strategy if set
        if retrieval_strategy == "CHROMADB":
            return "rag_retrieval"
        if retrieval_strategy in ("MONGODB", "BOTH"):
            return "structured_retrieval"

        # Legacy routing fallback (for backward compat with old classifier)
        if field_type == "STRUCTURED" and (concept != "unknown" or semantic_type not in ("UNKNOWN", "", None)):
            return "structured_retrieval"
        elif field_type == "CONTEXTUAL":
            return "rag_retrieval"
        else:
            state["final_response_status"] = FinalResponseStatus.UNSUPPORTED_FIELD.value
            return "missing_information"

    async def _node_missing_information(self, state: AgentState) -> dict[str, Any]:
        """No-data route — emits MISSING_INFORMATION unless a more specific status is already set."""
        logger.debug("Executing missing_information node")
        # Preserve a more specific status already established by security/routing
        existing_status = state.get("final_response_status")
        resolved_status = existing_status if existing_status else FinalResponseStatus.MISSING_INFORMATION.value
        return {
            "status": "retrieving",
            "retrieval_route": "missing_information",
            "structured_candidates": state.get("structured_candidates") or [],
            "rag_candidates": [],
            "final_response_status": resolved_status,
        }

    async def _node_structured_retrieval(self, state: AgentState) -> dict[str, Any]:
        """Retrieves user-scoped structured fact candidates.

        Now queries BOTH:
          1. structured_facts (Track B, ontology-mapped, via FactService)
          2. discovered_facts (Track A, dynamic, via DiscoveredFactsRepository)
        Results are merged and deduped before passing to reasoning.
        """
        logger.debug("Executing structured_retrieval node")
        semantic_result = state.get("semantic_result") or {}
        concept = semantic_result.get("ontology") or semantic_result.get("concept")
        semantic_type = semantic_result.get("semantic_type", "UNKNOWN")
        user_id = state.get("user_id")
        retrieval_strategy = semantic_result.get("retrieval_strategy", "")

        candidates: list[dict[str, Any]] = []

        # --- Source 1: structured_facts (ontology-mapped) ---
        if self.fact_service and concept and concept != "unknown":
            facts_verified = await self.fact_service.list(user_id=user_id, concept=concept, confirmed=True)
            if facts_verified.facts:
                candidates = [f.model_dump() for f in facts_verified.facts]
            else:
                facts_any = await self.fact_service.list(user_id=user_id, concept=concept)
                candidates = [f.model_dump() for f in facts_any.facts]

        # --- Source 2: discovered_facts (semantic_type-based) ---
        if self.discovered_facts_repo and user_id:
            # Try by semantic_type first
            if semantic_type and semantic_type not in ("UNKNOWN", ""):
                discovered = await self.discovered_facts_repo.find_by_semantic_type(
                    user_id, semantic_type
                )
                for d in discovered:
                    # Normalize to same shape as structured_fact candidate
                    candidates.append({
                        "value": d.get("value"),
                        "confidence": d.get("confidence", 0.5),
                        "is_user_confirmed": d.get("verification_status") == "VERIFIED",
                        "provenance": {
                            "extraction_method": d.get("extraction_method", "llm_dynamic"),
                            "extracted_text": d.get("evidence_text", ""),
                            "document_id": d.get("source_document_id", ""),
                            "page": d.get("source_page"),
                        },
                        "concept": concept or d.get("semantic_type", ""),
                        "source": "discovered_facts",
                        "semantic_type": d.get("semantic_type"),
                        "field": d.get("field"),
                    })

            # Also try by ontology mapping in discovered_facts
            if concept and concept != "unknown":
                ontology_discovered = await self.discovered_facts_repo.find_by_ontology(
                    user_id, concept
                )
                existing_values = {str(c.get("value", "")) for c in candidates}
                for d in ontology_discovered:
                    v = str(d.get("value", ""))
                    if v not in existing_values:
                        candidates.append({
                            "value": d.get("value"),
                            "confidence": d.get("confidence", 0.5),
                            "is_user_confirmed": d.get("verification_status") == "VERIFIED",
                            "provenance": {
                                "extraction_method": d.get("extraction_method", "llm_dynamic"),
                                "extracted_text": d.get("evidence_text", ""),
                                "document_id": d.get("source_document_id", ""),
                                "page": d.get("source_page"),
                            },
                            "concept": concept,
                            "source": "discovered_facts",
                            "semantic_type": d.get("semantic_type"),
                        })
                        existing_values.add(v)

        logger.info(
            "structured_retrieval concept=%s semantic_type=%s candidates=%d",
            concept,
            semantic_type,
            len(candidates),
        )
        rag_candidates: list[dict[str, Any]] = []
        if retrieval_strategy == "BOTH" and self.retrieval_service and user_id:
            current_field = state.get("current_field") or {}
            field_hints = " ".join(
                str(current_field.get(key) or "")[:120]
                for key in ("label", "placeholder", "nearby_text", "section_context", "section")
            )
            query = " ".join(part for part in (str(concept or ""), field_hints) if part).strip()
            if query:
                try:
                    rag_result = await self.retrieval_service.search(
                        user_id=user_id,
                        request=RAGRetrievalRequest(query=query, top_k=self.max_evidence_chunks),
                    )
                    rag_candidates = [item.model_dump() for item in rag_result.results]
                except Exception:
                    logger.exception("combined_rag_retrieval_failed")
        return {
            "status": "retrieving",
            "retrieval_route": "structured_retrieval",
            "structured_candidates": candidates,
            "rag_candidates": rag_candidates,
        }

    async def _node_rag_retrieval(self, state: AgentState) -> dict[str, Any]:
        """Runs ChromaDB similarity search scoped to the authenticated user (SRS §7, Phase 7)."""
        logger.debug("Executing rag_retrieval node")
        semantic_result = state.get("semantic_result") or {}
        concept = semantic_result.get("ontology") or semantic_result.get("concept", "unknown")
        user_id = state.get("user_id")
        current_field = state.get("current_field") or {}

        # Search with all user-visible field hints. Narrative questions need their
        # surrounding context so a prompt like "Tell us about yourself" can find
        # relevant resume and user-approved experience memories.
        label = str(current_field.get("label") or "")[:160]
        prompt_context = " ".join(
            str(current_field.get(key) or "")[:120]
            for key in ("placeholder", "nearby_text", "section_context", "section")
        )
        query = " ".join(part for part in (concept, label, prompt_context) if part).strip()

        rag_candidates: list[dict[str, Any]] = []
        if self.retrieval_service and user_id and (concept != "unknown" or label):
            try:
                request = RAGRetrievalRequest(
                    query=query or concept,
                    top_k=self.max_evidence_chunks,
                )
                result = await self.retrieval_service.search(user_id=user_id, request=request)
                rag_candidates = [r.model_dump() for r in result.results]
                logger.info(
                    "rag_retrieval_complete chunks=%d concept=%s",
                    len(rag_candidates),
                    concept,
                )
            except Exception as exc:
                logger.exception("rag_retrieval_failed concept=%s", concept)
                return {
                    "status": "retrieving",
                    "retrieval_route": "rag_retrieval",
                    "rag_candidates": [],
                    "errors": (state.get("errors") or []) + [f"RAG retrieval error: {exc}"],
                }

        return {
            "status": "retrieving",
            "retrieval_route": "rag_retrieval",
            "rag_candidates": rag_candidates,
        }

    async def _node_candidate_aggregation(self, state: AgentState) -> dict[str, Any]:
        """Merges structured and RAG candidates, deduplicates by value."""
        logger.debug("Executing candidate_aggregation node")
        structured = state.get("structured_candidates") or []
        rag = state.get("rag_candidates") or []

        # If already MISSING_INFORMATION (e.g. from missing_information node), propagate
        if state.get("final_response_status") == FinalResponseStatus.MISSING_INFORMATION.value:
            return {
                "status": "reasoning",
                "structured_candidates": structured,
                "rag_candidates": rag,
            }

        # Dedup structured candidates by value
        seen_values: set[str] = set()
        deduped_structured: list[dict[str, Any]] = []
        for c in structured:
            v = str(c.get("value", ""))
            if v not in seen_values:
                seen_values.add(v)
                deduped_structured.append(c)

        total = len(deduped_structured) + len(rag)
        logger.info(
            "candidate_aggregation structured=%d rag=%d total=%d",
            len(deduped_structured),
            len(rag),
            total,
        )

        return {
            "status": "reasoning",
            "structured_candidates": deduped_structured,
            "rag_candidates": rag,
        }

    async def _node_conflict_confidence(self, state: AgentState) -> dict[str, Any]:
        """LLM Reasoning Node: builds isolated prompt and calls the LLM (SRS §17)."""
        logger.debug("Executing conflict_confidence node")

        # Propagate any pre-set terminal status without invoking the LLM
        _TERMINAL_STATUSES = {
            FinalResponseStatus.MISSING_INFORMATION.value,
            FinalResponseStatus.SECURITY_BLOCKED.value,
            FinalResponseStatus.UNSUPPORTED_FIELD.value,
            FinalResponseStatus.ERROR.value,
        }
        pre_status = state.get("final_response_status")
        if pre_status in _TERMINAL_STATUSES:
            return {
                "status": "conflict_resolution",
                "confidence": 0.0,
                "conflict_result": {"status": pre_status},
                "final_response_status": pre_status,
            }

        semantic_result = state.get("semantic_result") or {}
        concept = semantic_result.get("ontology") or semantic_result.get("concept", "unknown")
        current_field = state.get("current_field") or {}
        structured = state.get("structured_candidates") or []
        rag = state.get("rag_candidates") or []

        reasoning_trace: list[str] = list(state.get("reasoning_trace") or [])

        # --- HEURISTIC CONFLICT RESOLUTION (Phase 13) ---
        if self.conflict_resolver and structured:
            outcome = self.conflict_resolver.resolve(concept, structured, rag)
            
            # If sensitive, always require confirmation; bypass LLM completely
            if concept.lower() in self.conflict_resolver.sensitive_concepts:
                reasoning_trace.append("heuristic: sensitive field forced confirmation")
                # Determine if there are multiple candidates
                if len(structured) > 1 and self.conflict_resolver.has_conflict(structured):
                    frs = FinalResponseStatus.MULTIPLE_CANDIDATES
                else:
                    frs = FinalResponseStatus.REQUIRES_CONFIRMATION
                
                return {
                    "status": "conflict_resolution",
                    "confidence": outcome["confidence"],
                    "conflict_result": {
                        "status": frs.value,
                        "value": outcome["selected_candidate"].get("value", "") if outcome["selected_candidate"] else "",
                        "reason": outcome["decision_reason"]
                    },
                    "final_response_status": frs.value,
                    "reasoning_trace": reasoning_trace,
                }
                
            # If heuristic succeeds with high confidence, use it directly (bypass LLM)
            if not outcome["requires_confirmation"]:
                reasoning_trace.append(f"heuristic: high confidence {outcome['confidence']}")
                return {
                    "status": "conflict_resolution",
                    "confidence": outcome["confidence"],
                    "conflict_result": {
                        "status": FinalResponseStatus.READY_TO_FILL.value,
                        "value": outcome["selected_candidate"].get("value", "") if outcome["selected_candidate"] else "",
                        "reason": outcome["decision_reason"]
                    },
                    "final_response_status": FinalResponseStatus.READY_TO_FILL.value,
                    "reasoning_trace": reasoning_trace,
                }
            
            reasoning_trace.append(f"heuristic: requires_confirmation (conf={outcome['confidence']}) - falling back to LLM")

        # --- LLM FALLBACK (Phase 12) ---
        # Build prompt — returns sentinel if evidence is empty
        prompt = build_reasoning_prompt(
            concept=concept,
            field_context=current_field,
            evidence_chunks=rag,
            structured_candidates=structured,
            max_evidence_chunks=self.max_evidence_chunks,
        )

        if prompt == EVIDENCE_INSUFFICIENT or not self.llm_provider:
            reasoning_trace.append("no_evidence_insufficient")
            return {
                "status": "conflict_resolution",
                "confidence": 0.0,
                "conflict_result": {"status": FinalResponseStatus.MISSING_INFORMATION.value},
                "final_response_status": FinalResponseStatus.MISSING_INFORMATION.value,
                "reasoning_trace": reasoning_trace,
            }

        # Call LLM
        try:
            raw_response = self.llm_provider.complete(prompt)
            reasoning_trace.append("llm_response_received")
        except Exception as exc:
            logger.exception("llm_reasoning_failed")
            reasoning_trace.append(f"llm_error:{exc}")
            return {
                "status": "conflict_resolution",
                "confidence": 0.0,
                "conflict_result": {"status": FinalResponseStatus.ERROR.value},
                "final_response_status": FinalResponseStatus.ERROR.value,
                "errors": (state.get("errors") or []) + [str(exc)],
                "reasoning_trace": reasoning_trace,
            }

        # Parse JSON response from LLM
        parsed = _parse_llm_json(raw_response)
        status_str = parsed.get("status", FinalResponseStatus.MISSING_INFORMATION.value)
        confidence = float(parsed.get("confidence", 0.0))

        # Validate the status string is a known enum value
        try:
            final_status = FinalResponseStatus(status_str)
        except ValueError:
            logger.warning("llm_returned_unknown_status status=%s", status_str)
            final_status = FinalResponseStatus.ERROR

        return {
            "status": "conflict_resolution",
            "confidence": confidence,
            "conflict_result": parsed,
            "final_response_status": final_status.value,
            "reasoning_trace": reasoning_trace,
        }

    def _route_confidence(self, state: AgentState) -> str:
        """Routes to HITL or final_response based on FinalResponseStatus."""
        frs = state.get("final_response_status", "")
        # Only READY_TO_FILL proceeds directly to final_response
        if frs in (
            FinalResponseStatus.READY_TO_FILL.value,
            FinalResponseStatus.MISSING_INFORMATION.value,
            FinalResponseStatus.UNSUPPORTED_FIELD.value,
            FinalResponseStatus.SECURITY_BLOCKED.value,
            FinalResponseStatus.ERROR.value,
        ):
            return "final_response"
        # REQUIRES_CONFIRMATION, MULTIPLE_CANDIDATES, LOW_CONFIDENCE go through HITL
        return "hitl"

    async def _node_hitl(self, state: AgentState) -> dict[str, Any]:
        """Prepares state for human review when confidence is low or conflict exists."""
        logger.debug("Executing hitl node")
        return {"status": "waiting_human"}

    async def _node_final_response(self, state: AgentState) -> dict[str, Any]:
        """Prepares the final autofill recommendation and persists it."""
        logger.debug("Executing final_response node")
        frs = state.get("final_response_status", FinalResponseStatus.MISSING_INFORMATION.value)
        conflict = state.get("conflict_result") or {}
        
        final_value: dict[str, Any] = {
            "status": frs,
            "value": conflict.get("value", ""),
            "confidence": state.get("confidence", 0.0),
            "reason": conflict.get("reason", ""),
        }
        
        user_id = state.get("user_id", "anonymous")
        # Recommendations must be associated with the browser form session,
        # not the internal per-field workflow ID, so the extension can fetch
        # all values approved for that form.
        session_id = state.get("session_id", "")
        field = state.get("current_field") or {}
        field_id = field.get("field_id", "")
        field_label = field.get("label", "")
        semantic_result = state.get("semantic_result") or {}
        concept = semantic_result.get("ontology") or semantic_result.get("concept", "unknown")
        
        # Aggregate sources
        structured = state.get("structured_candidates", [])
        rag = state.get("rag_candidates", [])
        source_fact_ids = []
        for c in structured:
            fid = c.get("fact_id")
            if fid:
                source_fact_ids.append(fid)
        # We could also append RAG document IDs if needed.

        # Determine DB status
        is_hitl = state.get("status") == "waiting_human" or frs in (
            FinalResponseStatus.REQUIRES_CONFIRMATION.value,
            FinalResponseStatus.MULTIPLE_CANDIDATES.value,
            FinalResponseStatus.LOW_CONFIDENCE.value,
        )
        db_status = (
            "pending_review"
            if is_hitl
            else FinalResponseStatus.READY_TO_FILL.value
            if frs == FinalResponseStatus.READY_TO_FILL.value
            else "generated"
        )
        
        # Persist to database
        if self.recommendations_repo:
            await self.recommendations_repo.create_recommendation(
                user_id=user_id,
                session_id=session_id,
                field_id=field_id,
                field_label=field_label,
                concept=concept,
                recommended_value=conflict.get("value", ""),
                confidence=state.get("confidence", 0.0),
                retrieval_type="mixed",
                source_fact_ids=source_fact_ids,
                status=db_status,
                decision_reason=conflict.get("reason", ""),
            )
            
        next_status = "waiting_human" if is_hitl else "filling"
        return {"status": next_status, "final_value": final_value}

    async def _node_browser_fill(self, state: AgentState) -> dict[str, Any]:
        """Placeholder for browser interaction/injection."""
        logger.debug("Executing browser_fill node")
        return {"status": "verifying"}

    async def _node_verify(self, state: AgentState) -> dict[str, Any]:
        """Placeholder for post-fill verification."""
        logger.debug("Executing verify node")
        return {"status": "completed"}

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Executes the graph with the given initial state."""
        final_state = await self.graph.ainvoke(state)
        return final_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_llm_json(raw: str) -> dict[str, Any]:
    """Try to parse the LLM's JSON response; fall back to MISSING_INFORMATION."""
    raw = raw.strip()
    # Handle bare enum sentinel returned by MockLLMProvider
    try:
        FinalResponseStatus(raw)
        return {"status": raw, "value": "", "confidence": 0.0, "reason": "no evidence"}
    except ValueError:
        pass

    # Try JSON parse
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        logger.warning("llm_non_json_response raw=%r", raw[:200])
        return {
            "status": FinalResponseStatus.MISSING_INFORMATION.value,
            "value": "",
            "confidence": 0.0,
            "reason": "LLM returned non-JSON response",
        }
