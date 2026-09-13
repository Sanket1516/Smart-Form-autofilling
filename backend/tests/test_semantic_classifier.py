"""Tests for TEST_PLAN TC-SEM-01 through TC-SEM-05 and Form Classification API endpoints."""

from fastapi.testclient import TestClient

from app.agents.semantic_classifier import SemanticClassifier
from app.agents.llm_provider import MockLLMProvider
from app.ontology.loader import FieldOntology
from app.schemas.forms import FieldObject


def test_tc_sem_01_exact_known_label() -> None:
    """TC-SEM-01: Field has exact known label -> correct semantic concept is classified."""
    classifier = SemanticClassifier(llm_provider=MockLLMProvider())

    f1 = FieldObject(field_id="f1", label="Name", input_type="text")
    res1 = classifier.classify_field(f1)
    assert res1.concept == "personal.full_name"
    assert res1.confidence >= 0.90
    assert res1.status == "classified"

    f2 = FieldObject(field_id="f2", label="Date of Birth", input_type="date")
    res2 = classifier.classify_field(f2)
    assert res2.concept == "personal.date_of_birth"
    assert res2.confidence >= 0.90


def test_tc_sem_02_synonyms() -> None:
    """TC-SEM-02: Field uses synonym -> equivalent concept is classified."""
    classifier = SemanticClassifier(llm_provider=MockLLMProvider())

    synonyms_test = [
        ("Full Name", "personal.full_name"),
        ("Applicant Name", "personal.full_name"),
        ("Name of Candidate", "personal.full_name"),
        ("Date of Birth", "personal.date_of_birth"),
        ("DOB", "personal.date_of_birth"),
        ("Contact Email", "personal.email"),
        ("Telephone Number", "personal.phone"),
        ("Mobile", "personal.phone"),
    ]

    for index, (label_text, expected_concept) in enumerate(synonyms_test):
        field = FieldObject(field_id=f"f_syn_{index}", label=label_text)
        result = classifier.classify_field(field)
        assert result.concept == expected_concept, f"Expected {expected_concept} for label '{label_text}', got {result.concept}"
        assert result.confidence >= 0.80


def test_tc_sem_03_contextual_label() -> None:
    """TC-SEM-03: Field has contextual label -> page/section context improves classification."""
    classifier = SemanticClassifier(llm_provider=MockLLMProvider())

    field_permanent = FieldObject(
        field_id="f_perm",
        label="University",
        section="Education",
    )
    res_perm = classifier.classify_field(field_permanent)
    assert res_perm.concept == "education.institution"
    assert res_perm.confidence >= 0.80

    field_current = FieldObject(
        field_id="f_curr",
        label="Company",
        section="Work Experience",
    )
    res_curr = classifier.classify_field(field_current)
    assert res_curr.concept == "experience.company"
    assert res_curr.confidence >= 0.80


def test_tc_sem_04_ambiguous_label() -> None:
    """TC-SEM-04: Field is ambiguous -> confidence decreases or field marked unknown."""
    classifier = SemanticClassifier(llm_provider=MockLLMProvider(), min_confidence=0.50)

    ambiguous_field = FieldObject(
        field_id="f_amb",
        label="Field 1",
        placeholder="",
    )
    res = classifier.classify_field(ambiguous_field)
    assert res.concept == "unknown"
    assert res.status == "unknown"
    assert res.confidence < 0.50


def test_tc_sem_05_unseen_wording_ontology_fallback() -> None:
    """TC-SEM-05: Previously unseen wording -> system attempts ontology mapping and handles uncertainty safely."""
    classifier = SemanticClassifier(llm_provider=MockLLMProvider(), min_confidence=0.50)

    # Unseen wording with fuzzy substring of known concept
    unseen_field = FieldObject(
        field_id="f_unseen",
        label="Please Enter Your Electronic Mail",
    )
    res = classifier.classify_field(unseen_field)
    assert res.concept in ("personal.email", "unknown")
    assert res.status in ("classified", "unknown")


def test_api_classify_single_field(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "field": {
            "field_id": "field_01",
            "label": "Email Address",
            "name": "email",
            "placeholder": "Enter email",
            "input_type": "text",
            "section": "Personal Information",
        }
    }
    res = test_client.post("/api/v1/forms/classify-field", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    classification = data["data"]
    assert classification["field_id"] == "field_01"
    assert classification["ontology"] == "personal.email"
    assert classification["field_type"] == "STRUCTURED"
    assert classification["confidence"] >= 0.90


def test_api_classify_batch_fields(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "fields": [
            {
                "field_id": "field_01",
                "label": "Name",
                "input_type": "text",
            },
            {
                "field_id": "field_02",
                "label": "Date of Birth",
                "input_type": "date",
            },
        ]
    }
    res = test_client.post("/api/v1/forms/classify-fields", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    classifications = data["data"]["classifications"]
    assert len(classifications) == 2
    assert classifications[0]["field_id"] == "field_01"
    assert classifications[0]["ontology"] == "personal.full_name"
    assert classifications[0]["field_type"] == "STRUCTURED"
    assert classifications[1]["field_id"] == "field_02"
    assert classifications[1]["ontology"] == "personal.date_of_birth"
    assert classifications[1]["field_type"] == "STRUCTURED"
