"""Tests for Routing and Structured Retrieval Nodes per TEST_PLAN TC-ROUTE and TC-SR."""

from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.agents.state import AgentState
from app.agents.graph import AutofillAgent
from app.schemas.facts import FactData
from app.services.facts import FactService
from app.schemas.forms import FieldObject

class MockFactService:
    def __init__(self, facts: list[Any] = None) -> None:
        self._facts = facts or []

    async def list(self, user_id: str, concept: str | None = None, source_document_id: str | None = None, confirmed: bool | None = None) -> Any:
        class MockFactsData:
            def __init__(self, facts):
                self.facts = facts
        
        filtered = self._facts
        if concept:
            filtered = [f for f in filtered if f.concept == concept]
        if confirmed is not None:
            filtered = [f for f in filtered if f.is_user_confirmed == confirmed]
            
        return MockFactsData(filtered)


@pytest.fixture
def mock_fact() -> FactData:
    return FactData(
        fact_id="fact-1",
        concept="first_name",
        value="John",
        value_type="string",
        source_document_id="doc-1",
        source_page=1,
        confidence=0.99,
        provenance={"extraction_method": "direct-parse"},
        is_user_confirmed=True,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        source={"document_id": "doc-1", "page": 1}
    )


@pytest.mark.asyncio
async def test_route_structured_retrieval(mock_fact: FactData):
    """TC-ROUTE-01: Routes to structured retrieval when a canonical fact exists."""
    fact_service = MockFactService(facts=[mock_fact])
    agent = AutofillAgent(fact_service=fact_service)
    
    state: AgentState = {
        "user_id": "user1",
        "semantic_result": {"concept": "first_name"}
    }
    
    route = await agent._route_retrieval(state)
    assert route == "structured_retrieval"


@pytest.mark.asyncio
async def test_route_missing_information():
    """TC-ROUTE-02: Routes to rag_retrieval when no facts exist and concept is known."""
    fact_service = MockFactService(facts=[])
    agent = AutofillAgent(fact_service=fact_service)
    
    state: AgentState = {
        "user_id": "user1",
        "semantic_result": {"concept": "first_name"}
    }
    
    route = await agent._route_retrieval(state)
    assert route == "rag_retrieval"


@pytest.mark.asyncio
async def test_route_rag_retrieval():
    """TC-ROUTE-03: Routes to RAG retrieval when concept is unknown (contextual evidence)."""
    fact_service = MockFactService(facts=[])
    agent = AutofillAgent(fact_service=fact_service)
    
    state: AgentState = {
        "user_id": "user1",
        "semantic_result": {"concept": "unknown"}
    }
    
    route = await agent._route_retrieval(state)
    assert route == "rag_retrieval"


@pytest.mark.asyncio
async def test_node_structured_retrieval(mock_fact: FactData):
    """TC-SR-01: Structured Retrieval Node returns candidates."""
    fact_service = MockFactService(facts=[mock_fact])
    agent = AutofillAgent(fact_service=fact_service)
    
    state: AgentState = {
        "user_id": "user1",
        "semantic_result": {"concept": "first_name"}
    }
    
    result = await agent._node_structured_retrieval(state)
    assert result["retrieval_route"] == "structured_retrieval"
    assert len(result["structured_candidates"]) == 1
    assert result["structured_candidates"][0]["value"] == "John"


def test_structured_retrieval_api(test_client: TestClient, auth_headers: dict):
    """TC-SR-02, TC-SR-03: API POST /retrieval/structured works."""
    # Note: Requires FactService in app.state which is injected in main.py but mock facts would be empty
    payload = {
        "concept": "first_name",
        "verified_only": False
    }
    response = test_client.post("/api/v1/retrieval/structured", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "results" in data["data"]
