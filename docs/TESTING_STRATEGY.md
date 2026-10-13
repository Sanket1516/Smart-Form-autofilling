# Testing Strategy

## Principles

- The default test run never touches the developer's MongoDB database, Cloudinary, or any paid LLM API.
- Each test belongs to exactly one category:
  - **mocked**: fakes or mock providers stand in for external services.
  - **real-service**: talks to a real local service (MongoDB, ChromaDB).
  - **real-provider**: calls an external API (Gemini).

  `docs/TEST_RESULTS.md` reports each category separately.
- All personal data in tests is synthetic. Real identity documents are never used.

## Backend (`pytest`, configured in `pyproject.toml`)

`backend/tests/conftest.py` forces the following settings before the app is imported:

| Setting | Value |
|---|---|
| `LLM_PROVIDER` | `mock` |
| `STORAGE_PROVIDER` | `local` (a temporary directory) |
| `PROCESSING_MODE` | `inline` |
| `MONGODB_DATABASE` | `smart_form_test_<random>` (dropped at session end) |
| `CHROMADB_COLLECTION` | `test_chunks_<random>` |

Markers:

| Marker | Needs | Behaviour when unavailable |
|---|---|---|
| *(none)* | nothing; pure functions and fakes | always runs |
| `mongo` | MongoDB at `MONGODB_URL` (local default) | skipped, with the reason shown |
| `chroma` | ChromaDB at `CHROMADB_URL` | skipped |
| `real_llm` | `RUN_REAL_LLM_TESTS=1` plus a configured provider and key | skipped |

Commands:

```bash
python -m pytest -m "not real_llm"  # default suite; activate the project venv first
RUN_REAL_LLM_TESTS=1 python -m pytest -m real_llm  # Unix-like shells; costs API calls
```

In PowerShell, opt in with `$env:RUN_REAL_LLM_TESTS="1"`, run
`python -m pytest -m real_llm`, then clear it with
`Remove-Item Env:RUN_REAL_LLM_TESTS`.

Coverage areas:

- **Auth:** success and failure, expired, revoked and malformed tokens, rate limits, account deletion cascade.
- **Authorisation:** cross-user access to documents, facts, conflicts, sessions, recommendations, memories and RAG.
- **Upload:** extension and magic-byte checks, size limit, empty, corrupted, DOCX and TXT files.
- **Processing:** deterministic extraction, LLM extraction using mock JSON, normalisation, provenance, conflicts, `requires_review` when OCR is unavailable.
- **RAG:** chunking, metadata, user filtering, similarity cutoff, empty results, embedding failure, reindex and delete.
- **Semantic pipeline:** deterministic mapping of varied labels, LLM batching only for ambiguous fields, invalid or partial LLM JSON, sensitive fields, conflicts, missing values, format validation, option matching.
- **API errors:** 400/401/403/404/409/413/422/429/503 in the standard error envelope.
- **End-to-end (pytest):** register → upload a synthetic PDF → inline processing → facts → resolve a conflict → session → analyze → recommendations → verify.

## Frontend (`frontend`, Vitest with Testing Library and jsdom)

Run with `npm --prefix frontend test`. The tests stub `fetch`. They cover:

- Login and register, with and without errors.
- Auth context.
- Document upload validation.
- Processing status polling.
- Editing and confirming profile facts.
- Conflict resolution.
- Review decisions.
- API failure states.

## Extension (`extension`)

- **Unit tests (Vitest, jsdom):** run with `npm --prefix extension test`. They cover:
  - detector: labels, accessible names, grouping, sensitive and hidden skipping, stable IDs;
  - autofill: text, textarea, select, checkbox, radio, date, React-controlled inputs, verification results;
  - API client: timeouts, 401 handling, retry policy;
  - recommendation validation.
- **E2E (Playwright, real Chromium with the built extension):** `make test-e2e`. It starts the isolated `smart-form-autofilling-test` Compose project, builds the extension bundle, and exercises the Compose backend with its mock LLM and test database. The test:
  1. uploads a synthetic document;
  2. opens `tests/fixtures/sample-application-form.html`;
  3. drives the popup;
  4. approves the fill;
  5. asserts the DOM values;
  6. asserts the form was not submitted.

## Structural checks

`tests/validate_extension.py` checks the manifest: Manifest V3, minimal permissions, required files.

## CI

`.github/workflows/ci.yml` runs ruff and black, the mocked backend suite with MongoDB, the Chroma integration suite with ChromaDB, frontend and extension type-check/tests/builds, Compose configuration validation, and a separate Playwright browser E2E job. Real-provider tests never run in CI.
