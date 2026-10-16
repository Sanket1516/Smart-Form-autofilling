# Judge Demonstration Guide

Written for: the presenter (you), rehearsing and then presenting the Smart Form Auto-Filling System live to academic judges.

This guide is self-contained: follow it top to bottom and you will not need to improvise explanations. It references only what is actually implemented in this repository (cross-checked against source on the date below) and the judge-demo dataset in `demo/`. Companion documents: [README.md](../README.md) (what the project is), [RUN_GUIDE.md](RUN_GUIDE.md) (how to start everything and where each path lives).

Legend: ✅ implemented and verified in source · 🟡 implemented, behaviour not independently re-run in this pass · ⚠️ known limitation, say it plainly if asked.

---

## Section A — Pre-demonstration checklist

Do this the evening before and again ~30 minutes before judges arrive.

### A.1 Services

```bash
docker compose up -d
docker compose ps        # mongodb, chromadb, redis, backend must show "healthy"; frontend "healthy" too
curl -s http://localhost:8000/api/v1/health/services   # llm: "configured" or "mock"; mongodb/chromadb: "healthy"
```

If you rebuilt backend code recently: `docker compose build backend worker && docker compose up -d backend worker`, then wait ~30–40 s before the next step (the API returns `Server disconnected` for a short window while it restarts).

### A.2 Environment

- `.env` exists, `JWT_SECRET_KEY` is a real random value (not `change-me`).
- `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` set if you want live AI-assisted extraction and Ask Documents answers. With `LLM_PROVIDER=mock` the deterministic paths (exact fact lookup, field classification by rule, document extraction by pattern) still work fully; only AI-written answers and AI-only field matches are empty.

### A.3 Dashboard and demo data

```bash
cd backend && python -m demo.cli generate   # from repo root: python -m demo.cli generate
python -m demo.cli load                     # uploads the 15 synthetic documents to the demo account (idempotent)
python -m demo.cli status                   # confirm all 15 show "processed"
```

Open http://localhost:5173, sign in as `demo.applicant@example.com` / `Demo-Applicant-2026!` (or your own account with `python -m demo.cli load --api ...` against it), and go to **Demo data** (`/demo-data`) in the sidebar. Confirm the table shows 15/15 processed with non-zero fact counts.

### A.4 Chrome extension

```bash
cd extension && npm run build     # -> extension/dist
```

Chrome → `chrome://extensions` → Developer mode on → **Load unpacked** → `extension/dist`. Open the extension popup once and sign in with the same demo account so the review flow doesn't need a login mid-demo.

### A.5 Browser tabs to have ready (in order)

1. Dashboard → `/demo-data`
2. Dashboard → `/documents` (one already-processed scanned document open, e.g. Class 10 marksheet)
3. Dashboard → `/ask`
4. `http://localhost:5173/demo/forms/index.html` (or open forms 6, 9, 13 directly)
5. A code editor (or this repo in VS Code) with the files listed in Section D pre-opened in tabs, for instant switching.

### A.6 Readiness checklist (tick every item right before presenting)

- [ ] `docker compose ps` — all healthy
- [ ] `/api/v1/health/services` — mongodb/chromadb healthy, llm configured (or mock, and you know that)
- [ ] Demo data page shows 15/15 processed
- [ ] Extension loaded, signed in, icon visible
- [ ] Ask page loads and the example questions are visible
- [ ] At least one demo form (e.g. form 6, Class 10 Educational Record) opens and renders
- [ ] You know the current evaluation numbers are from **a previous run** (`demo/results/REPORT.md`) unless you re-ran `python -m demo.cli evaluate` today

---

## Section B — Live demonstration sequence (target 10–15 minutes; short form in brackets ~6–7 min)

| # | Time | Open / run | Action | Say to judges | Shows | Files behind it | If it doesn't show |
|---|---|---|---|---|---|---|---|
| 1 | 1 min | — | Verbal intro | "People retype the same identity, academic and financial facts into form after form, copying from PDFs and scans by hand. This system reads your own documents once, turns them into verified facts, and fills forms from those facts — but only after you approve every value, and it never submits anything for you." | Problem framing | — | — |
| 2 | 1 min | Draw/point at architecture diagram in README §5 (or just narrate) | — | "Three parts: a FastAPI backend with MongoDB for facts and ChromaDB for document search, a React dashboard, and a Chrome extension. Documents go upload → OCR/parse → extraction → facts + vectors. A form goes detect fields → classify → resolve a value from your facts or your documents → you review → fill → it reads the page back to confirm." | Architecture | `backend/app/main.py`, README §5 | — |
| 3 *(short: skip, say "already loaded")* | 1 min | `/demo-data` | Point at the documents table, 15/15 processed | "These are 15 synthetic documents — identity sheet, PAN-style record, Class 10 and Class 12 marksheets, bank passbook and statement, certificates — all fictional, clearly marked, generated from one consistent profile so cross-document questions make sense." | Upload workflow exists & works | `frontend/src/pages/DemoData.tsx`, `demo/profile.py` | If a document shows "processing," wait or refresh; if "failed," open it and show the `processing_error` honestly |
| 4 | 1–2 min | `/documents` → open the **Class 10 marksheet** | Scroll to its extracted facts | "This was a scanned, slightly rotated image — it went through OCR, not just text extraction. Each value — roll number, subject marks, percentage, passing year — is stored with which document and page it came from, and a confidence score." | OCR + structured extraction with provenance | `backend/app/processing/extractor.py` (OCR), `backend/app/extraction/document_extractor.py` (table/label rules), `frontend/src/components/documents/DocumentDetails.tsx` | If a field looks wrong, say so — point at the confidence/provenance and explain the review step exists for exactly this |
| 5 | 30s | Same page or `/profile` | — | "Facts don't just sit per-document — they're merged into one profile. If two documents disagree, it shows as a conflict I can resolve, not a silent overwrite." | Structured storage + conflict handling | `backend/app/services/facts.py`, `frontend/src/pages/Conflicts.tsx` | — |
| 6 | 2 min | `/ask` | Click the prefilled question *"What was my Class 12 passing year and percentage?"*, press Ask | Read the answer and its cited source aloud | "This is Ask Documents. It isn't just an LLM guessing — exact numbers come straight from stored facts, never through the model. The model is only used to compose the sentence from evidence I show it, and every value is cited: document and page." | RAG + structured-fact exactness + source attribution | `backend/app/services/document_qa.py` (`DocumentQAService.answer`), `frontend/src/pages/Ask.tsx` | If `answer_mode` is `evidence_only` (LLM unavailable), say exactly that: "the model is unreachable right now, so it's listing the evidence directly instead of writing prose — nothing is fabricated either way" |
| 7 *(skip in short form)* | 1–2 min | `/ask`, ask *"What is my Class 10 percentage?"* then *"Compare the information from both marksheets."* | — | "Class 10 doesn't print a percentage at all on this board's marksheet — watch: it says so, it doesn't invent one. And this next question needs evidence from two different documents at once." | Honest "insufficient evidence" handling + multi-document reasoning | `document_qa.py` `_derive`, `_compose` | — |
| 8 *(skip in short form)* | 1 min | `/ask`, select the fictional **DemoScholar 2026** exam, ask the eligibility question | — | "This uses an entrance-exam readiness model with **clearly fictional rules I invented for this demo** — I'm not claiming these are real admission criteria. It shows which criteria are met, not met, or can't be determined, with the calculation shown — e.g. combined Physics+Chemistry+Mathematics percentage, computed from printed marks, not guessed." | Deterministic scenario reasoning | `backend/app/exams/service.py`, `backend/app/exams/demo_requirements.yaml` | — |
| 9 | 1 min | Open `demo/forms/form-06-class-10-educational-record.html` (or form index) in a new tab | Point out it's a plain HTML form with no pre-filled values | "This is an ordinary web form — no special hooks for this project. It has required fields, a dropdown, and a dynamically-rendered subject table." | Realistic target form | `frontend/public/demo/forms/form-06-...html`, `demo/forms_gen.py` | — |
| 10 | 30s | Click the extension icon on that tab | — | "The extension only runs when I open it on a tab — it doesn't run on every page I visit." | On-demand content-script injection | `extension/src/shared/tabs.ts`, `extension/public/manifest.json` | — |
| 11 | 1 min | Click **Analyze this form** | Wait for the review list | "It read every input/select/textarea on the page — labels, names, types, nearby text — and sent only that description to the backend, never the page's current values." | Field detection | `extension/src/content/detector.ts` | If analysis hangs >60s, check `docker logs smart-form-autofilling-dev-worker-1`; fall back to a form you tested earlier (form 1 or form 7 are simplest) |
| 12 | 1–2 min | Point at 2–3 rows in the review list | — | "Each field was matched to the same canonical concept my facts use — first by deterministic rules (the HTML `autocomplete` attribute, label wording), and only the leftover ambiguous ones go to the model in one batched call. Sensitive fields — bank account, category — are never pre-ticked; I have to tick them myself." | Semantic field mapping + review gating | `backend/app/agents/field_classifier.py`, `backend/app/agents/graph.py` (`FormFillGraph`), `extension/src/popup/AutofillFlow.tsx` | — |
| 13 | 1 min | Tick remaining rows, click **Fill N fields** | — | "Only ticked fields get written, and it writes through the real DOM property setter so React/Vue-controlled inputs pick it up too." | Autofill execution | `extension/src/content/autofill.ts` | — |
| 14 | 1 min | Point at the filled page / the "N fields filled and verified" message | — | "After filling, it reads the DOM back and only reports a field as verified if the page still shows that value — it's not just trusting what it wrote." | Post-fill verification | `autofill.ts` (`fillFields`), `POST /forms/sessions/{id}/verify` |  — |
| 15 *(skip in short form)* | 1 min | Scroll to a field with no document value (e.g. "Current occupation") and a dynamic subject row | — | "Anything no document supports stays empty and is marked missing on the page itself — it never guesses. And these subject-mark rows were rendered by the page's own script after load, which the extension still detected correctly." | Missing-value safety + dynamic-field handling | `frontend/public/demo/forms/demo-forms.js`, `backend/app/agents/graph.py` (`_resolve_profile`/`_resolve_documents` returning nothing) | — |
| 16 | 1–2 min | Switch to editor | Open `backend/app/agents/graph.py`, scroll to the `StateGraph` wiring (~line 115) | "This is the actual pipeline as an explicit state graph: sanitize, classify, resolve from profile, resolve from documents, decide, persist. Sanitize is where password/payment/OTP fields get blocked before anything else runs." | Source-level walkthrough | `backend/app/agents/graph.py` | — |
| 17 | 1 min | Open `backend/tests/test_indian_documents.py` or run `pytest` live if time allows | — | "These are real pytest assertions on synthetic Indian documents — checking things like 'Class 10 and Class 12 values never get mixed up' and 'a caste certificate number is never confused with its validity-certificate number.'" | Existing automated tests | `backend/tests/test_indian_documents.py` | Don't claim a pass/fail number unless you just ran it — see Section E for the honest way to present this |
| 18 | 1 min | — | Verbal summary | "Deterministic rules do the exact-value work — identifiers, dates, table totals. The model only ever fills gaps and writes prose from evidence I control. Known limitation: a dead `RAGAnswerService` class exists but no route uses it — the real answer path is `DocumentQAService`. Multi-column OCR can occasionally glue a label onto a neighbouring value, though the correct value still comes through." | Honest limitations | README §17 | — |

**Short-form (6–7 min):** steps 1, 2, 4, 6, 9–14, 18.

---

## Section C — Speaker notes: deeper distinctions to get right

**RAG vs. plain prompting.** Don't say "the AI reads your documents." Say: "retrieval finds the most similar stored chunks from *your own* indexed documents by vector similarity; the chosen chunks are placed in the prompt as labelled, untrusted evidence; the model is only allowed to write from that evidence." Then add the stronger point: for Ask Documents, *exact* values (an identifier, a date, a percentage) come from **structured facts in MongoDB**, computed/stored at extraction time — never re-derived by the LLM at answer time. The LLM's job is composing readable prose and nothing else when exact facts answer the question.

**Autofill: five distinct steps, not one.** (1) Detect — read the DOM, describe each field, never its value. (2) Interpret — map the description to a canonical concept, deterministic rules first. (3) Retrieve — pull a value from stored facts, or from document retrieval if the profile has nothing. (4) Decide — a confidence threshold and a sensitivity list decide whether this can be pre-ticked or needs the user's own tick. (5) Execute + verify — write through the native setter, dispatch input/change events, then re-read the DOM.

**What's deterministic vs. AI-driven**, said plainly if asked: identifier extraction (PAN/Aadhaar/licence-number shapes), date parsing, table/record parsing (marksheet subjects, bank transactions), percentage/age calculations, and first-pass field classification are **all deterministic code, not the LLM**. The LLM is used for: (a) extracting attributes a pattern didn't catch, (b) classifying the handful of form fields deterministic rules couldn't resolve, (c) composing the final Ask Documents sentence from evidence you already retrieved. If the LLM is unavailable, (a) and (b) simply contribute nothing extra (pattern-based results stand alone) and (c) falls back to listing the evidence directly.

---

## Section D — Source-code navigation table

| Feature | First file to open | Next file | Key function/class | What to explain |
|---|---|---|---|---|
| Backend entry point | `backend/app/main.py` | — | `lifespan()`, router includes | Dependency wiring: every service (`document_qa_service`, `form_fill_service`, …) is built once at startup and attached to `app.state` |
| Document upload route | `backend/app/api/v1/documents.py` | `backend/app/services/documents.py` | `upload_document` → `DocumentService.upload` | Size limit check, storage write, kicks off processing |
| OCR / extraction | `backend/app/processing/extractor.py` | `backend/app/processing/ocr.py` | `UniversalDocumentExtractor.extract`, `RapidOCRAdapter` | pdfplumber/docx native path vs. OCR path; table-row detection |
| Structured extraction | `backend/app/extraction/document_extractor.py` | `backend/app/extraction/deterministic.py`, `llm_extraction.py` | `DocumentAwareExtractor.extract` | Label/value parsing, identifier validators, then one LLM pass on what's left |
| Merge + storage | `backend/app/extraction/merge.py` | `backend/app/services/facts.py` | `merge_candidates` | Conflict detection, provenance kept per value |
| Database model/repositories | `backend/app/repositories/collections.py` | `backend/app/db/mongo.py` | `StructuredFactsRepository`, `DiscoveredFactsRepository` | Owner-scoped queries |
| Embeddings | `backend/app/retrieval/embeddings.py` | — | `EmbeddingProvider` | Default model, 384 dimensions |
| Vector indexing | `backend/app/db/chroma_client.py` | `backend/app/processing/chunking.py` | `ChromaClient`, `DocumentChunk` | HTTP v2 API, user-scoped collection |
| Retrieval query | `backend/app/services/retrieval.py` | — | `RAGRetrievalService.search` | top-k, min-similarity cutoff |
| Ask Documents (backend) | `backend/app/services/document_qa.py` | `backend/app/schemas/retrieval.py` | `DocumentQAService.answer`, `QuestionPlanner` | Structured-fact-first, derive, retrieve-if-needed, compose |
| Ask Documents (frontend) | `frontend/src/pages/Ask.tsx` | `frontend/src/services/api.ts` (`ragApi`) | — | Prefilled example questions, conversation history for follow-ups |
| LLM provider integration | `backend/app/agents/llm_provider.py` | `backend/app/core/config.py` | `get_llm_provider`, `GoogleProvider`/`OpenAIProvider`/`AnthropicProvider`/`OllamaProvider` | Mock-by-default, optional fallback provider |
| Form-field detection | `extension/src/content/detector.ts` | `extension/src/types/index.ts` | `extractFields` | `FieldObject` shape — never the current value |
| Semantic field mapping | `backend/app/agents/field_classifier.py` | `backend/app/ontology/field_ontology.yaml` | `FieldClassifier.classify` | Deterministic rules, LLM only for the rest |
| Autofill pipeline | `backend/app/agents/graph.py` | — | `FormFillGraph` (`_sanitize` → `_deterministic_classify` → `_llm_classify` → `_resolve_profile` → `_resolve_documents` → `_decide` → `_persist`) | The whole state machine in one file |
| Extension manifest | `extension/public/manifest.json` | — | — | MV3, no background worker, on-demand host permission |
| Content script | `extension/src/content/index.ts` | `extension/src/content/autofill.ts` | message router, `fillFields` | Injected on demand; mutation observer for dynamic forms |
| Extension ↔ backend | `extension/src/shared/api.ts` | `extension/src/popup/AutofillFlow.tsx` | `api.decide`, `api.approvedValues`, `api.verify` | Review-then-fill contract |
| Post-fill verification | `extension/src/content/autofill.ts` | `backend/app/api/v1/forms.py` (`verify_filled_values`) | `fillFields` return value | Applied vs. verified, persisted server-side |
| Tests / evaluation | `backend/tests/test_indian_documents.py` | `backend/tests/eval/run_eval.py`, `demo/evaluate.py` | — | Unit assertions vs. the judge-demo end-to-end evaluation |
| Config / deployment | `backend/app/core/config.py` | `docker-compose.yml`, `.env.example` | `Settings` | Every env var, its default, and why |

---

## Section E — Results and evidence you can show honestly

| Result | Where to get it live | Caveat |
|---|---|---|
| Extracted field values with page/confidence | `/documents/{id}` in the dashboard, or `GET /api/v1/documents/{id}/facts` | Live, trustworthy |
| A MongoDB record | `docker exec -it smart-form-autofilling-dev-mongodb-1 mongosh ...` then `db.structured_facts.findOne(...)` | Only if comfortable live-querying; otherwise skip |
| Retrieved passages | `/ask` answer's cited sources, or `POST /api/v1/retrieval/rag` directly against the API | Live |
| Ask Documents response incl. `answer_mode` | `/ask` page or raw API response | State plainly if `answer_mode=evidence_only` |
| Form-field mapping | Extension review list (each row shows the matched concept's label and source) | Live |
| Final DOM values | The filled form page itself, plus the "N filled and verified" toast | Live |
| Existing test output | Run `python -m pytest` (backend), `npm test` (frontend/extension) **right before presenting**, or show `docs/TEST_RESULTS.md` **labelled with its date** as a prior run | Never state a pass count you have not just observed |
| Evaluation metrics (extraction accuracy, retrieval top-1, Ask Documents correctness, autofill correctness) | `demo/results/REPORT.md` (generated 2026-10-16 in this repo's last run) or re-run `python -m demo.cli evaluate --browser` | **Label this explicitly as "from our last measured run"** unless you just re-ran it; do not present it as a live number unless it is |

**If asked for live, fresh numbers:** say "let me run the evaluation suite now" and run `python -m demo.cli evaluate` (API-only, ~2–3 minutes) or `--browser` (~8–10 minutes) rather than quoting old numbers as current.

### Results checklist for the presenter

- [ ] I know whether I'm showing a *live* number or a *recorded prior run*, and I will say which.
- [ ] I have not memorised an accuracy figure to recite without a source open.
- [ ] If a judge asks for a number I don't have live, I offer to run the suite rather than estimate.

---

## Section F — Architecture explanation (for Q&A depth)

- **Document parsing vs. OCR**: `pdfplumber`/`python-docx` read native text layers directly (no OCR needed, exact character accuracy); OCR (`RapidOCRAdapter`) is only invoked for image files or PDF pages with no extractable text layer (scanned/photographed pages), and includes deskew/contrast/orientation preprocessing.
- **Structured vs. vector retrieval**: structured facts (MongoDB `structured_facts`) answer exact-value questions with zero ambiguity; vector retrieval (ChromaDB) answers "what does this document say about X" questions where the exact field isn't pre-extracted, by finding the most semantically similar text chunks.
- **RAG vs. ordinary prompting**: ordinary prompting would ask the model to answer from its own training; RAG constrains the model to answer only from chunks retrieved from *this user's own* indexed documents, each wrapped as labelled untrusted evidence, with citations required.
- **Semantic field matching vs. browser autofill**: matching decides *what concept* a field means (e.g. "DOB", "date of birth", "जन्म तिथि" context → `personal.date_of_birth`); autofill is the separate, later act of writing an already-resolved value into that field and confirming the DOM kept it.
- **Intended vs. verified DOM values**: the recommendation is the *intended* value; only after `fillFields` re-reads the DOM does a field get marked `verified` — a framework that silently rejects or reformats the write will show as `applied: true, verified: false`.

---

## Section G — Likely judge questions and project-specific answers

**Why is this project needed?** Manual form-filling from physical/scanned documents is repetitive and error-prone, especially distinguishing similar fields (DOB vs. issue date, Class 10 vs. 12 percentage, account number vs. IFSC) — all specifically tested for in this project (`backend/tests/test_indian_documents.py`).

**Why an LLM at all, if so much is deterministic?** Deterministic rules can't cover every label phrasing or document layout. The LLM is a narrow, bounded fallback: one batched call for leftover ambiguous form fields, one for leftover document attributes, one to compose prose from evidence already chosen by retrieval/facts — never the sole source of an exact value.

**Why OCR specifically, and why RapidOCR?** Scanned or photographed documents have no text layer; `pdfplumber` returns nothing for them. RapidOCR (PP-OCR English models on ONNX Runtime) is the default because it's CPU-friendly (~0.45 GB/page) versus PaddleOCR (~2.5 GB/page); either is optional — without one, scanned documents are marked `requires_review`, never guessed.

**Why RAG instead of just asking the model?** So answers are grounded in the user's own uploaded documents and can cite a source, instead of the model inventing or recalling unrelated general knowledge.

**Why both a structured database and a vector database?** MongoDB gives exact, queryable, confidence-scored values with full provenance — the right tool for "what is my PAN number." ChromaDB gives semantic similarity search over free text — the right tool for "what does my income certificate say about supporting evidence," where there's no single pre-extracted field.

**How do embeddings and retrieval work here?** Each document chunk (and each saved answer) is embedded with `all-MiniLM-L6-v2` (384 dimensions) and stored in ChromaDB with user/document/page metadata. A question is embedded the same way; cosine-similarity search returns the top-k chunks above a minimum-similarity cutoff, scoped strictly to that user.

**How does the system identify a form field?** `extractFields` in the content script reads label text, `aria-label`, placeholder, `name`/`id`, nearby text, and HTML `autocomplete`; the backend classifier matches that description, HTML `autocomplete` first, against ontology concept aliases.

**How is the correct value selected when several candidates exist?** `FormFillGraph._resolve_profile` prefers user-confirmed facts, then highest-confidence extracted facts; conflicting values are surfaced to the user rather than silently picked.

**How is wrong retrieval handled?** Chunks below `RAG_MIN_SIMILARITY` are discarded before they ever reach the model; the Ask Documents service separates `facts` (exact), `derived` (calculated), and retrieved `sources`, so a weak retrieval only affects the free-text portion, never a fact already known exactly.

**How are OCR errors handled?** Validated identifier formats (checksum-style patterns) reject malformed OCR output rather than storing a wrong-but-plausible value; every extracted value keeps its raw OCR text as evidence so a human can check it. Known remaining gap: adjacent labels in dense multi-column layouts can occasionally be concatenated onto a value (see README §17) — the correct value is still present as a separate candidate in the cases observed.

**How does the extension talk to the backend?** Bearer JWT in the `Authorization` header, same REST API the dashboard uses; the extension's default host permission is the backend origin only, and site access for the page being filled is requested via `activeTab` at the moment the user opens the popup.

**How is missing information handled?** A field or fact with no supporting document/profile value is marked `missing_information` and left empty — it is never filled with a guess.

**How does security / user-data isolation work?** Every MongoDB query and Chroma call is filtered by the authenticated `user_id`; passwords are bcrypt-hashed; JWTs are short-lived and revocable; the extension never reads or sends a field's current value, only its description.

**How are API failures handled?** LLM calls have bounded retries for timeouts/429/5xx (never 4xx); on failure the deterministic result stands alone and Ask Documents falls back to `evidence_only` instead of erroring.

**What is deterministic vs. AI-driven?** See Section C.

**What are the project's limitations?** See README §17 and this guide's step 18 — stated plainly, not hidden.

**How could accuracy be improved?** Wider per-layout extraction rules for dense multi-column documents; expanded automated real-provider test coverage; a larger or fine-tuned embedding model for retrieval.

**Why is this architecture appropriate for a project like this?** It separates concerns that have very different reliability needs — exact values must never depend on a probabilistic model, so they don't; free-text understanding benefits from retrieval + LLM composition, so that's where those are used, deliberately bounded and always reviewed by the user before anything is written to a page.

---

## Section H — Failure recovery and demonstration safety

| Issue | Recognize it by | Check | Safe recovery | Do not claim |
|---|---|---|---|---|
| Backend unavailable | Dashboard/extension show network errors; `curl .../health` fails or times out | `docker compose ps`; `docker logs smart-form-autofilling-dev-backend-1 --tail 50` | Restart: `docker compose up -d backend worker`; wait 30–40s; narrate from README/architecture diagram meanwhile | That it's working when it isn't |
| Database unavailable | `health/services` shows `mongodb`/`chromadb` not healthy | `docker compose ps`, container logs | Restart that container; if it persists, fall back to walking source code and the recorded `demo/results/REPORT.md` | That live data is loading |
| Missing environment variable | Backend fails to start, `.env` error in logs | `docker logs ... backend` | Fix `.env`, rebuild/restart | — |
| LLM API unavailable | Ask Documents returns `answer_mode: "evidence_only"`; document processing warns "AI extraction was unavailable" | Response body / document warnings | Say so plainly (Section B, step 6) — evidence/facts are still real and correct | That the AI wrote the answer |
| Document processing failure | Document status `failed` or `requires_review` | Open the document, read `processing_error` | Show the error honestly; use an already-processed document instead | That it processed correctly |
| Ask Documents: no relevant evidence | `status: "insufficient_evidence"` | The answer text itself says so | Use it as a feature demo (step 7) — the system says it doesn't know rather than guessing | That it has an answer |
| Extension fails to connect | Popup shows a connection/auth error | Popup settings → backend URL; confirm it matches the running API port | Re-enter backend URL, re-sign-in | — |
| Form fields not detected | "Analyze this form" returns 0 rows | Try a simpler form (form 1); check content-script injection didn't fail (browser console) | Reload the form tab, reopen the popup | That detection is broken project-wide — show a form that does work |
| Autofill produces an incorrect value | A filled field's value is clearly wrong | Open the review row — was it pre-ticked (bug) or did the user tick it (expected, needed a correction)? | Acknowledge candidly; this is exactly why review-before-fill exists — demonstrate correcting it by hand in the review list | That autofill is 100% accurate — it is reviewed, not perfect, by design |
| Missing browser permission | Popup shows a permission prompt / "not allowed to read this page" | — | Accept the prompt for that tab | — |
| A required sample document is unavailable | `/demo-data` shows fewer than 15 processed | `python -m demo.cli status` | Run `python -m demo.cli load` again (idempotent, safe) | — |

**Never** fake a result, pre-fill a value outside the extension flow to make a demo "work," or present a cached number as live without saying so.

---

## Section I — Quick rehearsal checklist / cheat sheet

**Startup (do this first):**
```bash
docker compose up -d
python -m demo.cli load
cd extension && npm run build
```

**Verify:** `docker compose ps` healthy · `/api/v1/health/services` OK · `/demo-data` shows 15/15 · extension loaded + signed in.

**Tabs open:** Demo data · Documents (one scanned doc) · Ask · a demo form · editor with `graph.py`, `document_qa.py`, `detector.ts` ready.

**Exact questions to ask on `/ask`:** "What was my Class 12 passing year and percentage?" → "What is my Class 10 percentage?" → "Compare the information from both marksheets." → DemoScholar 2026 eligibility question.

**Forms to open:** 6 (Class 10 — dynamic subject table), 9 (bank — account number vs IFSC review-gating), 13 (category + validity certificate numbers).

**Main files to have ready:** `backend/app/agents/graph.py`, `backend/app/services/document_qa.py`, `extension/src/content/detector.ts`, `extension/src/content/autofill.ts`.

**Results to show:** document facts with provenance; an Ask answer with sources; the review list before fill; the filled + verified page; (if asked) a fresh `python -m demo.cli evaluate` run.

**Technical points to land:** deterministic-first, LLM-bounded; structured facts never go through the model; review-before-fill, verify-after-fill; never auto-submits; limitations stated honestly (dead `RAGAnswerService`, multi-column OCR edge cases).

**Final summary line:** "Everything demonstrated reads from this repository's actual implementation — nothing here is a mockup built just for presenting."
