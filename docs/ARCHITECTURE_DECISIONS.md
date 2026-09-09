# Architecture Decisions

## AD-001 Source specification authority

- **Problem:** The request named `PRD.md` and `SRS.md`, but the workspace contains a PRD DOCX and detailed SRS Markdown file.
- **Selected option:** Preserve all files in `Specifications/` unchanged; the supplied PRD DOCX and detailed SRS are authoritative source artifacts.
- **Reason and impact:** Requirements stay immutable and traceable; implementation references actual filenames.
- **Related requirement:** SRS section 41 and project source-of-truth instruction.

## AD-002 Canonical fact lifecycle

- **Problem:** The SRS names extracted/profile facts while the database design defines `structured_facts` and `profiles`.
- **Options considered:** Duplicate fact stores; profile-only data; lifecycle metadata on structured facts.
- **Selected option:** Use `structured_facts` as the provenance-preserving store with candidate, verified, superseded, and disputed states; use `profiles` as a usable projection.
- **Reason and impact:** Preserves multiple candidates without competing canonical stores. No collections are created in Phase 1.
- **Related requirement:** SRS 9–10 and 22; Database Design 6–9.

## AD-003 Final agent response ordering

- **Problem:** Some diagrams place Final Response before review; the SRS/API also describe it as incorporating user decisions.
- **Selected option:** Final Response Node creates the final validated recommendation after conflict resolution and required HITL. Pre-HITL results are provisional.
- **Reason and impact:** Unapproved values cannot become fill-ready. The five mandatory nodes remain unchanged.
- **Related requirement:** SRS 17–19 and 30; API Specification 31–35.

## AD-004 Background processing boundary

- **Problem:** Long work is asynchronous, but no worker technology is specified.
- **Selected option:** Keep one FastAPI service with future processing-service boundaries; defer durable queue selection until document processing.
- **Reason and impact:** Avoids unnecessary microservices. Phase 1 Compose includes only frontend, backend, MongoDB, and ChromaDB.
- **Related requirement:** SRS 26 and 35; API Specification 54.

## AD-005 Visual context scope

- **Problem:** Visual context is optional but appears in future evaluation variants.
- **Selected option:** Treat screenshots as optional future enrichment; begin future Field Objects with DOM and accessibility context.
- **Reason and impact:** No screenshot permissions, capture, or analysis is claimed in Phase 1.
- **Related requirement:** SRS 11 and 33; System Architecture 13.

## AD-006 Authentication direction

- **Problem:** Bearer authentication and logout invalidation are required but the mechanism is unspecified.
- **Selected option:** Implement configurable JWT bearer auth with server-side invalidation support in the authentication phase.
- **Reason and impact:** Supports the documented contract and extension compatibility. No auth code exists in Phase 1.
- **Related requirement:** SRS 6 and 27; API Specification 5 and 8–11.

## AD-007 Configuration and providers

- **Problem:** LLM, embedding, security, and deployment settings require configuration but no provider/model is selected.
- **Selected option:** Use environment-only configuration and provider-neutral boundaries.
- **Reason and impact:** No secrets, provider, model, or AI service is hard-coded or initialized in Phase 1.
- **Related requirement:** SRS 24, 26, 27, and 35.

## AD-008 Document storage and retention

- **Problem:** Requirements contain a document storage reference but no provider or retention policy.
- **Selected option:** Defer original-document storage and retention policy to Document Management while retaining an abstraction boundary.
- **Reason and impact:** No storage provider, upload endpoint, or original document handling is invented in Phase 1.
- **Related requirement:** SRS 7 and 27; Database Design 7 and 28.

