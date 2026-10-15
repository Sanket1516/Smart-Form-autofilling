# Evaluation: Indian document intelligence and exam-form filling

Run date: 2026-10-15. Reproduce with:

```
cd backend
python -m tests.eval.run_eval --mode baseline --rag     # extractor before the upgrade
python -m tests.eval.run_eval --mode current --rag      # development fixtures
python -m tests.eval.run_eval --mode current --set heldout
```

Raw reports: `docs/eval/baseline.json`, `current.json`, `heldout_first_run.json`, `heldout_after_fixes.json`.

## What is measured, and what is not

* **Deterministic path only.** The mock LLM returns nothing, so these numbers are the
  floor that works with no LLM configured. A configured LLM adds facts on top; it was not
  evaluated (real-provider calls cost money and need a key).
* **Synthetic text, not images.** Fixtures reproduce what the text extractor emits
  (OCR-style lines, bilingual labels, PDF table spans). **OCR quality was not measured**:
  PaddleOCR is not installed in this environment, so scanned images were not run through OCR.
* **Small sets.** 20 development documents and 60 form fields; 10 held-out documents and
  20 held-out form fields. Treat the percentages as indicative, not as population accuracy.
* **Development fixtures were used while building the extractor**, so their scores are
  optimistic. The **held-out first run** is the honest generalisation estimate: those
  fixtures (a different candidate, boards, banks, layouts and form wording) were written
  after development and scored once before any fix.

Scoring rules (`tests/eval/run_eval.py`): a fact is correct when its concept matches and its
value matches after normalisation; *wrong value* = right concept, different value; *forbidden*
= a concept the document must not yield (e.g. the account holder as the candidate's name,
an email address printed by UIDAI). Form outcomes: **fill** (filled automatically, value must
match), **review** (a suggestion the user must confirm), **abstain** (nothing proposed:
preferences, declarations, official codes, ambiguous labels). An *incorrect fill* is any
automatic fill with a wrong value or any automatic fill where review or abstention was required.

## Results

| Metric | Baseline (before) | After upgrade (dev set) | Held-out, first run | Held-out after fixes* |
|---|---|---|---|---|
| Document classification accuracy | 0.00 (no classifier) | 1.00 | 1.00 | 1.00 |
| Field recall | 0.17 | 1.00 | 1.00 | 1.00 |
| Field precision (scored facts) | 0.60 | 1.00 | 0.98 | 1.00 |
| Wrong-value facts / forbidden facts | 8 / 9 | 0 / 0 | 0 / 1 | 0 / 0 |
| Identifier exact match | 0.23 | 1.00 | 1.00 | 1.00 |
| Table records exactly right (subjects, transactions, members) | 0.00 | 1.00 | 0.50 | 1.00 |
| Table cell accuracy | 0.00 | 1.00 | 0.39 | 1.00 |
| Generic key-value coverage (unfamiliar labels preserved) | 0.00 | 1.00 | 1.00 | 1.00 |
| Source attribution (page + evidence containing the value) | 1.00 | 1.00 | 1.00 | 1.00 |
| Field-matching accuracy (form field → concept) | 0.33 | 1.00 | 0.85 | 1.00 |
| End-to-end correct outcome rate | 0.37 | 1.00 | 0.70 | 1.00 |
| Correct-fill rate (fields that should be filled) | 0.20 | 1.00 | 0.62 | 1.00 |
| **Incorrect-fill rate (wrong among automatic fills)** | **0.47 (7 of 15)** | **0.00** | **0.00** | **0.00** |
| RAG recall@3, semantic only | 1.00 | 1.00 | – | – |
| RAG precision@3, semantic only | 0.36 | 0.36 | – | – |
| RAG precision@3 with document-type filter | n/a (no types) | 1.00 | – | – |

\* "after fixes" is no longer a held-out measurement; it only shows the fixes worked.

Baseline incorrect fills were all one defect: the alias "marks" mapped to the overall
percentage, so "Physics Marks Obtained", "Maximum Marks" and "Total Marks" were filled with
88.67. Held-out first-run misses were general gaps, fixed generically: abbreviated CBSE
table headers ("SUB NAME", "PRAC./IA"), an income certificate's "Name of Applicant" (a
parent) taken as the candidate, and the labels "Father/Guardian Name", "IFS Code" and
"Income Group". No held-out failure was an incorrect fill: the system abstained or asked.

The document-type filter result uses the correct type per query (an oracle); in form
filling the type is derived from the field's concept (`DocumentRegistry.document_types_for`)
and the search falls back to all documents when the filtered search finds nothing.

## Remaining limitations

* OCR accuracy on real scans, rotated or low-quality images is unmeasured here.
* Layouts outside the fixtures will fail in ways not yet seen; the LLM path and the user
  review workflow are the safety net, and the system abstains rather than guesses.
* Names printed surname-first (e.g. some state marksheets) appear as a conflict with
  given-name-first documents and need one user choice.
* Percentages are computed only from printed totals; board rules such as CBSE best-of-five
  are not applied, and such computed values always need confirmation.
* Exam requirement profiles and upload limits were reviewed on 2026-10-15 against secondary
  sources only; they are marked unverified until checked against the official bulletins.

---

# Second pass (2026-10-15): real OCR, retrieval, Ask Documents, models

All numbers below were produced in this session by the scripts named; raw reports are in
`docs/eval/`. Data is synthetic: the same fixtures as above, **rendered as real images and
PDFs** (`tests/eval/render_documents.py`): clean scan, skewed 3–4°, rotated 90°, and a
"phone photo" (blur, low contrast, uneven light, noise), plus digital and scanned PDFs.

## Root causes found in the running system

| Symptom | Root cause (traced in code and live data) | Fix |
|---|---|---|
| Correct value stored, wrong value used | A résumé that mentions "Passport No" was classified as a **passport**; the LLM then labelled CV lines as Class 10/12 facts, which competed with the marksheets | Free-form guard in the classifier (`free_form_signals`), LLM may not relabel a CV as an official document; facts record their source `document_type`; the official document wins a disagreement and the value still needs confirmation |
| Marksheet scanned → no subject marks | OCR returned one span **per text box** ("01", "ENGLISH", "100", "082"); the table and label parsers need lines | OCR layout rebuilding: boxes → lines (skew-corrected) → `|` table spans with header-aligned columns (`processing/ocr.py`) |
| Rotated phone photos unreadable | No orientation handling | Orientation check (score of upright boxes), deskew from box angles |
| Bilingual cards lost names | English OCR turns the Hindi half into garbage ("71H / Name") so the label was unknown | Each side of "a / b" labels is tried |
| Ask Documents wrong/empty | Pure vector search on the question + one LLM call: no exact facts, no Class 10/12 scoping, no document filter, 503 when the LLM failed | New `DocumentQAService` (below) |
| Chunks mixed unrelated facts | Page text flattened and cut every 500 characters mid-word | Line-preserving chunks, table chunks repeat the header row, document type in the embedding text |
| Worker crashes / Docker engine stops | PaddlePaddle CPU inference keeps buffers per crop shape: **2.5 GB peak for one page**; with 2 worker processes the 8 GB Docker VM ran out and the engine stopped (observed twice) | RapidOCR (same PP-OCR English models on ONNX Runtime, **~0.2–0.45 GB**), worker concurrency 1, container memory limits, killed jobs marked failed |
| Form field filled from a mis-mapped concept | Fill confidence ignored how the *field* was classified | Model-chosen mappings cap the confidence; fallback-model mappings always need review |

## OCR benchmark (`tests/eval/ocr_benchmark.py`, 30 documents × 4 image variants)

Field recall = expected fields extracted exactly by the deterministic extractor from the OCR
text; records = table rows (subjects, transactions, members) with every cell right.

| Variant | Legacy adapter (binarise + pixel deskew, one span per box) | New layout pipeline, PaddleOCR | 
|---|---|---|
| Clean scan | fields 0.938 · records 0.146 · 1.7 s | fields 0.933 · records 0.634 · 2.1 s |
| Skewed 3–4° | fields 0.876 · records 0.293 · 1.6 s | fields 0.871 · records 0.634 · 3.9 s |
| Rotated 90° | **fields 0.000** · records 0.000 · classification 0.00 | fields 0.933 · records 0.634 · classification 1.00 · 7.1 s |
| Phone photo | fields 0.839 · records 0.073 | fields 0.839 · records 0.463 · classification 0.97 |

Reports: `ocr_benchmark.json` (legacy and first layout version), `ocr_benchmark_v2.json`
(tuned layout). The first layout version was worse on photos (fields 0.611) because CLAHE
contrast let the detector merge table cells ("100082"); switching that step to adaptive
binarisation and narrowing the cell-gap threshold produced the v2 numbers. Remaining
differences: one field fewer on clean/skewed pages and one photo misclassified.

### Engine comparison: PaddleOCR vs RapidOCR (same pipeline, `ocr_benchmark_rapidocr.json`)

PaddleOCR's CPU inference peaked at **2.5 GB for a single page** (detection alone 0.83 GB,
growing with every distinct recognition crop shape; allocator flags, `ir_optim` and batch
size did not help). Under the 3.5 GB worker limit the job was OOM-killed. RapidOCR runs the
**same English PP-OCR models** (converted with paddle2onnx, shipped in `backend/models/ocr`)
on ONNX Runtime; resident memory stayed **165–275 MB across 24 consecutive pages**.

| Variant | PaddleOCR fields · records | RapidOCR fields · records | RapidOCR s/page |
|---|---|---|---|
| Clean | 0.933 · 0.634 | **0.948 · 0.732** | 2.6 |
| Skewed | **0.871** · 0.634 | 0.850 · **0.707** | 4.9 |
| Rotated 90° | 0.933 · 0.634 | **0.948 · 0.732** | 7.8 |
| Photo | 0.839 · 0.463 | **0.855 · 0.561** | 4.0 |

RapidOCR is the default (`OCR_ENGINE=rapidocr`); PaddleOCR remains selectable. Rotated pages
cost about three extra reads (7–10 s per page on CPU).

## Model comparison (`tests/eval/llm_benchmark.py`, `docs/eval/llm_benchmark.json`)

Six grounded-answer cases (with the production prompt and validation) and eight
field-classification cases the deterministic matcher cannot resolve.

| Model | QA correct | Cites real evidence | Unsupported numbers | Field classification | Median QA latency |
|---|---|---|---|---|---|
| Gemini `gemini-3.5-flash-lite` (configured) | 6/6 | 6/6 | 0 | 8/8 | 5.8 s |
| `qwen2:7b` via Ollama (local, Apache-2.0, RTX 3050 6 GB) | 4/6 | 4/6 | 0 | 5/8 | 6.3 s |
| `gemma:2b` via Ollama | 2/6 | 1/6 | 0 | 1/8 | 3.4 s |

Decision: keep Gemini as primary; `qwen2:7b` is offered only as an optional fallback, and
its field mappings always go to the user (it mapped "Your mom's full name" to the father's
name). **No fine-tuning was done**: the failures found were caused by OCR layout,
classification and retrieval logic, all fixed in code, and the configured model scored
100% on the model-dependent tasks, so there was no model behaviour to train away.

## Ask Documents

Unit/API tests: `backend/tests/test_document_qa.py` (27 tests: planning, Class 10/12
separation, certificate numbers, selected documents, foreign document ids → 404, no
cross-user answers, conflicts, subject marks, eligibility, discarded unsupported numbers,
model failure → evidence-only answer, follow-ups, unprocessed documents, missing info).

### Full stack, real services (`tests/eval/e2e_probe.py`, `docs/eval/e2e_after.json`)

Fresh synthetic user on the running Compose stack (API, Celery worker, MongoDB, ChromaDB,
RapidOCR, `all-MiniLM-L6-v2`, Gemini). Seven uploads through the real upload API — four
digital PDFs and three **scanned-style PNG images** read by OCR — and a second user with
another Class 12 marksheet.

| Measure | Result |
|---|---|
| Uploads processed and correctly typed | 7 / 7 |
| Questions answered correctly (exact, document, multi-document, missing info, eligibility, absent value) | **9 / 9** |
| Answers citing the right document | 9 / 9 |
| Forbidden claims (wrong class, invented percentage, "you are eligible") | 0 |
| HTTP errors | 0 |
| Cross-user leak (other user asks for the 88.67 percentage) | none |
| Median answer time | 0.11 s (exact lookups answered from facts, no model call); generated answers 2–5 s |

The question set is small (9) and the documents are synthetic, so these are indicative, not
population accuracy. No baseline run of the old Ask endpoint was captured: the first
attempt was interrupted when the Docker engine ran out of memory (the PaddleOCR issue above).

Earlier run of the same probe, before the last fixes, scored 8/9: the income certificate
answer was masked ("**0000") because annual income is a sensitive concept; masking in
answers is now limited to identifiers (Aadhaar, PAN, account numbers).

### Browser extension (Playwright, real Chromium with the built extension)

7 / 7 passed: upload → review → approve → fill → verify on a fixture form (values read back
from the page, password and honeypot untouched, form not submitted), document recommendation
and attachment for upload fields, actionable errors, light/dark visual flows.

## Remaining limitations (second pass)

* All accuracy figures use synthetic documents. Real scans (stamps, handwriting, folds,
  Devanagari-only text) were not available; English OCR cannot read Indic scripts.
* Skewed pages lost a few fields with RapidOCR (0.850 vs 0.871 with PaddleOCR).
* Eligibility rules (NEET, JEE) are configured from published criteria but are **not
  verified** against the current session's bulletin; answers say so and never declare a
  person eligible. MHT CET has no eligibility rules configured.
* The local fallback model (`qwen2:7b`) is clearly weaker; its outputs pass the same
  validation and its field mappings always need user confirmation.
* Documents processed before this upgrade keep their old facts and chunks until they are
  reprocessed (`python -m app.scripts.reindex` or **Process again**).
