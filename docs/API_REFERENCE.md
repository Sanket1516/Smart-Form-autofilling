# API reference

Base URL: `/api/v1`. FastAPI publishes the complete request/response schema at `/docs` and `/openapi.json` when the service is running. Unless marked public below, routes require `Authorization: Bearer <access_token>`. Tokens in query strings are not accepted.

Success responses use `{ "success": true, "data": ..., "message": "..." }` (some message-only routes use `{ "success": true, "message": "..." }`). Errors use `{ "success": false, "error": { "code": ..., "message": ..., "details": ... } }`. Validation errors do not echo submitted values.

## Health and authentication

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/health` | Public | API and Mongo readiness; returns 503 when Mongo is unavailable. |
| GET | `/health/services` | Public | Mongo, Chroma, LLM and embedding state and model details. |
| POST | `/register` | Public | Register with `full_name`, `email`, `password`, `confirm_password`. |
| POST | `/login` | Public | Exchange `email` and `password` for a bearer token. |
| GET | `/me` | Authenticated | Return the current public account. |
| POST | `/logout` | Authenticated | Revoke the current token. |
| DELETE | `/me` | Authenticated | Revoke the token and delete the account and owned data. |

## Documents and facts

| Method | Path | Purpose |
|---|---|---|
| POST | `/documents` | Upload one supported PDF, DOCX, TXT or image file as multipart field `file`. |
| GET | `/documents` | List documents; optional `status`, `document_type`, `page` and `limit` filters. |
| GET | `/documents/{document_id}` | Get a document and its processing/index status. |
| GET | `/documents/{document_id}/status` | Poll processing progress. |
| GET | `/documents/{document_id}/facts` | List facts extracted from one owned document. |
| POST | `/documents/{document_id}/process` | Queue/restart processing. |
| POST | `/documents/{document_id}/reprocess` | Reprocess and replace extracted facts and chunks. |
| GET | `/documents/{document_id}/download` | Download with bearer-header authentication. |
| GET | `/documents/{document_id}/preview` | Preview with bearer-header authentication and restrictive headers. |
| DELETE | `/documents/{document_id}` | Delete the document, extracted facts and vector chunks. |
| GET | `/profile/facts` | List active facts; optional `concept`, `source_document_id` and `confirmed` filters. |
| POST | `/profile/facts` | Add a user-confirmed ontology fact (`concept`, `value`). |
| PUT | `/profile/facts/{fact_id}` | Edit/confirm a fact. |
| DELETE | `/profile/facts/{fact_id}` | Delete a user fact or reject an extracted fact. |
| GET | `/profile/facts/conflicts` | Compute single-value conflicts from active facts. |
| PATCH | `/profile/facts/conflicts/{conflict_id}/resolve` | Resolve with a listed candidate, a custom value, or reject all candidates. |
| GET | `/profile/discovered-facts` | List all extracted attributes; optional `semantic_type`, `document_id`, `ontology`. |

## Profile, memories and reviews

| Method | Path | Purpose |
|---|---|---|
| GET | `/profile` | Aggregated profile with source/provenance details. |
| PUT | `/profile` | Update profile values by ontology concept. |
| GET | `/profile/concepts` | List fillable ontology concepts and metadata. |
| GET | `/profile/corrections` | List saved corrections; optional `concept`. |
| POST | `/corrections` | Record a correction. |
| DELETE | `/profile/data` | Delete documents, facts, vectors, sessions, memories and other user data; retain account. |
| GET | `/profile/memories` | List saved answers. |
| POST | `/profile/memories` | Save an answer after explicit user action. |
| DELETE | `/profile/memories/{memory_id}` | Delete a saved answer and its vector. |
| GET | `/reviews/pending` | List pending recommendations; optional `session_id`. |
| POST | `/reviews/{review_id}/decision` | Confirm, edit, reject or skip a pending result. |
| GET | `/recommendations/{recommendation_id}` | Read one recommendation. |

## Forms and recommendations

`FieldObject` contains field labels, accessible names, type, options and a `has_value` boolean. Clients do not send the current field value. The extension reviews recommendations and submits decisions before filling; it never submits the page.

| Method | Path | Purpose |
|---|---|---|
| POST | `/forms/classify-field` | Classify one field using deterministic rules and, if ambiguous, the LLM. |
| POST | `/forms/classify-fields` | Batch classification. |
| POST | `/forms/sessions` | Create a form session (`website_origin`, `page_url`, `form_id`). |
| GET | `/forms/sessions` | List the current user's sessions for the Activity view. |
| GET | `/forms/sessions/{session_id}` | Read session status and counters. |
| POST | `/forms/sessions/{session_id}/analyze` | Start batch analysis (202); poll recommendations. |
| GET | `/forms/sessions/{session_id}/recommendations` | Read results with `reason`, `source`, `requires_confirmation`, candidates and lowercase statuses. |
| POST | `/forms/sessions/{session_id}/decisions` | Approve, edit, reject or skip fields. |
| POST | `/forms/sessions/{session_id}/answers` | Provide values for missing fields; optional explicit save-for-future. |
| GET | `/forms/sessions/{session_id}/approved-values` | Read approved values for filling. |
| POST | `/forms/sessions/{session_id}/verify` | Persist per-field `applied`, `verified` and optional `reason`, then update counters. |
| POST | `/forms/sessions/{session_id}/complete` | Close the session as submitted, not submitted or cancelled. |
| POST | `/forms/recommend` | Synchronous single-field wrapper around the batch graph. |
| POST | `/forms/recommendations` | Synchronous batch wrapper around the same graph. |
| POST | `/agent/run` | Start batch analysis and return a `run_id`/`session_id` (202). |
| GET | `/agent/runs/{run_id}` | Read run/session status and recommendations. |

## Retrieval

| Method | Path | Purpose |
|---|---|---|
| POST | `/retrieval/rag` | Retrieve similar chunks from the authenticated user's documents; accepts `query`, `top_k` and optional document-type filter. |
| POST | `/retrieval/rag/answer` | Answer from above-cutoff evidence; returns `insufficient_evidence` when no adequate evidence exists and 503 when the LLM fails. Sources list only chunks cited by the answer. |
| POST | `/retrieval/structured` | Retrieve facts by ontology `concept`; optional `verified_only`. |

Login, registration, upload, document processing, field classification, recommendations and RAG have per-process rate limits. The exact route schemas, bounds and response types are available from the generated OpenAPI document.
