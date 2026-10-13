"""Merge candidate facts from the deterministic and LLM extractors.

Candidates for the same concept (or semantic type) and the same value are
combined; agreement between both extractors raises confidence slightly.
Different values are never merged: they are kept as separate candidates and
become a conflict for the user to resolve.
"""

from __future__ import annotations

from app.extraction.normalize import comparison_key
from app.extraction.schemas import CandidateFact

_ORIGIN_RANK = {"extracted": 0, "normalized": 1, "derived": 2, "inferred": 3}


def merge_candidates(candidates: list[CandidateFact]) -> list[CandidateFact]:
    merged: dict[tuple[str, str], CandidateFact] = {}
    for candidate in candidates:
        key = (
            candidate.concept or f"semantic:{candidate.semantic_type}",
            comparison_key(candidate.data_type, candidate.value),
        )
        if not key[1]:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue
        methods = sorted({*existing.method.split("+"), *candidate.method.split("+")})
        agreeing = len(methods) > 1
        better = (
            candidate
            if _ORIGIN_RANK[candidate.origin] < _ORIGIN_RANK[existing.origin]
            else existing
        )
        merged[key] = CandidateFact(
            concept=existing.concept or candidate.concept,
            semantic_type=existing.semantic_type,
            field=existing.field,
            value=better.value,
            raw_value=better.raw_value,
            data_type=better.data_type,
            confidence=min(
                0.99, max(existing.confidence, candidate.confidence) + (0.03 if agreeing else 0)
            ),
            origin=better.origin,
            method="+".join(methods),
            page=better.page if better.page is not None else (existing.page or candidate.page),
            evidence_text=better.evidence_text or existing.evidence_text,
            entity_type=existing.entity_type or candidate.entity_type,
        )
    return list(merged.values())
