"""Exam-form field matching, safe filling, requirement profiles and upload checks."""

import asyncio
import io

import pytest
from app.agents.field_classifier import FieldClassifier, subject_qualifier
from app.agents.llm_provider import MockLLMProvider
from app.agents.value_formatting import format_for_field
from app.exams.service import ExamService
from app.ontology.loader import FieldOntology
from app.schemas.form_sessions import FieldObject
from app.services.facts import FactService

from tests.eval.run_eval import (
    InMemoryFacts,
    build_profile_records,
    evaluate_extraction,
    evaluate_forms,
)

ontology = FieldOntology()
classifier = FieldClassifier(ontology, MockLLMProvider(), threshold=0.75)


def classify(**kwargs):
    return classifier.classify_deterministic(
        FieldObject(field_id=kwargs.pop("field_id", "f"), **kwargs)
    )


@pytest.mark.parametrize(
    ("kwargs", "concept"),
    [
        ({"label": "IFSC Code"}, "financial.ifsc_code"),
        ({"label": "MICR Code"}, "financial.micr_code"),
        ({"label": "IFS Code"}, "financial.ifsc_code"),
        (
            {"label": "Year of Passing", "section": "Class 10th Details"},
            "academic.class10.passing_year",
        ),
        (
            {"label": "Year of Passing", "section": "Class 12th / Qualifying Examination"},
            "academic.class12.passing_year",
        ),
        ({"label": "Percentage of Marks", "section": "HSC Details"}, "academic.class12.percentage"),
        ({"label": "SSC Seat Number"}, "academic.class10.roll_number"),
        ({"label": "Caste Certificate Number"}, "caste_certificate.number"),
        ({"label": "Caste Validity Certificate Number"}, "caste_validity.number"),
        (
            {"label": "Certificate Number", "section": "Caste Certificate Details"},
            "caste_certificate.number",
        ),
        (
            {"label": "Certificate Number", "section": "Non-Creamy Layer Certificate"},
            "ncl_certificate.number",
        ),
        ({"label": "Father/Guardian Name"}, "personal.father_name"),
        ({"label": "Account Holder Name"}, "financial.account_holder_name"),
        ({"label": "Candidate Name (as per Class 10th certificate)"}, "personal.full_name"),
        (
            {"label": "Physics Marks Obtained", "section": "Class 12th Details"},
            "academic.class12.subject_marks",
        ),
    ],
)
def test_fields_map_to_the_specific_concept(kwargs, concept) -> None:
    assert classify(**kwargs).concept == concept


@pytest.mark.parametrize(
    "kwargs",
    [
        {"label": "Total Marks", "section": "Class 12th Details"},  # obtained or maximum?
        {"label": "Certificate Number"},  # which certificate?
        {"label": "Physics Marks"},  # class 10 or 12?
        {"label": "Board", "section": "Class 10 and 12 details"},
    ],
)
def test_ambiguous_fields_are_not_guessed(kwargs) -> None:
    result = classify(**kwargs)
    assert result.concept is None or not classifier.is_resolved(result)


def test_unscoped_passing_year_is_never_assigned_to_class_10_or_12() -> None:
    # without Class 10/12 context it stays the generic (résumé) graduation-year concept
    assert classify(label="Year of Passing").concept == "education.end_year"


def test_retrieval_is_filtered_to_documents_that_state_the_concept() -> None:
    from app.extraction.registry import get_registry

    registry = get_registry()
    assert registry.document_types_for("academic.class12.board") == ["CLASS_12_MARKSHEET"]
    assert set(registry.document_types_for("financial.ifsc_code")) == {
        "BANK_PASSBOOK",
        "BANK_STATEMENT",
    }
    assert registry.document_types_for("utility.consumer_number") == ["ELECTRICITY_BILL"]
    assert registry.document_types_for("caste_validity.number") == ["CASTE_VALIDITY_CERTIFICATE"]
    assert registry.document_types_for(None) == []


def test_subject_qualifier() -> None:
    assert subject_qualifier("Physics Marks Obtained") == {
        "subject": "physics",
        "measure": "marks_obtained",
    }
    assert subject_qualifier("Maximum marks in Maths") == {
        "subject": "mathematics",
        "measure": "max_marks",
    }
    assert subject_qualifier("Social Science grade")["subject"] == "social science"
    assert subject_qualifier("Physics") is None  # no marks word: not a marks field


def test_income_is_matched_to_a_range_option() -> None:
    options = [
        {"option_id": str(i), "value": v, "label": v}
        for i, v in enumerate(
            [
                "Up to 2.5 Lakh",
                "Above 2.5 Lakh and up to 6 Lakh",
                "Above 6 Lakh and up to 8 Lakh",
                "Above 8 Lakh",
            ]
        )
    ]
    field = FieldObject(
        field_id="i", label="Annual Family Income", input_type="select", options=options
    )
    assert format_for_field(field, "amount", "450000").value == "Above 2.5 Lakh and up to 6 Lakh"
    assert format_for_field(field, "amount", "250000").value == "Up to 2.5 Lakh"
    assert format_for_field(field, "amount", "900000").value == "Above 8 Lakh"


def test_pass_result_selects_passed_option() -> None:
    options = [
        {"option_id": "1", "value": "Passed", "label": "Passed"},
        {"option_id": "2", "value": "Appearing", "label": "Appearing"},
    ]
    field = FieldObject(
        field_id="r", label="Qualifying Examination Status", input_type="select", options=options
    )
    assert format_for_field(field, "string", "PASS").value == "Passed"


# ---------------------------------------------------------------------- whole-form regression guards


def test_exam_forms_end_to_end_never_fill_incorrectly() -> None:
    report = evaluate_forms(ontology, "current")
    assert report["incorrect_fills"] == 0
    assert report["wrong_suggestions"] == 0
    assert report["end_to_end_correct_outcome_rate"] >= 0.95
    rows = {r["label"]: r for r in report["rows"]}
    for label in (
        "Exam City Choice 1",
        "Medium of Question Paper",
        "Qualifying Examination Code",
        "Are you a Person with Benchmark Disability (PwBD)?",
        "Are you domiciled in Maharashtra?",
    ):
        assert (
            rows[label]["status"] == "missing_information"
        ), label  # user choices are never filled
    for label in ("Category", "Aadhaar Number", "Bank Account Number", "Annual Family Income"):
        assert rows[label]["status"] == "needs_review", label  # sensitive or eligibility data


def test_extraction_quality_floor() -> None:
    report = evaluate_extraction(ontology, "current")
    assert report["document_classification_accuracy"] == 1.0
    assert report["forbidden_facts"] == 0
    assert report["wrong_value_facts"] == 0
    assert report["field_recall"] >= 0.95


# ---------------------------------------------------------------------- exam readiness and uploads


def _exams() -> ExamService:
    return ExamService(
        FactService(InMemoryFacts(build_profile_records(ontology, "current", "u")), ontology),
        ontology,
    )


def test_neet_readiness_reports_available_confirmation_and_user_input() -> None:
    readiness = asyncio.run(_exams().readiness("u", "neet_ug"))
    items = {r["concept"]: r for s in readiness["sections"] for r in s["requirements"]}
    assert items["personal.full_name"]["status"] == "available"
    assert items["category.social_category"]["status"] == "needs_confirmation"
    assert items["exam.city_preference"]["status"] == "needs_user_input"
    assert items["exam.qualifying_exam_code"]["status"] == "needs_user_input"
    assert items["personal.mother_name"]["status"] == "conflict"
    assert items["address.permanent_address"]["status"] == "needs_confirmation"
    subjects = items["academic.class12.subjects"]
    assert subjects["status"] == "available" and not subjects["missing_subjects"]
    assert items["identity.aadhaar_number"]["value"].endswith("0124")
    assert "*" in items["identity.aadhaar_number"]["value"]  # masked
    uploads = {u["id"]: u for u in readiness["uploads"]}
    assert uploads["category_certificate"]["required"] is True  # category OBC on record
    assert (
        uploads["pwbd_certificate"]["required"] is None
    )  # depends on an answer only the user gives
    assert readiness["verified_against_official_bulletin"] is False


def test_jee_requires_mathematics_but_it_is_found() -> None:
    readiness = asyncio.run(_exams().readiness("u", "JEE_MAIN"))
    subjects = next(
        r
        for s in readiness["sections"]
        for r in s["requirements"]
        if r["concept"] == "academic.class12.subjects"
    )
    assert {f["subject"] for f in subjects["value"]} == {"physics", "chemistry", "mathematics"}


def test_upload_check_reports_format_and_size_problems() -> None:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 50), "white").save(buffer, format="JPEG")
    result = _exams().check_upload("NEET_UG", "photograph", "photo.jpg", buffer.getvalue())
    assert not result["ok"] and any("minimum" in p for p in result["problems"])
    assert result["dimensions"] == {"width": 40, "height": 50}
    assert result["verified_rules"] is False and result["note"]
    png = _exams().check_upload("NEET_UG", "signature", "sign.png", buffer.getvalue())
    assert any("Format" in p for p in png["problems"])
