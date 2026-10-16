# Judge demo: synthetic dataset, forms and evaluation

> **SYNTHETIC DEMO DATA — NOT A VALID GOVERNMENT DOCUMENT.** One fictional applicant (Kavya Suresh Deshpande).
> No real person, Aadhaar/PAN/passport/bank number, certificate, seal or signature is used. Identifiers only follow the
> *shape* a validator expects; none is valid or issued. Boards, banks, authorities and the "DemoScholar 2026" rules are fictional.

## Where things are

| What | Location |
|---|---|
| Source-of-truth profile | [`demo/profile.py`](profile.py) |
| 15 generated PDFs | [`frontend/public/demo/documents/`](../frontend/public/demo/documents) (`DEMO_01_…` to `DEMO_15_…`) |
| 15 generated forms (+ index, CSS, JS) | [`frontend/public/demo/forms/`](../frontend/public/demo/forms) |
| Generators | `documents_gen.py`, `forms_spec.py` + `forms_gen.py`, `manifest_gen.py` |
| **Answer key (tests only)** | [`demo/expected/manifest.json`](expected/manifest.json): never served, never read by the backend |
| Public question list (no answers) | `frontend/public/demo/scenarios.json` |
| Demo Data page | `/demo-data` in the web app (`frontend/src/pages/DemoData.tsx`) |
| API evaluation | `demo/evaluate.py` |
| Browser (Chrome extension) evaluation | `extension/tests/demo-autofill.spec.ts`, `extension/playwright.demo.config.ts` |
| Results | `demo/results/latest.json`, `demo/results/REPORT.md` |
| Fictional eligibility profile | `backend/app/exams/demo_requirements.yaml` (loaded only when `APP_ENV != production`) |

Documents: 7 digital PDFs; 5 scanned-style PDFs (rasterised, slightly rotated, noised: voter record, Class 10 marksheet,
birth record, passbook, category certificate), plus controlled OCR challenges (similar characters in identifiers such as
`DEMO0000417`, mixed date formats, dense 25-row transaction table, multi-column blocks, small print).

## Commands (from the repository root, stack running via `docker compose up -d`)

```bash
python -m demo.cli generate            # profile -> PDFs, forms, answer key, scenario list (deterministic)
python -m demo.cli load                # upload DEMO_* files to demo.applicant@example.com (idempotent, no duplicates)
python -m demo.cli status
python -m demo.cli evaluate            # API suite: extraction, storage, vector index, retrieval, Ask Documents
python -m demo.cli evaluate --browser  # + the real extension on all 15 forms (needs `cd extension && npm run build`)
DEMO_APPROVE_REVIEW=1 python -m demo.cli evaluate --browser   # also tick every reviewed value, as a careful user would
python -m demo.cli cleanup             # delete only DEMO_* documents (and their facts/vectors); --delete-account removes the demo account
```

Requirements: `pip install pymupdf reportlab pillow numpy httpx` for the generators and CLI; Node + `npx playwright install chromium`
for the browser suite. The demo account is separate from real accounts; override with `DEMO_EMAIL` / `DEMO_PASSWORD`.

## Design rules that keep the demo honest

* The forms contain **no values** and no canonical field keys. Values arrive only through the extension → backend → facts/RAG.
* Field badges on the forms (missing / filled / verified / review / your choice) are computed from the live DOM.
* Expected values are generated from `profile.py`, independently of OCR output.
* Fields no document holds (alternate mobile, Aadhaar, UPI ID, …) must stay empty; preferences, declarations and uploads must
  stay untouched. Forms are never submitted and no file is attached.
* Infrastructure failures (API unreachable, LLM provider 503/403, `evidence_only` answers) are retried, counted and reported
  separately from model-quality failures.

## Known limitations (see `REPORT.md` for current numbers)

* Document 13 combines a category certificate and its validity annexure in one file; classification is per document.
* Multi-column bills can glue a neighbouring label onto a value (kept as a conflicting extra value, correct one still present).
* Any `Category: …` line maps to the social-category concept; the demo documents avoid that label for non-category data.
* The LLM is an external service (Gemini); its availability affects Ask Documents answers and some extraction runs.
