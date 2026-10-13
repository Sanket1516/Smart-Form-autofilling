# Smart Form Auto-Filling System

A privacy-first form assistant that extracts profile facts from a user's documents, recommends values for web forms, and asks the user to review and approve values before filling. It never auto-submits a form.

## Components

- **Backend:** Python 3.11, FastAPI, MongoDB, LangGraph, and ChromaDB over its HTTP v2 API.
- **Extraction and retrieval:** deterministic fact extraction plus an optional LLM track; `all-MiniLM-L6-v2` embeddings (384 dimensions) by default.
- **Dashboard:** React, TypeScript and Vite, served by Nginx in Compose.
- **Browser extension:** Chrome Manifest V3, with on-demand site access, review-before-fill and no password-field collection.
- **Document processing:** PDF, DOCX, TXT and image parsing. PaddleOCR is an optional install; scanned pages without it require review.

The default LLM provider is `mock`, so startup and automated tests do not make paid API calls. Set `LLM_PROVIDER` and its API key to use a real provider. See the [security guide](docs/SECURITY.md) before deployment.

## Start with Docker Compose

Prerequisites: Docker Desktop with Compose v2. The development stack runs MongoDB, ChromaDB, Redis, the API, a Celery worker, the dashboard and an extension asset builder.

1. Copy `.env.example` to `.env`.
2. Replace `JWT_SECRET_KEY=change-me` with a unique random value of at least 32 characters. The backend deliberately rejects the example placeholder.
3. Start the stack:

```powershell
docker compose up --build
```

Open the dashboard at `http://localhost:5173`. The API is at `http://localhost:8000`; health is `/api/v1/health`, service status is `/api/v1/health/services`, and interactive OpenAPI docs are `/docs`.

Compose uses `PROCESSING_MODE=celery` and Redis. For local API development outside Compose, set `PROCESSING_MODE=inline`; this processes uploads as in-process asyncio tasks and does not need Redis. Both modes use the same pipeline.

The first embedding request downloads the configured sentence-transformer model. If changing the model, set its correct `EMBEDDING_DIMENSION`, choose a new `CHROMADB_COLLECTION`, and run the [reindex command](docs/DATABASE_SCHEMA.md#chromadb) from `backend`. The old collection is left in place until you verify the replacement.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
npm ci
```

Run the dashboard or extension locally with `npm --prefix frontend run dev` or `npm --prefix extension run dev`. The extension's backend URL can be changed in the popup settings. For backend-only local work, configure `.env` with reachable MongoDB and ChromaDB services and use `PROCESSING_MODE=inline`.

## Tests and checks

The default backend suite uses mock LLM responses and a temporary local storage directory. Tests marked `mongo`, `chroma` or `real_llm` need the service/API stated in [the testing strategy](docs/TESTING_STRATEGY.md).

```powershell
python -m pytest
npm run typecheck
npm test
npm run build
```

The full browser E2E runs a separate Compose project and loads the built extension into Chromium. It uses a synthetic document and the mock LLM. On Windows PowerShell:

```powershell
.\scripts\test-e2e.ps1
```

On Linux/macOS or CI, run `make test-e2e`. Both commands need Docker and network access to download the embedding model on first processing. The isolated test stack binds separate local ports and volumes so it can coexist with the development stack.

The opt-in `real_llm` tests can incur provider charges. Use only synthetic test data and enable them explicitly with `RUN_REAL_LLM_TESTS=1`.

## Project references

- [Implementation plan and phase status](docs/IMPLEMENTATION_PLAN.md)
- [Project audit](docs/PROJECT_AUDIT.md) — findings are a snapshot from before remediation.
- [Testing strategy](docs/TESTING_STRATEGY.md)
- [Latest test results](docs/TEST_RESULTS.md)
- [API reference](docs/API_REFERENCE.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
- [Security and privacy](docs/SECURITY.md)
- [Architecture decisions](docs/ARCHITECTURE_DECISIONS.md)

The original product specifications in `docs/specifications/` remain design references; use the API and database references for implemented behavior.
