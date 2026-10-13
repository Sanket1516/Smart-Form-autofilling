"""Fact review, conflicts, profile view, saved answers and data deletion (real MongoDB)."""

import pytest

from tests.conftest import Harness
from tests.factories import ID_CARD_LINES, RESUME_LINES, txt_bytes

pytestmark = pytest.mark.mongo


def _upload_both(harness: Harness, headers: dict) -> tuple[str, str]:
    first = harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
        "document_id"
    ]
    second = harness.upload(headers, "id-card.txt", txt_bytes(ID_CARD_LINES)).json()["data"][
        "document_id"
    ]
    harness.wait_processed(headers, first)
    harness.wait_processed(headers, second)
    return first, second


def _conflicts(harness: Harness, headers: dict) -> list[dict]:
    response = harness.client.get("/api/v1/profile/facts/conflicts", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]


def test_cross_document_conflict_is_detected_with_sources(harness: Harness) -> None:
    headers = harness.register()
    resume_id, card_id = _upload_both(harness, headers)
    conflicts = {c["concept"]: c for c in _conflicts(harness, headers)}
    dob = conflicts["personal.date_of_birth"]
    assert dob["conflict_type"] == "CROSS_DOCUMENT"
    values = {c["value"]: c["document_id"] for c in dob["candidates"]}
    assert values == {"1996-02-14": resume_id, "1996-02-15": card_id}

    profile = harness.client.get("/api/v1/profile", headers=headers).json()["data"]
    field = next(f for f in profile["fields"] if f["concept"] == "personal.date_of_birth")
    assert field["status"] == "conflict" and field["value"] is None  # never silently chosen
    assert "date_of_birth" not in profile["personal"]


def test_resolving_a_conflict_by_candidate(harness: Harness) -> None:
    headers = harness.register()
    _upload_both(harness, headers)
    dob = next(c for c in _conflicts(harness, headers) if c["concept"] == "personal.date_of_birth")
    index = next(i for i, c in enumerate(dob["candidates"]) if c["value"] == "1996-02-14")
    response = harness.client.patch(
        "/api/v1/profile/facts/conflicts/personal.date_of_birth/resolve",
        headers=headers,
        json={"resolution": "candidate", "candidate_index": index},
    )
    assert response.status_code == 200, response.text
    view = response.json()["data"]
    assert (
        view["status"] == "resolved" and view["value"] == "1996-02-14" and view["is_user_confirmed"]
    )
    assert all(c["concept"] != "personal.date_of_birth" for c in _conflicts(harness, headers))
    profile = harness.client.get("/api/v1/profile", headers=headers).json()["data"]
    assert profile["personal"]["date_of_birth"] == "1996-02-14"


def test_resolving_with_custom_value_and_reject(harness: Harness) -> None:
    headers = harness.register()
    _upload_both(harness, headers)
    custom = harness.client.patch(
        "/api/v1/profile/facts/conflicts/personal.date_of_birth/resolve",
        headers=headers,
        json={"resolution": "custom", "custom_value": "16/02/1996"},
    )
    assert custom.json()["data"]["value"] == "1996-02-16"
    assert custom.json()["data"]["origin"] == "user_provided"

    headers2 = harness.register()
    _upload_both(harness, headers2)
    reject = harness.client.patch(
        "/api/v1/profile/facts/conflicts/personal.date_of_birth/resolve",
        headers=headers2,
        json={"resolution": "reject"},
    )
    assert reject.status_code == 200
    profile = harness.client.get("/api/v1/profile", headers=headers2).json()["data"]
    assert not any(f["concept"] == "personal.date_of_birth" for f in profile["fields"])


def test_unknown_or_foreign_conflicts_return_404(harness: Harness) -> None:
    owner = harness.register()
    _upload_both(harness, owner)
    intruder = harness.register()
    response = harness.client.patch(
        "/api/v1/profile/facts/conflicts/personal.date_of_birth/resolve",
        headers=intruder,
        json={"resolution": "candidate_a"},
    )
    assert response.status_code == 404
    assert _conflicts(harness, intruder) == []


def test_new_document_disagreeing_with_a_confirmed_value_is_flagged(harness: Harness) -> None:
    headers = harness.register()
    harness.wait_processed(
        headers,
        harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
            "document_id"
        ],
    )
    dob = next(
        f
        for f in harness.client.get("/api/v1/profile/facts", headers=headers).json()["data"][
            "facts"
        ]
        if f["concept"] == "personal.date_of_birth"
    )
    confirm = harness.client.put(
        f"/api/v1/profile/facts/{dob['fact_id']}", headers=headers, json={"value": dob["value"]}
    )
    assert confirm.json()["data"]["is_user_confirmed"] is True
    harness.wait_processed(
        headers,
        harness.upload(headers, "id.txt", txt_bytes(ID_CARD_LINES)).json()["data"]["document_id"],
    )
    conflict = next(
        c for c in _conflicts(harness, headers) if c["concept"] == "personal.date_of_birth"
    )
    assert conflict["conflict_type"] == "VERIFIED_VS_NEW"


def test_editing_a_fact_creates_a_user_value_and_records_a_correction(harness: Harness) -> None:
    headers = harness.register()
    harness.wait_processed(
        headers,
        harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
            "document_id"
        ],
    )
    city = next(
        f
        for f in harness.client.get("/api/v1/profile/facts", headers=headers).json()["data"][
            "facts"
        ]
        if f["concept"] == "address.city"
    )
    edited = harness.client.put(
        f"/api/v1/profile/facts/{city['fact_id']}", headers=headers, json={"value": "Shelbyville"}
    ).json()["data"]
    assert edited["value"] == "Shelbyville" and edited["origin"] == "user_provided"
    assert edited["source_document_id"] == "user"
    corrections = harness.client.get("/api/v1/profile/corrections", headers=headers).json()["data"][
        "corrections"
    ]
    assert corrections[0]["original_value"] == "Springfield"
    assert (
        harness.client.get("/api/v1/profile", headers=headers).json()["data"]["address"]["city"]
        == "Shelbyville"
    )


def test_profile_update_and_invalid_values(harness: Harness) -> None:
    headers = harness.register()
    ok = harness.client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "fields": {"personal.full_name": "Avery Example"},
            "contact": {"email": "Avery@Example.com"},
        },
    )
    assert ok.status_code == 200 and ok.json()["data"]["saved"] == 2
    profile = harness.client.get("/api/v1/profile", headers=headers).json()["data"]
    assert profile["personal"]["full_name"] == "Avery Example"
    assert profile["contact"]["email"] == "avery@example.com"
    unknown = harness.client.put(
        "/api/v1/profile", headers=headers, json={"fields": {"made.up": "x"}}
    )
    assert unknown.status_code == 422


def test_memories_and_profile_answers(harness: Harness) -> None:
    headers = harness.register()
    concept_answer = harness.client.post(
        "/api/v1/profile/memories",
        headers=headers,
        json={"label": "Email", "concept": "personal.email", "value": "me@example.com"},
    )
    assert concept_answer.status_code == 201
    assert (
        harness.client.get("/api/v1/profile", headers=headers).json()["data"]["contact"]["email"]
        == "me@example.com"
    )
    free = harness.client.post(
        "/api/v1/profile/memories",
        headers=headers,
        json={
            "label": "Why do you want to join?",
            "concept": "free_text",
            "value": "To learn data engineering.",
        },
    ).json()["data"]
    memories = harness.client.get("/api/v1/profile/memories", headers=headers).json()["data"][
        "memories"
    ]
    assert [m["memory_id"] for m in memories] == [free["memory_id"]]
    assert free["indexed"] is True and harness.vectors.items
    assert (
        harness.client.delete(
            f"/api/v1/profile/memories/{free['memory_id']}", headers=headers
        ).status_code
        == 200
    )
    assert not harness.vectors.items
    other = harness.register()
    assert (
        harness.client.delete(
            f"/api/v1/profile/memories/{free['memory_id']}", headers=other
        ).status_code
        == 404
    )


def test_delete_all_data_removes_everything_but_the_account(harness: Harness) -> None:
    headers = harness.register()
    other = harness.register()
    _upload_both(harness, headers)
    harness.wait_processed(
        other,
        harness.upload(other, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"]["document_id"],
    )
    response = harness.client.delete("/api/v1/profile/data", headers=headers)
    assert response.status_code == 200
    assert harness.client.get("/api/v1/documents", headers=headers).json()["data"]["total"] == 0
    assert (
        harness.client.get("/api/v1/profile/facts", headers=headers).json()["data"]["facts"] == []
    )
    assert harness.client.get("/api/v1/auth/me", headers=headers).status_code == 200
    # the other user's data is untouched
    assert harness.client.get("/api/v1/documents", headers=other).json()["data"]["total"] == 1
    assert harness.vectors.items
