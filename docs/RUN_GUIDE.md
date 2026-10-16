# How to run the project and the judge demo

Written for: a developer or demo operator starting from a fresh checkout on Windows (Git Bash / PowerShell) who needs to run the app, load the demo data and walk through it.

> All demo data is synthetic: **SYNTHETIC DEMO DATA — NOT A VALID GOVERNMENT DOCUMENT**.

## 1. Prerequisites

| Tool | Used for |
|---|---|
| Docker Desktop | MongoDB, ChromaDB, Redis, backend, Celery worker, frontend |
| Python 3.11 + `.venv` | demo CLI, generators, backend tests |
| Node 22 + npm | frontend and Chrome extension builds |
| Chrome / Chromium | loading the extension |

Create `.env` from `.env.example` and set the LLM values (the project uses Gemini: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`). Without a working LLM key, extraction still runs on patterns and Ask Documents falls back to listing evidence.

Python packages for the demo tooling (from the repository root):

```bash
pip install pymupdf reportlab pillow numpy httpx
```

## 2. Start the stack

From the repository root:

```bash
docker compose up -d
docker compose ps          # wait until mongodb, chromadb, redis, backend are "healthy"
```

| Service | URL |
|---|---|
| Web app (nginx) | http://localhost:5173 |
| Backend API / docs | http://localhost:8000/api/v1 , http://localhost:8000/docs |
| Health | http://localhost:8000/api/v1/health/services |

After changing backend code, images must be rebuilt (code is baked into them) and you should wait about 40 seconds before using the API:

```bash
docker compose build backend worker && docker compose up -d backend worker
```

After changing frontend code: `docker compose build frontend && docker compose up -d --no-deps frontend`.

## 3. Build the Chrome extension

```bash
cd extension
npm install        # or run `npm install` once at the repository root (npm workspaces)
npm run build      # output: extension/dist
```

Load it: Chrome → `chrome://extensions` → enable *Developer mode* → *Load unpacked* → select `extension/dist`.
Open the extension popup, set the backend URL to `http://localhost:8000` if asked, and sign in with the demo account (section 5).

## 4. Where the demo lives (paths)

| What | Path |
|---|---|
| Single source-of-truth profile | `demo/profile.py` |
| 15 PDF documents | `frontend/public/demo/documents/DEMO_01_…` to `DEMO_15_…` |
| 15 forms (+ index, CSS, JS) | `frontend/public/demo/forms/` |
| Generators | `demo/documents_gen.py`, `demo/forms_spec.py`, `demo/forms_gen.py`, `demo/manifest_gen.py` |
| Answer key (tests only, never served) | `demo/expected/manifest.json` |
| Public question list (no answers) | `frontend/public/demo/scenarios.json` |
| Demo Data page source | `frontend/src/pages/DemoData.tsx` |
| API evaluation | `demo/evaluate.py` |
| Extension (browser) evaluation | `extension/tests/demo-autofill.spec.ts`, `extension/playwright.demo.config.ts` |
| Results | `demo/results/latest.json`, `demo/results/REPORT.md` |
| Fictional eligibility rules | `backend/app/exams/demo_requirements.yaml` (not loaded when `APP_ENV=production`) |

Full detail: `demo/README.md`.

## 5. Demo commands

Run from the repository root with the stack up.

```bash
python -m demo.cli generate     # rebuild PDFs, forms, answer key, scenario list (deterministic)
python -m demo.cli load         # upload DEMO_* files to the demo account; skips files already there
python -m demo.cli status       # per-document status, facts, chunks, index state
python -m demo.cli cleanup      # delete only DEMO_* documents (and their facts/vectors)
```

The CLI uses a dedicated account, `demo.applicant@example.com` (password `Demo-Applicant-2026!`, local use only), created automatically on first `load`. Override with the `DEMO_EMAIL` and `DEMO_PASSWORD` environment variables. Documents take roughly 15–60 seconds each to OCR, extract and index.

Evaluation (these run tests; use only when you want measured results):

```bash
python -m demo.cli evaluate             # API suite → demo/results/REPORT.md
python -m demo.cli evaluate --browser   # plus the real extension on all 15 forms
```

## 6. Walkthrough: each page, in order

Sign in at http://localhost:5173 with the demo account (or register your own and use it as the demo account).

1. **Demo data** — sidebar *Tools → Demo data* (`/demo-data`).
   Click *Load demo documents*. The table shows each document move from *Processing* to *Processed* with a fact count and *Searchable*. Loading twice never creates duplicates. *Remove demo documents* deletes only `DEMO_*` files.
2. **Documents** — `/documents`. Open any document to see extracted facts, page and evidence. Scanned ones (voter record, Class 10 marksheet, birth record, passbook, category certificate) went through OCR.
3. **Profile** — `/profile`. Merged values per concept (name, date of birth, addresses, Class 10 vs Class 12 values …). `/conflicts` and `/discovered-facts` show disagreements and unmapped data such as transactions and household members.
4. **Ask your documents** — `/ask`. On *Demo data* click any of the 28 questions; the Ask page opens with it prefilled (press *Ask*). Check the sources shown under each answer. Try a follow-up in the same conversation (e.g. “What is my Class 12 percentage?” then “And for Class 10?”). For the eligibility question choose the exam *DemoScholar 2026 (fictional)*; its rules are invented for the demo.
5. **Forms** — from *Demo data → Forms* open a form in a new tab (or http://localhost:5173/demo/forms/index.html).
   - Click the Smart Form extension icon → *Analyze this form*.
   - Review the proposed values (sensitive ones such as account numbers or category need an explicit tick; choices such as exam city, declarations and uploads are never filled).
   - Press *Fill*. The page’s status panel marks each field Verified / Filled / Review / Missing / Your choice from the live DOM. Nothing is ever submitted.
   - Good forms to show: **6/7** (Class 10 vs Class 12), **9** (account number vs IFSC), **13** (certificate vs validity number), **15** (long entrance application with dynamic fields).
6. **Evaluation** — bottom of *Demo data* shows the latest published summary; full report in `demo/results/REPORT.md`.

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `/demo` redirects to a dead port | The page is `/demo-data`; `/demo/` is the static asset folder. |
| `Server disconnected` from the CLI | Backend was restarting; wait ~40 s and rerun. |
| Documents stay *Processing* | The worker handles them one at a time; watch `docker logs smart-form-autofilling-dev-worker-1`. |
| “AI extraction was unavailable” warning | The external LLM returned 503/403; the CLI reprocesses automatically, or use *Reprocess* in Documents. |
| Ask answers list evidence only | LLM unavailable; retry later. |
| Extension cannot reach the form page | Click the extension on the form tab and accept the site access prompt; rebuild `extension/dist` if source changed. |
| Port 5173/8000 busy | Stop other stacks (`docker ps`) before `docker compose up -d`. |
