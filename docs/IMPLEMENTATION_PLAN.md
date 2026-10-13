# Implementation Plan

This plan is based on `docs/PROJECT_AUDIT.md`; finding IDs such as P0-1 refer to that document.
The status table at the end is updated as each phase finishes.

## Decisions log

| # | Decision | Reason |
|---|---|---|
| D1 | Personal files are removed from the working tree, but git history is **not** rewritten. `docs/SECURITY.md` gives the `git filter-repo` steps. | Owner's decision. Rewriting history is destructive. |
| D2 | The automated suite uses mock LLM providers. A separate opt-in test (`-m real_llm`, `RUN_REAL_LLM_TESTS=1`) calls Gemini with synthetic data only. | Owner's decision. Keeps cost and determinism under control. |
| D3 | One recommendation engine: a batch LangGraph pipeline. `/forms/sessions/{id}/analyze`, `/forms/recommend(ations)` and `/agent/run` all wrap it. | Owner's decision. Fixes duplication (P1-8). |
| D4 | Work goes on branch `feature/e2e-completion`, with one commit per phase and no push. | Owner's decision. |
| D5 | `PROCESSING_MODE=inline` (the default for local development) runs the pipeline as an in-process asyncio task. `celery` uses Redis plus a worker and is what Docker uses. | Redis is not required to run locally, and this removes the broken eager mode (P1-3). |
| D6 | The default embedding model is `all-MiniLM-L6-v2` (384 dimensions) everywhere. The vector collection records the model and dimension, and a mismatch is reported instead of producing silently wrong vectors. | Small download and CPU-friendly. Fixes P2 inconsistency. |
| D7 | PaddleOCR is optional (`requirements-ocr.txt`). Without it, scanned pages put the document in `requires_review` with an explicit message. | It is a very heavy dependency. Avoids garbage text (P1-13). |
| D8 | ChromaDB keeps its raw HTTP client and runs through Docker for local development. The in-memory fallback is removed. | Preserves the existing architecture and fixes P1-5. |
| D9 | The extension keeps Bearer JWT auth. The token lives only in extension storage, the background worker and the popup, and never in content scripts. | Fixes P0-6. |
| D10 | The dashboard keeps its token in `localStorage`, mitigated by a CSP and short expiry. | Switching to cookies would change the auth architecture shared with the extension. Residual risk is documented. |
| D11 | The extension injects its content script on demand (`activeTab` + `scripting`). Host permission covers only the backend origin. | Minimal permissions (P0-5). |
| D12 | A deterministic regex extraction track (the existing `CandidateFactExtractor`) runs alongside the LLM tracks. Facts record `origin` (`extracted`, `normalized` or `inferred`) and `extraction_method`. | Works without an LLM, and keeps explicit facts separate from inferred ones. |
| D13 | Conflicts are computed from active `structured_facts`; there is no separate conflict collection in the current write path. | Avoids maintaining a second source of truth; conflict resolution updates fact lifecycle state. |

## Required database changes

- `structured_facts`:
  - new fields: `origin`, `raw_value`, `evidence_text`, `extraction_method`, `status`;
  - `value` and `source_page` become optional when read back.
- `documents`: new fields `index_status`, `chunk_count`, `index_error`.
- `recommendations`:
  - upsert key `(user_id, session_id, field_id)`;
  - new fields `reason`, `source`, `requires_confirmation`, `candidates`, `fill_result`.
- `form_sessions`: `fill_results` and the verification counters.
- Indexes on `discovered_facts` and `user_memories`, plus a unique recommendation key `(user_id, session_id, field_id)`. There is no `discovered_conflicts` index because conflicts are derived from `structured_facts` (D13).
- Vector store: new collection `user_document_chunks_v2` (cosine distance, embedding model and dimension metadata). The old collection is left untouched; `python -m app.scripts.reindex` rebuilds the configured collection from processed source documents.

All schema changes are additive. Nothing existing is dropped.

## Required API changes

| Endpoint | Change |
|---|---|
| `GET /forms/sessions` | New: lists the user's form sessions (Activity page). |
| `POST /forms/sessions/{id}/verify` | Now persists fill results. Previously a stub. |
| Recommendation responses | Add `reason`, `source`, `requires_confirmation` and `candidates`. Status values are normalised to lowercase. |
| `PATCH /profile/facts/conflicts/{id}/resolve` | Also resolves structured-fact conflicts. |
| `/retrieval/rag/answer` | Returns 503 when the LLM fails, an "insufficient information" answer when retrieval finds nothing above the cutoff, and only the sources it cited. |
| `?token=` query parameter | Removed. Downloads and previews use a header-authenticated blob fetch. |
| `DELETE /auth/me`, `DELETE /profile/data` | Cascade across every user-owned store. |
| `GET /health/services` | Reports the real LLM, embedding and vector-store state. |

## Progress notes

- Phases 2–8 were implemented in commits `8ace0ed`, `45ab5a4`, `b1757b4`, `2d6ce47`, `11aa47c`, `cc7bdd7` and `05e5d2b`; the later LLM-safety change is `b7256c3`.
- Phase 3 cleanup found additional legacy user-specific fixtures and scripts that were still tracked. These were removed from the working tree during the remaining security work; history remains unchanged per D1.
- Phases 9–12 were completed in this worktree. Backend, frontend, extension, real-Chroma and Playwright results are recorded in `docs/TEST_RESULTS.md`.
- Acceptance rows below are marked complete only after the corresponding checks have been run.

## Phases and acceptance criteria

| Phase | Scope | Acceptance criteria |
|---|---|---|
| 1 | Audit and plan docs | `PROJECT_AUDIT`, `IMPLEMENTATION_PLAN` and `TESTING_STRATEGY` exist and are accurate. |
| 2 | Environment, config, startup and test isolation | The backend starts. The suite runs against a throwaway Mongo DB with a mock LLM and local storage. Config rejects weak secrets and unknown providers. |
| 3 | API and data integrity | Delete cascades, no `?token=`, account deletion works, CORS PATCH works, cross-user isolation is tested, stray personal data is removed. |
| 4 | Upload, extraction and profile | Synthetic PDF, DOCX and TXT produce facts with provenance in mock mode. A cross-document conflict is detected and resolvable. A corrupted PDF ends `failed` with a clear message. |
| 5 | Embeddings, Chroma and RAG | Real-Chroma tests pass. User isolation holds. No stale chunks after reprocess or delete. An empty or low-similarity result gives an "insufficient" answer. |
| 6 | Batch semantic pipeline | Varied labels map correctly. The LLM is called only for ambiguous fields. Invalid JSON gives `error`. Conflicting values go to review. Nothing is fabricated. |
| 7 | Extension | Minimal manifest. Sensitive fields are never read. Backend URL is configurable, with timeouts. Review, edit and approve, then fill, then verify. Never auto-submits. |
| 8 | Dashboard | No static demo data. `tsc` is clean. Fact review, conflicts, memories and RAG panel all work. |
| 9 | Security sweep | `SECURITY.md` is written. Log redaction, rate limits, CSP and compose secret hygiene are in place. |
| 10 | Tests and E2E | Backend, frontend and extension suites are green. Playwright E2E passes against the real backend. Results are in `TEST_RESULTS.md`. |
| 11 | Docker and reproducibility | Compose dev and test stacks are separated. Images contain no dev or debug files. |
| 12 | Documentation | README, `DATABASE_SCHEMA`, `API_REFERENCE`, `SECURITY` and `TEST_RESULTS` match the code. |

## Status

| Phase | Status | Notes |
|---|---|---|
| 0 Baseline | done | Pending working-tree changes committed as `a03f513`. |
| 1 Docs | done | |
| 2 Environment | done | `8ace0ed`: strict config, providers and isolated test settings. |
| 3 API and data | done | `45ab5a4` plus working-tree cleanup: auth, ownership, deletion, query-token removal and CORS. |
| 4 Extraction | done | `b1757b4`: deterministic/LLM extraction, provenance and review states. |
| 5 RAG | done | `b1757b4`: Chroma HTTP client, user scoping and grounded answer behavior; dimension metadata/reindex completed in this round. |
| 6 Semantic pipeline | done | `2d6ce47` and `b7256c3`: shared batch graph and prompt-safety filtering. |
| 7 Extension | done | `11aa47c`: on-demand permissions, private token handling and review-before-fill. |
| 8 Dashboard | done | `05e5d2b`: live data, profile review, conflicts, memories and Q&A. |
| 9 Security | done | Security guide, log redaction, Compose secret fail-fast, CSP configuration and removal of tracked personal fixtures/scripts. |
| 10 Tests | done | `docs/TEST_RESULTS.md`: backend 146 passed, frontend 22, extension 24, Chroma 3, Playwright 1; CI waits for Chroma readiness. |
| 11 Docker | done | Dev/test Compose configs validate; isolated images built and the full browser flow passed. |
| 12 Docs | done | README, API/database/security guides, testing strategy and results align with the implementation. |
