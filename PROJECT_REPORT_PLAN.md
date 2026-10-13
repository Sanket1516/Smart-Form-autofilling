# Project Report Plan

## 1. College Requirements Extracted

### Formatting (from `report-requirements/Report Writing Instructions.pdf`)

| Rule | Specification |
|---|---|
| Font | Times New Roman throughout |
| Body text size | 12 pt |
| Chapter title size | 24 pt |
| Line spacing | 1.5 |
| Page margins | Left 1.5", Right 1.0", Top 1.0", Bottom 1.0" |
| Main Headings | UPPER CASE, 12 pt |
| Sub-headings | Title Case, 12 pt |
| Sub-heading numbering | 1. MAIN → i. Sub → First Sub-Sub / Second Sub-Sub |
| Reference format (journal) | [N] Author1, Author2, "Title", Conference, Year, ISBN, Vol, Page |
| Reference format (book) | [N] Author, Title, Edition, Chapter, Pages, Publisher, Location, Year |
| Binding | Hard bound – Black Book, N+1 copies |
| Page numbering | Roman numerals for front matter; decimal from Chapter 1 onward |
| Chapter rule | Every chapter must have an introduction paragraph and a summary |
| Conclusion | One chapter at the end, not distributed |
| Appendices | Numbered in Roman Capitals (Appendix I, II …) |

### Required Chapter Structure (from Report Writing Instructions.pdf)

1. **First Page** (cover)
2. **Certificate**
3. **Certificate of Approval**
4. **Declaration**
5. **Acknowledgement**
6. **Abstract** (≈ 1 page)
7. **Table of Contents**
8. **List of Figures**
9. **List of Tables**
10. **Chapter 1 — Introduction**
11. **Chapter 2 — Literature Survey**
12. **Chapter 3 — Problem Definition & Proposed Solution**
13. **Chapter 4 — Design**
14. **Chapter 5 — Result Analysis: Snapshots**
15. **Chapter 6 — Testing**
16. **Chapter 7 — Conclusion & Future Work**
17. **References**
18. **Appendices**

### Confirmed Chapter Structure

**✓ Approved:** 7-chapter structure from the Instructions PDF. Advantages, limitations, and applications are incorporated into relevant chapters (no separate chapter):
- **Advantages** → Chapter 3 §3.3 (Proposed Solution Overview) and Chapter 7 §7.1 (Conclusion)
- **Limitations** → Chapter 3 §3.2 (Challenges) and Chapter 7 §7.2 (Future Work)
- **Applications** → Chapter 1 §1.2 (Motivation and Scope) and Chapter 3 §3.3

---

## 2. Project Identity

| Field | Value |
|---|---|
| Full title | Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms |
| Short name | Smart Form Auto-Filling System |
| Team members | Ashmit Patil (E246, 70552300048), Sanket Mali (E265, 70552300067), Pinak Salunke (E247, 70552300049) |
| Guide | Dr. Nitin Choubey, Professor in Computer Science |
| HoD | Dr. Nitin S. Choubey, Professor & Head, Computer Science Department ⚠ confirm before submission |
| Associate Dean | Dr. Venkatadri Marriboyina, Associate Dean, Shirpur Campus ⚠ confirm before submission |
| Department | Computer Science |
| Institution | Mukesh Patel School of Technology Management & Engineering (MPSTME), Shirpur Campus, SVKM's NMIMS |
| Academic session | 2026–27 |
| Branch | feature/e2e-completion (git) |

---

## 3. What Is Implemented

All features below are verified by passing tests (`docs/TEST_RESULTS.md`, 15 git commits).

### Backend (Python 3.11, FastAPI)
- JWT authentication with token revocation, bcrypt passwords, rate limiting (slowapi)
- Document upload: PDF (pdfplumber + pypdfium2), DOCX (python-docx), TXT, images (Pillow/OpenCV)
- **Deterministic extraction track**: regex/label patterns from a 300+-concept YAML ontology (email, phone, DOB, postal, named fields)
- **LLM extraction track**: Gemini/OpenAI/Anthropic via raw httpx, JSON mode; mock provider for tests
- Fact provenance: `origin` (extracted / normalized / inferred), `raw_value`, `evidence_text`, `confidence`, `source_page`
- Cross-document conflict detection (computed from active facts, not a separate collection)
- **8-node LangGraph batch pipeline** (sanitize → deterministic_classify → llm_classify → resolve_profile → resolve_documents → decide → persist)
- RAG: ChromaDB HTTP v2, `all-MiniLM-L6-v2` 384-dim embeddings, cosine similarity, grounded answers with citations
- Prompt-injection defence: `<UNTRUSTED_DOCUMENT>` tags + pattern detection filter before LLM calls
- Celery/Redis task queue (Docker) and inline asyncio mode (local dev)
- Structured JSON logging with redaction (tokens, emails, long digit runs)
- Full deletion cascade: vectors → facts → files; 503 before MongoDB on Chroma failure

### Dashboard (React 19, TypeScript, Vite)
- 11 pages: Login, Register, Dashboard, Documents, Profile, Conflicts, DiscoveredFacts, Reviews, Activity, Ask (RAG Q&A), Settings
- Typed API client with global 401 handler; previews/downloads via header-authenticated blobs (no `?token=`)
- nginx production config with CSP, security headers, and template-rendered API origin

### Chrome Extension (Manifest V3, Vite)
- On-demand field extraction (`activeTab` + `scripting`; no always-on content script)
- Sensitive field skip: password, payment, OTP, CAPTCHA, hidden, off-screen, honeypot
- Stable field IDs; per-tab flow state in `chrome.storage.session`
- Review-before-fill popup; never auto-submits; JWT never reaches the content script

### Tests
| Suite | Count | Method |
|---|---|---|
| Backend pytest (mock LLM + in-memory store) | 146 passed | `python -m pytest` |
| Real ChromaDB integration | 3 passed | `-m chroma` marker |
| Frontend Vitest | 22 passed | `npm --prefix frontend test` |
| Extension Vitest | 24 passed | `npm --prefix extension test` |
| Playwright browser E2E | 1 passed | Real Chromium + isolated Compose stack |

---

## 4. What Is Optional / Partially Configured

| Feature | Status | Notes |
|---|---|---|
| PaddleOCR | Optional | `INSTALL_OCR=true` in `.env`; without it, scanned docs → `requires_review` |
| Real LLM provider | Opt-in | `LLM_PROVIDER=google/openai/anthropic` + key; default is `mock` |
| Cloudinary storage | Opt-in | `STORAGE_PROVIDER=cloudinary`; default is local filesystem |
| Celery/Redis | Docker only | `docker compose up` enables it; local dev uses inline asyncio |

---

## 5. Available Evidence for the Report

| Evidence type | Available | Location |
|---|---|---|
| Test results summary | ✓ | `docs/TEST_RESULTS.md` |
| SRS / requirements | ✓ | `docs/specifications/SRS.md` |
| System architecture description | ✓ | `docs/specifications/SYSTEM_ARCHITECTURE.md` |
| API reference | ✓ | `docs/API_REFERENCE.md` |
| Database schema | ✓ | `docs/DATABASE_SCHEMA.md` |
| Architecture decisions log | ✓ | `docs/ARCHITECTURE_DECISIONS.md` |
| Security documentation | ✓ | `docs/SECURITY.md` |
| Implementation plan + phase status | ✓ | `docs/IMPLEMENTATION_PLAN.md` |
| Project audit (findings) | ✓ | `docs/PROJECT_AUDIT.md` |
| Ontology (300+ concepts) | ✓ | `backend/app/ontology/field_ontology.yaml` |
| Git history (15 commits) | ✓ | `git log --oneline` |
| ASCII architecture diagram | ✓ | `docs/specifications/SYSTEM_ARCHITECTURE.md` |
| UI screenshots | **✗ Missing** | Must be taken by running the application |
| Architecture diagram as image | **✗ Missing** | Only ASCII / text diagrams exist |
| Literature survey references | ⚠ Partial | 19 papers identified & peer-review verified; full citation strings (authors, pages, DOI) still needed |
| Full enrollment numbers | ✓ Confirmed | Ashmit Patil 70552300048 · Sanket Mali 70552300067 · Pinak Salunke 70552300049 |
| Guide's full designation | ✓ Confirmed | Dr. Nitin Choubey, Professor in Computer Science |

---

## 6. Missing Information Required Before Writing

1. **UI screenshots** — run the dashboard and extension, capture: Login, Dashboard, Documents (upload + status), Profile (facts), Conflicts resolution, Reviews, Ask (RAG answer), Extension popup (scan, review, fill, done).
2. **System architecture diagram as a PNG/SVG** — draw from the ASCII diagram in `SYSTEM_ARCHITECTURE.md` or export from a tool (draw.io, Mermaid).
3. **15+ literature survey references** — research papers on: web-form autofill, RAG, LangGraph/agent frameworks, document NLP/IE, prompt injection defences, browser extensions, privacy-preserving AI.
4. **Full enrollment numbers** for each team member (12-digit format used by NMIMS).
5. **Dr. Nitin Choubey's designation** (e.g., "Assistant Professor, Computer Science Department").
6. **Declaration page** — standard college-format declaration signed by students.
7. **HoD name** (for the certificate and acknowledgement pages).
8. **Associate Dean name** (for the acknowledgement).
9. ~~**Confirmation of chapter structure**~~ — ✓ Resolved: 7 chapters per Instructions PDF; advantages/limitations/applications folded into existing chapters.

---

## 7. Proposed Chapter-by-Chapter Outline

*(Following the Instructions PDF structure: 7 chapters. Titles below are those specified in the Instructions; font, size and spacing per the formatting rules above.)*

---

### Front Matter (Roman numeral pages)

| Page | Content |
|---|---|
| Cover (i) | Title, degree, institution, team, guide, academic session — per template |
| Certificate (ii) | Faculty certification — per template |
| Certificate of Approval (iii) | Examiner approval — per template |
| Declaration (iv) | Standard student declaration |
| Acknowledgement (v) | Guide, HoD, Dean, faculty, colleagues — per template |
| Abstract (vi) | Problem, approach, key results; ≈ 1 page |
| Table of Contents (vii) | Auto-generated with page numbers in Roman for front matter |
| List of Figures (viii) | All screenshots and diagrams |
| List of Tables (ix) | All data and comparison tables |

---

### Chapter 1 — Introduction

1.1 Background of the Project Topic
- Rise of digital forms across government, banking, education and employment portals.
- Limitation of browser-native autofill: no document intelligence, no provenance, no conflict handling.
- Opportunity for an AI-assisted, privacy-first approach.

1.2 Motivation and Scope
- User pain of re-entering the same information across forms.
- Privacy risks of existing autofill tools that read all fields indiscriminately.
- Scope: document upload → fact extraction → semantic form matching → user review → fill.

1.3 Problem Statement
- No existing open-source solution combines document extraction, ontology-based semantic matching, conflict resolution and review-before-fill in a single deployable system.

1.4 Salient Contributions
- 300+-concept YAML ontology covering personal, identity, address, contact, education, experience, financial and medical domains.
- Dual-track extraction (deterministic + optional LLM) with fact provenance.
- 8-node LangGraph batch pipeline with prompt-injection defence.
- Manifest V3 Chrome extension with on-demand permissions and human-in-the-loop review.
- 195 automated tests across backend, frontend and browser E2E.

1.5 Organisation of Report
- Summary of subsequent chapters.

---

### Chapter 2 — Literature Survey

2.1 Introduction to Automatic Form Filling and Information Extraction
- Background from ≥ 15 references covering:
  - Browser autofill (Chrome, Firefox baseline behaviour)
  - Named entity recognition (NER) and information extraction from documents
  - Retrieval-Augmented Generation (RAG) for document Q&A
  - LangGraph / LangChain agent orchestration frameworks
  - Prompt injection attacks and defences
  - Privacy-preserving AI systems and human-in-the-loop design
  - Web form understanding / semantic field classification

2.2 Exhaustive Literature Survey (≥ 10 journal/conference papers)
- Each entry: paper, publication, year, key finding, gap it leaves.

2.3 Summary of Gaps Leading to the Problem Statement
- No unified tool covers document intelligence + ontology matching + conflict resolution + privacy-safe browser fill.

---

### Chapter 3 — Problem Definition & Proposed Solution

3.1 Problem Statement (formal)
3.2 Challenges
- Heterogeneous form structures; no standard label vocabulary.
- Multiple conflicting values from different documents.
- Risk of LLM hallucination / prompt injection.
- Browser security model constraints (Manifest V3).

3.3 Proposed Solution Overview
- Architecture diagram (image to be created from `SYSTEM_ARCHITECTURE.md`).
- Two-sided pipeline: Document Preparation Side + Web Form Processing Side.

3.4 Technology Choices and Justification
- FastAPI, MongoDB, ChromaDB, LangGraph, all-MiniLM-L6-v2, React, MV3 — cite architecture decision records.

3.5 Workflow Summary
- Upload → parse → extract → index → session → detect → classify → resolve → review → fill → verify.

---

### Chapter 4 — Design

4.1 Block Diagram and High-Level Architecture
- Reproduce the two-sided diagram from `SYSTEM_ARCHITECTURE.md` as a figure.

4.2 Hardware Description
- Minimum local dev requirements; Docker Desktop, MongoDB, ChromaDB.

4.3 Software Description

4.3.1 Backend Modules
- `core/config.py`: validated settings, secret enforcement.
- `processing/pipeline.py`: parse → deterministic extraction → LLM extraction → merge → index.
- `agents/graph.py`: the 8-node LangGraph StateGraph (sanitize, deterministic_classify, llm_classify, resolve_profile, resolve_documents, decide, persist).
- `services/facts.py`: conflict computation, provenance, resolution.
- `db/chroma_client.py`: raw HTTP v2, user-scoped queries, model/dimension validation.

4.3.2 Ontology
- YAML structure, concept hierarchy, alias matching, sensitive concept flag.
- Sample from `field_ontology.yaml`.

4.3.3 Dashboard (React)
- Component map: AuthContext → pages (Login, Dashboard, Documents, Profile, Conflicts, Reviews, Activity, Ask, Settings).
- Shared API client with typed envelope parsing and 401 event.

4.3.4 Chrome Extension (MV3)
- `manifest.json` permissions model.
- Content script injection flow (`SFA_PING → SFA_EXTRACT → SFA_FILL`).
- AutofillFlow state machine (idle → scanned → analyzing → review → filling → done).

4.3.5 Database Schema
- MongoDB collections table (from `docs/DATABASE_SCHEMA.md`).
- ChromaDB collection metadata and chunk fields.

4.4 Flowchart / Algorithm
- Document processing pipeline flowchart.
- Form-filling pipeline flowchart (LangGraph nodes).

---

### Chapter 5 — Result Analysis: Snapshots

5.1 User Registration and Login
- Screenshot: Registration form → Dashboard redirect.

5.2 Document Upload and Processing
- Screenshot: Upload drag-and-drop → processing status → "Searchable".

5.3 Extracted Facts with Provenance
- Screenshot: Profile page showing origin pills, confidence, evidence text, source document.

5.4 Conflict Detection and Resolution
- Screenshot: Conflicts page with two candidates from different documents → resolution form.

5.5 Form Session and Semantic Classification
- Screenshot: Extension popup scan (field list, sensitive fields skipped) → analysing.

5.6 Review and Approve Before Fill
- Screenshot: Extension review list with source, confidence, reason → "Fill approved fields".

5.7 Fill Result Verification
- Screenshot: Sample form with fields filled → DOM verified tick marks.

5.8 RAG Document Q&A
- Screenshot: Ask page with answer and cited source snippet.

5.9 Service Health Dashboard
- Screenshot: Settings page with live system status.

---

### Chapter 6 — Testing

6.1 Testing Strategy
- Summary of three test layers (mock, real-service, real-provider) from `docs/TESTING_STRATEGY.md`.

6.2 Unit and Integration Tests (Backend)
- Tool: pytest; 146 passed.
- Coverage areas: auth, upload validation, extraction, conflicts, RAG, pipeline, API errors, deletion cascade, cross-user isolation.
- Table: test file → scope → count.

6.3 Frontend Tests
- Tool: Vitest + Testing Library; 22 passed.
- Coverage: Login/Register, upload, status polling, profile edit, conflict resolution, review decisions, API failure states.

6.4 Extension Unit Tests
- Tool: Vitest; 24 passed.
- Coverage: detector (sensitive skip, stable IDs), autofill (select, checkbox, radio, date), API client (timeout, 401, retry).

6.5 Real ChromaDB Integration
- 3 tests against the Compose Chroma service with real embeddings; user isolation, similarity cutoff, model mismatch detection.

6.6 Browser E2E (Playwright)
- 1 test passed; real Chromium, isolated Compose stack, mock LLM.
- Scenario: register → upload synthetic résumé → scan form → review → fill → verify DOM → no submission.

6.7 Test Results Summary
- Reproduce the results table from `docs/TEST_RESULTS.md`.

6.8 Security Testing Notes
- Log redaction verification, prompt-injection quarantine test, rate-limit test.

---

### Chapter 7 — Conclusion & Future Work

7.1 Conclusion
- The system achieves privacy-first, document-driven form filling with human-in-the-loop review across a desktop dashboard and a Chrome extension.
- All 195 automated tests pass; the Playwright browser E2E confirms the end-to-end flow.
- Key contributions: unified ontology, dual-track extraction with provenance, LangGraph batch pipeline, injection-safe RAG, MV3 extension.

7.2 Future Work
- OCR integration (PaddleOCR) for scanned documents.
- Firefox extension port.
- Mobile companion app.
- Support for dynamic forms with JavaScript-rendered fields.
- Multi-language ontology.
- Federated / on-device embedding models for stronger privacy.
- Automated literature-based ontology expansion.

---

### References

19 papers identified and peer-review verified (all KEEP). Full citation strings (authors, full title, volume, pages, DOI/ISBN) required before typesetting.

| [N] | Short name | Year | Venue | Status |
|---|---|---|---|---|
| [1] | WebArena | 2024 | ICLR | ⚠ full citation needed |
| [2] | Mind2Web | 2023 | NeurIPS D&B | ⚠ full citation needed |
| [3] | GPT-4V(ision) / SeeAct | 2024 | ICML | ⚠ full citation needed |
| [4] | WebVoyager | 2024 | ACL | ⚠ full citation needed |
| [5] | CogAgent | 2024 | CVPR | ⚠ full citation needed |
| [6] | SeeClick | 2024 | ACL | ⚠ full citation needed |
| [7] | Ferret-UI | 2024 | ECCV | ⚠ full citation needed |
| [8] | WorkArena | 2024 | ICML / PMLR | ⚠ full citation needed |
| [9] | LCoW | 2025 | ICLR | ⚠ full citation needed |
| [10] | GUI Agents: A Survey | 2025 | Findings of ACL | ⚠ full citation needed |
| [11] | LLM-based Autonomous Agents Survey | 2024 | Frontiers of Computer Science | ⚠ full citation needed |
| [12] | LLMs + Knowledge Graphs: A Roadmap | 2024 | IEEE TKDE | ⚠ full citation needed |
| [13] | HippoRAG | 2024 | NeurIPS | ⚠ full citation needed |
| [14] | Memory Mechanism of LLM Agents | 2025 | ACM TOIS | ⚠ full citation needed |
| [15] | Form Understanding in Scanned Documents | 2024 | Artificial Intelligence Review | ⚠ full citation needed |
| [16] | Leaky Autofill | 2024 | ACSAC | ⚠ full citation needed |
| [17] | FormLM | 2022 | EMNLP | ⚠ full citation needed |
| [18] | Automated Filling of Categorical Fields (LAFF) | 2023 | ACM TOSEM | ⚠ full citation needed |
| [19] | FormNexus / Semantic Constraint Inference | 2024 | ACM ISSTA | ⚠ full citation needed |

---

### Appendices

| Appendix | Content |
|---|---|
| Appendix I | Sample source code (key files: `agents/graph.py`, `processing/pipeline.py`, `content/detector.ts`) |
| Appendix II | Ontology excerpt (`field_ontology.yaml`, first 50 concepts) |
| Appendix III | `.env.example` configuration reference |
| Appendix IV | List of papers presented and published (if any) |

---

## 8. Action Items Before Writing Begins

| # | Item | Status | Owner |
|---|---|---|---|
| 1 | Chapter structure (7 chapters, Instructions PDF) | ✓ Done | — |
| 2 | Full 12-digit enrollment numbers for all three team members | ✓ Done | — |
| 3 | Dr. Nitin Choubey's full designation (title, department, post) | ✓ Done | — |
| 4 | HoD's name and Associate Dean's name for acknowledgement | ⚠ Provisional — confirm before submission | Team |
| 5 | UI screenshots (Login, Dashboard, Documents, Profile, Conflicts, Extension popup, Ask, Settings) | ⬜ Pending | Team |
| 6 | System architecture diagram as PNG or SVG | ⬜ Pending | Team |
| 7 | ≥ 15 literature references — 19 papers identified & verified | ⚠ Full citations (authors, pages, DOI) needed | Team |
| 8 | Paper presentation/publication details for Appendix IV (if any) | ⬜ Pending | Team |
