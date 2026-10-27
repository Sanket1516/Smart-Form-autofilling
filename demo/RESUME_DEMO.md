# Resume-and-form demo

A fictional graduate applicant (**Aarav Sharma**, all data invented and labelled `DEMO DATA`), a two-page resume PDF, and a
34-field "Graduate Software Engineer — Application Form". It shows, on the real pipeline, which answers come from **stored
facts** (no text generation), which are **written from retrieved resume text**, and which are **left empty because the resume
does not say**.

It is separate from the 15-document judge demo: its own account (`demo.resume@example.com`), its own file prefix
(`DEMO_RESUME_`) and its own folder, so the judge evaluation is unaffected.

## Start it

```powershell
docker compose up -d                                  # backend, worker, MongoDB, ChromaDB, Redis, frontend
docker compose build backend worker; docker compose up -d backend worker   # only after backend code changes
python -m demo.cli resume generate                    # optional: rebuild the PDF (a copy is already committed)
```

**In the dashboard** (http://localhost:5173, sign in with a *demo* account): sidebar → **Resume demo**.

1. **Load demo resume** — uploads the PDF through the normal documents API (text extraction, fact extraction, chunking, vector index).
2. Wait for steps 1–3 to read *Done* (**Initialize knowledge repository** re-runs processing if needed).
3. **Open demo form** — opens the form in its own tab (allow pop-ups once).
4. **Analyze form** — reads the 34 fields and classifies each (category, concept, rule- or AI-classified).
5. **Generate suggested answers** — runs the real form-fill graph; each field shows its category, the retrieved evidence with
   document and page, an evidence label, and an editable answer with a "Use this answer" tick.
6. **Fill the form** fills the form tab with the ticked answers (never the declaration, never Submit). **Clear all demo fields**
   empties it again; **Reset demo** clears the analysis; **Remove demo resume** deletes only `DEMO_RESUME_…` files.

**With the Chrome extension** (the real automation path): open
`http://localhost:5173/demo/resume/graduate-software-engineer-application.html`, click the Smart Form extension → *Analyze this
form* → review → *Fill*. The extension reads the same fields and calls the same backend. Submitting is always yours; the page
shows a local success screen and sends nothing.

**From the command line** (a separate account, no browser):

```powershell
python -m demo.cli resume load      # create demo.resume@example.com, upload + process the resume
python -m demo.cli resume check     # run the 34-field form through the real API and print category, mode, evidence per field
python -m demo.cli resume status
python -m demo.cli resume cleanup [--delete-account]
```

## How a field is answered

```
Resume PDF → text extraction (OCR only if scanned) → fact extraction (LLM, validated) → MongoDB structured facts
                                   └→ chunking → embeddings → ChromaDB                  (existing pipeline, unchanged)

Form field → classification:  ontology alias match on label / placeholder / name / id / section / input type  (no LLM)
                              └ ambiguous or unknown → one batched LLM classification call
          → structured concept?  value from the stored fact, copied, no generation            → High Evidence
          → open question?       search the resume's chunks for this question; the model writes a short first-person answer
                                 and must quote the passage; an answer whose quote is not in the retrieved text is discarded
                                                                                              → Partial Evidence (needs your tick)
          → nothing supports it  field stays empty, "No relevant information was found"       → Insufficient Evidence
```

* **Concepts** for this form live in `backend/app/ontology/candidate_ontology.yaml`. Open-question concepts carry
  `answer_only: true`: they are classified like any field but are never stored as profile facts, so they cannot be answered
  from a summary written at upload time.
* **No percentages**: evidence labels follow the documented rules (see the "How the evidence labels are decided" panel).
* **Conflicts**: two stored values for one field are never merged silently; the field goes to review with both candidates.
* **Cloud-computing question**: classified to its own open-question concept (`cloud.summary`), not to the tool-list concept
  that "Docker" would satisfy, so listing Docker never becomes a claim of cloud experience.

## Tests

| Layer | Command | Covers |
|---|---|---|
| Ontology and classification | `cd backend; python -m pytest tests/test_resume_demo.py -m "not mongo"` | all 33 form fields map to the intended concept without an LLM; open questions are prose and not extractable; similar questions map together; strengths ≠ weaknesses; cloud ≠ tool list; no alias collisions; the 15 judge forms classify exactly as before |
| Pipeline (real MongoDB, mock LLM) | `cd backend; python -m pytest tests/test_resume_demo.py -m mongo` (needs `docker-compose.test.yml` services) | open questions are grounded in retrieved text; unsupported claims and null answers stay empty |
| Frontend | `cd frontend; npx vitest run` | form reading, categories, evidence labels, fill/clear, and the demo page flow end to end with mocked API |
| Browser + live backend | `cd extension; npx playwright test -c playwright.resume.config.ts` (after `npm run build`, `resume load`) | the real extension analyses, pre-selects structured fields, leaves open questions for a tick, fills the DOM, never submits |

## Limits

* **Multi-select controls** are not supported end to end (the backend proposes one option and the extension fills one). The
  form uses single selects, text boxes and textareas for skills; comma-separated text is how the resume lists them.
* The model is an external service. If it is unavailable, factual fields still fill from stored facts, but open questions stay
  empty with "The AI provider is unavailable". Re-run when it is back.
* The dashboard's *Fill the form* works on the form tab opened from the dashboard (same origin). The app's security headers
  forbid embedding the form in a frame, so it is not previewed inside the page.

## Files

New: `demo/resume_profile.py`, `demo/resume_gen.py`, `demo/resume_demo.py`, `demo/RESUME_DEMO.md`,
`frontend/public/demo/resume/` (PDF, form, `resume-form.js`), `backend/app/ontology/candidate_ontology.yaml`,
`backend/tests/test_resume_demo.py`, `frontend/src/pages/ResumeDemo.tsx` + `.css`, `frontend/src/demo/resumeDemo.ts`,
`frontend/src/tests/resumeDemo.test.ts`, `frontend/src/tests/resumeDemoPage.test.tsx`,
`extension/tests/resume-demo.spec.ts`, `extension/playwright.resume.config.ts`.

Changed: `backend/app/ontology/loader.py` (`answer_only`), `backend/app/ontology/field_ontology.yaml` (include),
`backend/app/extraction/llm_extraction.py` (answer-only concepts are not extracted as facts), `demo/cli.py` (`resume` command),
`demo/client.py` and `demo/loader.py` (optional account name / file list), `frontend/src/services/api.ts` (form-session calls),
`frontend/src/App.tsx` and `components/layout/Sidebar.tsx` (route and menu entry), `extension/playwright.config.ts` (ignore the live spec).
