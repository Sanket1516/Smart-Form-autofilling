# Database schema

MongoDB is the source of truth for users, documents, extracted facts and workflow state. Most user-owned records contain `user_id`; repository queries and deletes include this owner key. Mongo `_id` values are ObjectIds for accounts, documents and structured facts, and strings for recommendation IDs and user-memory IDs. Timestamps are UTC.

## MongoDB collections

| Collection | Purpose and principal fields |
|---|---|
| `users` | `full_name`, unique `email`, `password_hash`, `status`, `created_at`, `updated_at`, optional `last_login_at`. Public APIs never return `password_hash`. |
| `documents` | `user_id`, `file_name`, `file_type`, `file_size`, `storage_reference`, optional `document_type` and `language`, processing `status`, upload/process timestamps, `checksum`, `current_stage`, `progress`, `processing_error`, `warnings`, `normalized_reference`, `page_count`, `fact_count`, `index_status`, `chunk_count`, `index_error`. |
| `structured_facts` | One sourced value per record: `user_id`, ontology `concept`, normalized `value`, `raw_value`, `value_type`, `origin`, `status`, `source_document_id`, optional `document_name`, `source_page`, `evidence_text`, `extraction_method`, `confidence`, `provenance`, `is_user_confirmed`, timestamps. `source_document_id="user"` identifies a value supplied by the user. |
| `discovered_facts` | Extractor output, including unmapped values: owner/document IDs, optional page/entity/ontology/document type, `field`, `semantic_type`, `value`, `data_type`, `confidence`, `evidence_text`, `origin`, `extraction_method`, timestamps. |
| `recommendations` | One result per user/session/field: `user_id`, `session_id`, `field_id`, field description, ontology `concept`, `recommended_value`, lowercase `status`, `confidence`, `reason`, `source`, `requires_confirmation`, `candidates`, option data, provenance and optional `fill_result`, timestamps. |
| `form_sessions` | `user_id`, `website_origin`, `page_url`, `form_id`, lifecycle `status`, `started_at`, field counters (`total_fields`, `filled_fields`, `reviewed_fields`, `failed_fields`), `fill_results`, optional submission and completion metadata. |
| `corrections` | User feedback: optional session/field IDs, `concept`, original/corrected values, `reason`, `created_at`. |
| `processing_records` | Per-document pipeline stage, `status`, start/completion times, retry count and safe error message. |
| `user_memories` | Explicitly saved free-form answers: string `_id`, owner, `label`, `concept`, `value`, `indexed`, timestamps. Recognized ontology answers are stored as user-confirmed structured facts instead. |
| `auth_token_revocations` | Revoked token `jti` and `expires_at`; a TTL index removes expired records. |

Conflict views are computed from active structured facts; there is no current write path for a `discovered_conflicts` collection. `profiles`, `discovered_conflicts`, `feedback` and `agent_runs` are included in deletion cleanup for compatibility with older data. The form-run endpoint now uses `form_sessions`.

## Indexes

Indexes are created idempotently at startup and existing indexes are not dropped. Current indexes are:

- `users`: unique `email`.
- `documents`: `user_id`; `(user_id, status)`; unique `(user_id, checksum)`.
- `structured_facts`: `(user_id, concept)`; `(user_id, status, concept)`; `(user_id, source_document_id)`.
- `discovered_facts`: `(user_id, source_document_id)`; `(user_id, semantic_type)`.
- `user_memories`: `(user_id, updated_at DESC)`.
- `recommendations`: unique `(user_id, session_id, field_id)`; `(user_id, status)`.
- `corrections`: `(user_id, concept)`.
- `processing_records`: `(user_id, document_id)`.
- `form_sessions`: `(user_id, started_at DESC)`.
- `auth_token_revocations`: unique `jti`; TTL `expires_at`.

The unique recommendation key prevents duplicate field results within a session. If a legacy database already contains duplicate `(user_id, session_id, field_id)` rows, MongoDB cannot create this unique index until those duplicates are reconciled.

## ChromaDB

The application uses the raw Chroma HTTP v2 API and the `user_document_chunks_v2` collection by default. The collection uses cosine distance and records `embedding_model` and `embedding_dimension` metadata. The default `all-MiniLM-L6-v2` model has 384 dimensions. A configured model/dimension mismatch is reported; no hash-vector or in-memory fallback is used.

Document chunks carry `user_id`, `document_id`, `document_name`, `document_type`, `page_number`, `language`, `chunk_index` and `source_type`. Saved-answer chunks use `source_type="user_memory"`. Every retrieval and delete operation filters by `user_id`.

To rebuild the configured collection from processed source documents, run from `backend` after setting `CHROMADB_COLLECTION` to the target collection:

```bash
python -m app.scripts.reindex
```

The script reprocesses documents from the configured storage backend and does not delete or modify a different Chroma collection. Keep the previous collection until the new index has been checked.
