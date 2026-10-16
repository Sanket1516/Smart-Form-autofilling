"""Deterministic, LLM-free extraction of explicit facts.

Precision matters more than recall here: a value is only taken when it has a
distinctive format (email, profile URL) or sits next to a label that exactly
matches an ontology alias ("Date of Birth: 15/03/1998"). The single heuristic
(a capitalised name line at the top of a résumé) is marked ``inferred`` with
low confidence so it always goes to user review.
"""

from __future__ import annotations

import re

from app.extraction.normalize import (
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_postal_code,
)
from app.extraction.schemas import CandidateFact
from app.ontology.loader import FieldOntology
from app.processing.schemas import NormalizedDocument

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%.]+/?", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-%.]+/?", re.I)
PHONE_RE = re.compile(r"(?<![\w])\+?\d[\d ()-]{6,}\d(?![\w])")
_PAIR_SPLIT = re.compile(r"\s{3,}|\t+|\s\|\s")
_LABELLED = re.compile(r"^\s*([A-Za-z][A-Za-z .'/()&-]{1,60}?)\s*[:=]\s*(.{1,200}?)\s*$")
_NAME_LINE = re.compile(r"^[A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){1,3}$")
_OTHER_PERSON_PHONE = re.compile(
    r"\b(emergency|guardian|parent'?s?|father'?s?|mother'?s?|relative|alternate|alternative|office|work)\b", re.I
)
_PHONE_LABEL = re.compile(r"\b(phone|mobile|mob|tel|telephone|contact|cell|whatsapp)\b", re.I)
_TYPED_NORMALIZERS = {
    "date": normalize_date,
    "email": normalize_email,
    "phone": normalize_phone,
    "postal_code": normalize_postal_code,
}
_HEADER_WORDS = {
    "resume",
    "curriculum",
    "vitae",
    "education",
    "experience",
    "skills",
    "projects",
    "summary",
    "objective",
    "profile",
    "contact",
    "certificate",
    "statement",
    "extract",
    "register",
    "record",
    "abstract",
    "sheet",
    "invoice",
    "letter",
    "report",
    "details",
    "information",
    "university",
    "college",
    "school",
}


class DeterministicExtractor:
    def __init__(self, ontology: FieldOntology) -> None:
        self.ontology = ontology

    def extract(self, document: NormalizedDocument) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        for page in document.pages:
            for span in page.spans:
                for line in span.text.splitlines():
                    facts.extend(self._from_line(line, page.page_number))
        facts.extend(self._name_heuristic(document))
        return facts

    # ------------------------------------------------------------------

    def _from_line(self, line: str, page: int) -> list[CandidateFact]:
        found: list[CandidateFact] = []
        stripped = line.strip()
        if not stripped:
            return found
        for match in EMAIL_RE.finditer(stripped):
            found.append(self._fact("personal.email", match.group(0), page, stripped, 0.97))
        for match in LINKEDIN_RE.finditer(stripped):
            found.append(self._fact("personal.linkedin", match.group(0), page, stripped, 0.95))
        for match in GITHUB_RE.finditer(stripped):
            found.append(self._fact("personal.github", match.group(0), page, stripped, 0.95))
        labelled_concepts: set[str] = set()
        for segment in _PAIR_SPLIT.split(stripped):
            match = _LABELLED.match(segment)
            if not match:
                continue
            label, raw_value = match.group(1), match.group(2)
            matches = self.ontology.match_text(label)
            if not matches or matches[0].score < 0.98:
                continue
            if len(matches) > 1 and matches[1].score >= matches[0].score:
                continue  # label is ambiguous (e.g. "Branch")
            concept = matches[0].concept
            if concept in ("personal.email", "personal.linkedin", "personal.github"):
                continue  # already captured by the format patterns above
            fact = self._fact(concept, raw_value, page, segment.strip(), 0.92)
            if fact is not None:
                found.append(fact)
                labelled_concepts.add(concept)
        if (
            "personal.phone" not in labelled_concepts
            and _PHONE_LABEL.search(stripped)
            and not _OTHER_PERSON_PHONE.search(stripped)
        ):
            for match in PHONE_RE.finditer(stripped):
                fact = self._fact("personal.phone", match.group(0), page, stripped, 0.88)
                if fact is not None:
                    found.append(fact)
        return [fact for fact in found if fact is not None]

    def _fact(
        self, concept: str, raw: str, page: int, evidence: str, confidence: float
    ) -> CandidateFact | None:
        raw = raw.strip().strip(",;")
        if not raw:
            return None
        data_type = self.ontology.data_type(concept)
        typed = _TYPED_NORMALIZERS.get(data_type)
        if typed is not None:
            value = typed(raw)
            if value is None:
                return None  # a typed value that does not parse is not trustworthy
        else:
            value = " ".join(raw.split())
            if concept.endswith("_name") or concept == "personal.full_name":
                value = normalize_name(value)
        return CandidateFact(
            concept=concept,
            semantic_type=concept.split(".", 1)[-1].upper(),
            field=concept.split(".", 1)[-1],
            value=value,
            raw_value=raw,
            data_type=data_type,
            confidence=confidence,
            origin="normalized" if str(value) != raw else "extracted",
            method="deterministic",
            page=page,
            evidence_text=evidence[:300],
        )

    def _name_heuristic(self, document: NormalizedDocument) -> list[CandidateFact]:
        if not document.pages:
            return []
        lines = [
            line.strip()
            for span in document.pages[0].spans[:8]
            for line in span.text.splitlines()
            if line.strip()
        ][:5]
        for line in lines:
            if not _NAME_LINE.match(line) or len(line) > 50:
                continue
            if {word.lower().strip(".") for word in line.split()} & _HEADER_WORDS:
                continue
            value = normalize_name(line)
            return [
                CandidateFact(
                    concept="personal.full_name",
                    semantic_type="FULL_NAME",
                    field="full_name",
                    value=value,
                    raw_value=line,
                    data_type="string",
                    confidence=0.6,
                    origin="inferred",
                    method="name_heuristic",
                    page=document.pages[0].page_number,
                    evidence_text=line,
                )
            ]
        return []
