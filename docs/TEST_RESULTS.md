# Test Results

Run date: 2026-10-13. Results below were collected locally on Windows with Python 3.11,
Node 22, Docker Compose, and Chromium. Backend tests used the mock LLM unless stated otherwise.

| Check | Result |
|---|---|
| `python -m ruff check backend tests` | Passed |
| `python -m black --check backend tests` | Passed; 111 files unchanged |
| `python -m pytest` | 146 passed, 7 deselected |
| Real Chroma integration (`-m chroma`) | 3 passed against the Compose Chroma service with real `all-MiniLM-L6-v2` embeddings |
| Frontend Vitest | 22 passed |
| Extension Vitest | 24 passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed for the dashboard and extension |
| Playwright browser E2E | 1 passed against the isolated Compose stack; upload, review, approve, fill, and no-submit assertions passed |
| Development and test Compose configuration | Both parsed successfully |
| Real-provider LLM tests | Not run; these are opt-in and can incur API charges |

The default backend command deselects the `chroma` and `real_llm` markers. The Chroma suite
was run separately against a temporary Compose service; the test project and its data volumes
were removed afterward. Playwright also ran in the isolated test Compose project and cleaned
up its containers and volumes. The CI workflow runs the same marked Chroma suite and browser
flow on pushes and pull requests.

## 2026-10-15: Indian document intelligence upgrade

| Check | Result |
|---|---|
| `python -m pytest` (repo root) | 239 passed, 7 deselected (was 146); new: `test_indian_documents.py`, `test_exam_forms.py`, `test_indian_api.py` |
| `python -m ruff check backend tests` / `black --check` | Pass for all changed files. `backend/app/processing/preprocessing.py` (unchanged here, from commit 86b6423) still fails both and needs `ruff --fix` + `black` |
| Frontend Vitest | 23 passed (1 new: profile subject tables, exam readiness, user choice, upload check) |
| Extension Vitest | 25 passed (1 new: nearest-heading section context) |
| `npm run lint` (frontend lint + both typechecks) / `npm run build` | Passed |
| Playwright browser E2E (isolated Compose stack) | 1 passed on the final code |
| Accuracy evaluation | See `docs/EVALUATION.md` (baseline vs upgrade vs held-out) |
| Real Chroma integration (`-m chroma`), real-provider LLM tests, OCR on real scans | Not run in this session |

## 2026-10-15 (second pass): OCR, retrieval, Ask Documents, model fallback, stability

| Check | Result |
|---|---|
| `python -m pytest` (repo root, needs MongoDB) | 288 passed, 7 deselected (`chroma`, `real_llm`) |
| Real ChromaDB integration (`-m chroma`, real `all-MiniLM-L6-v2`) | 3 passed |
| `ruff check backend tests` / `black --check` | Pass |
| Frontend Vitest | 27 passed (new: `ask.test.tsx`) |
| Frontend `npm run lint` / `npm run build` | Pass (1 pre-existing warning in `AuthContext.tsx`) |
| Extension Vitest / typecheck | 112 passed / pass |
| Extension Playwright (Chromium, built extension, host API on :8010) | 7 passed |
| Existing extraction evaluation (`tests.eval.run_eval`) | All 29 metrics unchanged (no regression) |
| OCR benchmark, 120 rendered images | See `EVALUATION.md` (legacy vs PaddleOCR layout vs RapidOCR) |
| LLM comparison (Gemini, qwen2:7b, gemma:2b) | See `EVALUATION.md` |
| Full-stack probe (Compose stack, Gemini, real uploads incl. OCR images) | 7/7 uploads processed, 9/9 questions correct, 0 HTTP errors, no cross-user leak |
| Real-provider pytest (`-m real_llm`) | Not run (opt-in) |

Operational finding: with PaddleOCR in two Celery processes the 8 GB Docker VM ran out of
memory and the Docker engine stopped (twice, needed `docker desktop restart`). Fixed by the
RapidOCR engine, worker concurrency 1, `mem_limit` on API/worker with `restart: unless-stopped`,
and marking documents whose worker died as failed.
