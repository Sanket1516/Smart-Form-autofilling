# Project Audit: Smart Form Auto-Filling System

Audit date: 2026-10-13. Baseline commit: `a03f513` on branch `feature/e2e-completion`, which
includes the working-tree changes that were pending at the start of the audit.

This document records what the repository contained **before** this round of work, so later
changes can be judged against it. Each finding has a priority:

- **P0**: the application cannot run, or there is a critical security or data-integrity problem.
- **P1**: an essential end-to-end feature does not work.
- **P2**: an important reliability, usability or maintainability issue.
- **P3**: an optional enhancement.

Progress against these findings is tracked in `docs/IMPLEMENTATION_PLAN.md`.

## 1. Inventory

| Area | Location | Technology |
|---|---|---|
| Backend | `backend/app` | Python 3.11, FastAPI, Pydantic v2, Motor (MongoDB), Celery and Redis, LangGraph, slowapi |
| Structured DB | MongoDB | `users`, `profiles`, `documents`, `structured_facts`, `discovered_facts`, `discovered_conflicts`, `recommendations`, `form_sessions`, `corrections`, `processing_records`, `agent_runs`, `auth_token_revocations`, `user_memories` |
| Vector DB | ChromaDB, through raw HTTP v2 calls (`db/chroma_client.py`) | collection `user_document_chunks` |
| Embeddings | `retrieval/embeddings.py` | sentence-transformers, with a silent MD5 "hash vector" fallback |
| LLM | `agents/llm_provider.py` | Google Gemini (raw `urllib`), OpenAI and Anthropic (SDKs not in requirements), and Mock providers |
| Document processing | `processing/` | pdfplumber, pypdfium2, PaddleOCR (optional, lazily loaded) |
| Extraction | `extraction/` | two LLM tracks (dynamic and ontology), and a regex extractor that is tested but never used |
| Agent | `agents/graph.py` | LangGraph `StateGraph`, one field per run |
| Dashboard | `frontend/` | React 19, Vite 8, react-router 7, TypeScript |
| Extension | `extension/` | Manifest V3, Vite 5, React 18, TypeScript. A legacy plain-JS Phase-1 copy also exists |
| Infrastructure | `docker-compose.yml`, `docker-compose.test.yml`, Dockerfiles, `Makefile`, `.github/workflows/ci.yml` | |

## 2. Baseline test and build results

These were measured before any change. The backend run used environment overrides so that it
would not touch the developer database, Cloudinary or Gemini.

| Command | Result |
|---|---|
| `pytest` (backend and `tests/`), Mongo unreachable, mock LLM | **123 passed, 6 failed**. All six failures were routes that need a live MongoDB: the suite is not isolated. |
| `extension: npx vitest run` | 16 passed |
| `extension: npx tsc --noEmit` | clean |
| `frontend: npx vitest run` | 10 passed |
| `frontend: npx tsc --noEmit -p tsconfig.app.json` | **about 20 errors**. The build script skips `tsc`, so the build still passed |
| `ruff check backend tests` (CI step) | **354 errors**, so CI never reaches pytest |
| Root `npm run build` | **fails**: it references workspace `smart-form-frontend`, but the package is named `temp-frontend` |

Local environment:

- MongoDB runs natively.
- ChromaDB, Redis and Ollama are not running.
- The virtualenv lacks `sentence-transformers`, `pdfplumber` and `paddleocr`, and has `langgraph`
  1.2 although the requirement pins `<1.0`.

## 3. Findings

### P0: security and data integrity

| ID | Finding | Location |
|---|---|---|
| P0-1 | Real-looking personal documents are tracked in git: a bank passbook scan, a passbook PDF and a personal PDF. The passbook image is also copied into the backend image. | `backend/app/sample_passbook.png`, `backend/passbook.pdf`, `test-data/sanket_mali.pdf` |
| P0-2 | Hard-coded application login credentials in tracked scripts. | `test_cloudinary.py`, `upload_e2e_docs.py`, `check_docs.py` (repo root) |
| P0-3 | Real-looking personal data (name, phone, account number) used as few-shot examples in LLM prompts. | `agents/prompts.py:115,128`, `extraction/dynamic_extractor.py:128-155` |
| P0-4 | Compose files fall back to a hard-coded JWT secret, so tokens could be forged on any deployment that doesn't set one. | `docker-compose.yml:73,147`, `docker-compose.test.yml:69` |
| P0-5 | The extension reads **password** values on every website, on every keystroke, and sends them to the background worker and the backend. It has `*://*/*` host permissions and an always-on content script. | `extension/src/content/detector.ts:325`, `extension/public/manifest.json` |
| P0-6 | The JWT is passed in messages to the content script, which runs inside untrusted pages. | `extension/src/popup/AutofillFlow.tsx`, `extension/src/content/autofill.ts` |
| P0-7 | Deleting a document leaves its structured facts, discovered facts and conflicts in place, and they keep feeding autofill. | `services/documents.py:170-186` |
| P0-8 | Local-storage deletion calls `rmdir` on a directory that is not empty, so every processed document fails to delete with a 500 and can never be deleted. | `storage/local.py:51-53` |
| P0-9 | `DELETE /auth/me` deletes the user, then calls `current_user()`, which returns 401. The token is not revoked, and all documents, facts and vectors are orphaned. | `api/v1/auth.py:88-93` |
| P0-10 | `?token=` is accepted as a credential on every endpoint, so JWTs leak into access logs and browser history. | `api/v1/auth.py:34-37` |

### P1: essential features broken

| ID | Finding | Location |
|---|---|---|
| P1-1 | `UnmappedExtraction` is used without an import. The resulting `NameError` makes the whole of extraction Track B fail. | `extraction/llm_extractor.py:195` |
| P1-2 | `FactService._data` reads `record["source_page"]` and `record["value"]`. Records written with `exclude_none` don't have them, so `/profile/facts` returns 500 and form analysis silently reports every field as missing. | `services/facts.py:122-139` |
| P1-3 | `CELERY_TASK_ALWAYS_EAGER=true` calls `asyncio.run` inside the running event loop. Documents stay in `processing` forever, so Redis and a worker are mandatory. | `tasks/documents.py:157`, `services/documents.py:152` |
| P1-4 | CORS doesn't allow PATCH, so conflict resolution from the dashboard fails its preflight. | `main.py:177` |
| P1-5 | Silent fallbacks hide outages: hash-vector embeddings, an in-memory Chroma store, and LLM providers that return the string `"ERROR"`, which callers treat as "missing". | `retrieval/embeddings.py:78-85`, `db/chroma_client.py:122-141`, `agents/llm_provider.py` |
| P1-6 | Cross-document conflicts are never detected for single-value facts: an upsert overwrites the earlier value, even a verified one. | `repositories/collections.py:76-111,200-247` |
| P1-7 | Ontology matching uses substring containment at ≥0.70, so `FATHER_NAME` maps to `personal.full_name` and `BANK_ACCOUNT_NUMBER` to `financial.bank_name`. | `ontology/loader.py:58-85` |
| P1-8 | There are three duplicate recommendation flows: bulk `/analyze`, LangGraph `/forms/recommend(ations)`, and `/agent/run`. The extension uses the bulk one, which sends the user's **entire** fact set and profile to the LLM. | `api/v1/forms.py:307-588`, `agents/graph.py`, `api/v1/agent.py` |
| P1-9 | Recommendations are re-inserted on every analyze run. `provenance` is always `[]` and `reason` is never returned. | `db/repositories/recommendations.py:54`, `forms.py:730` |
| P1-10 | Concept names in the label rules (`contact.email`, …) don't exist in the ontology (`personal.email`, …). | `forms.py:129-236`, `ontology/field_ontology.yaml` |
| P1-11 | The extension has a hard-coded backend URL, no request timeouts, and polling that never stops. "Done" is shown after a fixed delay, and `/verify` is a stub. | `extension/src/background/index.ts:3`, `AutofillFlow.tsx`, `forms.py:884-914` |
| P1-12 | The dashboard home and Activity pages show static demo data and have dead buttons. Reprocess crashes the document page (`setFacts()` with no argument). | `pages/Dashboard.tsx`, `pages/Activity.tsx`, `components/documents/DocumentDetails.tsx:148` |
| P1-13 | `.docx` uploads are accepted, but there is no DOCX extractor. Corrupted PDFs fall back to reading raw bytes as text, and the document is still marked `processed`. | `processing/extractor.py:187-203` |
| P1-14 | `MockE2EProvider` references `FinalResponseStatus.CONFIDENT_RECOMMENDATION`, which doesn't exist. | `agents/llm_provider.py:131,139` |
| P1-15 | Frontend uses `user.name`, but the API returns `full_name`. Logout never revokes the token on the server. | `Navbar.tsx:19`, `AuthContext.tsx:64` |

### P2: reliability and maintainability

- **Dead code:**
  - `app/database/*`, `app/db/chroma.py` and `app/api/health.py` (also broken).
  - Duplicate repositories in `repositories/collections.py`.
  - `pages/Stubs.tsx` and the legacy extension JS.
  - The unused `@crxjs/vite-plugin` dependency.
  - Stray maintenance scripts in `backend/app`, some importing a module that no longer exists.
- **Settings and status:**
  - Several settings are unused (`high_/medium_confidence_threshold`, `classifier_confidence_threshold`, `extraction_min_confidence`).
  - `/health` is hard-coded to "healthy", and the LLM and embedding status are hard-coded to "not_configured".
- **Performance:** synchronous LLM and embedding calls run inside async handlers and block the event loop.
- **Data:**
  - `discovered_facts`, `discovered_conflicts` and `user_memories` have no indexes.
  - Embedding dimensions are inconsistent: bge-m3 (1024) is the default, but `.env` uses MiniLM (384).
- **LLM output:**
  - OpenAI and Anthropic `max_tokens=256` truncates JSON.
  - The Gemini key is sent in the URL.
  - Retries also happen on 4xx errors.
- **Extension filling:**
  - Select matching is substring-first ("male" matches "Female").
  - Checkboxes are not React-compatible.
  - Verification compares option value against label.
- **Extension field detection:**
  - Field IDs are unstable across page loads.
  - Hidden-field detection is weak (no `visibility`, `opacity` or off-screen checks).
- **Tests:**
  - The Playwright tests can't pass.
  - The frontend has no `test` script.
  - CI lint fails.
- **Compose:** the test compose shares a project name with dev, and its worker has no JWT secret.

### P3: optional

- An Ollama provider.
- Shadow-DOM and iframe form detection.
- Moving the dashboard JWT from `localStorage` to an httpOnly cookie.

## 4. Specification documents

`Specifications/` and `docs/specifications/` contain the original design specs: PRD, SRS, API,
database, UI/UX and test plan. They describe intended behaviour and are kept unchanged as
design-time references. The documents that describe the **implemented** system are
`README.md`, `docs/DATABASE_SCHEMA.md`, `docs/API_REFERENCE.md` and `docs/SECURITY.md`.
