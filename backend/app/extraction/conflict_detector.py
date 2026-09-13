"""Cross-document and intra-document conflict detection for discovered facts.

Conflict types handled:
  1. Intra-document: same semantic_type has two different values in one document
  2. Cross-document: new extracted fact conflicts with an existing stored fact
  3. LLM vs deterministic: LLM extraction differs from deterministic regex signal
  4. Verified vs new: user-confirmed fact conflicts with newly extracted value

A conflict is NEVER silently resolved. It is stored with both candidates
and flagged for HITL resolution.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.extraction.schemas import DiscoveredAttribute

logger = logging.getLogger(__name__)


def _normalize_value(v: Any) -> str:
    """Normalize values for comparison (lowercased stripped string)."""
    return str(v or "").strip().lower()


class ConflictDetector:
    """Detects conflicts between newly extracted facts and existing stored facts."""

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        # Values are considered "same" if their normalized forms match
        # at or above this threshold (currently exact match only — can
        # be upgraded to fuzzy matching later).
        self.similarity_threshold = similarity_threshold

    def find_intra_document_conflicts(
        self,
        attributes: list[DiscoveredAttribute],
        document_id: str,
    ) -> dict[str, list[DiscoveredAttribute]]:
        """Group attributes by semantic_type and find intra-document duplicates.

        Returns a dict of semantic_type → list of conflicting attributes
        (only those semantic_types that have MORE than one distinct value).
        """
        grouped: dict[str, list[DiscoveredAttribute]] = {}
        for attr in attributes:
            key = attr.semantic_type
            grouped.setdefault(key, []).append(attr)

        conflicts: dict[str, list[DiscoveredAttribute]] = {}
        for semantic_type, attrs in grouped.items():
            distinct_values = {_normalize_value(a.value) for a in attrs}
            if len(distinct_values) > 1:
                conflicts[semantic_type] = attrs
                logger.info(
                    "conflict_detector: intra-document conflict for %s in %s — values: %s",
                    semantic_type,
                    document_id,
                    distinct_values,
                )
        return conflicts

    async def find_cross_document_conflicts(
        self,
        new_attributes: list[DiscoveredAttribute],
        user_id: str,
        document_id: str,
        discovered_facts_repo: Any,  # DiscoveredFactsRepository
    ) -> list[dict[str, Any]]:
        """Detect conflicts between new attributes and facts already stored in MongoDB.

        Returns a list of conflict descriptor dicts ready to be stored.
        """
        conflicts: list[dict[str, Any]] = []

        for attr in new_attributes:
            # Look up existing facts with same semantic_type for this user
            existing_facts = await discovered_facts_repo.find_by_semantic_type(
                user_id, attr.semantic_type
            )
            for existing in existing_facts:
                if existing.get("source_document_id") == document_id:
                    continue  # Same document — already handled as intra-doc conflict

                existing_val = _normalize_value(existing.get("value"))
                new_val = _normalize_value(attr.value)

                if existing_val == new_val:
                    continue  # Consistent — no conflict

                # Check if the existing fact is user-verified
                is_verified = existing.get("verification_status") == "VERIFIED"

                conflict: dict[str, Any] = {
                    "user_id": user_id,
                    "field": attr.field,
                    "semantic_type": attr.semantic_type,
                    "ontology": attr.ontology,
                    "conflict_status": "CONFLICT",
                    "verification_status": "UNVERIFIED",
                    "is_verified_conflict": is_verified,
                    "candidates": [
                        {
                            "value": existing.get("value"),
                            "document_id": existing.get("source_document_id"),
                            "page": existing.get("source_page"),
                            "confidence": existing.get("confidence", 0.5),
                            "evidence": existing.get("evidence_text", ""),
                            "is_user_confirmed": is_verified,
                            "stored_fact_id": str(existing.get("_id", "")),
                        },
                        {
                            "value": attr.value,
                            "document_id": document_id,
                            "page": attr.evidence.page,
                            "confidence": attr.confidence,
                            "evidence": attr.evidence.text,
                            "is_user_confirmed": False,
                            "stored_fact_id": None,
                        },
                    ],
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
                conflicts.append(conflict)
                logger.info(
                    "conflict_detector: cross-document conflict for %s (user=%s) — "
                    "existing=%r new=%r",
                    attr.semantic_type,
                    user_id,
                    existing.get("value"),
                    attr.value,
                )

        return conflicts

    def detect_llm_vs_deterministic(
        self,
        llm_value: Any,
        deterministic_value: Any,
        semantic_type: str,
        field: str,
        document_id: str,
    ) -> dict[str, Any] | None:
        """Compare LLM-extracted value against deterministic regex value.

        Returns a conflict descriptor if values differ significantly, else None.
        """
        if llm_value is None or deterministic_value is None:
            return None
        if _normalize_value(llm_value) == _normalize_value(deterministic_value):
            return None

        logger.info(
            "conflict_detector: llm_vs_deterministic for %s — llm=%r det=%r",
            semantic_type,
            llm_value,
            deterministic_value,
        )
        return {
            "field": field,
            "semantic_type": semantic_type,
            "conflict_type": "LLM_VS_DETERMINISTIC",
            "candidates": [
                {
                    "value": llm_value,
                    "extraction_method": "llm_dynamic",
                    "document_id": document_id,
                    "confidence": None,
                },
                {
                    "value": deterministic_value,
                    "extraction_method": "deterministic_regex",
                    "document_id": document_id,
                    "confidence": None,
                },
            ],
        }
