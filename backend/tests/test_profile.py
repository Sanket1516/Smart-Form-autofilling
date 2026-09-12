"""Tests for Profile read/update, fact aggregation, and history-preserving corrections."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from app.core.security import decode_access_token
from app.models.documents import StructuredFact
from app.schemas.facts import FactUpdateRequest
from app.services.corrections import CorrectionsService
from app.services.facts import FactService
from app.services.profile import ProfileService


class FakeProfilesRepository:
    def __init__(self) -> None:
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1

    async def get_for_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return next((p for p in self.profiles.values() if p["user_id"] == user_id), None)

    async def create(self, user_id: str, document: Any) -> Dict[str, Any]:
        profile_id = f"profile-{self.next_id}"
        self.next_id += 1
        record = {"_id": profile_id, **document.model_dump(exclude_none=True)}
        self.profiles[profile_id] = record
        return record

    async def update(self, user_id: str, profile_id: str, updates: Dict[str, Any]) -> bool:
        record = self.profiles.get(profile_id)
        if not record or record["user_id"] != user_id:
            return False
        record.update(updates)
        return True


class FakeStructuredFactsRepository:
    def __init__(self) -> None:
        self.facts: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1

    async def list(self, user_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        result = [f for f in self.facts.values() if f["user_id"] == user_id]
        if filters:
            for k, v in filters.items():
                result = [f for f in result if f.get(k) == v]
        return result

    async def list_filtered(
        self,
        user_id: str,
        concept: Optional[str] = None,
        source_document_id: Optional[str] = None,
        confirmed: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        filters: Dict[str, Any] = {}
        if concept is not None:
            filters["concept"] = concept
        if source_document_id is not None:
            filters["source_document_id"] = source_document_id
        if confirmed is not None:
            filters["is_user_confirmed"] = confirmed
        return await self.list(user_id, filters)

    async def get(self, user_id: str, fact_id: str) -> Optional[Dict[str, Any]]:
        record = self.facts.get(fact_id)
        return record if record and record["user_id"] == user_id else None

    async def create(self, user_id: str, document: Any) -> Dict[str, Any]:
        fact_id = f"fact-{self.next_id}"
        self.next_id += 1
        record = {"_id": fact_id, **document.model_dump(exclude_none=True)}
        self.facts[fact_id] = record
        return record

    async def update(self, user_id: str, fact_id: str, updates: Dict[str, Any]) -> bool:
        record = await self.get(user_id, fact_id)
        if not record:
            return False
        record.update(updates)
        return True


class FakeCorrectionsRepository:
    def __init__(self) -> None:
        self.corrections: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1

    async def create(self, user_id: str, document: Any) -> Dict[str, Any]:
        corr_id = f"corr-{self.next_id}"
        self.next_id += 1
        record = {"_id": corr_id, **document.model_dump(exclude_none=True)}
        self.corrections[corr_id] = record
        return record

    async def list(self, user_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        result = [c for c in self.corrections.values() if c["user_id"] == user_id]
        if filters:
            for k, v in filters.items():
                result = [c for c in result if c.get(k) == v]
        return result


@pytest.fixture
def profile_test_setup(test_client: TestClient):
    profiles_repo = FakeProfilesRepository()
    facts_repo = FakeStructuredFactsRepository()
    corrections_repo = FakeCorrectionsRepository()

    test_client.app.state.profile_service = ProfileService(profiles_repo, facts_repo)
    test_client.app.state.corrections_service = CorrectionsService(corrections_repo)
    test_client.app.state.fact_service = FactService(
        facts_repo, corrections_repository=corrections_repo
    )
    return {
        "profiles_repo": profiles_repo,
        "facts_repo": facts_repo,
        "corrections_repo": corrections_repo,
    }


def get_test_user_id(test_client: TestClient, auth_headers: Dict[str, str]) -> str:
    token = auth_headers["Authorization"].split(" ")[1]
    payload = decode_access_token(token, test_client.app.state.settings)
    return payload["sub"]


def test_get_empty_profile(
    test_client: TestClient, auth_headers: Dict[str, str], profile_test_setup
) -> None:
    response = test_client.get("/api/v1/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    profile = data["data"]
    assert "user_id" in profile
    assert profile["personal"] == {}
    assert profile["contact"] == {}
    assert profile["address"] == {}
    assert profile["education"] == []
    assert profile["employment"] == []


@pytest.mark.asyncio
async def test_profile_merges_structured_facts(
    test_client: TestClient, auth_headers: Dict[str, str], profile_test_setup
) -> None:
    facts_repo = profile_test_setup["facts_repo"]
    user_id = get_test_user_id(test_client, auth_headers)

    now = datetime.now(UTC)
    fact1 = StructuredFact(
        user_id=user_id,
        concept="full_name",
        value="Jane Doe",
        value_type="string",
        source_document_id="doc_1",
        source_page=1,
        confidence=0.95,
        provenance={"document_name": "resume.pdf", "extraction_method": "llm", "extracted_text": "Jane Doe"},
        is_user_confirmed=True,
        created_at=now,
        updated_at=now,
    )
    fact2 = StructuredFact(
        user_id=user_id,
        concept="date_of_birth",
        value="1995-05-20",
        value_type="date",
        source_document_id="doc_1",
        source_page=1,
        confidence=0.90,
        provenance={"document_name": "resume.pdf", "extraction_method": "rule", "extracted_text": "20/05/1995"},
        is_user_confirmed=False,
        created_at=now,
        updated_at=now,
    )
    fact3 = StructuredFact(
        user_id=user_id,
        concept="email",
        value="jane.doe@example.com",
        value_type="email",
        source_document_id="doc_1",
        source_page=1,
        confidence=0.98,
        provenance={"document_name": "resume.pdf", "extraction_method": "regex", "extracted_text": "jane.doe@example.com"},
        is_user_confirmed=True,
        created_at=now,
        updated_at=now,
    )
    fact4 = StructuredFact(
        user_id=user_id,
        concept="current_address",
        value="123 Main St, New York, NY",
        value_type="string",
        source_document_id="doc_1",
        source_page=1,
        confidence=0.88,
        provenance={"document_name": "resume.pdf", "extraction_method": "ner", "extracted_text": "123 Main St"},
        is_user_confirmed=False,
        created_at=now,
        updated_at=now,
    )

    await facts_repo.create(user_id, fact1)
    await facts_repo.create(user_id, fact2)
    await facts_repo.create(user_id, fact3)
    await facts_repo.create(user_id, fact4)

    response = test_client.get("/api/v1/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    profile = data["data"]

    assert profile["personal"]["full_name"] == "Jane Doe"
    assert profile["personal"]["date_of_birth"] == "1995-05-20"
    assert profile["contact"]["email"] == "jane.doe@example.com"
    assert profile["address"]["current"] == "123 Main St, New York, NY"


def test_update_profile(
    test_client: TestClient, auth_headers: Dict[str, str], profile_test_setup
) -> None:
    payload = {
        "personal": {"full_name": "Jane Updated Name", "gender": "Female"},
        "contact": {"phone": "1234567890"},
        "address": {"permanent": "456 Oak Rd, Boston, MA"},
    }
    response = test_client.put("/api/v1/profile", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["updated"] is True

    get_res = test_client.get("/api/v1/profile", headers=auth_headers)
    assert get_res.status_code == 200
    profile = get_res.json()["data"]
    assert profile["personal"]["full_name"] == "Jane Updated Name"
    assert profile["personal"]["gender"] == "Female"
    assert profile["contact"]["phone"] == "1234567890"
    assert profile["address"]["permanent"] == "456 Oak Rd, Boston, MA"


@pytest.mark.asyncio
async def test_fact_correction_records_history(
    test_client: TestClient, auth_headers: Dict[str, str], profile_test_setup
) -> None:
    facts_repo = profile_test_setup["facts_repo"]
    user_id = get_test_user_id(test_client, auth_headers)
    now = datetime.now(UTC)

    fact = StructuredFact(
        user_id=user_id,
        concept="phone",
        value="0000000000",
        value_type="phone",
        source_document_id="doc_2",
        source_page=1,
        confidence=0.70,
        provenance={"document_name": "id.pdf", "extraction_method": "ocr", "extracted_text": "0000000000"},
        is_user_confirmed=False,
        created_at=now,
        updated_at=now,
    )
    created = await facts_repo.create(user_id, fact)
    fact_id = str(created["_id"])

    update_payload = {"value": "+19876543210", "is_user_confirmed": True, "reason": "Corrected typo"}
    put_res = test_client.put(
        f"/api/v1/profile/facts/{fact_id}", json=update_payload, headers=auth_headers
    )
    assert put_res.status_code == 200
    assert put_res.json()["data"]["value"] == "+19876543210"

    corr_res = test_client.get("/api/v1/profile/corrections", headers=auth_headers)
    assert corr_res.status_code == 200
    corrections = corr_res.json()["data"]["corrections"]
    assert len(corrections) >= 1

    matched = [c for c in corrections if c["field_id"] == fact_id]
    assert len(matched) == 1
    corr = matched[0]
    assert corr["concept"] == "phone"
    assert corr["original_value"] == "0000000000"
    assert corr["corrected_value"] == "+19876543210"
    assert corr["reason"] == "Corrected typo"


def test_standalone_correction_creation(
    test_client: TestClient, auth_headers: Dict[str, str], profile_test_setup
) -> None:
    payload = {
        "session_id": "session_99",
        "field_id": "field_address",
        "concept": "current_address",
        "original_value": "Old Address",
        "corrected_value": "New Address",
        "reason": "Moved to new house",
    }
    res = test_client.post("/api/v1/corrections", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["concept"] == "current_address"
    assert data["original_value"] == "Old Address"
    assert data["corrected_value"] == "New Address"
    assert data["reason"] == "Moved to new house"
