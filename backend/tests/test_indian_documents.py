"""Indian document intelligence: classification, extraction, validation, tables, profile."""

import asyncio
from datetime import UTC, datetime

import pytest
from app.extraction import validators
from app.extraction.normalize import (
    comparison_key,
    normalize_amount,
    normalize_gender,
    normalize_identifier,
    normalize_number,
    same_address,
)
from app.extraction.registry import get_registry
from app.extraction.service import DocumentExtractionService
from app.ontology.loader import FieldOntology, detect_scope
from app.processing.schemas import ExtractedSpan, NormalizedDocument, NormalizedPage
from app.services.facts import FactService
from bson import ObjectId

from tests.eval.run_eval import InMemoryFacts, _label_key, _same
from tests.indian_fixtures import (
    AADHAAR_FRONT,
    CLASS10_CBSE,
    CLASS12_HSC,
    CONFLICTING_DOB,
    DOCUMENTS,
    INJECTED_CASTE,
    INVALID_AADHAAR,
    DocFixture,
)

ontology = FieldOntology()
service = DocumentExtractionService(ontology, llm_extractor=None)


def extract(fixture: DocFixture):
    return asyncio.run(service.extract(fixture.normalized()))


def by_concept(result) -> dict[str, list]:
    found: dict[str, list] = {}
    for candidate in result.candidates:
        if candidate.concept:
            found.setdefault(candidate.concept, []).append(candidate)
    return found


def lines(*texts: str) -> NormalizedDocument:
    return NormalizedDocument(
        pages=[
            NormalizedPage(
                page_number=1,
                spans=[
                    ExtractedSpan(page_number=1, text=t, source_method="direct-parse")
                    for t in texts
                ],
            )
        ]
    )


# ---------------------------------------------------------------------- per document type


@pytest.mark.parametrize("fixture", DOCUMENTS, ids=lambda f: f.fixture_id)
def test_document_is_classified_and_expected_fields_are_extracted(fixture: DocFixture) -> None:
    result = extract(fixture)
    assert result.document_type == fixture.document_type
    found = by_concept(result)
    for concept, expected in fixture.expected.items():
        values = [c.value for c in found.get(concept, [])]
        assert any(
            _same(expected, v) for v in values
        ), f"{concept}: expected {expected!r}, got {values!r}"
        assert all(_same(expected, v) for v in values), f"{concept}: conflicting values {values!r}"
    for concept in fixture.absent:
        assert concept not in found, f"{concept} must not be extracted from {fixture.fixture_id}"


@pytest.mark.parametrize("fixture", [f for f in DOCUMENTS if f.records], ids=lambda f: f.fixture_id)
def test_record_tables_keep_every_row(fixture: DocFixture) -> None:
    found = by_concept(extract(fixture))
    for concept, rows in fixture.records.items():
        actual = [c.value for c in found.get(concept, [])]
        for row in rows:
            assert any(all(_same(v, a.get(k)) for k, v in row.items()) for a in actual), row


@pytest.mark.parametrize(
    "fixture", [f for f in DOCUMENTS if f.preserved_labels], ids=lambda f: f.fixture_id
)
def test_unfamiliar_labels_are_preserved_as_key_values(fixture: DocFixture) -> None:
    labels = {
        _label_key(str(c.extra.get("original_label")))
        for c in extract(fixture).candidates
        if c.concept is None and c.extra.get("original_label")
    }
    for label in fixture.preserved_labels:
        assert _label_key(label) in labels


def test_every_extracted_value_keeps_page_evidence_and_original_text() -> None:
    for fixture in DOCUMENTS:
        text = fixture.normalized().text
        for candidate in extract(fixture).candidates:
            assert candidate.page is not None
            assert candidate.evidence_text
            if candidate.method != "derived":
                assert candidate.raw_value not in (None, "")
            assert " ".join(candidate.evidence_text.split())[:40].casefold() in " ".join(
                text.split()
            ).casefold() or candidate.method in ("derived", "table")


def test_all_registered_types_have_fixture_coverage() -> None:
    covered = {f.document_type for f in DOCUMENTS}
    assert set(get_registry().types) <= covered


# ---------------------------------------------------------------------- identifiers and privacy


def test_identifier_validators() -> None:
    assert validators.aadhaar("2345 6789 0124").value == "234567890124"
    assert validators.aadhaar("2345 6789 0123") is None  # checksum fails
    assert validators.aadhaar("1234 5678 9012") is None  # cannot start with 0/1
    repaired = validators.aadhaar("2345 6789 O124")
    assert repaired.value == "234567890124" and repaired.repaired
    assert validators.pan("abcpe1234f").value == "ABCPE1234F"
    assert validators.pan("ABCXE1234F") is None  # 4th letter is not a holder type
    assert validators.ifsc("EXBK0001234").value == "EXBK0001234"
    assert validators.ifsc("EXBK1001234") is None
    assert validators.micr("411123045").value == "411123045"
    assert validators.epic("XYZ1234567").value == "XYZ1234567"
    assert validators.driving_licence("MH12 20250012345").value == "MH1220250012345"
    assert validators.mask("234567890124") == "********0124"


def test_invalid_aadhaar_checksum_never_becomes_a_profile_value() -> None:
    assert "identity.aadhaar_number" not in by_concept(extract(INVALID_AADHAAR))


def test_aadhaar_is_not_taken_from_a_bank_reference_number() -> None:
    statement = next(f for f in DOCUMENTS if f.fixture_id == "bank_statement_table")
    assert "identity.aadhaar_number" not in by_concept(extract(statement))


def test_leading_zeros_and_debit_credit_are_preserved() -> None:
    statement = next(f for f in DOCUMENTS if f.fixture_id == "bank_statement_table")
    found = by_concept(extract(statement))
    assert found["financial.account_number"][0].value == "001234567890"
    rows = [c.value for c in found["financial.transactions"]]
    atm = next(r for r in rows if r["description"].startswith("ATM"))
    assert atm["reference"] == "000045" and atm["debit"] == "2000.00" and "credit" not in atm


def test_ifsc_and_micr_stay_distinct() -> None:
    found = by_concept(extract(next(f for f in DOCUMENTS if f.fixture_id == "bank_passbook_table")))
    assert found["financial.ifsc_code"][0].value == "EXBK0001234"
    assert found["financial.micr_code"][0].value == "411123045"


# ---------------------------------------------------------------------- certificates and category


def test_caste_certificate_and_validity_certificate_are_distinguished() -> None:
    validity = by_concept(
        extract(next(f for f in DOCUMENTS if f.document_type == "CASTE_VALIDITY_CERTIFICATE"))
    )
    assert validity["caste_validity.number"][0].value == "CVC/2025/PUN/009876"
    # the caste certificate number printed on the validity certificate is the referenced certificate
    assert validity["caste_certificate.number"][0].value == "CC/2024/PUN/012345"


def test_certificate_and_application_numbers_are_not_confused() -> None:
    found = by_concept(
        extract(next(f for f in DOCUMENTS if f.document_type == "INCOME_CERTIFICATE"))
    )
    assert found["income_certificate.number"][0].value == "INC/2025/HVL/004321"
    assert found["income_certificate.application_number"][0].value == "APP-2025-778899"


def test_category_is_never_inferred_from_a_name() -> None:
    document = lines(
        "CASTE CERTIFICATE",
        "Certificate No: CC/2024/PUN/099999",
        "This is to certify that AARAV EXAMPLE PATIL son of SURESH EXAMPLE PATIL resident of Pune.",
    )
    found = by_concept(asyncio.run(service.extract(document)))
    assert "category.social_category" not in found and "category.caste" not in found


def test_instructions_inside_a_document_do_not_change_extraction() -> None:
    found = by_concept(extract(INJECTED_CASTE))
    assert [c.value for c in found["category.social_category"]] == ["OBC"]
    assert "financial.annual_income" not in found


def test_income_certificate_applicant_is_not_the_candidate() -> None:
    document = lines(
        "INCOME CERTIFICATE",
        "Name of Applicant: Ramesh Example Deshmukh",
        "Annual Family Income: Rs. 7.2 Lakh",
    )
    found = by_concept(asyncio.run(service.extract(document)))
    assert "personal.full_name" not in found
    assert found["financial.annual_income"][0].value == "720000"


# ---------------------------------------------------------------------- marksheets


def test_class_10_and_class_12_values_never_mix() -> None:
    class10 = by_concept(extract(CLASS10_CBSE))
    class12 = by_concept(extract(CLASS12_HSC))
    assert not any(c.startswith("academic.class12") for c in class10)
    assert not any(c.startswith("academic.class10") for c in class12)


def test_percentage_is_only_computed_from_printed_totals() -> None:
    # CBSE prints no aggregate: no percentage may appear
    assert "academic.class10.percentage" not in by_concept(extract(CLASS10_CBSE))
    # HSC totals without a printed percentage: computed, marked derived, below auto-fill confidence
    pages = [[line for line in CLASS12_HSC.pages[0] if not str(line).startswith("Percentage")]]
    without = DocFixture("hsc_no_pct", "CLASS_12_MARKSHEET", "table", pages)
    derived = by_concept(extract(without))["academic.class12.percentage"][0]
    assert derived.value == "88.67" and derived.origin == "derived" and derived.confidence < 0.85
    assert "best of five" in derived.extra["derivation"]


def test_exam_date_result_date_and_passing_year_are_distinct() -> None:
    found = by_concept(extract(CLASS12_HSC))
    assert found["academic.class12.exam_month"][0].value == "February"
    assert found["academic.class12.exam_year"][0].value == "2025"
    assert found["academic.class12.result_date"][0].value == "2025-05-21"
    passing = found["academic.class12.passing_year"][0]
    assert passing.value == "2025" and passing.origin == "derived"


# ---------------------------------------------------------------------- normalisation and scope


def test_value_normalisers() -> None:
    assert normalize_amount("Rs. 4,50,000/-") == "450000"
    assert normalize_amount("Rs 7.2 Lakh") == "720000"
    assert normalize_amount("5,000.00") == "5000.00"
    assert normalize_number("082") == "82"
    assert normalize_number("AB") is None
    assert normalize_gender("पुरुष / MALE") == "Male"
    assert normalize_gender("F") == "Female"
    assert normalize_identifier("001234 567890") == "001234567890"
    assert comparison_key("identifier", "ABCPE 1234 F") == comparison_key(
        "identifier", "abcpe1234f"
    )
    assert comparison_key("amount", "Rs. 4,50,000") == comparison_key("amount", "450000.00")
    assert same_address(
        "Flat 12, MG Road, Pune 411001", "Flat 12, MG Road, Pune, Maharashtra 411001"
    )
    assert not same_address("Flat 12, MG Road, Pune 411001", "Flat 12, MG Road, Pune 411002")


@pytest.mark.parametrize(
    ("text", "scope"),
    [
        ("Class 12th / Qualifying Examination Details", "class_12"),
        ("SSC Details", "class_10"),
        ("Higher Secondary (HSC)", "class_12"),
        ("Secondary School Examination", "class_10"),
        ("Class 10 and 12 marks", None),
        ("Caste Validity Certificate Number", "caste_validity"),
        ("Personal Details", None),
    ],
)
def test_scope_detection(text: str, scope: str | None) -> None:
    assert detect_scope(text) == scope


# ---------------------------------------------------------------------- profile: conflicts and provenance


def _records(fixtures: list[DocFixture]) -> list[dict]:
    now = datetime.now(UTC)
    records = []
    for fixture in fixtures:
        for candidate in extract(fixture).candidates:
            if candidate.concept and ontology.is_fillable(candidate.concept):
                records.append(
                    {
                        "_id": ObjectId(),
                        "user_id": "u",
                        "concept": candidate.concept,
                        "value": candidate.value,
                        "origin": candidate.origin,
                        "status": "active",
                        "source_document_id": fixture.fixture_id,
                        "document_name": fixture.fixture_id,
                        "source_page": candidate.page,
                        "evidence_text": candidate.evidence_text,
                        "confidence": candidate.confidence,
                        "is_user_confirmed": False,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
    return records


def test_conflicting_documents_keep_both_values_with_provenance() -> None:
    views = asyncio.run(
        FactService(
            InMemoryFacts(_records([AADHAAR_FRONT, CONFLICTING_DOB])), ontology
        ).resolve_view("u")
    )
    view = views["personal.date_of_birth"]
    assert view.status == "conflict"
    assert {c.value for c in view.candidates} == {"2007-02-14", "2007-02-15"}
    assert {c.document_id for c in view.candidates} == {
        AADHAAR_FRONT.fixture_id,
        CONFLICTING_DOB.fixture_id,
    }


def test_same_address_in_different_wording_is_one_value() -> None:
    fixtures = [
        f
        for f in DOCUMENTS
        if f.fixture_id in ("aadhaar_back_ocr", "voter_id_clean", "driving_licence_clean")
    ]
    view = asyncio.run(FactService(InMemoryFacts(_records(fixtures)), ontology).resolve_view("u"))[
        "address.full_address"
    ]
    assert view.status == "resolved"
    assert len({s.document_id for s in view.sources}) == 3
