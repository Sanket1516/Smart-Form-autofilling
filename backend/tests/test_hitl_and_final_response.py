"""Tests for HITL and Final Response Nodes (API_SPECIFICATION §34-35)."""

from __future__ import annotations

import uuid
from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.db.repositories.recommendations import RecommendationsRepository
from app.agents.graph import AutofillAgent
from app.agents.state import AgentState
from app.agents.enums import FinalResponseStatus
from app.main import app


class FakeRecommendationsRepository:
    def __init__(self):
        self.recs = []

    async def create_recommendation(
        self, user_id, session_id, field_id, field_label, concept,
        recommended_value, confidence, retrieval_type, source_fact_ids,
        status, decision_reason=""
    ):
        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        self.recs.append({
            "_id": rec_id,
            "user_id": user_id,
            "session_id": session_id,
            "field_id": field_id,
            "field_label": field_label,
            "concept": concept,
            "recommended_value": recommended_value,
            "confidence": confidence,
            "retrieval_type": retrieval_type,
            "source_fact_ids": source_fact_ids,
            "status": status,
            "reason": decision_reason
        })
        return rec_id

    async def get_pending_reviews(self, user_id: str):
        return [r for r in self.recs if r["user_id"] == user_id and r["status"] == "pending_review"]

    async def get_recommendation(self, user_id: str, rec_id: str):
        return next((r for r in self.recs if r["_id"] == rec_id and r["user_id"] == user_id), None)

    async def update_status(self, user_id: str, rec_id: str, status: str, value: str | None = None):
        for r in self.recs:
            if r["_id"] == rec_id and r["user_id"] == user_id:
                r["status"] = status
                if value is not None:
                    r["recommended_value"] = value
                return True
        return False


@pytest.fixture
def fake_repo():
    repo = FakeRecommendationsRepository()
    original = app.state.recommendations_repo
    app.state.recommendations_repo = repo
    yield repo
    app.state.recommendations_repo = original


@pytest.mark.asyncio
async def test_hitl_01_get_pending_reviews(
    test_client: TestClient,
    fake_repo: FakeRecommendationsRepository,
    auth_headers: dict[str, str]
):
    """TC-HITL-01: GET /reviews/pending returns pending_review recommendations."""
    # The token from auth_headers maps to user-1 in the fake users db of test_client.
    # In conftest, the fake user gets an ID, but for the endpoint it looks at request.state.user_id.
    # Let's just create the recommendation under the exact user_id that gets extracted, or we can check the response.
    # We will create it under "user-1" (the first user created by FakeUsers in conftest).
    user_id = "user-1"
    
    rec_id = await fake_repo.create_recommendation(
        user_id=user_id,
        session_id="wf-1",
        field_id="f1",
        field_label="Label",
        concept="concept",
        recommended_value="val",
        confidence=0.5,
        retrieval_type="mixed",
        source_fact_ids=["fact-1"],
        status="pending_review",
        decision_reason="test"
    )
    
    resp = test_client.get("/api/v1/reviews/pending", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]["reviews"]
    assert len(data) >= 1
    assert any(r["review_id"] == rec_id for r in data)


@pytest.mark.asyncio
async def test_hitl_02_post_decision_confirm(
    test_client: TestClient,
    fake_repo: FakeRecommendationsRepository,
    auth_headers: dict[str, str]
):
    """TC-HITL-02: POST /decision confirm updates to approved."""
    user_id = "user-1"
    
    rec_id = await fake_repo.create_recommendation(
        user_id=user_id,
        session_id="wf-1",
        field_id="f1",
        field_label="Label",
        concept="concept",
        recommended_value="val",
        confidence=0.5,
        retrieval_type="mixed",
        source_fact_ids=[],
        status="pending_review",
    )
    
    resp = test_client.post(
        f"/api/v1/reviews/{rec_id}/decision",
        json={"decision": "confirm"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"
    
    doc = await fake_repo.get_recommendation(user_id, rec_id)
    assert doc["status"] == "approved"


@pytest.mark.asyncio
async def test_hitl_03_post_decision_edit(
    test_client: TestClient,
    fake_repo: FakeRecommendationsRepository,
    auth_headers: dict[str, str]
):
    """TC-HITL-03: POST /decision edit updates value and status."""
    user_id = "user-1"
    
    rec_id = await fake_repo.create_recommendation(
        user_id=user_id,
        session_id="wf-1",
        field_id="f1",
        field_label="Label",
        concept="concept",
        recommended_value="val",
        confidence=0.5,
        retrieval_type="mixed",
        source_fact_ids=[],
        status="pending_review",
    )
    
    resp = test_client.post(
        f"/api/v1/reviews/{rec_id}/decision",
        json={"decision": "edit", "value": "new_val"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    
    doc = await fake_repo.get_recommendation(user_id, rec_id)
    assert doc["status"] == "edited"
    assert doc["recommended_value"] == "new_val"


@pytest.mark.asyncio
async def test_hitl_04_post_decision_reject(
    test_client: TestClient,
    fake_repo: FakeRecommendationsRepository,
    auth_headers: dict[str, str]
):
    """TC-HITL-04: POST /decision reject sets status to rejected."""
    user_id = "user-1"
    
    rec_id = await fake_repo.create_recommendation(
        user_id=user_id,
        session_id="wf-1",
        field_id="f1",
        field_label="Label",
        concept="concept",
        recommended_value="val",
        confidence=0.5,
        retrieval_type="mixed",
        source_fact_ids=[],
        status="pending_review",
    )
    
    resp = test_client.post(
        f"/api/v1/reviews/{rec_id}/decision",
        json={"decision": "reject"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    
    doc = await fake_repo.get_recommendation(user_id, rec_id)
    assert doc["status"] == "rejected"


@pytest.mark.asyncio
async def test_hitl_05_final_response_creates_pending_review(
    fake_repo: FakeRecommendationsRepository
):
    """TC-HITL-05: final_response creates pending_review recommendation for waiting_human."""
    agent = AutofillAgent(recommendations_repo=fake_repo) # type: ignore
    state: AgentState = {
        "user_id": "test_user_agent",
        "workflow_id": "wf-1",
        "semantic_result": {"concept": "address"},
        "status": "waiting_human",
        "final_response_status": FinalResponseStatus.REQUIRES_CONFIRMATION.value,
        "conflict_result": {"value": "123 Main St", "reason": "conflict"}
    }
    
    result = await agent._node_final_response(state)
    assert result["status"] == "waiting_human"
    
    docs = await fake_repo.get_pending_reviews("test_user_agent")
    assert len(docs) >= 1
    assert any(d["recommended_value"] == "123 Main St" for d in docs)


@pytest.mark.asyncio
async def test_hitl_06_final_response_creates_generated(
    fake_repo: FakeRecommendationsRepository
):
    """TC-HITL-06: final_response creates generated recommendation for filling."""
    agent = AutofillAgent(recommendations_repo=fake_repo) # type: ignore
    state: AgentState = {
        "user_id": "test_user_agent_2",
        "workflow_id": "wf-2",
        "semantic_result": {"concept": "address"},
        "status": "filling",
        "final_response_status": FinalResponseStatus.READY_TO_FILL.value,
        "conflict_result": {"value": "123 Main St", "reason": "no conflict"}
    }
    
    result = await agent._node_final_response(state)
    assert result["status"] == "filling"
    
    docs = await fake_repo.get_pending_reviews("test_user_agent_2")
    assert len(docs) == 0 # because it's 'generated'
