"""Document upload, validation, processing, provenance and deletion (real MongoDB)."""

import json

import pytest
from app.agents.llm_provider import TASK_DOCUMENT_EXTRACTION

from tests.conftest import Harness
from tests.factories import ID_CARD_LINES, RESUME_LINES, docx_bytes, pdf_bytes, txt_bytes

pytestmark = pytest.mark.mongo


def _facts(harness: Harness, headers: dict, **params) -> list[dict]:
    response = harness.client.get("/api/v1/profile/facts", headers=headers, params=params)
    assert response.status_code == 200
    return response.json()["data"]["facts"]


def test_pdf_upload_is_processed_into_facts_and_indexed(harness: Harness) -> None:
    headers = harness.register()
    response = harness.upload(headers, "resume.pdf", pdf_bytes(RESUME_LINES), "application/pdf")
    assert response.status_code == 201, response.text
    document = harness.wait_processed(headers, response.json()["data"]["document_id"])
    assert document["status"] == "processed"
    assert document["index_status"] == "indexed" and document["chunk_count"] >= 1
    assert document["fact_count"] >= 5

    facts = {f["concept"]: f for f in _facts(harness, headers)}
    dob = facts["personal.date_of_birth"]
    assert dob["value"] == "1996-02-14" and dob["raw_value"] == "14/02/1996"
    assert dob["origin"] == "normalized"
    assert dob["source_document_id"] == document["document_id"]
    assert dob["document_name"] == "resume.pdf" and dob["source_page"] == 1
    assert "Date of Birth" in dob["evidence_text"]
    assert facts["personal.email"]["origin"] == "extracted"
    assert "nationality" not in json.dumps(facts)  # nothing invented

    chunks = list(harness.vectors.items.values())
    assert chunks and all(
        item["metadata"]["document_id"] == document["document_id"] for item in chunks
    )
    assert {"user_id", "document_name", "page_number", "chunk_index", "document_type"} <= set(
        chunks[0]["metadata"]
    )


def test_docx_and_txt_uploads_are_supported(harness: Harness) -> None:
    headers = harness.register()
    for name, content in (
        ("card.docx", docx_bytes(ID_CARD_LINES)),
        ("notes.txt", txt_bytes(RESUME_LINES)),
    ):
        response = harness.upload(headers, name, content)
        assert response.status_code == 201, response.text
        assert (
            harness.wait_processed(headers, response.json()["data"]["document_id"])["status"]
            == "processed"
        )


@pytest.mark.parametrize(
    ("name", "content", "mime"),
    [
        ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
        ("fake.pdf", b"this is not a pdf", "application/pdf"),
        ("fake.docx", b"PK\x03\x04 not really a zip", None),
        ("binary.txt", b"\x00\x01\x02", "text/plain"),
        ("empty.pdf", b"", "application/pdf"),
        ("mismatch.pdf", b"%PDF-1.4 ...", "image/png"),
    ],
)
def test_invalid_files_are_rejected(
    harness: Harness, name: str, content: bytes, mime: str | None
) -> None:
    response = harness.upload(harness.register(), name, content, mime)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_oversized_and_duplicate_uploads(harness: Harness) -> None:
    headers = harness.register()
    limit = harness.client.app.state.settings.max_upload_size_mb * 1024 * 1024
    big = b"%PDF-1.4\n" + b"0" * (limit + 10)
    assert harness.upload(headers, "big.pdf", big, "application/pdf").status_code == 413
    content = txt_bytes(["Email: dup@example.com"])
    assert harness.upload(headers, "a.txt", content).status_code == 201
    duplicate = harness.upload(headers, "b.txt", content)
    assert duplicate.status_code == 409


def test_corrupted_pdf_fails_with_a_clear_message(harness: Harness) -> None:
    headers = harness.register()
    response = harness.upload(
        headers, "broken.pdf", b"%PDF-1.4\n%garbage that is not a pdf", "application/pdf"
    )
    document = harness.wait_processed(headers, response.json()["data"]["document_id"])
    assert document["status"] == "failed"
    assert "could not be read" in document["processing_error"]
    assert _facts(harness, headers) == []


def test_scanned_document_without_ocr_requires_review(harness: Harness, monkeypatch) -> None:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buffer, format="PNG")
    headers = harness.register()
    response = harness.upload(headers, "scan.png", buffer.getvalue(), "image/png")
    document = harness.wait_processed(headers, response.json()["data"]["document_id"])
    assert document["status"] == "requires_review"
    assert "OCR" in document["processing_error"]


def test_llm_facts_are_merged_and_document_type_recorded(harness: Harness) -> None:
    harness.llm.handlers[TASK_DOCUMENT_EXTRACTION] = lambda prompt: json.dumps(
        {
            "document_type": "RESUME",
            "attributes": [
                {
                    "field": "degree",
                    "semantic_type": "DEGREE",
                    "concept": "education.degree",
                    "value": "Bachelor of Technology in Computer Science",
                    "page": 1,
                    "evidence": "Degree: Bachelor of Technology in Computer Science",
                    "confidence": 0.9,
                },
                {
                    "field": "skill",
                    "semantic_type": "SKILL",
                    "concept": None,
                    "value": "dashboards",
                    "page": 1,
                    "evidence": "reporting dashboards",
                    "confidence": 0.7,
                },
            ],
        }
    )
    headers = harness.register()
    response = harness.upload(headers, "resume.pdf", pdf_bytes(RESUME_LINES), "application/pdf")
    document = harness.wait_processed(headers, response.json()["data"]["document_id"])
    assert document["document_type"] == "RESUME"
    degree = next(f for f in _facts(harness, headers) if f["concept"] == "education.degree")
    assert degree["extraction_method"] == "deterministic+llm"
    discovered = harness.client.get(
        "/api/v1/profile/discovered-facts",
        headers=headers,
        params={"document_id": document["document_id"]},
    ).json()["data"]
    assert any(item["semantic_type"] == "SKILL" and item["ontology"] is None for item in discovered)


def test_indexing_failure_keeps_facts_and_is_reported(harness: Harness) -> None:
    harness.embeddings.fail = True
    headers = harness.register()
    response = harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES))
    document = harness.wait_processed(headers, response.json()["data"]["document_id"])
    assert document["status"] == "processed"
    assert document["index_status"] == "failed" and document["index_error"]
    assert _facts(harness, headers)


def test_reprocessing_replaces_previous_facts_and_chunks(harness: Harness) -> None:
    headers = harness.register()
    document_id = harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
        "document_id"
    ]
    harness.wait_processed(headers, document_id)
    before = len(_facts(harness, headers))
    chunks_before = len(harness.vectors.items)
    assert (
        harness.client.post(
            f"/api/v1/documents/{document_id}/reprocess", headers=headers
        ).status_code
        == 202
    )
    harness.wait_processed(headers, document_id)
    assert len(_facts(harness, headers)) == before
    assert len(harness.vectors.items) == chunks_before


def test_delete_cascades_to_facts_vectors_and_file(harness: Harness) -> None:
    headers = harness.register()
    document_id = harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
        "document_id"
    ]
    harness.wait_processed(headers, document_id)
    assert _facts(harness, headers)
    assert harness.vectors.items

    assert (
        harness.client.delete(f"/api/v1/documents/{document_id}", headers=headers).status_code
        == 200
    )
    assert _facts(harness, headers) == []
    assert not [
        i for i in harness.vectors.items.values() if i["metadata"]["document_id"] == document_id
    ]
    assert (
        harness.client.get(f"/api/v1/documents/{document_id}", headers=headers).status_code == 404
    )
    # the same file can be uploaded again after deletion
    assert harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).status_code == 201


def test_delete_is_refused_when_vector_store_is_down(harness: Harness) -> None:
    headers = harness.register()
    document_id = harness.upload(headers, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
        "document_id"
    ]
    harness.wait_processed(headers, document_id)
    harness.vectors.down = True
    response = harness.client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert response.status_code == 503
    harness.vectors.down = False
    assert _facts(harness, headers)  # nothing was half-deleted


def test_users_cannot_access_each_others_documents(harness: Harness) -> None:
    owner = harness.register()
    intruder = harness.register()
    document_id = harness.upload(owner, "resume.txt", txt_bytes(RESUME_LINES)).json()["data"][
        "document_id"
    ]
    harness.wait_processed(owner, document_id)
    for method, path in (
        ("get", f"/api/v1/documents/{document_id}"),
        ("get", f"/api/v1/documents/{document_id}/status"),
        ("get", f"/api/v1/documents/{document_id}/facts"),
        ("get", f"/api/v1/documents/{document_id}/download"),
        ("post", f"/api/v1/documents/{document_id}/process"),
        ("delete", f"/api/v1/documents/{document_id}"),
    ):
        assert getattr(harness.client, method)(path, headers=intruder).status_code == 404, path
    assert harness.client.get("/api/v1/documents", headers=intruder).json()["data"]["total"] == 0
    assert _facts(harness, intruder) == []


def test_download_returns_original_bytes_with_safe_headers(harness: Harness) -> None:
    headers = harness.register()
    content = txt_bytes(RESUME_LINES)
    document_id = harness.upload(headers, 'my "resume".txt', content).json()["data"]["document_id"]
    response = harness.client.get(f"/api/v1/documents/{document_id}/download", headers=headers)
    assert response.content == content
    assert response.headers["cache-control"] == "no-store"
    assert '"resume"' not in response.headers["content-disposition"].split("filename*=")[0]
