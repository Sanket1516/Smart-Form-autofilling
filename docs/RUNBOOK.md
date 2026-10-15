# Runbook: start, check and demo the system

This is the tested startup procedure (Windows 11, Docker Desktop, PowerShell). Commands
also work in Git Bash with `/` paths.

## 1. Services and ports

| Service | Port (host) | Health check |
|---|---|---|
| API (FastAPI) | 8000 | `GET http://localhost:8000/api/v1/health`, `/api/v1/health/services` |
| Dashboard (Nginx) | 5173 | `http://localhost:5173` |
| MongoDB | 27017 | API `/health/services` → `mongodb: healthy` |
| ChromaDB | `CHROMADB_PORT` (18001 in the local `.env`) | `GET http://localhost:18001/api/v2/heartbeat` |
| Redis + Celery worker | internal | worker log shows `celery@... ready` |
| Ollama (optional local model) | 11434 | `GET http://localhost:11434/api/version` |

`CHROMADB_URL` in `.env` is used by anything that runs **on the host** (tests, scripts,
a locally started API). Inside Compose the API and worker use `http://chromadb:8000`.
Keep `CHROMADB_URL` on the same port as `CHROMADB_PORT`.

## 2. Configuration

1. `copy .env.example .env` and set `JWT_SECRET_KEY` (32+ random characters).
2. Choose the model provider (see `.env.example` for the privacy note):
   * hosted: `LLM_PROVIDER=google`, `LLM_MODEL=<gemini model id>`, `LLM_API_KEY=...`
   * fully local: `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2:7b`,
     `LLM_BASE_URL=http://host.docker.internal:11434`
   * optional fallback: `LLM_FALLBACK_PROVIDER=ollama`, `LLM_FALLBACK_MODEL=qwen2:7b`
3. Scanned documents need OCR: `INSTALL_OCR=true` (PaddleOCR is built into the images).
4. On machines where Docker has 8 GB RAM or less keep `CELERY_WORKER_CONCURRENCY=1`:
   every worker process loads its own OCR model, and running OCR in several processes
   at once exhausted an 8 GB Docker VM during testing (the engine had to be restarted).

## 3. Start

```powershell
docker compose up --build -d
docker compose ps                                   # all services Up / healthy
curl http://localhost:8000/api/v1/health/services   # every service "healthy" or "configured"
```

Optional local model (no data leaves the machine):

```powershell
ollama serve            # separate terminal, or the Ollama app
ollama pull qwen2:7b    # 4.4 GB, Apache-2.0; fits a 6 GB GPU
```

Load the browser extension: `chrome://extensions` → Developer mode → **Load unpacked** →
`extension/dist` (built by the `extension-builder` service or `npm --prefix extension run build`).
Set the backend URL in the popup if it is not `http://localhost:8000`.

## 4. After upgrading the extraction / OCR / chunking code

Existing documents keep the facts and chunks they were processed with. Reprocess them:

```powershell
docker compose exec backend python -m app.scripts.reindex
```

or press **Process again** on a document. This rebuilds facts (with source document
type and review flags), OCR text and the line-preserving chunks.

## 5. Demo flow

1. Register on the dashboard, upload documents (PDF, PNG/JPG, DOCX, TXT up to 10 MB).
   Status moves *Uploaded → Processing → Processed* (or *Failed* / *Needs attention*).
2. **Documents → document**: extracted values with page, evidence and how they were read.
3. **Ask your documents**: e.g. "What was my Class 12 passing year and percentage?",
   "Compare the information in my uploaded marksheets", "Am I eligible for NEET UG?",
   "Which required information for NEET is missing from my profile?". Select documents to
   restrict the answer; ask follow-ups in the same conversation.
4. Open a web form, click the extension → **Analyze this form** → review proposed values
   (sources shown) → approve → **Fill** → the popup reports which fields were filled *and*
   verified. Forms are never submitted.

## 6. Tests and evaluations

```powershell
.venv\Scripts\python -m pytest                                  # backend (needs MongoDB)
.venv\Scripts\python -m pytest backend/tests/integration -m chroma   # real ChromaDB + embeddings
npm --prefix frontend test ; npm --prefix extension test       # unit tests
cd extension; npm run build; npx playwright test               # browser E2E (host API on :8010)

cd backend
python -m tests.eval.run_eval --out ../docs/eval/current.json           # extraction accuracy
python -m tests.eval.render_documents --out ../test-data/rendered       # synthetic scans/PDFs
docker compose exec backend python -m tests.eval.ocr_benchmark ...      # OCR (needs PaddleOCR)
python -m tests.eval.llm_benchmark --providers configured,ollama:qwen2:7b
python -m tests.eval.e2e_probe --api http://localhost:8000              # full stack, real APIs
```

Results from the last run are in `docs/EVALUATION.md` and `docs/TEST_RESULTS.md`.

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Ask Documents says "documents not ready" | Documents are still processing or failed; check the Documents page. |
| Answers marked *AI unavailable — evidence shown as found* | The model provider failed (quota, network, key). Facts and passages are still shown; configure `LLM_FALLBACK_*` for a fallback. |
| Scanned upload ends in *Needs attention* | OCR is not installed (`INSTALL_OCR=true`, rebuild) or `OCR_ENGINE=none`. |
| `/health/services` shows `chromadb: unhealthy` | ChromaDB container down or `CHROMADB_URL` port wrong (host runs). |
| Docker commands return HTTP 500 | Docker Desktop engine stopped (often out of memory): `docker desktop restart`, then `docker compose up -d`. |
