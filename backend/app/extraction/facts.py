"""Deterministic candidate fact extraction with source provenance."""

import re
from datetime import UTC, datetime
from typing import Any

from app.models.documents import StructuredFact
from app.processing.schemas import NormalizedDocument

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")
DOB_RE = re.compile(
    r"(?i)(?:date\s+of\s+birth|dob|birth\s*date)\s*[:=-]?\s*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},\s*\d{2,4}|\d{1,2}-[A-Za-z]{3,9}-\d{2,4})"
)
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
PASSPORT_RE = re.compile(
    r"(?i)\b(?:passport|passport\s*(?:no|number))\s*[:#-]?\s*([A-Z0-9]{6,12})\b"
)
AADHAAR_RE = re.compile(r"(?<!\d)(\d{4}[ -]?\d{4}[ -]?\d{4})(?!\d)")


class CandidateFactExtractor:
    """Extract supported candidate concepts without overwriting existing facts."""

    def extract(
        self, normalized: NormalizedDocument, document_id: str, document_name: str
    ) -> list[StructuredFact]:
        facts: list[StructuredFact] = []
        now = datetime.now(UTC)
        for page in normalized.pages:
            for span in page.spans:
                facts.extend(
                    self._from_span(
                        span.text,
                        span.page_number,
                        span.source_method,
                        document_id,
                        document_name,
                        now,
                    )
                )
        return facts

    def _from_span(
        self,
        text: str,
        page: int,
        method: str,
        document_id: str,
        document_name: str,
        timestamp: datetime,
    ) -> list[StructuredFact]:
        facts: list[StructuredFact] = []
        candidates: list[tuple[str, Any, str, float]] = []
        for match in EMAIL_RE.finditer(text):
            candidates.append(("email", match.group(0).lower(), "email", 0.98))
        for match in PHONE_RE.finditer(text):
            normalized_phone = _normalize_phone(match.group(0))
            if normalized_phone:
                candidates.append(("phone_number", normalized_phone, "phone", 0.90))
        for match in DOB_RE.finditer(text):
            normalized_date = _normalize_date(match.group(1))
            if normalized_date:
                candidates.append(("date_of_birth", normalized_date, "date", 0.92))
        for match in PAN_RE.finditer(text.upper()):
            candidates.append(("pan_number", match.group(0).upper(), "identifier", 0.96))
        for match in PASSPORT_RE.finditer(text):
            candidates.append(("passport_number", match.group(1).upper(), "identifier", 0.90))
        for match in AADHAAR_RE.finditer(text):
            candidates.append(
                ("aadhaar_number", re.sub(r"\D", "", match.group(1)), "identifier", 0.88)
            )

        labelled = re.match(
            r"(?i)^\s*(full\s*name|first\s*name|last\s*name|name|address|current\s+address|permanent\s+address|"
            r"university|college|degree|education|organization|company|employer|skills?)\s*[:=-]\s*(.+?)\s*$",
            text,
        )
        if labelled:
            label, value = labelled.groups()
            key = re.sub(r"\s+", "_", label.lower())
            concept = {
                "name": "full_name",
                "full_name": "full_name",
                "first_name": "first_name",
                "last_name": "last_name",
                "current_address": "current_address",
                "permanent_address": "permanent_address",
                "address": "current_address",
                "university": "university",
                "college": "university",
                "degree": "degree",
                "education": "education",
                "organization": "organization",
                "company": "organization",
                "employer": "organization",
                "skills": "skills",
                "skill": "skills",
            }.get(key)
            if concept:
                candidates.append((concept, value.strip(), "string", 0.82))

        for concept, value, value_type, confidence in candidates:
            facts.append(
                StructuredFact(
                    user_id="pending",
                    concept=concept,
                    value=value,
                    value_type=value_type,
                    source_document_id=document_id,
                    source_page=page,
                    confidence=confidence,
                    provenance={
                        "document_name": document_name,
                        "extraction_method": method,
                        "extracted_text": text,
                    },
                    is_user_confirmed=False,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
        return facts


def with_user_id(fact: StructuredFact, user_id: str) -> StructuredFact:
    return fact.model_copy(update={"user_id": user_id})


def _normalize_date(value: str) -> str | None:
    cleaned = value.strip()
    patterns = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y.%m.%d",
        "%d.%m.%Y",
    )
    for pattern in patterns:
        try:
            return datetime.strptime(cleaned, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _normalize_phone(value: str) -> str | None:
    raw = value.strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if raw.startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    if 10 <= len(digits) <= 15:
        return f"+{digits}"
    return None
