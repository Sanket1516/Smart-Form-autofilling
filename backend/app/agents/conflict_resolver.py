"""Candidate aggregation and conflict resolution (SRS §18)."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class ConflictOutcome(TypedDict):
    """Result of the conflict resolution process per SRS §18.5."""
    selected_candidate: dict[str, Any] | None
    confidence: float
    candidate_set: list[dict[str, Any]]
    provenance: dict[str, Any]
    decision_reason: str
    requires_confirmation: bool


class ConflictResolver:
    """Heuristic conflict resolution engine (SRS §18.1, §18.2, §18.4, §31)."""

    def __init__(self, confidence_threshold: float, sensitive_concepts: list[str]) -> None:
        self.confidence_threshold = confidence_threshold
        self.sensitive_concepts = [c.lower() for c in sensitive_concepts]

    def has_conflict(self, candidates: list[dict[str, Any]]) -> bool:
        """Returns True if there are multiple non-equivalent values (SRS §18.1)."""
        seen_values = set()
        for c in candidates:
            # Normalize to string for basic equivalence
            val = str(c.get("value", "")).strip().lower()
            if val:
                seen_values.add(val)
        return len(seen_values) > 1

    def resolve(
        self,
        concept: str,
        structured_candidates: list[dict[str, Any]],
        rag_candidates: list[dict[str, Any]]
    ) -> ConflictOutcome:
        """Resolves conflicts using heuristic scoring (SRS §18.2)."""
        all_candidates = []
        
        # 1. Score Structured Candidates
        for c in structured_candidates:
            base_score = float(c.get("confidence", 0.5))
            
            # Boost if user-confirmed (verification status)
            if c.get("is_user_confirmed"):
                base_score = min(1.0, base_score + 0.3)
                
            # Provenance/Reliability weight
            prov = c.get("provenance", {})
            method = prov.get("extraction_method", "")
            if method == "direct-parse":
                base_score = min(1.0, base_score + 0.1)
            elif method == "ocr":
                base_score = min(1.0, base_score + 0.05)
                
            all_candidates.append({
                "value": c.get("value", ""),
                "score": base_score,
                "raw_candidate": c,
                "type": "structured",
                "is_explicit_conflict": c.get("status") == "CONFLICT",
            })
            
        # 2. Score RAG Candidates (only if value exists, but RAG chunks are text blocks)
        # Note: RAG returns raw text chunks, not structured 'value's.
        # They will only be scored heuristically if we can extract a value, 
        # but RAG needs LLM. We just record them here. 
        # For pure RAG, we defer to LLM, so score is 0 if no structured candidates exist.

        # 3. Aggregation & Selection
        if not all_candidates:
            return {
                "selected_candidate": None,
                "confidence": 0.0,
                "candidate_set": structured_candidates,
                "provenance": {},
                "decision_reason": "No structured candidates available",
                "requires_confirmation": True
            }

        # Sort by heuristic score descending
        all_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidate = all_candidates[0]
        
        selected = top_candidate["raw_candidate"]
        final_confidence = top_candidate["score"]
        
        # Apply Confidence Gate and Sensitive Field rules (SRS §18.3, §18.4, §31)
        requires_confirmation = False
        reason = "Heuristic resolution succeeded"
        
        if concept.lower() in self.sensitive_concepts:
            requires_confirmation = True
            reason = f"Sensitive field '{concept}' always requires confirmation"
        elif any(c.get("is_explicit_conflict") for c in all_candidates):
            requires_confirmation = True
            reason = "Document extractor explicitly flagged a conflict for this concept"
        elif final_confidence < self.confidence_threshold:
            requires_confirmation = True
            reason = f"Confidence {final_confidence:.2f} is below threshold {self.confidence_threshold}"
        elif self.has_conflict(structured_candidates):
            reason = "Resolved conflict based on heuristic scoring (verification/reliability)"

        return {
            "selected_candidate": selected,
            "confidence": final_confidence,
            "candidate_set": structured_candidates,
            "provenance": selected.get("provenance", {}),
            "decision_reason": reason,
            "requires_confirmation": requires_confirmation
        }
