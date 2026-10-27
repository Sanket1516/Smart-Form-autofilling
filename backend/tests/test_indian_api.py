"""API flow for Indian documents: upload -> classify -> profile -> exam readiness."""

import io

import pytest

from tests.indian_fixtures import AADHAAR_FRONT, CLASS12_HSC_SCANNED

pytestmark = pytest.mark.mongo


def _txt(fixture) -> bytes:
    return fixture.normalized().text.encode("utf-8")


def _upload(harness, headers, fixture):
    response = harness.upload(headers, f"{fixture.fixture_id}.txt", _txt(fixture), "text/plain")
    assert response.status_code in (200, 201, 202), response.text
    return harness.wait_processed(headers, response.json()["data"]["document_id"])


def test_marksheet_and_aadhaar_flow(harness) -> None:
    headers = harness.register("Aarav Example")
    marksheet = _upload(harness, headers, CLASS12_HSC_SCANNED)
    aadhaar = _upload(harness, headers, AADHAAR_FRONT)
    assert marksheet["status"] == "processed" and marksheet["document_type"] == "CLASS_12_MARKSHEET"
    assert aadhaar["document_type"] == "AADHAAR_CARD"
    assert marksheet["document_type_confidence"] > 0.6

    profile = harness.client.get("/api/v1/profile", headers=headers).json()["data"]
    fields = {f["concept"]: f for f in profile["fields"]}
    subjects = fields["academic.class12.subjects"]
    assert subjects["group"] == "subjects"
    assert {row["name"] for row in subjects["values"]} >= {"PHYSICS", "CHEMISTRY", "BIOLOGY"}
    assert fields["academic.class12.percentage"]["value"] == "88.67"
    assert fields["identity.aadhaar_number"]["sensitive"] is True

    facts = harness.client.get(
        "/api/v1/profile/facts", headers=headers, params={"concept": "academic.class12.roll_number"}
    ).json()["data"]["facts"]
    assert facts[0]["provenance"]["document_type"] == "CLASS_12_MARKSHEET"
    assert facts[0]["provenance"]["original_label"].startswith("Seat No")

    discovered = harness.client.get(
        "/api/v1/profile/discovered-facts",
        headers=headers,
        params={"ontology": "identity.aadhaar_number"},
    ).json()["data"]
    assert discovered and all(d["masked"] for d in discovered)
    assert all(
        "2345" not in str(d["value"]) and "2345 6789" not in d["evidence_text"] for d in discovered
    )

    readiness = harness.client.get("/api/v1/exams/NEET_UG/readiness", headers=headers).json()[
        "data"
    ]
    items = {r["concept"]: r for s in readiness["sections"] for r in s["requirements"]}
    assert items["academic.class12.subjects"]["status"] == "available"
    assert items["academic.class12.subjects"]["missing_subjects"] == []
    assert items["exam.city_preference"]["status"] == "needs_user_input"

    exams = harness.client.get("/api/v1/exams", headers=headers).json()["data"]
    # the fictional DemoScholar profile is added outside production (see exams/demo_requirements.yaml)
    assert {e["exam_id"] for e in exams} - {"DEMOSCHOLAR_2026"} == {
        "NEET_UG",
        "JEE_MAIN",
        "MHT_CET",
    }
    types = harness.client.get("/api/v1/document-types", headers=headers).json()["data"]
    assert len(types) >= 15


def test_upload_check_endpoint_validates_without_storing(harness) -> None:
    from PIL import Image

    headers = harness.register()
    buffer = io.BytesIO()
    Image.new("RGB", (300, 400), "white").save(buffer, format="JPEG", quality=95)
    response = harness.client.post(
        "/api/v1/exams/NEET_UG/uploads/signature/check",
        headers=headers,
        files={"file": ("sign.jpg", buffer.getvalue(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["dimensions"] == {"width": 300, "height": 400}
    assert "ok" in data and data["verified_rules"] is False
    documents = harness.client.get("/api/v1/documents", headers=headers).json()["data"]["documents"]
    assert documents == []  # nothing was stored


def test_exam_endpoints_require_authentication(harness) -> None:
    assert harness.client.get("/api/v1/exams").status_code == 401
    assert harness.client.get("/api/v1/exams/NEET_UG/readiness").status_code == 401
