"""Render evaluation results (console summary and Markdown). Pure formatting: no numbers are computed here
beyond percentages of the counts already in the report."""

from __future__ import annotations

from typing import Any


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def console(report: dict[str, Any]) -> str:
    ex, st, ask = report["extraction"], report["storage_and_retrieval"], report["ask_documents"]
    lines = [
        "=== DEMO EVALUATION (live stack) ===",
        f"LLM: {report['stack'].get('llm')} ({report['stack']['details'].get('llm_model', '?')})",
        f"documents processed: {sum(u['status'] == 'processed' for u in report['uploads'])}/{len(report['uploads'])}",
        f"document-type accuracy:     {pct(ex['document_type_accuracy'])}",
        f"exact-field accuracy:       {pct(ex['exact_field_accuracy'])} ({ex['fields_correct']}/{ex['fields_expected']})"
        f"  clean (no conflicting value): {pct(ex['clean_field_accuracy'])}",
        f"subject-table accuracy:     {pct(ex['subject_table_accuracy'])}   all record rows: {ex['record_rows_matched']}/{ex['record_rows_expected']}",
        f"scanned / digital fields:   {pct(ex['scanned_field_accuracy'])} / {pct(ex['digital_field_accuracy'])}",
        f"structured storage:         {st['documents_with_structured_facts']}   vector indexed: {st['documents_vector_indexed']}",
        f"retrieval top-1 / top-4:    {pct(st['retrieval_top1'])} / {pct(st['retrieval_top4'])} ({st['queries']} queries)",
        f"Ask Documents correctness:  {pct(ask['answer_correctness'])}  fully passing {ask['fully_passing']}/{ask['questions']}"
        f"  source attribution {pct(ask['source_attribution_accuracy'])}",
        f"infrastructure errors: {ask['infrastructure_errors']}   evidence-only (LLM unavailable): {ask['llm_unavailable_answers']}"
        f"   forbidden-value hits: {ask['forbidden_value_hits']}",
    ]
    fill = report.get("autofill")
    if fill and fill.get("ran"):
        t = fill["totals"]
        lines += [
            f"autofill [{fill.get('mode')}]: forms {t['forms_analyzed']}/{t['forms']}  correctly filled {t['correct']}  "
            f"incorrectly filled {t['incorrect']}  missing handled safely {t['missing_safe']}/{t['missing_expected']}  "
            f"held for review {t['held_for_review']}  missed {t['missed']}  user-only violated {t['user_violations']}  "
            f"submitted forms {t['submitted']}  files attached {t['files_attached']}"]
    elif fill:
        lines.append(f"autofill: NOT RUN ({fill.get('error')})")
    return "\n".join(lines)


def render(report: dict[str, Any]) -> str:
    ex, st, ask = report["extraction"], report["storage_and_retrieval"], report["ask_documents"]
    md = ["# Demo evaluation report", "",
          f"Generated {report['generated_at']} against `{report['api']}`. All figures come from live calls to the real "
          "pipeline; the answer key is `demo/expected/manifest.json`.", "",
          f"LLM provider: **{report['stack'].get('llm')}** · model `{report['stack']['details'].get('llm_model', '?')}` · "
          f"embedding `{report['stack']['details'].get('embedding_model', '?')}`", "",
          "## Extraction (OCR → structured facts)", "",
          "| Metric | Result |", "|---|---|",
          f"| Document-type accuracy | {pct(ex['document_type_accuracy'])} |",
          f"| Exact-field accuracy | {pct(ex['exact_field_accuracy'])} ({ex['fields_correct']}/{ex['fields_expected']}) |",
          f"| …with no conflicting extra value | {pct(ex['clean_field_accuracy'])} |",
          f"| Subject-wise table accuracy | {pct(ex['subject_table_accuracy'])} |",
          f"| All record rows (subjects, transactions, members) | {ex['record_rows_matched']}/{ex['record_rows_expected']} |",
          f"| Scanned-document fields | {pct(ex['scanned_field_accuracy'])} |",
          f"| Digital-PDF fields | {pct(ex['digital_field_accuracy'])} |", "",
          "### Per document", "", "| # | File | Type found | Fields | Records |", "|---|---|---|---|---|"]
    for d in ex["per_document"]:
        if d.get("status") != "processed":
            md.append(f"| {d['number']} | {d['file']} | {d.get('status')} | – | – |")
            continue
        rec = ", ".join(f"{k.split('.')[-1]} {v['matched_rows']}/{v['expected_rows']}" for k, v in d["records"].items()) or "–"
        good = sum(r["correct"] for r in d["fields"])
        md.append(f"| {d['number']} | {d['file']} | {d.get('document_type')} {'✓' if d['type_ok'] else '✗'} | {good}/{len(d['fields'])} | {rec} |")
    miss = [(d["file"], r) for d in ex["per_document"] for r in d.get("fields", []) if not r["correct"]]
    if miss:
        md += ["", "### Fields not extracted correctly", "", "| File | Concept | Expected | Found |", "|---|---|---|---|"]
        for file, r in miss:
            md.append(f"| {file} | {r['concept']} | {r['expected']} | {r['found'] or '—'} |")
    md += ["", "## Storage, indexing and retrieval", "",
           f"* structured facts stored (MongoDB): {st['documents_with_structured_facts']}",
           f"* vector-indexed (ChromaDB): {st['documents_vector_indexed']}",
           f"* retrieval top-1 {pct(st['retrieval_top1'])}, top-4 {pct(st['retrieval_top4'])} over {st['queries']} queries", "",
           "## Ask Documents", "",
           f"* questions: {ask['questions']} · fully passing: {ask['fully_passing']} · answer correctness: {pct(ask['answer_correctness'])}",
           f"* source attribution: {pct(ask['source_attribution_accuracy'])} over {ask['source_attribution_questions']} questions with expected sources",
           f"* infrastructure errors: {ask['infrastructure_errors']} · evidence-only answers (LLM unavailable): {ask['llm_unavailable_answers']} "
           f"· forbidden-value hits: {ask['forbidden_value_hits']} · median latency {ask['median_seconds']} s", "",
           "| ID | Category | Outcome | Status | Failed checks |", "|---|---|---|---|---|"]
    for r in ask["results"]:
        failed = ", ".join(k for k, v in (r.get("checks") or {}).items() if not v) or ("error: " + str(r.get("error"))[:60] if r["outcome"] == "infrastructure_error" else "")
        md.append(f"| {r['id']} | {r['category']} | {r['outcome']} | {r.get('status', '–')} | {failed} |")
    fill = report.get("autofill")
    if fill:
        md += ["", "## Browser autofill (real extension, real backend)", ""]
        if not fill.get("ran"):
            md.append(f"Not run: {fill.get('error')}")
        else:
            t = fill["totals"]
            md += [f"Mode: **{fill.get('mode')}** · forms analysed {t['forms_analyzed']}/{t['forms']} · extension build `{fill.get('extension', '')}`", "",
                   "| Measure | Count |", "|---|---|",
                   f"| Fields correctly filled | {t['correct']} |", f"| Fields incorrectly filled | {t['incorrect']} |",
                   f"| Missing-in-documents fields left empty | {t['missing_safe']}/{t['missing_expected']} |",
                   f"| Expected values held for review (not filled) | {t['held_for_review']} |",
                   f"| Expected values missed (empty, not flagged) | {t['missed']} |",
                   f"| User-only fields touched | {t['user_violations']} |",
                   f"| Forms submitted | {t['submitted']} |", f"| Files attached | {t['files_attached']} |", "",
                   "| Form | Fill-expected | Correct | Incorrect | Held | Missed | Missing-safe | User-safe |", "|---|---|---|---|---|---|---|---|"]
            for f in fill["forms"]:
                c = f["counts"]
                md.append(f"| {f['number']} {f['title']} | {c['fill_expected']} | {c['correct']} | {c['incorrect']} | {c['held_for_review']} | {c['missed']} | {c['missing_safe']}/{c['missing_expected']} | {c['user_safe']}/{c['user_expected']} |")
    return "\n".join(md) + "\n"


def public_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Aggregate numbers only (no expected values or answers), safe to show in the web UI."""
    ex, st, ask = report["extraction"], report["storage_and_retrieval"], report["ask_documents"]
    metrics = [
        {"label": "Documents processed", "value": f"{sum(u['status'] == 'processed' for u in report['uploads'])}/{len(report['uploads'])}"},
        {"label": "Document-type accuracy", "value": pct(ex["document_type_accuracy"])},
        {"label": "Exact-field accuracy", "value": f"{pct(ex['exact_field_accuracy'])} ({ex['fields_correct']}/{ex['fields_expected']})"},
        {"label": "Subject-table accuracy", "value": pct(ex["subject_table_accuracy"])},
        {"label": "Retrieval top-1 / top-4", "value": f"{pct(st['retrieval_top1'])} / {pct(st['retrieval_top4'])}"},
        {"label": "Ask Documents: answers passing every check", "value": f"{ask['fully_passing']}/{ask['questions']}"},
        {"label": "Ask Documents: source attribution", "value": pct(ask["source_attribution_accuracy"])},
        {"label": "Infrastructure failures (not model quality)", "value": str(ask["infrastructure_errors"] + ask["llm_unavailable_answers"])},
    ]
    fill = report.get("autofill")
    if fill and fill.get("ran"):
        t = fill["totals"]
        metrics += [
            {"label": f"Autofill ({fill.get('mode')}): correctly / incorrectly filled", "value": f"{t['correct']} / {t['incorrect']}"},
            {"label": "Autofill: missing values left empty", "value": f"{t['missing_safe']}/{t['missing_expected']}"},
            {"label": "Autofill: forms submitted / files attached", "value": f"{t['submitted']} / {t['files_attached']}"},
        ]
    return {"generated_at": report["generated_at"], "metrics": metrics,
            "note": "Aggregates from the last local run of `python -m demo.cli evaluate`; see demo/results/REPORT.md."}
