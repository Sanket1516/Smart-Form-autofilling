# Smart Form Auto-Filling System

Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms.

## Project overview

This capstone project will assist users with dynamic web forms by extracting evidence-backed personal knowledge from documents, understanding field meaning, and providing verified browser recommendations. It is designed around user control, provenance, and privacy.

## Problem statement and objectives

Repeated entry of personal data across changing forms is error-prone. The project will understand fields semantically, organize traceable user facts, route direct facts to MongoDB and contextual evidence to ChromaDB, and provide safe, explainable assistance.

## Key features and architecture

```text
React dashboard -> FastAPI -> MongoDB
Chrome extension -> FastAPI -> ChromaDB
Future: document processing + LangGraph agent workflow + browser autofill
```

The required future LangGraph nodes are Semantic Classification, Routing, Structured Retrieval, RAG Retrieval, and Final Response. The Chrome extension communicates with FastAPI.

## Technology stack

| Layer | Technology |
|---|---|
| Web UI | React, Vite, JavaScript |
| Browser | Chrome Extension Manifest V3 |
| API | Python 3.11, FastAPI |
| Structured store | MongoDB |
| Vector store | ChromaDB |
| Future orchestration | LangGraph, LangChain |
| Future document processing | pdfplumber, PaddleOCR, OpenCV |
| Containers | Docker and Docker Compose |

## Repository structure

```text
backend/        FastAPI app, connectivity, backend tests
docs/           Architecture decisions
extension/      Chrome MV3 foundation
frontend/       React/Vite foundation
infra/          Reserved deployment assets
shared/         Reserved shared contracts and ontology assets
Specifications/ Supplied immutable source specifications
test-data/      Reserved anonymized fixtures
tests/          Cross-project tests
```

## Data and processing responsibilities

MongoDB will be the canonical structured store for users, profiles, document metadata, facts, provenance, sessions, recommendations, corrections, feedback, and audits. ChromaDB will store document chunks, embeddings, and source metadata for semantic retrieval; it never replaces MongoDB facts.

Planned document pipeline: upload -> validation -> PDF parsing/OCR -> normalization -> fact extraction -> verification/canonicalization -> MongoDB plus chunks/embeddings -> ChromaDB.

Planned agent workflow: Field Object -> classification -> routing -> structured or RAG retrieval -> conflict/HITL -> Final Response -> approved autofill -> verification.

## Prerequisites

- Docker Desktop with the daemon running
- Docker Compose v2+
- Node.js 22+
- Python 3.11+
- Google Chrome for loading the unpacked extension

## Environment variables

Copy `.env.example` to `.env` for local customization; never commit `.env`.

| Variables | Purpose |
|---|---|
| `APP_*`, `*_PORT` | Application name, version, and ports |
| `MONGODB_*` | Database URL, credentials, database, timeout |
| `CHROMADB_*` | Vector service URL, collection placeholder, timeout |
| `LLM_*`, `EMBEDDING_MODEL` | Future provider configuration |
| `JWT_*`, `CORS_ORIGINS` | Future security and browser/API policy |
| Upload/confidence settings | Future document and safety policy |

## Docker setup

```powershell
docker compose --env-file .env.example up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Stop services with `docker compose --env-file .env.example down`. Use `down -v` only when intentionally deleting local database volumes.

Ports: frontend `5173`, backend `8000`, MongoDB `27017`, ChromaDB `8001`.

## Local development

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:MONGODB_URL='mongodb://localhost:27017'
$env:CHROMADB_URL='http://localhost:8001'
uvicorn app.main:app --app-dir backend --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000`.

### Chrome extension

1. Open `chrome://extensions` and enable Developer mode.
2. Choose **Load unpacked** and select `extension/`.
3. Open the extension popup to check the backend.

## Testing and database setup

```powershell
python -m pytest backend/tests tests
cd frontend; npm run build
```

Docker Compose initializes only database connectivity and persistent volumes. It does not create application collections or retrieval logic. If containers fail, inspect `docker compose logs <service>` and first confirm Docker Desktop is running.

## Development workflow and security

Each phase follows plan -> implement -> test -> verify -> document. Never commit secrets; treat webpages as untrusted; enforce user ownership in future protected APIs; do not fabricate personal data; and keep autofill separate from form submission.

## Current implementation status

- [x] Repository foundation, Git initialization, environment template, and license.
- [x] Docker Compose foundation for frontend, backend, MongoDB, and ChromaDB.
- [x] FastAPI shell, database connection managers, and `/health` endpoint.
- [x] React health/status shell.
- [x] Chrome MV3 popup, service worker, passive content-script file, and backend-client foundation.
- [x] Initial backend, frontend-build, and extension-structure tests.
- [~] Architecture decisions and project documentation.
- [ ] Authentication and authorization.
- [ ] Document upload, storage, OCR, PDF parsing, and fact extraction.
- [ ] MongoDB collections/profile knowledge and ChromaDB indexing.
- [ ] Semantic classification, LangGraph agents, structured retrieval, and RAG.
- [ ] Conflict resolution, HITL, autofill, verification, and feedback.

## Roadmap and known limitations

Next phases cover backend/database implementation, authentication, document processing, knowledge indexing, dynamic form detection, semantic understanding, retrieval, HITL, autofill, security hardening, and evaluation.

Phase 1 deliberately contains no authentication, upload, OCR, extraction, model integration, agent execution, form detection, semantic classification, retrieval, autofill, or form submission. The extension does not modify webpages.

## Team information

Final-Year Capstone Project, 2026-27, MPSTME Shirpur Campus. Add approved team member details when available.

