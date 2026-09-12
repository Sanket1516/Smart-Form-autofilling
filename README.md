# Smart Form Auto-Filling System

The Smart Form Auto-Filling System is an agentic AI framework for context-aware semantic understanding and intelligent assistance of dynamic web forms. It combines a React dashboard, a Chrome Manifest V3 extension, a FastAPI service, structured and vector persistence, and a document/agent roadmap that keeps recommendations evidence-backed and user-controlled.

## Technology stack

| Area | Technology |
| --- | --- |
| Web application | React, Vite |
| Browser integration | Chrome Extension Manifest V3 |
| API | Python 3.11, FastAPI, Uvicorn |
| Agent orchestration | LangGraph, LangChain (planned integration) |
| Structured database | MongoDB |
| Vector database | ChromaDB |
| Document processing | PaddleOCR, pdfplumber, OpenCV (planned integration) |
| Delivery | Docker, Docker Compose, GitHub Actions |

## Repository structure

```text
backend/                 FastAPI application, layered modules, Docker stages, tests
  app/api/v1/             Versioned HTTP routers
  app/core/               Settings, structured logging, exception handling
  app/core/security.py    bcrypt password hashing and JWT validation
  app/db/                 MongoDB and ChromaDB connectivity modules
  app/db/revocations.py   Persistent JWT revocation with TTL cleanup
  app/storage/             Swappable local-volume storage abstraction
  app/models/             Validated MongoDB document shapes
  app/repositories/       User-scoped CRUD repositories for all collections
  app/schemas/            Typed API response and health contracts
  app/services/           Health aggregation and startup services
  app/services/auth.py    Registration, login, logout, and rate limiting
  app/services/documents.py Document validation and lifecycle service
  app/processing/            Page-preserving PDF parsing, OCR, preprocessing, normalization
  app/extraction/            Candidate fact detection, normalization, and provenance
  app/tasks/               Celery application and document worker task
  app/agents/             Reserved LangGraph agent package
frontend/                React/Vite dashboard and production Dockerfile
extension/               Chrome Manifest V3 popup, worker, content script, API client
infra/                   Infrastructure notes and deployment asset location
docs/specifications/     Seven working specification documents for this project
  SRS.md
  USER_FLOWS.md
  SYSTEM_ARCHITECTURE.md
  DATABASE_DESIGN.md
  API_SPECIFICATION.md
  UI_UX_SPECIFICATION.md
  TEST_PLAN.md
tests/                   Cross-project validation tests
test-data/               Reserved anonymized fixtures
docker-compose.yml       Local backend, frontend, MongoDB, and ChromaDB stack
.github/workflows/       Continuous integration checks
```

The seven specifications are maintained under `docs/specifications/`. The similarly named files under `Specifications/` are supplied source documents retained for reference.

## Prerequisites

- Docker Desktop with Docker Compose v2 and the daemon running
- Python 3.11+
- Node.js 22+ and npm
- Google Chrome for loading the unpacked extension

## Environment

Copy `.env.example` to `.env` when changing local settings. The compose file also provides safe development defaults, so a clean checkout can start without `.env`.

The template defines application and port settings, `LOG_LEVEL`, MongoDB credentials, URL, and database, ChromaDB URL, tenant, database, collection, and timeout, JWT secret/algorithm/expiry, login rate-limit attempts/window, `STORAGE_ROOT`, `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER`, LLM provider/model/API key, embedding model, CORS origins, upload size, and high/medium confidence thresholds. Do not commit `.env` or real API keys.

## Run the stack

From the repository root:

```powershell
docker compose up --build
```

The dashboard is available at `http://localhost:5173`, the API at `http://localhost:8000`, and the API health endpoint at `http://localhost:8000/api/v1/health`. Service health is available at `/api/v1/health/services`. MongoDB is exposed on `27017` and ChromaDB on `8001`. Stop the stack with `docker compose down`; add `-v` only when local database volumes should be deleted.

Authentication endpoints are available under `/api/v1/auth`: `POST /register`, `POST /login`, protected `GET /me`, and protected `POST /logout`. Passwords are bcrypt-hashed, access tokens are signed JWTs, logout persists token revocation until expiry, duplicate emails return `EMAIL_ALREADY_EXISTS`, invalid credentials return the same `INVALID_CREDENTIALS` response, and repeated login failures are rate limited.

Document endpoints are available under `/api/v1/documents`: authenticated multipart `POST` upload, paginated/filterable `GET` list, `GET /{document_id}`, `POST /{document_id}/process` (202), `GET /{document_id}/status`, `DELETE /{document_id}`, and `POST /{document_id}/reprocess` (202). Uploads validate supported PDF, PNG/JPEG, TXT, and DOCX types, size, magic bytes, and SHA-256 duplicates. Original files are stored through `LocalFileStorage` under the configured upload volume.

Document processing now runs the bounded pipeline `validation -> pdfplumber parsing/table extraction -> PaddleOCR/OpenCV fallback -> extraction -> normalization -> embedding/storage boundaries`. Normalized pages retain page boundaries, layout dimensions, spans, and `source_method` values (`direct-parse` or `ocr`). Every pipeline stage is written to `processing_records`; OCR failures retry through Celery and then transition to `requires_review` instead of being silently ignored. PaddleOCR, PaddlePaddle, pdfplumber, OpenCV, Pillow, and PDF rendering dependencies are installed in the backend image with the required Linux libraries.

After normalization, candidate facts are extracted for names, dates of birth, phone numbers, email addresses, addresses, education, organizations, skills, PAN/passport/Aadhaar-style identifiers, and other supported labeled fields. Dates are normalized to ISO 8601, phone numbers to a consistent international form, and every candidate retains its original text, page, source method, document, and confidence. Candidates are inserted independently into `structured_facts`; existing facts are never overwritten. Protected fact APIs are available at `GET /api/v1/profile/facts`, `PUT /api/v1/profile/facts/{fact_id}`, and `GET /api/v1/documents/{document_id}/facts`.

To use a customized environment:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Local development

Backend setup from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

The backend Dockerfile provides `dev` and `prod` stages. Compose uses `prod` by default; set `BACKEND_BUILD_TARGET=dev` in `.env` for hot reload during container development.

Document processing uses Celery with Redis as the broker/backend. Redis provides a durable queue boundary and lets processing run independently from API workers; the `worker` Compose service consumes document jobs. Set `CELERY_TASK_ALWAYS_EAGER=true` only for deterministic local unit tests. `PROCESSING_MAX_RETRIES`, `OCR_LANGUAGE`, and `OCR_RESOLUTION` configure bounded retries and OCR behavior.

Frontend setup:

```powershell
npm install
npm run dev --workspace=smart-form-frontend
```

Load the extension by opening `chrome://extensions`, enabling Developer mode, selecting **Load unpacked**, and choosing `extension/`.

## Test and quality checks

```powershell
python -m pytest backend/tests tests
python -m ruff check backend tests
python -m black --check backend tests
npm run lint
npm run build
```

Document-specific tests can be run with `python -m pytest backend/tests/test_documents.py`.

OCR and parsing tests can be run with `python -m pytest backend/tests/test_processing_pipeline.py`; these cover TC-OCR-01 through TC-OCR-06, including direct parsing provenance, OCR provenance, page preservation, low-quality best effort, tables, and controlled OCR failure.

Extraction and structured-fact tests can be run with `python -m pytest backend/tests/test_extraction.py`; these cover TC-EXT-01 through TC-EXT-06 and the initial structured-fact persistence/linkage case.

The CI workflow runs these checks and validates the compose configuration. Startup creates the MongoDB collections and the exact indexes from `DATABASE_DESIGN.md` section 25, and ensures the ChromaDB `user_document_chunks` collection with its user/document/page/language/chunk metadata contract. User-scoped repositories always include `user_id` in reads, updates, and deletes; TC-DB-08 regression tests cover cross-user document and fact isolation. Authentication tests cover TC-AUTH-01 through TC-AUTH-08, including invalid input, duplicate email, safe login failures, missing tokens, logout invalidation, and client-supplied user-ID attempts. The API provides versioned health endpoints, typed success/error envelopes, request IDs, JSON logs, CORS restrictions, and MongoDB/ChromaDB probes. LLM and embedding services report `not_configured` until their provider integrations are added.

## Development principles

Future phases must extend this README and `docker-compose.yml` with every new service, setting, command, and test. Personal data must remain user-scoped and evidence-backed; the extension must keep autofill separate from form submission; secrets must stay outside version control.
