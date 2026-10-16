"""Deterministic extraction for registered Indian document types.

For a classified document this extracts:

* identifiers found anywhere on the document, validated (Aadhaar checksum, PAN,
  IFSC, EPIC, passport, licence formats);
* labelled values ("Label: value", "Label   value", or a label line followed by
  its value line, as OCR and bilingual cards print them). Labels resolve through
  the document type's own label map first, then the ontology, then the document
  scope (on a caste certificate "Certificate No" is the caste certificate number);
* every other labelled value as a generic key-value (``concept=None``) with its
  original label, so unfamiliar fields are preserved, not discarded;
* layout rules (Aadhaar name above the date of birth, a standalone gender line,
  S/O relation prefixes, "This is to certify that <NAME>", header lines naming
  the board or bank, exam month/year) and value phrases;
* record tables (subjects, transactions, household members) and printed totals.

Derived values are explicit: passing year from a PASS result and the exam year,
and a percentage only from printed total marks and printed maximum marks. Values
are never taken from outside the document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.extraction import validators
from app.extraction.normalize import normalize_name, normalize_value
from app.extraction.registry import DocumentType, label_key
from app.extraction.schemas import CandidateFact
from app.extraction.tables import parse_marks, parse_members, parse_transactions
from app.ontology.loader import FieldOntology
from app.processing.schemas import NormalizedDocument

_SENTENCE_WORDS = {"from", "for", "is", "are", "of", "as", "in", "on", "at", "to", "by", "and", "the",
                   "that", "which", "was", "were", "has", "have", "with", "shall", "will"}
_MAX_LABEL_CHARS = 80
_MAX_LABEL_WORDS = 12
_PAIR_SPLIT = re.compile(r"\s{3,}|\t+")
_MRZ = re.compile(r"^[A-Z0-9<]{25,}$")
_PIN = re.compile(r"(?<!\d)[1-9]\d{2}\s?\d{3}(?!\d)")
_NAME_LINE = re.compile(r"^[A-Za-z][A-Za-z.' ]{2,60}$")
_RELATION = re.compile(r"^\s*(S/O|D/O|W/O|C/O|S/o|D/o|W/o|C/o)\s*[:.-]?\s*([^,]+),?\s*(.*)$")
_RELATION_CONCEPT = {
    "s/o": "personal.father_name",
    "d/o": "personal.father_name",
    "w/o": "personal.spouse_name",
}
_CERTIFY = re.compile(
    r"certify that\s+(?:(?i:shri|smt|kumari|kumar|kum|mr|mrs|ms|miss|master)\.?\s+)?"
    r"([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){1,5})"
)
_EXAM_SESSION = re.compile(r"EXAMINATION\b([^0-9]*?)((?:19|20)\d{2})", re.I)
_MONTH_WORD = re.compile(
    r"\b(JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?|"
    r"SEP(?:TEMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)\b",
    re.I,
)
_MONTHS = {
    m[:3]: m
    for m in (
        "January February March April May June July August September October November December".split()
    )
}
_ADDRESS_TYPES = {"address"}
_ZIP_FROM = {"address.full_address", "address.permanent_address", "address.correspondence_address"}
_PASS = re.compile(r"^\s*(pass|passed|qualified|successful)\b", re.I)
_RECORD_CONCEPTS = {
    "subject": "education.subjects",
    "transaction": "financial.transactions",
    "member": "ration_card.members",
}


@dataclass
class _Line:
    text: str
    page: int


class DocumentAwareExtractor:
    def __init__(self, ontology: FieldOntology) -> None:
        self.ontology = ontology

    def extract(self, document: NormalizedDocument, doc_type: DocumentType) -> list[CandidateFact]:
        self.doc_type = doc_type
        lines = [
            _Line(line.strip(), page.page_number)
            for page in document.pages
            for span in page.spans
            if not span.is_table
            for line in span.text.splitlines()
            if line.strip()
        ]
        facts: list[CandidateFact] = []
        facts += self._identifiers(lines)
        facts += self._labelled(lines)
        facts += self._layout_rules(lines)
        facts += self._phrases(lines)
        facts += self._tables(document)
        facts += self._derived(facts)
        return facts

    # ------------------------------------------------------------------ helpers

    def _scoped(self, concept: str | None) -> str | None:
        if concept is None:
            return None
        return self.ontology.scoped(concept, self.doc_type.scope)

    def _fact(
        self,
        concept: str | None,
        raw: str,
        line: _Line,
        *,
        evidence: str | None = None,
        confidence: float = 0.92,
        method: str = "document_rule",
        label: str | None = None,
        origin: str | None = None,
    ) -> CandidateFact | None:
        raw = raw.strip().strip(",;")
        if not raw:
            return None
        extra: dict[str, object] = {"document_type": self.doc_type.type_id}
        if label:
            extra["original_label"] = label
        if (
            concept is None
            or self.ontology.is_abstract(concept)
            or not self.ontology.is_known(concept)
        ):
            return CandidateFact(
                concept=None,
                semantic_type=(label_key(label or "value").replace(" ", "_") or "VALUE").upper()[
                    :120
                ],
                field=(label_key(label or "value").replace(" ", "_") or "value")[:120],
                value=" ".join(raw.split()),
                raw_value=raw,
                data_type="string",
                confidence=round(min(confidence, 0.9), 3),
                origin="extracted",
                method=method,
                page=line.page,
                evidence_text=(evidence or line.text)[:500],
                extra=extra,
            )
        data_type = self.ontology.data_type(concept)
        kind = self.ontology.validator(concept)
        repaired = False
        if kind:
            checked = validators.validate(kind, raw)
            if checked is None:
                extra["validation"] = "failed"
                # an identifier that fails its format/checksum never becomes a profile value
                return self._fact(
                    None, raw, line, evidence=evidence, label=label or concept, method=method
                )
            value: object = checked.value
            repaired = checked.repaired
            extra["validation"] = "repaired" if repaired else "valid"
        else:
            value, _ = normalize_value(data_type, raw)
            if value in (None, ""):
                return None
            if concept.endswith("_name") or concept in (
                "personal.full_name",
                "personal.given_names",
            ):
                value = normalize_name(value)
        if data_type in _TYPED_PATTERNS and not re.fullmatch(
            _TYPED_PATTERNS[data_type], str(value)
        ):
            # the normalizer could not interpret it: keep it as text, never as a typed value
            return self._fact(
                None, raw, line, evidence=evidence, label=label or concept, method=method
            )
        compact_raw = " ".join(raw.split())
        return CandidateFact(
            concept=concept,
            semantic_type=concept.split(".", 1)[-1].upper(),
            field=concept.split(".", 1)[-1],
            value=value,
            raw_value=raw,
            data_type=data_type,
            confidence=round(confidence - (0.07 if repaired else 0), 3),
            origin="normalized" if repaired or str(value) != compact_raw else "extracted",
            method=method,
            page=line.page,
            evidence_text=(evidence or line.text)[:500],
            extra=extra,
        )

    def _resolve_label(self, label: str) -> tuple[bool, str | None]:
        """(is_label, concept). A known label may map to ``None`` (keep as key-value).

        Bilingual labels ("नाम / Name") lose their Indic half in English OCR
        ("71H / Name"); when the whole label is unknown each "/" part is tried,
        English (last) part first.
        """
        resolved = self._resolve_single_label(label)
        if resolved[0] or "/" not in label:
            return resolved
        for part in reversed(label.split("/")):
            if len(part.strip()) >= 3:
                resolved = self._resolve_single_label(part.strip())
                if resolved[0]:
                    return resolved
        return False, None

    def _resolve_single_label(self, label: str) -> tuple[bool, str | None]:
        key = label_key(label)
        if not key:
            return False, None
        if key in self.doc_type.labels:
            mapped = self.doc_type.labels[key]
            return True, self._scoped(mapped)
        matches = self.ontology.match_text(label)
        if not matches or matches[0].score < 0.98:
            return False, None
        tied = [m.concept for m in matches if m.score >= matches[0].score]
        if len(tied) > 1:
            scoped = [c for c in tied if self.ontology.scoped(c, self.doc_type.scope) != c]
            if len(scoped) != 1:
                return True, None
            return True, self._scoped(scoped[0])
        return True, self._scoped(matches[0].concept)

    # ------------------------------------------------------------------ identifiers

    def _identifiers(self, lines: list[_Line]) -> list[CandidateFact]:
        facts = []
        seen: set[tuple[str, str]] = set()
        for kind, concept in self.doc_type.identifiers.items():
            for line in lines:
                if _MRZ.match(line.text):
                    continue
                for raw, checked in validators.find(kind, line.text):
                    if (concept, checked.value) in seen:
                        continue
                    seen.add((concept, checked.value))
                    fact = self._fact(concept, raw, line, method="identifier", confidence=0.95)
                    if fact is not None:
                        facts.append(fact)
        return facts

    # ------------------------------------------------------------------ labelled values

    def _labelled(self, lines: list[_Line]) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        consumed: set[int] = set()
        for index, line in enumerate(lines):
            if index in consumed or _MRZ.match(line.text):
                continue
            segments = [s.strip() for s in _PAIR_SPLIT.split(line.text) if s.strip()]
            paired = False
            for position, segment in enumerate(segments):
                if paired:  # this segment was consumed as the previous label's value
                    paired = False
                    continue
                label, value = self._split_segment(segment)
                if label is None:
                    continue
                is_label, concept = self._resolve_label(label)
                if not value and is_label and position + 1 < len(segments):
                    # "Label    Value": OCR flattens a colon-less two-column table row into
                    # one line with a wide gap; a known label takes the next segment as its
                    # value unless that segment is itself a label.
                    following = segments[position + 1]
                    if not self._resolve_label(following.partition(":")[0])[0] and not (
                        ":" in following and self._split_segment(following)[0]
                    ):
                        value, paired = following, True
                        segment = f"{segment} {following}"
                if not value:
                    if not is_label or len(_PAIR_SPLIT.split(line.text)) > 1:
                        continue
                    value, used = self._following_value(lines, index, concept)
                    consumed.update(used)
                    if not value:
                        continue
                    evidence = " ".join(lines[i].text for i in [index, *used])
                elif (
                    concept
                    and self.ontology.data_type(concept) in _ADDRESS_TYPES
                    and value.endswith(",")
                ):
                    more, used = self._following_value(lines, index, concept)
                    consumed.update(used)
                    value = f"{value} {more}".strip()
                    evidence = " ".join(lines[i].text for i in [index, *used])
                else:
                    evidence = segment
                if not is_label and not self._looks_like_pair(label, value):
                    continue
                facts.extend(self._labelled_fact(concept, value, line, evidence, label))
        return facts

    def _split_segment(self, segment: str) -> tuple[str | None, str]:
        if ":" in segment:
            label, _, value = segment.partition(":")
            label = label.strip()
            if (
                label
                and len(label) <= _MAX_LABEL_CHARS
                and len(label.split()) <= _MAX_LABEL_WORDS
                and re.search(r"[A-Za-z]", label)
            ):
                return label, value.strip()
            return None, ""
        if len(segment) <= _MAX_LABEL_CHARS and self._resolve_label(segment)[0]:
            return segment, ""  # a label on its own line; the value follows
        # "Roll No. 12345678", "Mother's Name MEENA ...": longest known label prefix
        words = segment.split()
        for size in range(min(6, len(words) - 1), 0, -1):
            candidate = " ".join(words[:size])
            is_label, concept = self._resolve_label(candidate)
            value = " ".join(words[size:])
            if value.split()[0].casefold() in _SENTENCE_WORDS:
                continue  # running prose ("annual income from all sources for ..."), not a value
            if is_label and concept is not None and _value_like(concept, value):
                return candidate, value
        return None, ""

    @staticmethod
    def _looks_like_pair(label: str, value: str) -> bool:
        """Unknown labels are kept only when the line really is 'label: value'."""
        return (
            bool(value)
            and len(label.split()) <= 8
            and not label.lower().startswith(("http", "www"))
        )

    def _following_value(
        self, lines: list[_Line], index: int, concept: str | None
    ) -> tuple[str, list[int]]:
        is_address = bool(concept) and self.ontology.data_type(concept or "") in _ADDRESS_TYPES
        used: list[int] = []
        parts: list[str] = []
        for offset in range(1, 5 if is_address else 2):
            position = index + offset
            if position >= len(lines) or lines[position].page != lines[index].page:
                break
            text = lines[position].text
            if ":" in text and self._resolve_label(text.partition(":")[0])[0]:
                break
            if not is_address and self._resolve_label(text)[0]:
                break
            if is_address and (validators.find("aadhaar", text) or "@" in text or "www." in text):
                break
            parts.append(text)
            used.append(position)
            if not is_address or _PIN.search(text):
                break
        return " ".join(parts), used

    def _labelled_fact(
        self, concept: str | None, value: str, line: _Line, evidence: str, label: str
    ) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        if concept and self.ontology.data_type(concept) in _ADDRESS_TYPES:
            match = _RELATION.match(value)
            if match and "relation_prefix" in self.doc_type.rules:
                relation = match.group(1).lower()
                if relation in _RELATION_CONCEPT:
                    fact = self._fact(
                        _RELATION_CONCEPT[relation],
                        match.group(2),
                        line,
                        evidence=evidence,
                        confidence=0.8,
                        method="relation_prefix",
                    )
                    if fact:
                        facts.append(fact)
                value = match.group(3)
        fact = self._fact(concept, value, line, evidence=evidence, label=label, method="label")
        if fact is None:
            return facts
        facts.append(fact)
        if fact.concept in _ZIP_FROM:
            pin = _PIN.findall(str(fact.value))
            if pin:
                zip_fact = self._fact(
                    "address.zipcode",
                    pin[-1].replace(" ", ""),
                    line,
                    evidence=evidence,
                    confidence=0.9,
                    method="address_pincode",
                )
                if zip_fact:
                    facts.append(zip_fact)
        return facts

    # ------------------------------------------------------------------ layout rules

    def _layout_rules(self, lines: list[_Line]) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        rules = self.doc_type.rules
        if "name_before_dob" in rules:
            for index, line in enumerate(lines[1:], start=1):
                if re.search(r"\b(DOB|Date of Birth|Year of Birth)\b|जन्म", line.text, re.I):
                    previous = lines[index - 1]
                    if _NAME_LINE.match(previous.text) and not re.search(
                        r"government|india|authority|male|female", previous.text, re.I
                    ):
                        fact = self._fact(
                            "personal.full_name",
                            previous.text,
                            previous,
                            evidence=f"{previous.text} {line.text}",
                            confidence=0.86,
                            method="layout_name_before_dob",
                        )
                        if fact:
                            facts.append(fact)
                    break
        if "gender_line" in rules:
            for line in lines:
                parts = [p.strip() for p in re.split(r"/", line.text)]
                if (
                    any(p.upper() in ("MALE", "FEMALE", "TRANSGENDER") for p in parts)
                    and len(line.text) <= 30
                ):
                    fact = self._fact(
                        "identity.gender", parts[-1], line, confidence=0.9, method="layout_gender"
                    )
                    if fact:
                        facts.append(fact)
                    break
        if self.doc_type.certify_that:
            for line in lines:
                match = _CERTIFY.search(line.text)
                if match:
                    fact = self._fact(
                        self._scoped(self.doc_type.certify_that),
                        match.group(1),
                        line,
                        evidence=line.text,
                        confidence=0.88,
                        method="certify_that",
                    )
                    if fact:
                        facts.append(fact)
                    break
        header = self.doc_type.header
        if header:
            pattern = re.compile(header["pattern"])
            exclude = re.compile(header["exclude"]) if header.get("exclude") else None
            for line in lines[: int(header.get("lines", 4))]:
                if pattern.search(line.text) and not (exclude and exclude.search(line.text)):
                    fact = self._fact(
                        self._scoped(header["concept"]),
                        line.text,
                        line,
                        confidence=0.88,
                        method="header",
                    )
                    if fact:
                        facts.append(fact)
                    break
        if "exam_session" in rules:
            for line in lines[:8]:
                match = _EXAM_SESSION.search(line.text)
                if match:
                    month_match = _MONTH_WORD.search(match.group(1))
                    if month_match:
                        printed = month_match.group(1)
                        month = _MONTHS.get(printed[:3].title(), printed.title())
                        fact = self._fact(
                            self._scoped("education.exam_month"),
                            month,
                            line,
                            confidence=0.9,
                            method="exam_header",
                        )
                        if fact:
                            fact.raw_value = printed
                            facts.append(fact)
                    fact = self._fact(
                        self._scoped("education.exam_year"),
                        match.group(2),
                        line,
                        confidence=0.9,
                        method="exam_header",
                    )
                    if fact:
                        facts.append(fact)
                    break
        return facts

    def _phrases(self, lines: list[_Line]) -> list[CandidateFact]:
        facts = []
        for pattern, concept in self.doc_type.phrases:
            for line in lines:
                match = pattern.search(line.text)
                if match:
                    fact = self._fact(
                        self._scoped(concept),
                        match.group(1),
                        line,
                        evidence=line.text,
                        confidence=0.86,
                        method="phrase",
                    )
                    if fact:
                        facts.append(fact)
                    break
        return facts

    # ------------------------------------------------------------------ tables

    def _tables(self, document: NormalizedDocument) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        tables = self.doc_type.tables
        records = []
        if "marks" in tables:
            marks = parse_marks(document.pages)
            records += marks.records
            if marks.totals.values:
                line = _Line(marks.totals.evidence, marks.totals.page or 1)
                for key, value in marks.totals.values.items():
                    fact = self._fact(
                        self._scoped(f"education.{key}"),
                        value,
                        line,
                        confidence=0.9,
                        method="table_totals",
                    )
                    if fact:
                        facts.append(fact)
        if "transactions" in tables:
            records += parse_transactions(document.pages)
        if "members" in tables:
            records += parse_members(document.pages)
        for record in records:
            base = _RECORD_CONCEPTS[record.kind]
            concept = (
                self._scoped("education.subject_marks").replace("subject_marks", "subjects")
                if record.kind == "subject"
                else base
            )
            if not self.ontology.is_known(concept):
                continue
            facts.append(
                CandidateFact(
                    concept=concept,
                    semantic_type=record.kind.upper(),
                    field=record.kind,
                    value=record.values,
                    raw_value=record.evidence,
                    data_type="record",
                    confidence=0.9 if record.method == "table" else 0.85,
                    origin="extracted",
                    method=record.method,
                    page=record.page,
                    evidence_text=record.evidence[:500],
                    extra={"document_type": self.doc_type.type_id},
                )
            )
        return facts

    # ------------------------------------------------------------------ derived values

    def _derived(self, facts: list[CandidateFact]) -> list[CandidateFact]:
        scope = self.doc_type.scope
        if scope not in ("class_10", "class_12"):
            return []
        by_concept = {f.concept: f for f in facts if f.concept}
        derived: list[CandidateFact] = []
        prefix = "academic.class10" if scope == "class_10" else "academic.class12"
        result = by_concept.get(f"{prefix}.result_status")
        year = by_concept.get(f"{prefix}.exam_year")
        if (
            result
            and year
            and _PASS.match(str(result.value))
            and f"{prefix}.passing_year" not in by_concept
        ):
            derived.append(
                _derived_fact(
                    f"{prefix}.passing_year",
                    str(year.value),
                    "year",
                    year,
                    f"Passed ({result.value}) in the {year.value} examination",
                    0.9,
                )
            )
        obtained = by_concept.get(f"{prefix}.marks_obtained")
        maximum = by_concept.get(f"{prefix}.max_marks")
        if obtained and maximum and f"{prefix}.percentage" not in by_concept:
            try:
                percent = round(float(obtained.value) * 100 / float(maximum.value), 2)
            except (TypeError, ValueError, ZeroDivisionError):
                percent = None
            if percent is not None and 0 <= percent <= 100:
                derived.append(
                    _derived_fact(
                        f"{prefix}.percentage",
                        f"{percent:.2f}",
                        "percentage",
                        obtained,
                        f"Computed from printed totals {obtained.value}/{maximum.value}; board-specific rules (e.g. best of five) are not applied",
                        0.75,
                    )
                )
        return derived


def _derived_fact(
    concept: str, value: str, data_type: str, base: CandidateFact, note: str, confidence: float
) -> CandidateFact:
    return CandidateFact(
        concept=concept,
        semantic_type=concept.split(".", 1)[-1].upper(),
        field=concept.split(".", 1)[-1],
        value=value,
        raw_value=value,
        data_type=data_type,
        confidence=confidence,
        origin="derived",
        method="derived",
        page=base.page,
        evidence_text=base.evidence_text,
        extra={**base.extra, "derivation": note},
    )


_TITLE_WORDS = re.compile(
    r"\b(certificate|card|statement|bill|passbook|licen[cs]e|marksheet|examination|department)\b",
    re.I,
)


def _value_like(concept: str, value: str) -> bool:
    """For 'Label value' lines without a colon: is the remainder a value, not a title word?"""
    if any(char.isdigit() for char in value):
        return True
    if concept.endswith("name") or concept.endswith("_name"):
        return len(value.split()) >= 1 and not _TITLE_WORDS.search(value)
    return len(value.split()) >= 2 and not _TITLE_WORDS.search(value)


_TYPED_PATTERNS = {
    "date": r"\d{4}-\d{2}-\d{2}",
    "number": r"\d+(?:\.\d+)?",
    "percentage": r"\d{1,3}(?:\.\d+)?",
    "year": r"(?:19|20)\d{2}",
    "amount": r"\d+(?:\.\d+)?",
    "gender": r"Male|Female|Transgender",
}
