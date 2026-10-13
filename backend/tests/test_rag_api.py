"""Retrieval and grounded answers (real MongoDB, in-memory vector store double)."""

import json
import re

import pytest
from app.agents.llm_provider import TASK_RAG_ANSWER, LLMProviderError

from tests.conftest import Harness
from tests.factories import RESUME_LINES, txt_bytes

pytestmark = pytest.mark.mongo


def _ingest(harness: Harness, headers: dict, lines: list[str], name: str = "resume.txt") -> str:
    document_id = harness.upload(headers, name, txt_bytes(lines)).json()["data"]["document_id"]
    harness.wait_processed(headers, document_id)
    return document_id


def test_search_returns_only_the_callers_chunks_with_sources(harness: Harness) -> None:
    alice = harness.register()
    bob = harness.register()
    alice_doc = _ingest(harness, alice, RESUME_LINES)
    _ingest(harness, bob, ["Bob Sample worked as a data analyst at Initech."], "bob.txt")
    response = harness.client.post(
        "/api/v1/retrieval/rag",
        headers=alice,
        json={"query": "data analyst experience", "top_k": 10},
    )
    results = response.json()["data"]["results"]
    assert results and {r["metadata"]["document_id"] for r in results} == {alice_doc}
    assert results[0]["metadata"]["document_name"] == "resume.txt"
    assert "Initech" not in json.dumps(results)


def test_unrelated_query_returns_nothing_above_the_cutoff(harness: Harness) -> None:
    headers = harness.register()
    _ingest(harness, headers, RESUME_LINES)
    response = harness.client.post(
        "/api/v1/retrieval/rag", headers=headers, json={"query": "zebra migration volcano"}
    )
    assert response.json()["data"]["results"] == []


def test_answer_is_grounded_and_returns_only_cited_sources(harness: Harness) -> None:
    def answer(prompt: str) -> str:
        assert "UNTRUSTED_EVIDENCE" in prompt
        first = re.search(r"\[(C\d+)\]", prompt).group(1)
        return json.dumps(
            {
                "answer": "You worked as a data analyst at Example Corp.",
                "used_chunk_ids": [first, "C99"],
                "confidence": 0.9,
            }
        )

    harness.llm.handlers[TASK_RAG_ANSWER] = answer
    headers = harness.register()
    _ingest(harness, headers, RESUME_LINES)
    data = harness.client.post(
        "/api/v1/retrieval/rag/answer",
        headers=headers,
        json={"question": "Where did I work as a data analyst?"},
    ).json()["data"]
    assert data["status"] == "answered" and "Example Corp" in data["answer"]
    assert len(data["sources"]) == 1 and data["sources"][0]["document_name"] == "resume.txt"


def test_no_evidence_means_no_llm_call_and_no_answer(harness: Harness) -> None:
    headers = harness.register()
    data = harness.client.post(
        "/api/v1/retrieval/rag/answer",
        headers=headers,
        json={"question": "What is my passport number?"},
    ).json()["data"]
    assert data == {
        "answer": "",
        "status": "insufficient_evidence",
        "confidence": 0.0,
        "sources": [],
    }
    assert harness.llm.calls_for(TASK_RAG_ANSWER) == []


def test_uncited_answer_is_treated_as_insufficient(harness: Harness) -> None:
    harness.llm.handlers[TASK_RAG_ANSWER] = lambda p: json.dumps(
        {"answer": "You are a famous astronaut.", "used_chunk_ids": [], "confidence": 0.9}
    )
    headers = harness.register()
    _ingest(harness, headers, RESUME_LINES)
    data = harness.client.post(
        "/api/v1/retrieval/rag/answer",
        headers=headers,
        json={"question": "data analyst experience"},
    ).json()["data"]
    assert data["status"] == "insufficient_evidence" and data["answer"] == ""


def test_llm_and_retrieval_failures_return_errors_not_fake_answers(harness: Harness) -> None:
    headers = harness.register()
    _ingest(harness, headers, RESUME_LINES)

    def boom(prompt: str) -> str:
        raise LLMProviderError("down")

    harness.llm.handlers[TASK_RAG_ANSWER] = boom
    failed = harness.client.post(
        "/api/v1/retrieval/rag/answer",
        headers=headers,
        json={"question": "data analyst experience"},
    )
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "LLM_UNAVAILABLE"

    harness.llm.handlers[TASK_RAG_ANSWER] = lambda p: "certainly! here you go"
    invalid = harness.client.post(
        "/api/v1/retrieval/rag/answer",
        headers=headers,
        json={"question": "data analyst experience"},
    )
    assert invalid.status_code == 502

    harness.vectors.down = True
    down = harness.client.post(
        "/api/v1/retrieval/rag", headers=headers, json={"query": "data analyst"}
    )
    assert down.status_code == 503 and down.json()["error"]["code"] == "RETRIEVAL_UNAVAILABLE"


def test_structured_retrieval_is_user_scoped(harness: Harness) -> None:
    alice = harness.register()
    bob = harness.register()
    _ingest(harness, alice, RESUME_LINES)
    body = {"concept": "personal.email"}
    assert harness.client.post("/api/v1/retrieval/structured", headers=alice, json=body).json()[
        "data"
    ]["results"]
    assert (
        harness.client.post("/api/v1/retrieval/structured", headers=bob, json=body).json()["data"][
            "results"
        ]
        == []
    )
