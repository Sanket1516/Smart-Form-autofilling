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
