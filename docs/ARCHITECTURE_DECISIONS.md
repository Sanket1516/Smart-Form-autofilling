# Architecture decisions

These decisions describe the implemented system. The original product specifications remain unchanged in `docs/specifications/` and `Specifications/`.

| ID | Decision | Reason |
|---|---|---|
| AD-001 | MongoDB `structured_facts` is the provenance-preserving fact store; the profile and conflict views are computed from active facts. | Keeps source values and verification state without a second canonical profile store. |
| AD-002 | `/forms/sessions/{id}/analyze`, `/forms/recommend(ations)` and `/agent/run` use one batch LangGraph pipeline. | Avoids separate recommendation behavior across clients. |
| AD-003 | Local API development defaults to `PROCESSING_MODE=inline`; Compose uses Celery with Redis and a worker. | Local work does not require a queue, while Docker processing survives API request completion. |
| AD-004 | `all-MiniLM-L6-v2` at 384 dimensions is the default embedding model. Chroma collection metadata records the model and configured dimension. | Provides a small CPU-friendly default and makes model/dimension mismatches visible. |
| AD-005 | Chroma is accessed through its raw HTTP v2 API. Unavailability raises an error; there is no in-memory vector fallback. | Retrieval and deletion must not silently diverge across API processes. |
| AD-006 | The application writes to `user_document_chunks_v2`; reindexing processes source documents into the configured collection and leaves other collections untouched. | Supports rebuilding and checking a replacement index before retiring an older one. |
| AD-007 | The automated suite uses the mock LLM and synthetic data. Real-provider tests are opt-in. | Keeps default runs deterministic and avoids unexpected API costs or real user data. |
| AD-008 | PaddleOCR is optional. Scanned documents that cannot be read without OCR enter `requires_review`. | Avoids a heavyweight dependency and avoids treating unreadable pages as facts. |
| AD-009 | Authentication uses bearer JWTs in the `Authorization` header. Extension tokens stay in extension storage/popup/background; they never enter the page content script. | Supports the dashboard and extension clients while keeping credentials out of untrusted page scripts. |
| AD-010 | The dashboard stores its token in `localStorage`, protected by a restrictive production CSP and short token expiry. | Preserves the existing shared authentication architecture; the residual XSS risk is documented in `SECURITY.md`. |
| AD-011 | The extension requests page access on demand with `activeTab` and `scripting`; its default host permission is limited to the backend origin. | Reduces default access to unrelated sites. |
| AD-012 | Personal files are removed from the current tree but Git history is not rewritten. | Rewriting commit history is disruptive; the coordinated cleanup procedure is documented in `SECURITY.md`. |
| AD-013 | Conflict lists are derived from active `structured_facts`; the application does not persist a separate conflict collection. | Keeps resolution state on the candidate facts and avoids a duplicate source of truth. |
| AD-014 | Only synthetic PDFs, DOCX and text are used in automated tests; generated fixtures are not checked in. | Keeps test data reproducible and prevents personal files from entering the repository. |
