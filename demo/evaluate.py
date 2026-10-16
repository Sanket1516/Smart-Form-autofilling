"""API-level evaluation against the independent answer key (`demo/expected/manifest.json`).

    python -m demo.cli evaluate            # API suite (+ browser suite when --browser)

Measures, against the real stack (OCR -> extraction -> MongoDB -> ChromaDB -> Ask Documents):

* document-type accuracy, exact-field accuracy, record/table accuracy (subjects, transactions, members)
* scanned vs digital extraction accuracy (OCR path)
* structured storage and vector indexing per document, retrieval top-1 / top-4
* Ask Documents: answer correctness, forbidden-value hits, source attribution, status handling, follow-ups
* scenario reasoning (fictional eligibility rules)

Infrastructure failures (API/LLM unreachable, ``evidence_only`` answers because the model was unavailable) are
reported separately from model-quality failures. Nothing is fabricated: every number comes from a live call.
"""

from __future__ import annotations

import difflib
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from demo.client import DemoClient, InfrastructureError

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "expected" / "manifest.json"
DOC_NO = re.compile(r"DEMO_(\d\d)_")

DATE_CONCEPTS = ("date", "valid_until", "expiry")
NUMERIC_CONCEPTS = ("percentage", "marks", "annual_income", "bill_amount", "units_consumed", "year")
ID_CONCEPTS = ("number", "ifsc", "micr", "pan", "licence_number")


# ------------------------------------------------------------------ value comparison
def _alnum(text: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).casefold())


def _num(text: Any) -> float | None:
    cleaned = re.sub(r"[^0-9.\-]", "", str(text).replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def same(concept: str, expected: Any, actual: Any) -> bool:
    if isinstance(actual, dict):
        actual = " ".join(map(str, actual.values()))
    last = concept.rsplit(".", 1)[-1]
    if any(k in last for k in DATE_CONCEPTS) and last not in ("passing_year", "exam_year"):
        return str(actual)[:10] == str(expected)[:10]
    if concept.endswith(("phone", "phone")):
        return re.sub(r"\D", "", str(actual))[-10:] == re.sub(r"\D", "", str(expected))[-10:]
    if last in ("passing_year", "exam_year", "percentage", "max_marks", "marks_obtained", "annual_income",
                "bill_amount", "units_consumed"):
        a, b = _num(actual), _num(expected)
        return a is not None and b is not None and abs(a - b) < 0.006
    if any(k in last for k in ID_CONCEPTS) or last in ("ifsc_code", "account_number", "registration_number"):
        return _alnum(actual) == _alnum(expected)
    a, b = _alnum(actual), _alnum(expected)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.93


def norm_text(text: str) -> str:
    text = re.sub(r"(?<=\d),(?=\d)", "", str(text))
    return re.sub(r"\s+", " ", text.casefold())


# --------------------------------------------------------------------- extraction eval
def evaluate_extraction(client: DemoClient, manifest: dict, loaded: dict[str, dict]) -> dict:
    per_doc, totals = [], {"fields": 0, "correct": 0, "clean": 0, "rows": 0, "rows_ok": 0}
    split = {"scanned": [0, 0], "digital": [0, 0]}
    type_ok = 0
    sub_rows = [0, 0]
    discovered = client.discovered_facts()  # record tables (transactions, members) are stored here
    for doc in manifest["documents"]:
        info = loaded.get(doc["file"])
        entry: dict[str, Any] = {"number": doc["number"], "file": doc["file"], "scanned": bool(doc.get("scanned"))}
        if not info or info["status"] != "processed":
            entry.update(status=(info or {}).get("status", "not loaded"), fields=[], error=(info or {}).get("error"))
            per_doc.append(entry)
            totals["fields"] += len(doc["fields"])
            split["scanned" if doc.get("scanned") else "digital"][1] += len(doc["fields"])
            continue
        facts = client.doc_facts(info["document_id"])
        by_concept: dict[str, list[Any]] = {}
        for fact in facts:
            by_concept.setdefault(fact["concept"], []).append(fact)
        accepted = doc.get("accept_types") or [doc["expected_type"]]
        got_type = info.get("document_type")
        ok_type = got_type in accepted or (doc["expected_type"] in ("OTHER", "RATION_CARD") and got_type in (None, "OTHER", "RATION_CARD"))
        type_ok += ok_type
        rows = []
        for concept, expected in doc["fields"].items():
            candidates = by_concept.get(concept, [])
            values = [c["value"] for c in candidates]
            correct = any(same(concept, expected, v) for v in values)
            clean = correct and all(same(concept, expected, v) for v in values)
            page = next((c.get("source_page") for c in candidates if same(concept, expected, c["value"])), None)
            want_page = (doc.get("concept_pages") or {}).get(concept)
            rows.append({"concept": concept, "expected": expected, "found": values[:3], "correct": correct,
                         "clean": clean, "page": page, "page_ok": (page == want_page) if want_page else None})
            totals["fields"] += 1
            totals["correct"] += correct
            totals["clean"] += clean
            bucket = split["scanned" if doc.get("scanned") else "digital"]
            bucket[0] += correct
            bucket[1] += 1
        record_rows = {}
        for concept, expected_rows in (doc.get("records") or {}).items():
            found = [f["value"] for f in by_concept.get(concept, []) if isinstance(f["value"], dict)]
            found += [f["value"] for f in discovered
                      if f.get("source_document_id") == info["document_id"] and f.get("ontology") == concept
                      and isinstance(f.get("value"), dict)]
            ok = 0
            for exp in expected_rows:
                if any(_row_match(concept, exp, f) for f in found):
                    ok += 1
            record_rows[concept] = {"expected_rows": len(expected_rows), "matched_rows": ok, "found_rows": len(found)}
            totals["rows"] += len(expected_rows)
            totals["rows_ok"] += ok
            if "subjects" in concept:
                sub_rows[0] += ok
                sub_rows[1] += len(expected_rows)
        entry.update(status="processed", llm_unavailable=bool(info.get("llm_unavailable")), expected_type=doc["expected_type"], document_type=got_type, type_ok=ok_type,
                     fields=rows, records=record_rows,
                     field_accuracy=round(sum(r["correct"] for r in rows) / max(1, len(rows)), 3))
        per_doc.append(entry)
    n_docs = len(manifest["documents"])
    return {
        "documents": n_docs,
        "document_type_accuracy": round(type_ok / n_docs, 3),
        "exact_field_accuracy": round(totals["correct"] / max(1, totals["fields"]), 3),
        "clean_field_accuracy": round(totals["clean"] / max(1, totals["fields"]), 3),
        "fields_expected": totals["fields"], "fields_correct": totals["correct"],
        "record_rows_expected": totals["rows"], "record_rows_matched": totals["rows_ok"],
        "record_row_accuracy": round(totals["rows_ok"] / max(1, totals["rows"]), 3),
        "subject_table_accuracy": round(sub_rows[0] / max(1, sub_rows[1]), 3),
        "scanned_field_accuracy": round(split["scanned"][0] / max(1, split["scanned"][1]), 3),
        "digital_field_accuracy": round(split["digital"][0] / max(1, split["digital"][1]), 3),
        "documents_with_llm_unavailable": sum(1 for d in per_doc if d.get("llm_unavailable")),
        "per_document": per_doc,
    }


def _row_match(concept: str, exp: dict, got: dict) -> bool:
    if "subjects" in concept:
        name_ok = _alnum(exp["name"]) == _alnum(got.get("name", ""))
        marks = got.get("marks_obtained") or got.get("total")
        return name_ok and _num(marks) == _num(exp.get("marks_obtained") or exp.get("total"))
    if "transactions" in concept:
        return _alnum(exp["reference"]) in _alnum(json.dumps(got))
    if "members" in concept:
        return _alnum(exp["name"]) in _alnum(json.dumps(got))
    return False


# ----------------------------------------------------- storage / indexing / retrieval
def evaluate_storage_and_retrieval(client: DemoClient, manifest: dict, loaded: dict[str, dict]) -> dict:
    stored = indexed = 0
    docs_by_no: dict[int, str] = {}
    for doc in manifest["documents"]:
        info = loaded.get(doc["file"])
        if not info:
            continue
        docs_by_no[doc["number"]] = info["document_id"]
        if info["status"] == "processed" and (info.get("facts") or 0) > 0:
            stored += 1
        if info.get("index_status") == "indexed" and (info.get("chunks") or 0) > 0:
            indexed += 1
    id_to_no = {v: k for k, v in docs_by_no.items()}
    top1 = top4 = 0
    rows = []
    for item in manifest["retrieval"]:
        try:
            results = client.search(item["query"], top_k=4)
        except InfrastructureError:
            raise
        ranked = [id_to_no.get((r.get("metadata") or {}).get("document_id")) for r in results]
        hit1 = bool(ranked) and ranked[0] == item["document"]
        hit4 = item["document"] in ranked
        top1 += hit1
        top4 += hit4
        rows.append({"query": item["query"], "expected": item["document"], "ranked": ranked, "top1": hit1, "top4": hit4})
    n = len(manifest["retrieval"])
    total = len(manifest["documents"])
    return {"documents_with_structured_facts": f"{stored}/{total}", "documents_vector_indexed": f"{indexed}/{total}",
            "retrieval_top1": round(top1 / n, 3), "retrieval_top4": round(top4 / n, 3), "queries": n, "detail": rows}


# ----------------------------------------------------------------------- Ask Documents
def _haystack(data: dict) -> str:
    parts = [data.get("answer", "")]
    parts += [str(f.get("value")) for f in data.get("facts", [])]
    parts += [str(d.get("value")) for d in data.get("derived", [])]
    parts += [f"{r.get('label')} {r.get('detail')}" for r in data.get("requirements", [])]
    parts += [m.get("label", "") for m in data.get("missing", [])]
    parts += [s.get("snippet", "") for s in data.get("sources", [])]
    return norm_text(" ".join(map(str, parts)))


def _cited(data: dict) -> set[int]:
    names = [f.get("document_name") or "" for f in data.get("facts", [])]
    names += [s.get("document_name") or "" for s in data.get("sources", [])]
    return {int(m.group(1)) for n in names if (m := DOC_NO.search(n))}


def score_question(item: dict, data: dict | None, error: str | None) -> dict:
    row: dict[str, Any] = {"id": item["id"], "category": item["category"], "question": item["question"]}
    if error or data is None:
        return {**row, "outcome": "infrastructure_error", "error": error}
    answer = data.get("answer", "")
    hay = _haystack(data)
    cited = _cited(data)
    expected_docs = set(item.get("cite_docs", []))
    row.update(status=data.get("status"), answer_mode=data.get("answer_mode"), question_type=data.get("question_type"),
               confidence=data.get("confidence"), answer=answer[:700], cited_documents=sorted(cited),
               facts_used=len(data.get("facts", [])), sources_used=len(data.get("sources", [])),
               requirements=[{"label": r["label"], "outcome": r["outcome"]} for r in data.get("requirements", [])][:30])
    if data.get("answer_mode") == "evidence_only":
        row["llm_unavailable"] = True
    checks = {}
    checks["expected_values"] = all(any(norm_text(v) in hay for v in group) for group in item.get("expect", []))
    forbidden = [f for f in item.get("forbid", []) if norm_text(f) in norm_text(answer)]
    forbidden += [m.group(0) for rx in item.get("forbid_regex", []) if (m := re.search(rx, answer))]
    checks["no_forbidden"] = not forbidden
    row["forbidden_hits"] = forbidden
    if item.get("expect_any_text"):
        checks["expected_phrase"] = any(p in hay for p in item["expect_any_text"])
    if item.get("expect_status"):
        checks["status"] = data.get("status") in item["expect_status"]
    if item.get("min_requirements"):
        counts: dict[str, int] = {}
        for r in data.get("requirements", []):
            counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
        checks["requirements_counts"] = all(counts.get(k, 0) >= v for k, v in item["min_requirements"].items())
        row["requirement_counts"] = counts
    if item.get("requirements_mention_any"):
        text = norm_text(" ".join(f"{r['label']} {r['detail']}" for r in data.get("requirements", [])) + " " + answer)
        checks["requirements_mention"] = any(k in text for k in item["requirements_mention_any"])
    if item.get("eligibility"):
        got = {r["label"]: r["outcome"] for r in data.get("requirements", [])}
        detail = {}
        for label, ok in item["eligibility"].items():
            detail[label] = {"expected": ok, "got": got.get(label)}
        row["eligibility_detail"] = detail
        checks["eligibility"] = all(v["got"] in v["expected"] for v in detail.values())
    if expected_docs:
        need = item.get("cite_min", 1)
        hits = len(cited & expected_docs)
        checks["source_attribution"] = hits >= need
        row["source_precision"] = round(hits / len(cited), 2) if cited else None
    row["checks"] = checks
    row["correct"] = all(v for k, v in checks.items() if k != "source_attribution")
    row["outcome"] = "pass" if all(checks.values()) else "fail"
    return row


def evaluate_ask(client: DemoClient, manifest: dict) -> dict:
    results, threads, previous_answer = [], {}, {}
    for item in manifest["questions"]:
        history = []
        parent = item.get("follow_up_of")
        if parent and parent in previous_answer:
            history = previous_answer[parent]
        started = time.monotonic()
        data = err = None
        retries = 0
        while True:
            try:
                data = client.ask(item["question"], history=history, exam_id=item.get("exam_id"))
                err = None
            except InfrastructureError as exc:
                data, err = None, str(exc)
            except RuntimeError as exc:
                data, err = None, f"HTTP error: {exc}"
            # evidence_only means the LLM provider was unavailable: retry before counting it
            if (err or (data or {}).get("answer_mode") == "evidence_only") and retries < 2:
                retries += 1
                time.sleep(8)
                continue
            break
        row = score_question(item, data, err)
        row["llm_retries"] = retries
        row["seconds"] = round(time.monotonic() - started, 2)
        results.append(row)
        if data is not None:
            previous_answer[item["id"]] = [*history, {"role": "user", "content": item["question"]},
                                           {"role": "assistant", "content": (data.get("answer") or "")[:1500] or "(no answer)"}]
    scored = [r for r in results if r["outcome"] != "infrastructure_error"]
    attributable = [r for r in scored if "source_attribution" in r["checks"]]
    return {
        "questions": len(results),
        "answered_without_infrastructure_error": len(scored),
        "infrastructure_errors": len(results) - len(scored),
        "llm_unavailable_answers": sum(1 for r in scored if r.get("llm_unavailable")),
        "answer_correctness": round(sum(r["correct"] for r in scored) / max(1, len(scored)), 3),
        "fully_passing": sum(r["outcome"] == "pass" for r in scored),
        "forbidden_value_hits": sum(bool(r["forbidden_hits"]) for r in scored),
        "source_attribution_accuracy": round(sum(r["checks"]["source_attribution"] for r in attributable) / max(1, len(attributable)), 3),
        "source_attribution_questions": len(attributable),
        "median_seconds": round(statistics.median(r["seconds"] for r in results), 2) if results else None,
        "results": results,
    }


def run_api_suite(client: DemoClient, manifest: dict, loaded_rows: list[dict]) -> dict:
    loaded = {row["file"]: row for row in loaded_rows}
    health = client.health()
    started = time.time()
    extraction = evaluate_extraction(client, manifest, loaded)
    storage = evaluate_storage_and_retrieval(client, manifest, loaded)
    ask = evaluate_ask(client, manifest)
    return {"stack": {"llm": health.get("llm"), "details": health.get("details", {}), "mongodb": health.get("mongodb"),
                      "chromadb": health.get("chromadb")},
            "uploads": loaded_rows, "extraction": extraction, "storage_and_retrieval": storage,
            "ask_documents": ask, "evaluation_seconds": round(time.time() - started, 1)}
