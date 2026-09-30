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
  app/api/v1/             Versioned HTTP routers (auth, documents, facts, profile, corrections, forms, retrieval)
  app/core/               Settings, structured logging, exception handling
  app/core/security.py    bcrypt password hashing and JWT validation
  app/db/                 MongoDB and ChromaDB connectivity & client modules
  app/db/revocations.py   Persistent JWT revocation with TTL cleanup
  app/storage/             Swappable local-volume storage abstraction
  app/models/             Validated MongoDB document shapes (profiles, corrections, facts, documents)
  app/repositories/       User-scoped CRUD repositories for all collections
  app/schemas/            Typed API response, health, fact, profile, correction, forms, and retrieval contracts
  app/services/           Health aggregation, auth, document, fact, profile, corrections, and RAG retrieval services
  app/ontology/           Universal Field Ontology definition (field_ontology.yaml) and concept synonym loader
  app/agents/             Semantic Classification Agent (semantic_classifier.py) and reserved LangGraph agents
  app/processing/         Page-preserving PDF parsing, OCR, preprocessing, normalization, and text chunking
  app/extraction/         Candidate fact detection, normalization, and provenance
  app/retrieval/          Pluggable EmbeddingProvider interface and BGE-M3 default model implementation
  app/tasks/              Celery application and document worker task
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
docker-compose.yml       Local backend, frontend, MongoDB, Redis, and ChromaDB stack
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

The template defines application and port settings, `LOG_LEVEL`, MongoDB credentials, URL, and database, ChromaDB URL, tenant, database, collection, and timeout, JWT secret/algorithm/expiry, login rate-limit attempts/window, `STORAGE_ROOT`, `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER`, `EXTRACTION_MIN_CONFIDENCE`, `CLASSIFIER_CONFIDENCE_THRESHOLD`, `EMBEDDING_MODEL_NAME`, `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, LLM provider/model/API key, embedding model, CORS origins, upload size, and high/medium confidence thresholds. Do not commit `.env` or real API keys.

## To launch the Smart Form Auto-Filling System in development mode, run:

```bash
docker compose up --build
```

### Running Tests (Phase 22 End-to-End)

The project includes a unified test runner managed by `Makefile` that covers the entire stack.

**Available Commands**:
- `make test-backend`: Runs pytest suite for the FastAPI backend, asserting ownership rules, auth boundaries, and business logic with `pytest-cov` output.
- `make test-frontend`: Runs the Vitest component tests.
- `make test-extension`: Runs Playwright test logic against local fixtures.
- `make test-e2e`: Spins up `docker-compose.test.yml`, seeding a disposable testing environment with MongoDB, ChromaDB, and a mocked LLM (`mock-e2e`). It then runs Playwright in Chromium (with the extension loaded) to walk the full signup -> document upload -> form autofill chain.
- `make test-all`: Runs all of the above tests sequentially.

To execute the entire regression suite locally, just run:
```bash
make test-all
```

The dashboard is available at `http://localhost:5173`, the API at `http://localhost:8000`, and the API health endpoint at `http://localhost:8000/api/v1/health`. Service health is available at `/api/v1/health/services`. MongoDB is exposed on `27017` and ChromaDB on `8001`. Stop the stack with `docker compose down`; add `-v` only when local database volumes should be deleted.

Authentication endpoints are available under `/api/v1/auth`: `POST /register`, `POST /login`, protected `GET /me`, and protected `POST /logout`. Passwords are bcrypt-hashed, access tokens are signed JWTs, logout persists token revocation until expiry, duplicate emails return `EMAIL_ALREADY_EXISTS`, invalid credentials return the same `INVALID_CREDENTIALS` response, and repeated login failures are rate limited.

Document endpoints are available under `/api/v1/documents`: authenticated multipart `POST` upload, paginated/filterable `GET` list, `GET /{document_id}`, `POST /{document_id}/process` (202), `GET /{document_id}/status`, `DELETE /{document_id}`, and `POST /{document_id}/reprocess` (202). Uploads validate supported PDF, PNG/JPEG, TXT, and DOCX types, size, magic bytes, and SHA-256 duplicates. Original files are stored through `LocalFileStorage` under the configured upload volume.

Document processing now runs the bounded pipeline `validation -> pdfplumber parsing/table extraction -> PaddleOCR/OpenCV fallback -> extraction -> normalization -> embedding -> chromadb_storage`. Normalized pages retain page boundaries, layout dimensions, spans, and `source_method` values (`direct-parse` or `ocr`). Every pipeline stage is written to `processing_records`; OCR failures retry through Celery and then transition to `requires_review` instead of being silently ignored.

In parallel with structured fact extraction, normalized document text is chunked using `TextChunker` with configurable size (`RAG_CHUNK_SIZE`) and overlap (`RAG_CHUNK_OVERLAP`). Chunks are passed through a pluggable `EmbeddingProvider` (defaulting to `BAAI/bge-m3` via `EMBEDDING_MODEL_NAME`) to generate vector embeddings. Chunks and embeddings are persisted into ChromaDB's `user_document_chunks` collection with exact metadata per DATABASE_DESIGN §18 (`user_id`, `document_id`, `document_name`, `page_number`, `language`, `chunk_index`). Document deletion automatically cascades chunk removals from ChromaDB.

The RAG Retrieval API is available under `/api/v1/retrieval/rag` (`POST /api/v1/retrieval/rag`) per API_SPECIFICATION §30. It accepts query text, `top_k`, and optional `document_type` and `language` filters, returning vector similarity scores and page-level metadata. Server-side security enforces authenticated user isolation using the JWT session token; client-supplied `user_id` values are strictly ignored (SRS §27.3).

The extension offers **Use a Document** and **Ask Me Instead**. Ask Me analyzes only the current form, reuses approved profile facts and relevant RAG evidence, then asks only for required fields that remain unresolved. Answers stay attached to that form session unless the user checks **Save this answer for future forms**. Approved saved answers are kept in the user's profile and user-scoped Chroma collection; they can be reviewed or deleted through `GET /api/v1/profile/memories`, `POST /api/v1/profile/memories`, and `DELETE /api/v1/profile/memories/{memory_id}`. The existing delete-profile-data action removes those saved memories and their vectors.

`POST /api/v1/retrieval/rag/answer` accepts a personal-history question and returns a concise answer grounded in that authenticated user's retrieved evidence, plus source document/page metadata. It supports narrative prompts such as "Tell us about yourself" and "Describe your past experience"; unsupported details are not invented.

### Universal Field Ontology & Semantic Field Classification Agent (Phase 9)

The Universal Field Ontology is defined in `app/ontology/field_ontology.yaml` as a versioned (`1.0.0`), extensible YAML configuration covering standard concepts from SRS §12.1 and DATABASE_DESIGN §8 (`full_name`, `first_name`, `last_name`, `date_of_birth`, `email_address`, `phone_number`, `address`, `current_address`, `permanent_address`, `city`, `state`, `country`, `postal_code`, `organization`, `education`, `skill`, `linkedin`, `github`, `gender`, `nationality`). Each concept includes semantically equivalent label synonyms per SRS §12.3 (e.g. "Full Name", "Applicant Name", "Given Name", "Name of Candidate", "DOB", "Residential Address", "Telephone Number", "Mobile").

The `FieldObject` schema (`app/schemas/forms.py`) strictly implements SRS §11.2 (`field_id`, `tag`, `type`/`input_type`, `name`, `id`, `placeholder`, `label`, `aria_label`, `aria_description`, `autocomplete`, `required`, `pattern`, `nearby_text`, `section_context`/`section`, `position`, `dom_context`, `accessibility_context`, `visual_context`).

The `SemanticClassifier` agent (`app/agents/semantic_classifier.py`) consumes a `FieldObject` and evaluates HTML attributes (`autocomplete`, `label`, `placeholder`, `name`, `id`, `aria_label`, `nearby_text`, `section_context`) to determine canonical concept classification, confidence (0.0 to 1.0), alternatives list, and `context_used` metadata per SRS §13.6. Section context rules boost confidence for ambiguous fields (e.g. `label="Address"` + `section="Permanent Location"` -> `permanent_address`). Unrecognized or ambiguous fields below the confidence threshold fallback safely to `concept="unknown"` per SRS §12.4. The agent is strictly semantic — it **never fabricates personal data values** (SRS §13.5).

API Endpoints:
- `POST /api/v1/forms/classify-field`: Classifies a single form field (API_SPECIFICATION §25).
- `POST /api/v1/forms/classify-fields`: Batch classifies multiple form fields (API_SPECIFICATION §26).

### LangGraph/LangChain Agent Orchestration, Routing & RAG Reasoning (Phase 10–12)

The system incorporates LangGraph to orchestrate an agentic state machine handling the full autofill workflow (SRS §30). The agent execution uses a persistent, database-backed checkpoint pattern (`MongoAgentStore`) to manage state asynchronously.

**Routing (Phase 11)**: The Agent Routing Node makes intelligent decisions based on the current field's information requirement (SRS §14). It prefers structured retrieval when verified canonical facts for a concept exist, selects RAG retrieval for contextual document evidence when concepts are unknown, or triggers a `missing_information` route when neither applies.

**RAG Retrieval Node (Phase 12)**: Calls the ChromaDB similarity search scoped strictly to the authenticated user — the `user_id` is enforced server-side and never trusted from the client. Query strings are constructed from the semantic concept and sanitized field label only.

**Conflict Resolution & Confidence Gate (Phase 13)**: Heuristic scoring evaluates candidates based on source reliability, verification status, and recency. If multiple non-equivalent candidates exist, it flags a conflict. A confidence gate (`CONFIDENCE_THRESHOLD`) ensures that only high-confidence candidates are autofilled (`READY_TO_FILL`). Sensitive field concepts (e.g., SSN, credit cards) bypass automatic fill entirely, always mapping to `REQUIRES_CONFIRMATION` or `MULTIPLE_CANDIDATES`.

**LLM Reasoning Node (Phase 12 & 13)**: Acts as a fallback when heuristic scoring yields low confidence or when only unstructured RAG text is available. A pluggable `LLMProvider` interface (configurable via `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`) drives a structured reasoning step using a strict prompt template. The template isolates all webpage-originated data in an `<UNTRUSTED_WEBPAGE_DATA>` block (SRS §27.6, API_SPECIFICATION §52) so field/page content cannot be interpreted as LLM instructions. Supported providers: `openai`, `anthropic`, `mock` (default — no API key required for testing).

**Human-in-the-Loop & Final Response (Phase 14)**: The `Final Response` node aggregates all intermediate states and persists a recommendation to the `recommendations` collection. If the agent graph determines human confirmation is required (`REQUIRES_CONFIRMATION` / `MULTIPLE_CANDIDATES`), the recommendation is saved as `pending_review` and graph execution pauses. The `GET /api/v1/reviews/pending` and `POST /api/v1/reviews/{id}/decision` APIs manage manual human confirmation, editing, rejection, or skipping. Approved decisions may update canonical profile preferences. A dismissed or skipped review will not execute an autofill (SRS §19.4).

**No-Fabrication Enforcement (SRS §17.3)**: If retrieved evidence is insufficient to make a recommendation, the node returns `MISSING_INFORMATION` without calling the LLM. The LLM is never permitted to invent plausible-looking values.
    
**`FinalResponseStatus` Enum (SRS §17.2)**: All nodes share this enum: `READY_TO_FILL`, `REQUIRES_CONFIRMATION`, `MULTIPLE_CANDIDATES`, `MISSING_INFORMATION`, `UNSUPPORTED_FIELD`, `LOW_CONFIDENCE`, `SECURITY_BLOCKED`, `ERROR`.
    
**Prompt Injection Defence**: Regex-based heuristics check every field/page attribute for known injection patterns before any processing. Flagged fields receive `SECURITY_BLOCKED` immediately — the LLM is never called and no user data is included in the response.

### Form Lifecycle API & End-to-End Integration (Phase 15)

The entire "Minimal Required API Set" (API_SPECIFICATION §61) is now complete, tying together document processing, extraction, semantic classification, LangGraph agent reasoning, human-in-the-loop decisions, and form filling tracking.
The `form_sessions` collection tracks the lifecycle of each form filling attempt with states: `started` → `processing` → `review_required` → `ready` → `completed`/`failed`/`cancelled`. 
The `POST /api/v1/forms/sessions/{id}/analyze` API spawns the agent orchestration in the background. Recommendations are retrieved securely using `GET /api/v1/forms/sessions/{id}/recommendations` and the session results are committed using `POST /api/v1/forms/sessions/{id}/complete`.

An extensive, single-flow integration test simulates a full user journey spanning all components from registration to form session completion.

New environment variables:
- `LLM_PROVIDER` — LLM backend (`openai`, `anthropic`, `mock`). Default: `mock`.
- `LLM_MODEL` — Model name for the chosen provider.
- `LLM_API_KEY` — API key (required only for `openai`/`anthropic`).
- `LLM_REASONING_TIMEOUT_SECONDS` — LLM call timeout in seconds. Default: `30`.
- `LLM_MAX_EVIDENCE_CHUNKS` — Maximum chunks included in the prompt (data minimization). Default: `5`.
- `CONFIDENCE_THRESHOLD` — Minimum confidence score for automatic fill. Default: `0.85`.
- `SENSITIVE_FIELD_CONCEPTS` — Comma-separated list of concepts requiring human confirmation. Default: `ssn,credit_card,passport_number,password`.

API Endpoints:
- `POST /api/v1/agent/run`: Initiates a background LangGraph agent workflow run (API_SPECIFICATION §31).
- `GET /api/v1/agent/runs/{run_id}`: Retrieves the current state and execution status (API_SPECIFICATION §33).
- `GET /api/v1/profile`: Fetches the unified canonical profile.
- `PUT /api/v1/profile`: Full replacement of a canonical profile section.
- `PUT /api/v1/profile/facts/{fact_id}`: Partially updates a stored fact.
- `GET /api/v1/reviews/pending`: Gets all pending recommendation reviews for the user.
- `POST /api/v1/reviews/{id}/decision`: Confirms, edits, rejects, or skips a pending recommendation.
- `POST /api/v1/retrieval/structured`: Fetches structured candidate facts by concept and verification state (API_SPECIFICATION §29).
- `POST /api/v1/forms/sessions`: Creates a new form session tracking object.
- `GET /api/v1/forms/sessions/{id}`: Retrieves the status of a form session.
- `POST /api/v1/forms/sessions/{id}/analyze`: Accepts a batch Field Object array and runs the LangGraph agent for each field.
- `GET /api/v1/forms/sessions/{id}/recommendations`: Returns the generated recommendations.
- `POST /api/v1/forms/sessions/{id}/complete`: Marks the form filling session as complete.

### Core Web Dashboard & Frontend Shell (Phase 16 & 17)

The React frontend (built with Vite and TypeScript) provides the primary user interface for managing documents, reviewing knowledge facts, and tracking form sessions.
The interface is constructed using a strict Vanilla CSS token system (`4/8/12/16/24/32/48px` scales) and semantic confidence badges (`High`, `Medium`, `Low`, `Conflict`) that ensure accessibility without relying solely on color.
The application routing (`react-router-dom`) protects all core views (Dashboard, Documents, Profile, Activity, Reviews, Settings) via an `AuthContext` which manages JWT session tokens locally and attaches them to `VITE_API_BASE_URL` API calls.

**Phase 17 UI Additions:**
- **Document Management**: Drag-and-drop document upload interface with visual processing timelines and polling mechanisms for extraction status.
- **Knowledge Profile**: Consolidates extracted facts and user details, visualizing the agent's knowledge base complete with source provenance and confidence indicators.
- **Field Reviews**: A Human-in-the-Loop conflict resolution UI for reviewing, confirming, editing, or rejecting agentic field autofill suggestions.
- **Activity History**: A timeline for form sessions, uploaded documents, and resolved reviews.
- **Settings & Privacy**: Extension preferences and privacy controls, including destructive "Delete Data" and "Delete Account" flows with mandatory user confirmations.

For local development, the frontend runs via `npm run dev`. For production, `docker-compose.yml` mounts a multi-stage Dockerfile that builds the static output and serves it using an Nginx alpine image with client-side routing fallback (`try_files $uri /index.html`).

To use a customized environment:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Environment Variables and Secrets

All secrets are strictly managed via environment variables. The application will not boot if critical secrets are missing. Do **NOT** commit secrets to version control.

```bash
# Security configurations
JWT_SECRET_KEY="your-secure-random-secret"
APP_ENV="production"
```

## Production Security Requirements

When deploying to production, ensure:
1. **HTTPS**: The backend must run behind an HTTPS proxy (e.g., Nginx, Traefik).
2. **Secure Cookies**: If utilizing cookie-based auth in the future, ensure `Secure` and `HttpOnly` flags are enabled.
3. **Rate Limiting**: The system utilizes SlowAPI for rate limiting. Ensure your proxy forwards the `X-Forwarded-For` header correctly so IP-based rate limiting functions properly.
4. **CORS**: By default, the API only allows requests from the specific Chrome extension origin (`chrome-extension://[a-p]{32}`). Do not use wildcard CORS in production.
5. **Storage Provider**: Set `STORAGE_PROVIDER` to `cloudinary` in production instead of `local` to ensure robust, externalized secure file storage. You must provide `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`. Ensure "Strict Deliveries" for PDFs and ZIPs is unchecked in your Cloudinary security settings to allow the worker to download processed documents via signed URLs.

## Chrome Extension & Autofill Engine

The Chrome Extension is a Manifest V3 implementation that connects your browser sessions with the backend autofill engine.

**Features added:**
- **Dynamic Field Detection**: Employs a robust `MutationObserver` on `document.body` (SRS §11.5) to catch dynamically inserted single-page-app fields.
- **Semantic Field Extraction**: Parses deeply nested inputs and constructs a structured `FieldObject` strictly conforming to SRS §11.2 (including ARIA labels, sections, layouts, and neighboring text).
- **Session Auth Handshake**: The extension background worker securely manages backend API tokens and initiates tracking sessions via `POST /api/v1/forms/sessions`.
- **Minimal Permissions**: Requests only what is absolutely necessary (`storage` for JWT auth state, `activeTab` for ad-hoc popup actions, and `*://*/*` for dynamic autofill detection globally).

### Building & Loading the Extension
The extension is built automatically when you run `docker compose up --build` via the `extension-builder` service. You can also build it manually:
```powershell
cd extension
npm install
npm run build
```

To load it into Chrome:
1. Navigate to `chrome://extensions/`
2. Enable **Developer mode** in the top right.
3. Click **Load unpacked** and select the `extension/dist` directory from this repository.
4. Click the extension icon to sign in to your Smart Form account!

## ChromaDB Backup & Re-Embedding Recovery Procedure (DATABASE_DESIGN §29)

ChromaDB vector data is stored in the persistent Docker volume `chromadb_data` mounted at `/data`. In the event of vector store corruption, schema migration, or data loss, restore embeddings from the source documents using the following procedure:

1. **Verify Source Availability**: Ensure MongoDB and source document files stored in `STORAGE_ROOT` (`document_data` volume) are intact.
2. **Reset ChromaDB Collection**: Clear or recreate the `user_document_chunks` collection via ChromaDB management or container restart.
3. **Re-Trigger Document Pipelines**: Iterate over all non-deleted document records in MongoDB (`status != 'deleted'`) and invoke `reprocess_document` (`POST /api/v1/documents/{document_id}/reprocess`).
4. **Automated Re-Embedding**: The Celery document worker executes the processing pipeline end-to-end, re-extracting text, generating chunk embeddings, and re-indexing all vectors into ChromaDB.
5. **Verify Index Integrity**: Query `/api/v1/retrieval/rag` to confirm top-k vector similarity search results are restored.

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

- Build the extension:
  ```bash
  cd extension
  npm run build
  ```
  The extension output will be available in `extension/dist`. Load this folder into Chrome by opening `chrome://extensions`, enabling Developer mode, selecting **Load unpacked**, and choosing `extension/`.

## Testing
- **Backend**: `pytest`
- **Frontend**: `npm test`
- **Extension (E2E Autofill)**: `npx playwright test`
  ```bash
  cd extension
  npx playwright install
  npx playwright test
  ```

## Test and quality checks

```powershell
python -m pytest backend/tests tests
python -m ruff check backend tests
python -m black --check backend tests
cd frontend && npm run build
cd frontend && npx vitest run
```

Document-specific tests can be run with `python -m pytest backend/tests/test_documents.py`.

OCR and parsing tests can be run with `python -m pytest backend/tests/test_processing_pipeline.py`; these cover TC-OCR-01 through TC-OCR-06.

Extraction and structured-fact tests can be run with `python -m pytest backend/tests/test_extraction.py`; these cover TC-EXT-01 through TC-EXT-06 and TC-DB-01 through TC-DB-03.

RAG chunking, embedding generation, vector storage, and RAG retrieval tests can be run with `python -m pytest backend/tests/test_rag.py`.

Profile read/update, fact aggregation, and history-preserving correction tests can be run with `python -m pytest backend/tests/test_profile.py`.

Universal Field Ontology and Semantic Classification Agent tests can be run with `python -m pytest backend/tests/test_semantic_classifier.py`; these cover TEST_PLAN TC-SEM-01 through TC-SEM-05.

LangGraph agent orchestration, routing logic, and structured retrieval tests can be run with `python -m pytest backend/tests/test_agent_graph.py` and `python -m pytest backend/tests/test_routing_and_retrieval.py`.

RAG Retrieval Node, LLM Reasoning, FinalResponseStatus, adversarial prompt-injection tests can be run with `python -m pytest backend/tests/test_rag_and_reasoning.py`; these cover TC-RAG-01 through TC-RAG-04 and TC-AGENT-04 through TC-AGENT-06.

Conflict resolution, heuristic scoring, confidence gating, and sensitive fields handling tests can be run with `python -m pytest backend/tests/test_conflict_resolution.py`; these cover TC-CON-01 through TC-CON-05.

Human-in-the-Loop review APIs and the Final Response node aggregation tests can be run with `python -m pytest backend/tests/test_hitl_and_final_response.py`; these cover TC-HITL-01 through TC-HITL-06.

The comprehensive end-to-end integration test walking the entire minimal API set (register → upload → process → create session → analyze → recommendations → complete) can be run with `python -m pytest backend/tests/test_end_to_end.py`.

The CI workflow runs these checks and validates the compose configuration. Startup creates the MongoDB collections and the exact indexes from `DATABASE_DESIGN.md` section 25, and ensures the ChromaDB `user_document_chunks` collection with its user/document/page/language/chunk metadata contract. User-scoped repositories always include `user_id` in reads, updates, and deletes; TC-DB-08 regression tests cover cross-user document and fact isolation. Authentication tests cover TC-AUTH-01 through TC-AUTH-08, including invalid input, duplicate email, safe login failures, missing tokens, logout invalidation, and client-supplied user-ID attempts. The API provides versioned health endpoints, typed success/error envelopes, request IDs, JSON logs, CORS restrictions, and MongoDB/ChromaDB probes.

## Development principles

Future phases must extend this README and `docker-compose.yml` with every new service, setting, command, and test. Personal data must remain user-scoped and evidence-backed; the extension must keep autofill separate from form submission; secrets must stay outside version control.
