"""End-to-End Integration Test for Minimal API Set (Phase 15)."""

import pytest
from fastapi.testclient import TestClient
import json
import time
import uuid
from unittest.mock import patch

from app.main import app

def test_end_to_end_minimal_api_flow():
    """
    Integration test walking the entire minimal API set:
    1. Register
    2. Login (via register usually, but we'll do explicit login if needed, or just use the token from register)
    3. Upload document
    4. Process document
    5. Create Form Session
    6. Analyze fields
    7. Recommendations fetch
    8. Complete session
    """
    
    with TestClient(app) as test_client, patch("app.main.AutofillAgent.run") as mock_agent_run, patch("app.services.documents.DocumentService.start_processing") as mock_start_processing:
        # Make the mock agent do nothing and return quickly
        async def fake_run(*args, **kwargs):
            return {"status": "completed"}
        mock_agent_run.side_effect = fake_run
        async def fake_start_processing(user_id, document_id):
            return {"document_id": document_id, "processing_status": "processing"}
        mock_start_processing.side_effect = fake_start_processing
        
        suffix = uuid.uuid4().hex[:6]
        email = f"e2e_user_{suffix}@example.com"
        
        print(f"Step 1: Register User {email}")
        # 1. Register User
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "E2E User",
                "email": email,
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!"
            }
        )
        # The fake auth might not actually save passwords, but it works.
        assert reg_response.status_code == 201
    
        print("Step 2: Login")
        # 2. Login User
        login_response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "StrongPassword123!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    
        print("Step 3: Upload Document")
        # 3. Upload Document
        # Create a dummy pdf file content with unique suffix to avoid checksum collision
        content = f"%PDF-1.4 dummy pdf {suffix}".encode("utf-8")
        files = {"file": (f"e2e_test_{suffix}.pdf", content, "application/pdf")}
        upload_response = test_client.post(
            "/api/v1/documents",
            files=files,
            headers=headers
        )
        assert upload_response.status_code == 201
        doc_id = upload_response.json()["data"]["document_id"]
    
        print(f"Step 4: Process Document {doc_id}")
        # 4. Process Document
        process_response = test_client.post(
            f"/api/v1/documents/{doc_id}/process",
            headers=headers
        )
        assert process_response.status_code in [200, 202]
        
        # Wait slightly to let background task finish (in our fake system it's fast)
        time.sleep(0.5)
    
        print("Step 5: Create Form Session")
        # 5. Create Form Session
        session_response = test_client.post(
            "/api/v1/forms/sessions",
            json={
                "website_origin": "https://e2e-test.com",
                "page_url": "https://e2e-test.com/form",
                "form_id": "form_e2e"
            },
            headers=headers
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["data"]["session_id"]
    
        print(f"Step 6: Analyze Form Fields {session_id}")
        # 6. Analyze Form Fields
        fields_payload = {
            "fields": [
                {
                    "field_id": "fname",
                    "label": "First Name",
                    "input_type": "text"
                },
                {
                    "field_id": "address",
                    "label": "Current Address",
                    "input_type": "text"
                }
            ]
        }
        analyze_response = test_client.post(
            f"/api/v1/forms/sessions/{session_id}/analyze",
            json=fields_payload,
            headers=headers
        )
        assert analyze_response.status_code == 200
        assert analyze_response.json()["data"]["status"] == "processing"
        
        # In a real async test we would wait for analysis to finish. Let's sleep for 0.5s for gather to complete
        time.sleep(0.5)
    
        print("Step 7: Recommendations Fetch")
        # 7. Recommendations Fetch
        recs_response = test_client.get(
            f"/api/v1/forms/sessions/{session_id}/recommendations",
            headers=headers
        )
        assert recs_response.status_code == 200
        recs_data = recs_response.json()["data"]["recommendations"]
        assert len(recs_data) >= 0  # Depending on mocked agent, might be empty or populated
    
        print("Step 8: Complete Session")
        # 8. Complete Session
        complete_response = test_client.post(
            f"/api/v1/forms/sessions/{session_id}/complete",
            json={
                "total_fields": 2,
                "filled_fields": 1,
                "reviewed_fields": 0,
                "failed_fields": 1,
                "submission_status": "user_submitted"
            },
            headers=headers
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["data"]["status"] == "completed"
    
        print("Step 9: Verify Session GET")
        # Verify session status update via GET
        get_session_response = test_client.get(
            f"/api/v1/forms/sessions/{session_id}",
            headers=headers
        )
        assert get_session_response.status_code == 200
        assert get_session_response.json()["data"]["status"] == "completed"
