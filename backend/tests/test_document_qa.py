"""Ask Documents: planning, exact lookups, scoping, calculations, eligibility and safety.

Runs the real API against the throwaway MongoDB with in-memory vectors and a
scripted model. Documents are the synthetic Indian fixtures.
"""

import json

import pytest
from app.agents.llm_provider import TASK_RAG_ANSWER, LLMProviderError
from app.exams.service import load_exam_profiles
from app.ontology.loader import FieldOntology
from app.schemas.retrieval import ChatTurn
from app.services.document_qa import QuestionPlanner

from tests.conftest import Harness
from tests.indian_fixtures import (
    CASTE_CERTIFICATE,
    CASTE_VALIDITY,
    CLASS10_CBSE,
    CLASS12_HSC,
    CONFLICTING_DOB,
    INCOME_CERTIFICATE,
)

ASK = "/api/v1/retrieval/rag/answer"


def _upload(harness: Harness, headers: dict, fixture) -> str:
    content = fixture.normalized().text.encode("utf-8")
    response = harness.upload(headers, f"{fixture.fixture_id}.txt", content, "text/plain")
    assert response.status_code == 201, response.text
    document_id = response.json()["data"]["document_id"]
    assert harness.wait_processed(headers, document_id)["status"] == "processed"
    return document_id


def _ask(harness: Harness, headers: dict, question: str, **extra) -> dict:
    response = harness.client.post(ASK, headers=headers, json={"question": question, **extra})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _values(data: dict) -> dict[str, str]:
    return {f["concept"]: str(f["value"]) for f in data["facts"]}


# ---------------------------------------------------------------------- planner (no database)

PLANNER = QuestionPlanner(FieldOntology(), load_exam_profiles())


@pytest.mark.parametrize(
    ("question", "primary", "concepts"),
    [
        (
            "What was my Class 12 passing year and percentage?",
            "exact_lookup",
            ["academic.class12.passing_year", "academic.class12.percentage"],
        ),
        ("What is my Class X percentage?", "exact_lookup", ["academic.class10.percentage"]),
        (
            "What is my caste certificate number and caste validity certificate number?",
            "multi_document",
            ["caste_validity.number", "caste_certificate.number"],
        ),
        ("Am I eligible for NEET UG?", "eligibility", []),
        ("Which required information for NEET is missing from my profile?", "missing_info", []),
        (
            "Which documents do I need for JEE Main, and which do I already have?",
            "requirements",
            [],
        ),
    ],
)
def test_planner_routes_and_scopes(question: str, primary: str, concepts: list[str]) -> None:
    plan = PLANNER.plan(question, [])
    assert plan.primary == primary
    assert sorted(plan.concepts) == sorted(concepts)


def test_planner_never_maps_class12_question_to_class10() -> None:
    plan = PLANNER.plan("What is my HSC board and percentage?", [])
    assert plan.concepts and all(c.startswith("academic.class12.") for c in plan.concepts)


@pytest.mark.parametrize(
    ("question", "concept"),
    [
        ("What is my mum's name?", "personal.mother_name"),
        ("What is my mom's name?", "personal.mother_name"),
        ("What is my dad's name?", "personal.father_name"),
    ],
)
def test_planner_informal_parent_names_never_answer_with_the_applicant_name(
    question: str, concept: str
) -> None:
    plan = PLANNER.plan(question, [])
    assert concept in plan.concepts
    assert "personal.full_name" not in plan.concepts


def test_planner_year_question_about_a_degree_asks_for_the_completion_year() -> None:
    assert PLANNER.plan("What year did I finish my degree?", []).concepts[0] == "education.end_year"
    assert "education.end_year" not in PLANNER.plan("What is my degree?", []).concepts


def test_planner_follow_up_reuses_previous_subject_with_new_scope() -> None:
    history = [ChatTurn(role="user", content="What was my Class 12 passing year and percentage?")]
    plan = PLANNER.plan("And what about Class 10?", history)
    assert plan.follow_up
    assert sorted(plan.concepts) == ["academic.class10.passing_year", "academic.class10.percentage"]


def test_planner_detects_exam_from_history() -> None:
    history = [ChatTurn(role="user", content="Am I eligible for NEET UG?")]
    assert PLANNER.plan("Which documents do I need?", history).exam_id == "NEET_UG"


# ---------------------------------------------------------------------- API

pytestmark_api = pytest.mark.mongo


@pytestmark_api
def test_exact_lookup_comes_from_facts_without_llm(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    _upload(harness, headers, CLASS10_CBSE)
    data = _ask(harness, headers, "What was my Class 12 passing year and percentage?")
    assert data["status"] == "answered" and data["answer_mode"] == "structured"
    assert _values(data) == {
        "academic.class12.passing_year": "2025",
        "academic.class12.percentage": "88.67",
    }
    assert all(f["document_name"] == "class12_hsc_table.txt" for f in data["facts"])
    assert "2023" not in data["answer"]  # the Class 10 year never leaks into a Class 12 answer
    assert harness.llm.calls_for(TASK_RAG_ANSWER) == []


@pytestmark_api
def test_class10_percentage_is_not_invented_when_not_printed(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS10_CBSE)
    data = _ask(harness, headers, "What is my Class 10 percentage?")
    assert data["status"] in ("partial", "insufficient_evidence")
    assert [m["concept"] for m in data["missing"]] == ["academic.class10.percentage"]
    assert "does not print a percentage" in data["missing"][0]["reason"]
    assert data["derived"] == [] and "%" not in data["answer"]


@pytestmark_api
def test_percentage_is_calculated_only_from_printed_totals(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    data = _ask(harness, headers, "What is my Class 12 percentage?")
    # printed on the marksheet: reported as a fact, not recalculated
    assert _values(data)["academic.class12.percentage"] == "88.67"


@pytestmark_api
def test_certificate_numbers_stay_distinct(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CASTE_CERTIFICATE)
    _upload(harness, headers, CASTE_VALIDITY)
    data = _ask(
        harness,
        headers,
        "What is my caste certificate number and what is my caste validity certificate number?",
    )
    values = _values(data)
    assert values["caste_certificate.number"] == "CC/2024/PUN/012345"
    assert values["caste_validity.number"] == "CVC/2025/PUN/009876"


@pytestmark_api
def test_selected_documents_limit_the_answer(harness: Harness) -> None:
    headers = harness.register()
    class10 = _upload(harness, headers, CLASS10_CBSE)
    _upload(harness, headers, CLASS12_HSC)
    data = _ask(harness, headers, "What was my Class 12 passing year?", document_ids=[class10])
    assert data["facts"] == []
    assert [m["concept"] for m in data["missing"]] == ["academic.class12.passing_year"]
    searched = [d for d in data["documents"] if d["searched"]]
    assert [d["document_id"] for d in searched] == [class10]


@pytestmark_api
def test_foreign_document_ids_are_refused(harness: Harness) -> None:
    alice = harness.register()
    bob = harness.register()
    bob_doc = _upload(harness, bob, CLASS12_HSC)
    _upload(harness, alice, CLASS10_CBSE)
    response = harness.client.post(
        ASK, headers=alice, json={"question": "What is my percentage?", "document_ids": [bob_doc]}
    )
    assert response.status_code == 404
    assert "88.67" not in response.text


@pytestmark_api
def test_answers_never_cross_users(harness: Harness) -> None:
    alice = harness.register()
    bob = harness.register()
    _upload(harness, alice, CLASS12_HSC)
    _upload(harness, bob, INCOME_CERTIFICATE)
    data = _ask(harness, bob, "What was my Class 12 percentage?")
    assert "88.67" not in json.dumps(data)


@pytestmark_api
def test_conflicting_documents_are_reported_not_guessed(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS10_CBSE)
    _upload(harness, headers, CONFLICTING_DOB)
    data = _ask(harness, headers, "What is my date of birth?")
    assert data["status"] == "partial"
    assert data["facts"] == []
    values = {v["value"] for v in data["conflicts"][0]["values"]}
    assert values == {"2007-02-14", "2007-02-15"}


@pytestmark_api
def test_subject_marks_come_from_the_right_marksheet(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    _upload(harness, headers, CLASS10_CBSE)
    data = _ask(harness, headers, "How many marks did I get in Physics in Class 12?")
    assert [f["value"] for f in data["facts"]] == ["91"]
    assert data["facts"][0]["document_name"] == "class12_hsc_table.txt"


@pytestmark_api
def test_eligibility_checks_rules_and_never_declares_eligibility(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    data = _ask(harness, headers, "Am I eligible for NEET UG based on my documents?")
    assert data["question_type"] == "eligibility"
    outcomes = {r["label"]: r["outcome"] for r in data["requirements"]}
    assert outcomes["Passed Class 12 (or equivalent)"] == "met"
    assert outcomes["Physics, Chemistry, Biology/Biotechnology and English in Class 12"] == "met"
    assert all("NOT verified" in r["source"] for r in data["requirements"])
    aggregate = next(d for d in data["derived"] if "aggregate" in d["label"].lower())
    assert aggregate["value"] == "90.67"  # (91 + 88 + 93) / 300
    assert "you are eligible" not in data["answer"].lower()
    assert "not a decision on your eligibility" in data["answer"]


@pytestmark_api
def test_unsupported_numbers_from_the_model_are_discarded(harness: Harness) -> None:
    harness.llm.handlers[TASK_RAG_ANSWER] = lambda p: json.dumps(
        {
            "answer": "Your Class 12 aggregate is 97.5% so you are certainly eligible.",
            "used_fact_ids": ["F1"],
            "confidence": 0.9,
        }
    )
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    data = _ask(harness, headers, "Compare the information in my uploaded marksheets.")
    assert "97.5" not in data["answer"]
    assert any("discarded" in w for w in data["warnings"])
    assert data["answer_mode"] in ("evidence_only", "structured")


@pytestmark_api
def test_model_failure_keeps_structured_facts(harness: Harness) -> None:
    def boom(prompt: str) -> str:
        raise LLMProviderError("provider down")

    harness.llm.handlers[TASK_RAG_ANSWER] = boom
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    _upload(harness, headers, CLASS10_CBSE)
    data = _ask(harness, headers, "Compare the information in my uploaded marksheets.")
    assert data["answer_mode"] == "evidence_only"
    assert "88.67" in data["answer"] and "2023" in data["answer"]


@pytestmark_api
def test_follow_up_question_uses_conversation(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    _upload(harness, headers, CLASS10_CBSE)
    data = _ask(
        harness,
        headers,
        "And for Class 10?",
        history=[{"role": "user", "content": "What was my Class 12 passing year?"}],
    )
    assert _values(data) == {"academic.class10.passing_year": "2023"}


@pytestmark_api
def test_unprocessed_documents_are_reported(harness: Harness) -> None:
    headers = harness.register()
    bad = harness.upload(headers, "broken.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")
    document_id = bad.json()["data"]["document_id"]
    harness.wait_processed(headers, document_id)
    data = _ask(harness, headers, "What is my date of birth?")
    assert data["status"] == "documents_not_ready"
    assert any("failed processing" in w for w in data["warnings"])


@pytestmark_api
def test_missing_information_for_an_exam(harness: Harness) -> None:
    headers = harness.register()
    _upload(harness, headers, CLASS12_HSC)
    data = _ask(harness, headers, "Which required information for NEET is missing from my profile?")
    labels = " ".join(r["label"] for r in data["requirements"])
    assert "Class 10" in labels  # nothing from a Class 10 marksheet yet
    assert all(r["outcome"] != "met" for r in data["requirements"])
    assert data["status"] in ("answered", "partial")


@pytestmark_api
def test_invalid_requests_are_rejected(harness: Harness) -> None:
    headers = harness.register()
    assert harness.client.post(ASK, headers=headers, json={"question": ""}).status_code == 422
    assert harness.client.post(ASK, json={"question": "hi"}).status_code == 401


@pytestmark_api
def test_owner_sees_amounts_but_identifiers_stay_masked(harness: Harness) -> None:
    from tests.indian_fixtures import AADHAAR_FRONT

    headers = harness.register()
    _upload(harness, headers, INCOME_CERTIFICATE)
    _upload(harness, headers, AADHAAR_FRONT)
    income = _ask(harness, headers, "What is my annual income according to my income certificate?")
    assert "450000" in json.dumps(income)
    aadhaar = _ask(harness, headers, "What is my Aadhaar number?")
    value = str(aadhaar["facts"][0]["value"])
    assert value.startswith("*") and value[-4:].isdigit()


@pytestmark_api
def test_document_stuck_in_processing_is_reported_failed(harness: Harness) -> None:
    from datetime import UTC, datetime, timedelta

    from bson import ObjectId
    from pymongo import MongoClient

    headers = harness.register()
    document_id = _upload(harness, headers, INCOME_CERTIFICATE)
    import os

    client: MongoClient = MongoClient(os.environ["MONGODB_URL"])
    client[os.environ["MONGODB_DATABASE"]]["documents"].update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "status": "processing",
                "processing_started_at": datetime.now(UTC) - timedelta(hours=2),
            }
        },
    )
    client.close()
    data = harness.client.get(f"/api/v1/documents/{document_id}", headers=headers).json()["data"]
    assert data["status"] == "failed"
    assert "Try processing the document again" in data["processing_error"]


def test_model_answers_lose_internal_labels_and_echoed_rules() -> None:
    from app.services.document_qa import _clean_answer

    text = (
        "A document being uploaded does not mean its conditions are met. "
        "Passed Class 12: met [R1]. Aggregate 90.67% [D1, F2]. Percentage missing [MISSING]."
    )
    assert _clean_answer(text) == "Passed Class 12: met. Aggregate 90.67%. Percentage missing."


# ------------------------------------------------------------------ demo-driven regressions
def _planner():
    from app.exams.service import load_exam_profiles
    from app.ontology.loader import FieldOntology
    from app.services.document_qa import QuestionPlanner

    return QuestionPlanner(FieldOntology(), load_exam_profiles())


def test_another_persons_phone_is_never_answered_with_the_applicants_own_number() -> None:
    plan = _planner().plan("What is the applicant's mother's mobile number?", [])
    assert plan.third_party and "personal.phone" not in plan.concepts
    assert (
        "personal.phone" in _planner().plan("What is the applicant's mobile number?", []).concepts
    )


def test_same_as_follow_up_compares_with_the_previous_questions_subject() -> None:
    from app.schemas.retrieval import ChatTurn

    history = [
        ChatTurn(role="user", content="What is the correspondence address?"),
        ChatTurn(role="assistant", content="Room 214 ..."),
    ]
    plan = _planner().plan("Is it the same as the permanent address?", history)
    assert {"address.correspondence_address", "address.permanent_address"} <= set(plan.concepts)


def test_which_documents_questions_are_provenance_questions() -> None:
    assert (
        "provenance"
        in _planner().plan("Which documents mention the applicant's father's name?", []).kinds
    )


def test_transaction_period_is_read_from_the_question() -> None:
    from app.services.document_qa import transaction_period

    assert transaction_period("transactions between 1 September 2026 and 15 September 2026?") == (
        "2026-09-01",
        "2026-09-15",
    )
    assert transaction_period("transactions between 01/09/2026 and 15/09/2026") == (
        "2026-09-01",
        "2026-09-15",
    )
    assert transaction_period("what transactions occurred in February 2028?") == (
        "2028-02-01",
        "2028-02-29",
    )
    assert transaction_period("list my transactions") is None
