"""TC-EXT-01 through TC-EXT-06 and structured-fact persistence tests."""

from datetime import UTC, datetime
from typing import Any

import pytest
from app.extraction.facts import CandidateFactExtractor
from app.processing.schemas import ExtractedSpan, NormalizedDocument, NormalizedPage
from app.services.facts import FactService


class FakeFactsRepository:
    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records = records or []

    async def list_filtered(self, user_id: str, *args: Any) -> list[dict[str, Any]]:
        return [record for record in self.records if record["user_id"] == user_id]

    async def list_for_document(self, user_id: str, document_id: str) -> list[dict[str, Any]]:
        return [
            record
            for record in self.records
            if record["user_id"] == user_id and record["source_document_id"] == document_id
        ]

    async def get(self, user_id: str, fact_id: str) -> dict[str, Any] | None:
        return next(
            (
                record
                for record in self.records
                if record["_id"] == fact_id and record["user_id"] == user_id
            ),
            None,
        )

    async def update(self, user_id: str, fact_id: str, values: dict[str, Any]) -> bool:
        record = await self.get(user_id, fact_id)
        if record is None:
            return False
        record.update(values)
        return True


def normalized_text(*lines: str) -> NormalizedDocument:
    return NormalizedDocument(
        pages=[
            NormalizedPage(
                page_number=1,
                spans=[
                    ExtractedSpan(
                        page_number=1,
                        text=line,
                        source_method="direct-parse",
                    )
                    for line in lines
                ],
            )
        ]
    )


def test_tc_ext_01_extracts_name_and_email() -> None:
    facts = CandidateFactExtractor().extract(
        normalized_text("Full Name: Ada Lovelace", "Email: Ada@Example.com"),
        "doc-1",
        "resume.pdf",
    )
    assert {fact.concept for fact in facts} >= {"full_name", "email"}
    assert next(fact for fact in facts if fact.concept == "email").value == "ada@example.com"


def test_tc_ext_02_normalizes_date_to_iso() -> None:
    facts = CandidateFactExtractor().extract(
        normalized_text("Date of Birth: 15/08/2004"), "doc-1", "id.pdf"
    )
    assert next(fact for fact in facts if fact.concept == "date_of_birth").value == "2004-08-15"


def test_tc_ext_03_extracts_address_education_and_organization() -> None:
    facts = CandidateFactExtractor().extract(
        normalized_text(
            "Current Address: 1 Main Street, Pune",
            "University: Example University",
            "Organization: Example Labs",
        ),
        "doc-1",
        "resume.pdf",
    )
    assert {fact.concept for fact in facts} >= {"current_address", "university", "organization"}


def test_tc_ext_04_extracts_identifiers_and_phone() -> None:
    facts = CandidateFactExtractor().extract(
        normalized_text("PAN: ABCDE1234F", "Phone: 98765 43210"), "doc-1", "id.pdf"
    )
    assert next(fact for fact in facts if fact.concept == "pan_number").value == "ABCDE1234F"
    assert next(fact for fact in facts if fact.concept == "phone_number").value == "+919876543210"


def test_tc_ext_05_duplicate_candidates_are_preserved() -> None:
    facts = CandidateFactExtractor().extract(
        normalized_text("Email: first@example.com", "Email: second@example.com"),
        "doc-1",
        "resume.pdf",
    )
    assert [fact.value for fact in facts if fact.concept == "email"] == [
        "first@example.com",
        "second@example.com",
    ]


def test_tc_ext_06_provenance_and_confidence_are_preserved() -> None:
    document = NormalizedDocument(
        pages=[
            NormalizedPage(
                page_number=2,
                spans=[
                    ExtractedSpan(
                        page_number=2,
                        text="Date of Birth: 15/08/2004",
                        source_method="ocr",
                    )
                ],
            )
        ]
    )
    fact = next(
        fact
        for fact in CandidateFactExtractor().extract(document, "doc-1", "scan.pdf")
        if fact.concept == "date_of_birth"
    )
    assert fact.source_page == 2
    assert fact.provenance == {
        "document_name": "scan.pdf",
        "extraction_method": "ocr",
        "extracted_text": "Date of Birth: 15/08/2004",
    }
    assert 0 <= fact.confidence <= 1


@pytest.mark.asyncio
async def test_tc_db_03_fact_is_user_and_document_linked() -> None:
    timestamp = datetime.now(UTC)
    repository = FakeFactsRepository(
        [
            {
                "_id": "fact-1",
                "user_id": "user-1",
                "concept": "full_name",
                "value": "Ada Lovelace",
                "value_type": "string",
                "source_document_id": "doc-1",
                "source_page": 1,
                "confidence": 0.9,
                "provenance": {},
                "is_user_confirmed": False,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ]
    )
    facts = await FactService(repository).list_for_document("user-1", "doc-1")
    assert facts.facts[0].fact_id == "fact-1"
    assert facts.facts[0].source_document_id == "doc-1"


@pytest.mark.asyncio
async def test_fact_candidates_for_multiple_sources_are_not_overwritten() -> None:
    extractor = CandidateFactExtractor()
    first = extractor.extract(normalized_text("Email: first@example.com"), "doc-1", "a.pdf")
    second = extractor.extract(normalized_text("Email: second@example.com"), "doc-2", "b.pdf")
    assert [fact.value for fact in first + second if fact.concept == "email"] == [
        "first@example.com",
        "second@example.com",
    ]
