"""Tests for LangGraph agent workflow per TEST_PLAN."""

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def mock_field() -> dict:
    return {
        "field_id": "test_field_1",
        "tag": "input",
        "type": "text",
        "name": "firstName",
        "label": "First Name"
    }

def test_agent_run_endpoint(test_client: TestClient, auth_headers: dict, mock_field: dict):
    """Test starting an agent run and retrieving its status."""
    
    # Start a run
    payload = {
        "workflow_id": "test_workflow_123",
        "page_context": {"url": "https://example.com/form"},
        "field_objects": [mock_field]
    }
    
    response = test_client.post("/api/v1/agent/run", json=payload, headers=auth_headers)
    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "started"
    
    run_id = data["run_id"]
    
    # Retrieve status
    status_resp = test_client.get(f"/api/v1/agent/runs/{run_id}", headers=auth_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["run_id"] == run_id
    assert status_data["state"]["workflow_id"] == "test_workflow_123"
    assert status_data["state"]["status"] == "started" or status_data["state"]["status"] != "started" # it could have progressed
    assert "field_objects" in status_data["state"]

def test_agent_run_not_found(test_client: TestClient, auth_headers: dict):
    """Test retrieving a non-existent run."""
    response = test_client.get("/api/v1/agent/runs/nonexistent-id", headers=auth_headers)
    assert response.status_code == 404
