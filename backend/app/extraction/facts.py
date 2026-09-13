"""Deterministic candidate fact extraction with source provenance.

Covers the full ontology:
  Personal  : full_name, first_name, last_name, middle_name, date_of_birth, gender, nationality
  Contact   : email, phone_number, linkedin, github, website
  Address   : address, current_address, permanent_address, city, state, country, postal_code
  Identity  : pan_number, passport_number, aadhaar_number
  Education : university, degree, specialization, graduation_year, cgpa, percentage
  Employment: organization, job_title, employment_dates, work_experience
  Skills    : skills, certifications, languages
  Other     : summary, achievements
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.models.documents import StructuredFact
from app.processing.schemas import NormalizedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")
DOB_RE = re.compile(
    r"(?i)(?:date\s+of\s+birth|dob|birth\s*date)\s*[:=\-–—]?\s*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{4}[/-]\d{1,2}[/-]\d{1,2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},\s*\d{2,4}"
    r"|\d{1,2}-[A-Za-z]{3,9}-\d{2,4})"
)
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
PASSPORT_RE = re.compile(
    r"(?i)\b(?:passport|passport\s*(?:no|number))\s*[:#\-–—]?\s*([A-Z0-9]{6,12})\b"
)
AADHAAR_RE = re.compile(r"(?<!\d)(\d{4}[ -]?\d{4}[ -]?\d{4})(?!\d)")

LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%.]+/?", re.IGNORECASE
)
GITHUB_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[\w\-%.]+(?:/[\w\-%.]+)*/?", re.IGNORECASE
)
URL_RE = re.compile(r"https?://[^\s,;><\"']+", re.IGNORECASE)

CGPA_RE = re.compile(
    r"(?i)(?:cgpa|gpa|grade\s*point\s*average)\s*[:=\-–—]?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)"
)
PERCENTAGE_RE = re.compile(
    r"(?i)(?:percentage|marks|score)\s*[:=\-–—]?\s*([0-9]+(?:\.[0-9]+)?\s*%?)"
)
GRAD_YEAR_RE = re.compile(
    r"(?i)(?:graduation|passed\s*out|batch|class\s*of|year\s*of\s*passing)\s*[:=\-–—]?\s*((?:19|20)\d{2})"
)
EMP_DATE_RE = re.compile(
    r"(?i)((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(?:19|20)\d{2})"
    r"\s*(?:to|–|—|-)\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(?:19|20)\d{2}|[Pp]resent|[Cc]urrent)"
)
YEAR_RANGE_RE = re.compile(
    r"\b((?:19|20)\d{2})\s*(?:to|–|—|-)\s*((?:19|20)\d{2}|[Pp]resent|[Cc]urrent)\b"
)

# ---------------------------------------------------------------------------
# Labelled-field regex
# Separators: colon, equals, single/double dash, en-dash, em-dash, dots (3+), space-only
# ---------------------------------------------------------------------------
_SEP = r"\s*(?:[:=]|[-–—]|\.{2,}|\s)\s*"

_LABEL_MAP: dict[str, str] = {
    "full.name": "full_name",
    "name": "full_name",
    "applicant.name": "full_name",
    "candidate.name": "full_name",
    "first.name": "first_name",
    "given.name": "first_name",
    "forename": "first_name",
    "last.name": "last_name",
    "surname": "last_name",
    "family.name": "last_name",
    "middle.name": "middle_name",
    "middle.initial": "middle_name",
    "gender": "gender",
    "sex": "gender",
    "nationality": "nationality",
    "citizenship": "nationality",
    "address": "current_address",
    "current.address": "current_address",
    "present.address": "current_address",
    "local.address": "current_address",
    "residential.address": "current_address",
    "permanent.address": "permanent_address",
    "home.address": "permanent_address",
    "native.address": "permanent_address",
    "city": "city",
    "town": "city",
    "state": "state",
    "province": "state",
    "country": "country",
    "nation": "country",
    "postal.code": "postal_code",
    "pin.code": "postal_code",
    "pincode": "postal_code",
    "zip.code": "postal_code",
    "zip": "postal_code",
    "postcode": "postal_code",
    "university": "university",
    "college": "university",
    "institute": "university",
    "institution": "university",
    "school": "university",
    "degree": "degree",
    "qualification": "degree",
    "course": "degree",
    "specialization": "specialization",
    "specialisation": "specialization",
    "major": "specialization",
    "branch": "specialization",
    "stream": "specialization",
    "graduation.year": "graduation_year",
    "passing.year": "graduation_year",
    "year.of.passing": "graduation_year",
    "batch": "graduation_year",
    "cgpa": "cgpa",
    "gpa": "cgpa",
    "percentage": "percentage",
    "marks": "percentage",
    "organization": "organization",
    "company": "organization",
    "employer": "organization",
    "workplace": "organization",
    "job.title": "job_title",
    "designation": "job_title",
    "role": "job_title",
    "position": "job_title",
    "profile": "job_title",
    "experience": "work_experience",
    "work.experience": "work_experience",
    "total.experience": "work_experience",
    "years.of.experience": "work_experience",
    "skills": "skills",
    "skill": "skills",
    "technical.skills": "skills",
    "competencies": "skills",
    "technologies": "skills",
    "tools": "skills",
    "certifications": "certifications",
    "certification": "certifications",
    "certificates": "certifications",
    "certificate": "certifications",
    "languages": "languages",
    "language": "languages",
    "known.languages": "languages",
    "education": "education",
    "summary": "summary",
    "objective": "summary",
    "career.objective": "summary",
    "profile.summary": "summary",
    "about": "summary",
    "achievements": "achievements",
    "accomplishments": "achievements",
    "awards": "achievements",
    "linkedin": "linkedin",
    "linkedin.profile": "linkedin",
    "github": "github",
    "github.profile": "github",
    "website": "website",
    "portfolio": "website",
}

# Build the alternation from longest to shortest to avoid prefix-matching issues.
# Keys in _LABEL_MAP use dots as separators (e.g. "current.address").
# We escape each word individually and join with a flexible separator pattern.
def _build_label_alt(key: str) -> str:
    parts = key.split(".")
    return r"[\s.\-]*".join(re.escape(p) for p in parts)


_label_alts = "|".join(
    _build_label_alt(k) for k in sorted(_LABEL_MAP.keys(), key=len, reverse=True)
)
LABELLED_RE = re.compile(
    rf"(?im)^\s*({_label_alts}){_SEP}(.+?)\s*$",
)

# Skills-section scanner: lines of bullet items after a "Skills" heading
_SKILLS_SECTION_RE = re.compile(
    r"(?im)^(?:technical\s+)?skills?\s*[:\-–—]?\s*\n((?:\s*[•\-*▸►→✓✔]?\s*.+\n?)+)",
)

# Name heuristic: two or three capitalised words on their own line (likely at top)
_NAME_LINE_RE = re.compile(
    r"(?m)^[ \t]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})[ \t]*$"
)


# ---------------------------------------------------------------------------
# Public extractor
# ---------------------------------------------------------------------------

class CandidateFactExtractor:
    """Extract all supported candidate concepts without overwriting existing facts."""

    def extract(
        self, normalized: NormalizedDocument, document_id: str, document_name: str
    ) -> list[StructuredFact]:
        facts: list[StructuredFact] = []
        now = datetime.now(UTC)

        # Build full document text for multi-line patterns (skills section, name heuristic)
        all_text = "\n".join(
            span.text for page in normalized.pages for span in page.spans if span.text.strip()
        )

        # Per-span extraction
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

        # Multi-line patterns over full document text
        facts.extend(
            self._skills_section_facts(all_text, document_id, document_name, now)
        )

        # Name heuristic: first capitalised-word-only line is likely the full name
        facts.extend(
            self._name_heuristic_facts(all_text, document_id, document_name, now)
        )

        concept_counts: dict[str, int] = {}
        for f in facts:
            concept_counts[f.concept] = concept_counts.get(f.concept, 0) + 1
        logger.info(
            "extraction_complete",
            extra={
                "document_id": document_id,
                "total_facts": len(facts),
                "concepts": concept_counts,
            },
        )

        return facts

    # ------------------------------------------------------------------

    def _from_span(
        self,
        text: str,
        page: int,
        method: str,
        document_id: str,
        document_name: str,
        timestamp: datetime,
    ) -> list[StructuredFact]:
        candidates: list[tuple[str, Any, str, float]] = []

        # --- Pattern-based ---
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

        for match in LINKEDIN_RE.finditer(text):
            candidates.append(("linkedin", match.group(0).strip(), "url", 0.95))

        for match in GITHUB_RE.finditer(text):
            candidates.append(("github", match.group(0).strip(), "url", 0.95))

        for match in CGPA_RE.finditer(text):
            candidates.append(("cgpa", match.group(1).strip(), "number", 0.90))

        for match in PERCENTAGE_RE.finditer(text):
            candidates.append(("percentage", match.group(1).strip(), "number", 0.85))

        for match in GRAD_YEAR_RE.finditer(text):
            candidates.append(("graduation_year", match.group(1).strip(), "year", 0.88))

        for match in EMP_DATE_RE.finditer(text):
            date_range = f"{match.group(1)} - {match.group(2)}"
            candidates.append(("employment_dates", date_range, "string", 0.85))

        for match in YEAR_RANGE_RE.finditer(text):
            date_range = f"{match.group(1)} - {match.group(2)}"
            candidates.append(("employment_dates", date_range, "string", 0.80))

        # --- Labelled fields ---
        for match in LABELLED_RE.finditer(text):
            raw_label = match.group(1).lower().strip()
            value = match.group(2).strip()
            if not value:
                continue
            # normalise whitespace in label to match _LABEL_MAP keys (with dots as wildcards)
            normalised_label = re.sub(r"\s+", ".", raw_label)
            concept = _resolve_label(normalised_label)
            if concept:
                # Map "education" meta-concept to "degree" if it reads like a degree
                if concept == "education":
                    concept = "degree"
                candidates.append((concept, value, "string", 0.82))

        return [
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
            for concept, value, value_type, confidence in candidates
        ]

    # ------------------------------------------------------------------

    def _skills_section_facts(
        self,
        full_text: str,
        document_id: str,
        document_name: str,
        timestamp: datetime,
    ) -> list[StructuredFact]:
        """Extract the Skills section as a single concatenated fact."""
        match = _SKILLS_SECTION_RE.search(full_text)
        if not match:
            return []
        raw = match.group(1)
        items = [
            re.sub(r"^[•\-*▸►→✓✔\s]+", "", line).strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        if not items:
            return []
        skills_value = ", ".join(items)
        return [
            StructuredFact(
                user_id="pending",
                concept="skills",
                value=skills_value,
                value_type="string",
                source_document_id=document_id,
                source_page=1,
                confidence=0.80,
                provenance={
                    "document_name": document_name,
                    "extraction_method": "section-scan",
                    "extracted_text": raw[:200],
                },
                is_user_confirmed=False,
                created_at=timestamp,
                updated_at=timestamp,
            )
        ]

    def _name_heuristic_facts(
        self,
        full_text: str,
        document_id: str,
        document_name: str,
        timestamp: datetime,
    ) -> list[StructuredFact]:
        """Detect the first standalone capitalised-word line as the candidate full name."""
        # Only inspect the first 600 characters (typically the header of a resume)
        header = full_text[:600]
        for match in _NAME_LINE_RE.finditer(header):
            name = match.group(1).strip()
            # Must be 2+ words, skip very short or very long matches
            if " " not in name or len(name) > 60:
                continue
            # Skip if this is a section header keyword
            _SKIP = {
                "education", "experience", "skills", "projects", "certifications",
                "achievements", "summary", "objective", "contact", "references",
                "personal", "details", "profile", "employment", "work",
            }
            words = name.lower().split()
            if any(w in _SKIP for w in words):
                continue
            return [
                StructuredFact(
                    user_id="pending",
                    concept="full_name",
                    value=name,
                    value_type="string",
                    source_document_id=document_id,
                    source_page=1,
                    confidence=0.75,
                    provenance={
                        "document_name": document_name,
                        "extraction_method": "name-heuristic",
                        "extracted_text": name,
                    },
                    is_user_confirmed=False,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def with_user_id(fact: StructuredFact, user_id: str) -> StructuredFact:
    return fact.model_copy(update={"user_id": user_id})


def _resolve_label(normalised_label: str) -> str | None:
    """Look up a normalised (dot-joined, lowercase) label in _LABEL_MAP."""
    # Direct lookup first
    if normalised_label in _LABEL_MAP:
        return _LABEL_MAP[normalised_label]
    # Fuzzy: try stripping trailing dots/spaces
    stripped = normalised_label.rstrip(".")
    if stripped in _LABEL_MAP:
        return _LABEL_MAP[stripped]
    # Try partial match for compound labels like "current.address"
    for key, concept in _LABEL_MAP.items():
        if re.fullmatch(key.replace(".", r"[\s.]*"), normalised_label, re.IGNORECASE):
            return concept
    return None


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
