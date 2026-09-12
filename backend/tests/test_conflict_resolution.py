"""Tests for candidate aggregation, conflict resolution, confidence gating, and sensitive fields (SRS §18).

Covers: TC-CON-01, TC-CON-02, TC-CON-03, TC-CON-04, TC-CON-05.
"""

from __future__ import annotations

import pytest

from app.agents.conflict_resolver import ConflictResolver
from app.agents.graph import AutofillAgent
from app.agents.enums import FinalResponseStatus
from app.agents.state import AgentState


def make_candidate(value: str, confidence: float = 0.5, confirmed: bool = False, method: str = "") -> dict:
    return {
        "value": value,
        "confidence": confidence,
        "is_user_confirmed": confirmed,
        "provenance": {"extraction_method": method}
    }


def test_tc_con_01_conflict_detection():
    """TC-CON-01: Detects when multiple non-equivalent values exist for the same concept."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=[])
    
    # No conflict (single candidate)
    assert resolver.has_conflict([make_candidate("123 Main St")]) is False
    
    # No conflict (equivalent values)
    assert resolver.has_conflict([
        make_candidate("123 Main St"),
        make_candidate("123 main st ")
    ]) is False
    
    # Conflict
    assert resolver.has_conflict([
        make_candidate("123 Main St"),
        make_candidate("456 Broad St")
    ]) is True


def test_tc_con_02_verification_boost():
    """TC-CON-02: Selects verified canonical facts over unverified recent facts."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=[])
    
    # Both start at 0.50. Verified gets +0.3 boost.
    candidates = [
        make_candidate("Old Address", confidence=0.5, confirmed=True),
        make_candidate("New Address", confidence=0.6, confirmed=False),
    ]
    
    outcome = resolver.resolve("address", candidates, [])
    assert outcome["selected_candidate"]["value"] == "Old Address"
    assert outcome["confidence"] == pytest.approx(0.8)


def test_tc_con_03_reliability_boost():
    """TC-CON-03: Ranks direct-parse (+0.1) higher than OCR (+0.05)."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=[])
    
    candidates = [
        make_candidate("OCR Address", confidence=0.7, method="ocr"),
        make_candidate("Direct Address", confidence=0.7, method="direct-parse"),
    ]
    
    outcome = resolver.resolve("address", candidates, [])
    assert outcome["selected_candidate"]["value"] == "Direct Address"
    assert outcome["confidence"] == pytest.approx(0.8)


def test_tc_con_04_confidence_gate():
    """TC-CON-04: Autofill=1 if Conf >= tau. Requires confirmation if Conf < tau."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=[])
    
    # Confidence reaches 0.9 (0.6 + 0.3 verified) -> >= 0.85 -> no confirmation
    high_conf = make_candidate("High", confidence=0.6, confirmed=True)
    outcome_high = resolver.resolve("first_name", [high_conf], [])
    assert outcome_high["requires_confirmation"] is False
    
    # Confidence reaches 0.8 (0.5 + 0.3 verified) -> < 0.85 -> requires confirmation
    low_conf = make_candidate("Low", confidence=0.5, confirmed=True)
    outcome_low = resolver.resolve("first_name", [low_conf], [])
    assert outcome_low["requires_confirmation"] is True


def test_tc_con_05_sensitive_fields():
    """TC-CON-05: Sensitive fields always require confirmation regardless of confidence."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=["ssn"])
    
    # Even with 1.0 confidence (0.9 + 0.3 verified maxed to 1.0)
    candidate = make_candidate("123-45-678", confidence=0.9, confirmed=True)
    outcome = resolver.resolve("ssn", [candidate], [])
    
    assert outcome["confidence"] == 1.0
    assert outcome["requires_confirmation"] is True
    assert "always requires confirmation" in outcome["decision_reason"]


@pytest.mark.asyncio
async def test_agent_graph_integration_high_confidence():
    """Graph integration: High confidence heuristic skips LLM and goes to READY_TO_FILL."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=["ssn"])
    agent = AutofillAgent(conflict_resolver=resolver, llm_provider=None) # No LLM needed
    
    state: AgentState = {
        "semantic_result": {"concept": "first_name"},
        "structured_candidates": [
            make_candidate("John", confidence=0.8, confirmed=True) # score 1.0
        ],
        "rag_candidates": []
    }
    
    result = await agent._node_conflict_confidence(state)
    assert result["final_response_status"] == FinalResponseStatus.READY_TO_FILL.value
    assert result["conflict_result"]["value"] == "John"


@pytest.mark.asyncio
async def test_agent_graph_integration_sensitive_field():
    """Graph integration: Sensitive field skips LLM and goes to REQUIRES_CONFIRMATION."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=["ssn"])
    agent = AutofillAgent(conflict_resolver=resolver, llm_provider=None)
    
    state: AgentState = {
        "semantic_result": {"concept": "ssn"},
        "structured_candidates": [
            make_candidate("1234", confidence=0.9, confirmed=True) # score 1.0 but sensitive
        ],
        "rag_candidates": []
    }
    
    result = await agent._node_conflict_confidence(state)
    assert result["final_response_status"] == FinalResponseStatus.REQUIRES_CONFIRMATION.value
    assert result["conflict_result"]["value"] == "1234"


@pytest.mark.asyncio
async def test_agent_graph_integration_multiple_candidates_sensitive():
    """Graph integration: Sensitive field with conflicts goes to MULTIPLE_CANDIDATES."""
    resolver = ConflictResolver(confidence_threshold=0.85, sensitive_concepts=["ssn"])
    agent = AutofillAgent(conflict_resolver=resolver, llm_provider=None)
    
    state: AgentState = {
        "semantic_result": {"concept": "ssn"},
        "structured_candidates": [
            make_candidate("1234", confidence=0.9, confirmed=True),
            make_candidate("5678", confidence=0.8, confirmed=True)
        ],
        "rag_candidates": []
    }
    
    result = await agent._node_conflict_confidence(state)
    assert result["final_response_status"] == FinalResponseStatus.MULTIPLE_CANDIDATES.value
