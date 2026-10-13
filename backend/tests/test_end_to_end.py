"""End-to-end acceptance flow through the HTTP API (real MongoDB, mock LLM, vector double).

Create account -> upload synthetic document -> process -> review facts -> resolve
conflict -> open session for the sample form -> analyze -> review -> approved
values -> report fill results -> complete.
"""

import pytest

from tests.conftest import Harness
from tests.factories import ID_CARD_LINES, RESUME_LINES, pdf_bytes, txt_bytes

pytestmark = pytest.mark.mongo

SAMPLE_FORM_FIELDS = [
    {
        "field_id": "full_legal_name",
        "label": "Full legal name",
        "input_type": "text",
        "required": True,
    },
    {
        "field_id": "email_address",
        "label": "Email address",
        "input_type": "email",
        "required": True,
    },
    {"field_id": "phone_number", "label": "Phone number", "input_type": "tel"},
    {"field_id": "date_of_birth", "label": "Date of birth", "input_type": "date", "required": True},
    {"field_id": "postal_code", "label": "Postal code", "input_type": "text"},
    {"field_id": "education", "label": "Highest qualification", "input_type": "text"},
]


def test_complete_acceptance_flow(harness: Harness) -> None:
    client = harness.client
    headers = harness.register("Avery Quinn Example")

    resume = harness.upload(
        headers, "resume.pdf", pdf_bytes(RESUME_LINES), "application/pdf"
    ).json()["data"]
    id_card = harness.upload(headers, "id-card.txt", txt_bytes(ID_CARD_LINES)).json()["data"]
    assert harness.wait_processed(headers, resume["document_id"])["status"] == "processed"
    assert harness.wait_processed(headers, id_card["document_id"])["index_status"] == "indexed"

    # Review extracted facts: confirm the heuristic name, resolve the DOB conflict.
    facts = client.get("/api/v1/profile/facts", headers=headers).json()["data"]["facts"]
    name = next(
        f for f in facts if f["concept"] == "personal.full_name" and f["origin"] == "inferred"
    )
    client.put(
        f"/api/v1/profile/facts/{name['fact_id']}", headers=headers, json={"value": name["value"]}
    )
    conflict = next(
        c
        for c in client.get("/api/v1/profile/facts/conflicts", headers=headers).json()["data"]
        if c["concept"] == "personal.date_of_birth"
    )
    chosen = next(
        i for i, c in enumerate(conflict["candidates"]) if c["document_id"] == resume["document_id"]
    )
    resolved = client.patch(
        "/api/v1/profile/facts/conflicts/personal.date_of_birth/resolve",
        headers=headers,
        json={"resolution": "candidate", "candidate_index": chosen},
    )
    assert resolved.json()["data"]["value"] == "1996-02-14"

    # The extension opens a session for the sample form and requests analysis.
    session_id = client.post(
        "/api/v1/forms/sessions",
        headers=headers,
        json={
            "website_origin": "http://127.0.0.1:8765",
            "page_url": "http://127.0.0.1:8765/sample-form.html",
            "form_id": "application",
        },
    ).json()["data"]["session_id"]
    assert (
        client.post(
            f"/api/v1/forms/sessions/{session_id}/analyze",
            headers=headers,
            json={"fields": SAMPLE_FORM_FIELDS},
        ).status_code
        == 202
    )
    recs = {
        r["field_id"]: r
        for r in client.get(
            f"/api/v1/forms/sessions/{session_id}/recommendations", headers=headers
        ).json()["data"]["recommendations"]
    }
    assert recs["full_legal_name"]["recommended_value"] == "Avery Quinn Example"
    assert recs["email_address"]["recommended_value"] == "avery.example@example.com"
    assert recs["phone_number"]["recommended_value"] == "+15550104477"
    assert recs["date_of_birth"]["recommended_value"] == "1996-02-14"
    assert recs["postal_code"]["recommended_value"] == "560001"
    assert recs["education"]["recommended_value"] == "Bachelor of Technology in Computer Science"
    for rec in recs.values():
        assert rec["reason"] and 0.0 <= rec["confidence"] <= 1.0

    # The user approves everything that still needs review.
    pending = [r["field_id"] for r in recs.values() if r["status"] == "needs_review"]
    if pending:
        client.post(
            f"/api/v1/forms/sessions/{session_id}/decisions",
            headers=headers,
            json={"decisions": [{"field_id": f, "decision": "approve"} for f in pending]},
        )
    approved = client.get(
        f"/api/v1/forms/sessions/{session_id}/approved-values", headers=headers
    ).json()["data"]
    values = {v["field_id"]: v["value"] for v in approved["approved_values"]}
    assert set(values) == {f["field_id"] for f in SAMPLE_FORM_FIELDS}

    # The extension fills the page, verifies, and reports back; nothing is submitted.
    results = [{"field_id": f, "applied": True, "verified": True} for f in values]
    verify = client.post(
        f"/api/v1/forms/sessions/{session_id}/verify", headers=headers, json={"results": results}
    )
    assert verify.json()["data"]["filled_fields"] == len(values)
    complete = client.post(
        f"/api/v1/forms/sessions/{session_id}/complete",
        headers=headers,
        json={"submission_status": "not_submitted"},
    )
    assert complete.json()["data"]["status"] == "closed"
