"""Repeatable accuracy evaluation on the synthetic Indian document fixtures.

    cd backend
    python -m tests.eval.run_eval --out ../docs/eval/current.json [--rag]

Measures the deterministic pipeline (the mock LLM returns nothing), which is
what runs when no LLM is configured and is the floor the LLM path builds on.
``--mode baseline`` scores the pre-upgrade extractor (``DeterministicExtractor``
only, no document classification, tables or generic key-values).

Nothing here is tuned to the numbers: fixtures and expected outcomes live in
``tests/indian_fixtures.py`` and are scored by the rules below.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "eval-secret-key-that-is-long-enough-123456")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from app.extraction.normalize import appears_in, normalize_date  # noqa: E402
from app.extraction.schemas import CandidateFact  # noqa: E402
from app.ontology.loader import FieldOntology  # noqa: E402
from bson import ObjectId  # noqa: E402

from tests.indian_fixtures import (  # noqa: E402
    DOCUMENTS,
    FORM_CASES,
    PROFILE_DOCUMENTS,
    USER_FACTS,
    DocFixture,
)

IDENTIFIER_HINTS = (
    "_number",
    "ifsc_code",
    "micr_code",
    "cif_number",
    ".number",
    "roll_number",
)


@dataclass
class Outcome:
    document_type: str
    facts: list[CandidateFact]
    records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    labels: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------- extraction adapters


def baseline_extract(ontology: FieldOntology, fixture: DocFixture) -> Outcome:
    from app.extraction.deterministic import DeterministicExtractor
    from app.extraction.merge import merge_candidates

    candidates = DeterministicExtractor(ontology).extract(fixture.normalized())
    return Outcome("UNKNOWN", merge_candidates(candidates))


def current_extract(ontology: FieldOntology, fixture: DocFixture) -> Outcome:
    from app.extraction.service import DocumentExtractionService

    service = DocumentExtractionService(ontology, llm_extractor=None)
    result = asyncio.run(service.extract(fixture.normalized(), fixture.file_name))
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    labels: set[str] = set()
    facts = []
    for candidate in result.candidates:
        if isinstance(candidate.value, dict):
            records[candidate.concept or candidate.field].append(candidate.value)
            continue
        if candidate.concept is None and candidate.extra.get("original_label"):
            labels.add(_label_key(candidate.extra["original_label"]))
        facts.append(candidate)
    return Outcome(result.document_type, facts, dict(records), labels)


# ---------------------------------------------------------------------- comparison helpers


def _label_key(label: str) -> str:
    return " ".join(re.sub(r"[^0-9a-z]+", " ", label.casefold()).split())


def _same(expected: str, actual: Any) -> bool:
    if actual is None:
        return False
    exp, act = str(expected), str(actual)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", exp):
        return normalize_date(act) == exp
    norm = lambda s: re.sub(r"[^0-9a-z]+", "", s.casefold())  # noqa: E731
    if norm(exp) == norm(act):
        return True
    try:
        return abs(float(exp.replace(",", "")) - float(act.replace(",", ""))) < 1e-6
    except ValueError:
        return False


def _is_identifier(concept: str) -> bool:
    return concept.endswith(IDENTIFIER_HINTS) or concept in {
        "identity.aadhaar_number",
        "identity.pan_number",
    }


def _ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


# ---------------------------------------------------------------------- extraction metrics


def evaluate_extraction(ontology: FieldOntology, mode: str) -> dict[str, Any]:
    extract = baseline_extract if mode == "baseline" else current_extract
    totals = defaultdict(float)
    per_document = []
    by_variant: dict[str, list[float]] = defaultdict(lambda: [0, 0])
    for fixture in DOCUMENTS:
        outcome = extract(ontology, fixture)
        text = fixture.normalized().text
        by_concept: dict[str, list[CandidateFact]] = defaultdict(list)
        for fact in outcome.facts:
            if fact.concept:
                by_concept[fact.concept].append(fact)
        correct = 0
        attributed = 0
        for concept, value in fixture.expected.items():
            matches = [f for f in by_concept.get(concept, []) if _same(value, f.value)]
            wrong = [f for f in by_concept.get(concept, []) if not _same(value, f.value)]
            totals["expected"] += 1
            totals["wrong_values"] += len(wrong)
            if matches:
                correct += 1
                fact = matches[0]
                if (
                    fact.page is not None
                    and fact.evidence_text
                    and appears_in(fact.raw_value, fact.evidence_text)
                    and appears_in(fact.evidence_text, text)
                ):
                    attributed += 1
            if _is_identifier(concept):
                totals["identifiers"] += 1
                totals["identifiers_exact"] += bool(matches)
        forbidden = sum(len(by_concept.get(concept, [])) for concept in fixture.absent)
        concept_facts = sum(len(v) for v in by_concept.values())
        totals["correct"] += correct
        totals["attributed"] += attributed
        totals["forbidden"] += forbidden
        totals["concept_facts"] += concept_facts
        totals["classified"] += outcome.document_type == fixture.document_type
        by_variant[fixture.variant][0] += correct
        by_variant[fixture.variant][1] += len(fixture.expected)

        record_cells = record_cells_ok = records_total = records_exact = 0
        for concept, expected_rows in fixture.records.items():
            actual_rows = outcome.records.get(concept, [])
            for expected_row in expected_rows:
                records_total += 1
                best = max(
                    (
                        sum(_same(v, row.get(k)) for k, v in expected_row.items())
                        for row in actual_rows
                    ),
                    default=0,
                )
                record_cells += len(expected_row)
                record_cells_ok += best
                records_exact += best == len(expected_row)
        totals["record_cells"] += record_cells
        totals["record_cells_ok"] += record_cells_ok
        totals["records"] += records_total
        totals["records_exact"] += records_exact

        labels_expected = {_label_key(label) for label in fixture.preserved_labels}
        labels_found = len(labels_expected & outcome.labels)
        totals["labels"] += len(labels_expected)
        totals["labels_found"] += labels_found

        per_document.append(
            {
                "fixture": fixture.fixture_id,
                "variant": fixture.variant,
                "expected_type": fixture.document_type,
                "predicted_type": outcome.document_type,
                "fields_correct": f"{correct}/{len(fixture.expected)}",
                "forbidden_facts": forbidden,
                "records_exact": f"{records_exact}/{records_total}",
                "labels_preserved": f"{labels_found}/{len(labels_expected)}",
            }
        )

    scored = totals["correct"] + totals["wrong_values"] + totals["forbidden"]
    return {
        "documents": len(DOCUMENTS),
        "document_classification_accuracy": _ratio(totals["classified"], len(DOCUMENTS)),
        "field_recall": _ratio(totals["correct"], totals["expected"]),
        "field_precision_scored": _ratio(totals["correct"], scored),
        "wrong_value_facts": int(totals["wrong_values"]),
        "forbidden_facts": int(totals["forbidden"]),
        "identifier_exact_match": _ratio(totals["identifiers_exact"], totals["identifiers"]),
        "table_record_exact_match": _ratio(totals["records_exact"], totals["records"]),
        "table_cell_accuracy": _ratio(totals["record_cells_ok"], totals["record_cells"]),
        "generic_kv_coverage": _ratio(totals["labels_found"], totals["labels"]),
        "source_attribution_accuracy": _ratio(totals["attributed"], totals["correct"]),
        "field_recall_by_variant": {
            variant: _ratio(ok, total) for variant, (ok, total) in sorted(by_variant.items())
        },
        "per_document": per_document,
    }


# ---------------------------------------------------------------------- form filling


class InMemoryFacts:
    """Just enough of StructuredFactsRepository for FactService.resolve_view."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records

    async def list_active(self, user_id: str, concept: str | None = None) -> list[dict[str, Any]]:
        return [
            r
            for r in self.records
            if r["user_id"] == user_id
            and r.get("status", "active") == "active"
            and (concept is None or r["concept"] == concept)
        ]


class NoRetrieval:
    async def search(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []


def build_profile_records(ontology: FieldOntology, mode: str, user_id: str) -> list[dict[str, Any]]:
    extract = baseline_extract if mode == "baseline" else current_extract
    now = datetime.now(UTC)
    records: list[dict[str, Any]] = []
    for fixture in PROFILE_DOCUMENTS:
        outcome = extract(ontology, fixture)
        candidates = list(outcome.facts) + [
            CandidateFact(
                semantic_type="RECORD",
                field=concept.split(".")[-1],
                value=row,
                raw_value=row,
                data_type="record",
                confidence=0.9,
                origin="extracted",
                method="table",
                concept=concept,
            )
            for concept, rows in outcome.records.items()
            for row in rows
        ]
        for candidate in candidates:
            if not candidate.concept or not ontology.is_fillable(candidate.concept):
                continue
            records.append(
                {
                    "_id": ObjectId(),
                    "user_id": user_id,
                    "concept": candidate.concept,
                    "value": candidate.value,
                    "raw_value": candidate.raw_value,
                    "value_type": candidate.data_type,
                    "origin": candidate.origin,
                    "status": "active",
                    "source_document_id": fixture.fixture_id,
                    "document_name": fixture.fixture_id,
                    "source_page": candidate.page,
                    "evidence_text": candidate.evidence_text,
                    "extraction_method": candidate.method,
                    "confidence": candidate.confidence,
                    "provenance": dict(candidate.extra),
                    "is_user_confirmed": False,
                    "created_at": now,
                    "updated_at": now,
                }
            )
    for concept, value in USER_FACTS.items():
        records.append(
            {
                "_id": ObjectId(),
                "user_id": user_id,
                "concept": concept,
                "value": value,
                "raw_value": value,
                "value_type": ontology.data_type(concept),
                "origin": "user_provided",
                "status": "active",
                "source_document_id": "user",
                "document_name": "Entered by you",
                "confidence": 1.0,
                "is_user_confirmed": True,
                "created_at": now,
                "updated_at": now,
            }
        )
    return records


def evaluate_forms(ontology: FieldOntology, mode: str) -> dict[str, Any]:
    from app.agents.field_classifier import FieldClassifier
    from app.agents.graph import FormFillGraph
    from app.agents.llm_provider import MockLLMProvider
    from app.core.config import get_settings
    from app.schemas.form_sessions import FieldObject
    from app.services.facts import FactService

    settings = get_settings()
    user_id = "eval-user"
    facts = FactService(InMemoryFacts(build_profile_records(ontology, mode, user_id)), ontology)
    llm = MockLLMProvider()
    graph = FormFillGraph(
        settings=settings,
        ontology=ontology,
        classifier=FieldClassifier(ontology, llm, settings.classifier_confidence_threshold),
        facts=facts,
        retrieval=NoRetrieval(),  # type: ignore[arg-type]
        llm=llm,
        recommendations=None,  # type: ignore[arg-type]
    )
    results: dict[str, list[dict[str, Any]]] = {}
    for form in sorted({case.form for case in FORM_CASES}):
        cases = [case for case in FORM_CASES if case.form == form]
        fields = [FieldObject(**case.field) for case in cases]
        results[form] = asyncio.run(graph.run(user_id, None, fields, persist=False))

    counts = defaultdict(int)
    rows = []
    for form, items in results.items():
        cases = [case for case in FORM_CASES if case.form == form]
        for case, item in zip(cases, items, strict=True):
            status = item["status"]
            proposed = [item.get("recommended_value")] + [
                c.get("value") for c in item.get("candidates") or []
            ]
            proposed = [p for p in proposed if p not in (None, "")]
            concept_ok = item.get("concept") == case.concept or (
                case.concept is None and status in ("security_blocked", "skipped")
            )
            counts["concept_ok"] += concept_ok
            counts[f"expected_{case.outcome}"] += 1
            if status == "ready":
                counts["ready"] += 1
            if case.outcome == "fill":
                if status == "ready" and _same(case.value, item["recommended_value"]):
                    verdict = "correct_fill"
                elif status == "ready":
                    verdict = "incorrect_fill"
                elif status == "needs_review" and any(_same(case.value, p) for p in proposed):
                    verdict = "safe_review"
                else:
                    verdict = "missed"
            elif case.outcome == "review":
                if status == "ready":
                    verdict = "incorrect_fill"
                elif status == "needs_review" and (
                    case.value is None or any(_same(case.value, p) for p in proposed)
                ):
                    verdict = "correct_review"
                elif status == "needs_review":
                    verdict = "wrong_suggestion"
                else:
                    verdict = "missed"
            else:
                if status == "ready":
                    verdict = "incorrect_fill"
                elif proposed:
                    verdict = "wrong_suggestion"
                else:
                    verdict = "correct_abstain"
            counts[verdict] += 1
            rows.append(
                {
                    "form": form,
                    "label": case.field.get("label"),
                    "expected": case.outcome,
                    "status": status,
                    "concept": item.get("concept"),
                    "verdict": verdict,
                }
            )
    total = len(FORM_CASES)
    correct = counts["correct_fill"] + counts["correct_review"] + counts["correct_abstain"]
    return {
        "fields": total,
        "field_matching_accuracy": _ratio(counts["concept_ok"], total),
        "end_to_end_correct_outcome_rate": _ratio(correct, total),
        "correct_fill_rate": _ratio(counts["correct_fill"], counts["expected_fill"]),
        "incorrect_fill_rate": _ratio(counts["incorrect_fill"], counts["ready"]),
        "incorrect_fills": counts["incorrect_fill"],
        "wrong_suggestions": counts["wrong_suggestion"],
        "verdicts": {
            key: counts[key]
            for key in (
                "correct_fill",
                "safe_review",
                "correct_review",
                "correct_abstain",
                "missed",
                "wrong_suggestion",
                "incorrect_fill",
            )
        },
        "rows": rows,
    }


# ---------------------------------------------------------------------- retrieval

RAG_QUERIES = [
    ("What are my class 12 physics marks?", "class12_hsc_table", "CLASS_12_MARKSHEET"),
    ("Which board did I pass class 10 from?", "class10_cbse_table", "CLASS_10_MARKSHEET"),
    ("What is the IFSC code of my bank branch?", "bank_passbook_table", "BANK_PASSBOOK"),
    (
        "What is my caste validity certificate number?",
        "caste_validity_clean",
        "CASTE_VALIDITY_CERTIFICATE",
    ),
    ("What is my annual family income?", "income_certificate_clean", "INCOME_CERTIFICATE"),
    ("Which state am I domiciled in?", "domicile_certificate_marathi", "DOMICILE_CERTIFICATE"),
    ("What is my passport expiry date?", "passport_clean", "PASSPORT"),
    ("What is my electricity consumer number?", "electricity_bill_clean", "ELECTRICITY_BILL"),
    ("Who are the members on my ration card?", "ration_card_table", "RATION_CARD"),
    ("What is my driving licence validity?", "driving_licence_clean", "DRIVING_LICENCE"),
    (
        "Where was I born according to the birth certificate?",
        "birth_certificate_clean",
        "BIRTH_CERTIFICATE",
    ),
    ("What is my voter ID EPIC number?", "voter_id_clean", "VOTER_ID"),
    (
        "Is my non creamy layer certificate valid?",
        "ncl_certificate_clean",
        "NON_CREAMY_LAYER_CERTIFICATE",
    ),
    (
        "What transactions are in my bank statement for July?",
        "bank_statement_table",
        "BANK_STATEMENT",
    ),
]


def evaluate_retrieval(ontology: FieldOntology, mode: str, top_k: int = 3) -> dict[str, Any]:
    """Real MiniLM embeddings, in-memory cosine search over each document's chunks."""
    import numpy as np
    from app.processing.chunking import TextChunker
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    extract = baseline_extract if mode == "baseline" else current_extract
    chunker = TextChunker(500, 50)
    chunks = []
    for fixture in PROFILE_DOCUMENTS:
        doc_type = extract(ontology, fixture).document_type
        for chunk in chunker.chunk_document(
            fixture.normalized(), "u", fixture.fixture_id, fixture.fixture_id, doc_type
        ):
            chunks.append(chunk)
    vectors = model.encode([c.text for c in chunks], normalize_embeddings=True)

    def run(filtered: bool) -> dict[str, float | None]:
        hits = relevant_retrieved = retrieved = 0
        for query, relevant, doc_type in RAG_QUERIES:
            q = model.encode([query], normalize_embeddings=True)[0]
            pool = [
                i
                for i, c in enumerate(chunks)
                if not filtered or c.metadata["document_type"] == doc_type
            ]
            ranked = sorted(pool, key=lambda i: float(np.dot(vectors[i], q)), reverse=True)[:top_k]
            docs = [chunks[i].metadata["document_id"] for i in ranked]
            hits += relevant in docs
            relevant_retrieved += sum(d == relevant for d in docs)
            retrieved += len(docs)
        return {
            f"recall_at_{top_k}": _ratio(hits, len(RAG_QUERIES)),
            f"precision_at_{top_k}": _ratio(relevant_retrieved, retrieved),
        }

    return {
        "queries": len(RAG_QUERIES),
        "chunks": len(chunks),
        "semantic_only": run(False),
        "semantic_plus_document_type_filter": run(True),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("baseline", "current"), default="current")
    parser.add_argument(
        "--set",
        choices=("dev", "heldout"),
        default="dev",
        help="dev: fixtures used during development; heldout: written afterwards, never tuned on",
    )
    parser.add_argument("--rag", action="store_true", help="also measure retrieval (loads MiniLM)")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    if args.set == "heldout":
        from tests import heldout_fixtures as heldout

        global DOCUMENTS, PROFILE_DOCUMENTS, FORM_CASES, USER_FACTS
        DOCUMENTS = heldout.HELDOUT_DOCUMENTS
        PROFILE_DOCUMENTS = heldout.HELDOUT_PROFILE_DOCUMENTS
        FORM_CASES = heldout.HELDOUT_FORM_CASES
        USER_FACTS = heldout.HELDOUT_USER_FACTS
    ontology = FieldOntology()
    report: dict[str, Any] = {
        "mode": args.mode,
        "fixture_set": args.set,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "llm": "none (mock provider returns empty output; deterministic path only)",
        "ocr_quality": "not measured: PaddleOCR is not installed in this environment",
        "extraction": evaluate_extraction(ontology, args.mode),
        "form_filling": evaluate_forms(ontology, args.mode),
    }
    if args.rag:
        report["retrieval"] = evaluate_retrieval(ontology, args.mode)
    summary = {k: v for k, v in report["extraction"].items() if k != "per_document"}
    summary |= {k: v for k, v in report["form_filling"].items() if k not in ("rows",)}
    if "retrieval" in report:
        summary["retrieval"] = report["retrieval"]
    print(json.dumps(summary, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
