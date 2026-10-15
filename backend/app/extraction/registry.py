"""Document-type registry and deterministic document classification.

Classification scores each registered type by weighted keyword presence plus
validated identifiers (a checksum-valid Aadhaar number is strong evidence for an
Aadhaar card). A type is chosen only when it clears ``min_score`` and beats the
runner-up by ``min_margin``; otherwise the document stays ``UNKNOWN`` and the LLM
(if configured) may classify it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.extraction import validators
from app.processing.schemas import NormalizedDocument

REGISTRY_PATH = Path(__file__).parent / "document_types.yaml"
_SCOPE_PREFIX = {
    "class_10": "academic.class10.",
    "class_12": "academic.class12.",
    "caste_certificate": "caste_certificate.",
    "caste_validity": "caste_validity.",
    "ncl_certificate": "ncl_certificate.",
    "income_certificate": "income_certificate.",
    "domicile_certificate": "domicile_certificate.",
    "birth_certificate": "birth_certificate.",
    "passport": "passport.",
    "driving_licence": "driving_licence.",
}
_TYPE_PREFIX = {
    "BANK_PASSBOOK": ["financial."],
    "BANK_STATEMENT": ["financial."],
    "ELECTRICITY_BILL": ["utility."],
    "RATION_CARD": ["ration_card."],
}
_LABEL_KEY = re.compile(r"[^a-z0-9]+")


def label_key(label: str) -> str:
    """ASCII words of a label, lower-case: "जन्म तिथि / DOB" -> "dob"."""
    return " ".join(_LABEL_KEY.sub(" ", label.casefold()).split())


@dataclass(frozen=True)
class DocumentType:
    type_id: str
    label: str
    keywords: dict[str, float]
    identifiers: dict[str, str]
    identifier_weight: float
    scope: str | None
    labels: dict[str, str | None]
    certify_that: str | None
    header: dict[str, Any] | None
    phrases: list[tuple[re.Pattern[str], str]]
    rules: frozenset[str]
    tables: frozenset[str]


@dataclass
class Classification:
    document_type: str = "UNKNOWN"
    confidence: float = 0.0
    scores: dict[str, float] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    free_form: bool = False


class DocumentRegistry:
    def __init__(self, path: Path = REGISTRY_PATH) -> None:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        self.min_score = float(data.get("min_score", 3))
        self.min_margin = float(data.get("min_margin", 1))
        self.ignore_phrases = [p.casefold() for p in data.get("ignore_phrases", [])]
        free_form = data.get("free_form_signals") or {}
        self.free_form_phrases = [p.casefold() for p in free_form.get("phrases", [])]
        self.free_form_min_hits = int(free_form.get("min_hits", 3))
        self.free_form_override = float(free_form.get("override_score", 9))
        self.types: dict[str, DocumentType] = {}
        for type_id, entry in data["document_types"].items():
            self.types[type_id] = DocumentType(
                type_id=type_id,
                label=entry["label"],
                keywords={k.casefold(): float(v) for k, v in (entry.get("keywords") or {}).items()},
                identifiers=dict(entry.get("identifiers") or {}),
                identifier_weight=float(entry.get("identifier_weight", 0)),
                scope=entry.get("scope"),
                labels={label_key(k): v for k, v in (entry.get("labels") or {}).items()},
                certify_that=entry.get("certify_that"),
                header=entry.get("header"),
                phrases=[
                    (re.compile(p["pattern"]), p["concept"]) for p in entry.get("phrases") or []
                ],
                rules=frozenset(entry.get("rules") or []),
                tables=frozenset(entry.get("tables") or []),
            )

    def get(self, type_id: str | None) -> DocumentType | None:
        return self.types.get(type_id or "")

    def document_types_for(self, concept: str | None) -> list[str]:
        """Document types that state ``concept`` (for metadata-filtered retrieval)."""
        if not concept:
            return []
        found = []
        for doc_type in self.types.values():
            produced = set(doc_type.identifiers.values()) | {
                c for c in doc_type.labels.values() if c
            }
            produced |= {doc_type.certify_that} if doc_type.certify_that else set()
            if doc_type.header:
                produced.add(doc_type.header["concept"])
            prefixes = [_SCOPE_PREFIX[doc_type.scope]] if doc_type.scope in _SCOPE_PREFIX else []
            prefixes += _TYPE_PREFIX.get(doc_type.type_id, [])
            if concept in produced or any(concept.startswith(p) for p in prefixes):
                found.append(doc_type.type_id)
        return found

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"document_type": t.type_id, "label": t.label, "tables": sorted(t.tables)}
            for t in self.types.values()
        ]

    def classify(self, document: NormalizedDocument) -> Classification:
        text = " ".join(
            span.text for page in document.pages[:2] for span in page.spans if not span.is_table
        )
        lowered = " ".join(text.casefold().replace(".", " ").split())
        for phrase in self.ignore_phrases:
            lowered = lowered.replace(phrase, " ")
        scores: dict[str, float] = {}
        evidence: dict[str, list[str]] = {}
        for doc_type in self.types.values():
            score = 0.0
            hits = []
            for phrase, weight in doc_type.keywords.items():
                if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", lowered):
                    score += weight
                    hits.append(phrase)
            for kind in doc_type.identifiers:
                if validators.find(kind, text):
                    score += doc_type.identifier_weight
                    hits.append(f"valid {kind}")
            scores[doc_type.type_id] = score
            evidence[doc_type.type_id] = hits
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best, best_score = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
        free_form_hits = [
            phrase
            for phrase in self.free_form_phrases
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", lowered)
        ]
        if len(free_form_hits) >= self.free_form_min_hits and best_score < self.free_form_override:
            return Classification(scores=scores, evidence=free_form_hits, free_form=True)
        if best_score < self.min_score or best_score - runner_up < self.min_margin:
            return Classification(scores=scores)
        confidence = min(0.99, 0.6 + 0.04 * best_score + 0.05 * (best_score - runner_up))
        return Classification(best, round(confidence, 3), scores, evidence[best])


@lru_cache
def get_registry() -> DocumentRegistry:
    return DocumentRegistry()
