# Security and privacy

This document describes the current implementation and the controls required before deployment. The system stores identity and employment facts, uploaded documents, saved answers and form activity. Treat MongoDB, ChromaDB, local storage volumes, backups and logs as sensitive data stores.

## Authentication and authorization

- API access uses short-lived JWT bearer tokens in the `Authorization` header. Query-string tokens are not accepted. The default token lifetime is 30 minutes; logout and account deletion revoke the token using `jti` records with MongoDB TTL expiry.
- Passwords are hashed with bcrypt. Registration rejects mismatched passwords and values longer than bcrypt's 72-byte limit. Login and registration are rate-limited; document upload, processing, classification, recommendations and RAG routes have additional limits.
- Every user-owned MongoDB lookup and Chroma query is scoped by the authenticated `user_id`. Document preview and download responses use `Cache-Control: no-store`; PDF previews also use a restrictive content security policy and `nosniff`.
- `DELETE /api/v1/profile/data` deletes user records, stored document files and vectors while retaining the account. `DELETE /api/v1/auth/me` also removes the account. If Chroma is unavailable, deletion returns 503 before removing MongoDB records. Storage deletion failures are logged without document contents.

## Browser clients

- The Chrome extension requests `activeTab`, `scripting` and `storage`; site access is granted on demand. It ignores password and other protected controls, and sends field descriptions and a `has_value` flag rather than current field values. Recommendations require user review before filling, and filling never submits a form.
- Extension JWTs are held in extension storage, the popup and the background worker. They are not passed into the page content script. The backend URL is configurable in extension settings.
- The dashboard stores its JWT in `localStorage` as selected in the architecture decisions. The production Nginx configuration sends a restrictive CSP and security headers, and the default token lifetime is 30 minutes. A successful script injection into the dashboard origin could still read the token; use dependency review, CSP maintenance and short expiry to reduce that exposure.

## Secrets and deployment

- Generate a unique secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and set `JWT_SECRET_KEY` in an untracked `.env`. Compose fails when the variable is missing, and backend configuration rejects known placeholders and secrets shorter than 32 characters.
- `.env.example` intentionally contains the rejected value `change-me` so `docker compose config` can validate the YAML. Replace it before starting the application. Do not use the test stack's fixed JWT or MongoDB credentials outside local testing.
- Keep production MongoDB, ChromaDB and Redis private. Put TLS termination and an authenticated network boundary in front of the HTTP services. The checked-in Compose file is for local development, not a hardened public deployment.
- Do not put real documents, credentials, JWTs, API keys or user data in test fixtures. The test provider uses synthetic values and makes no paid API calls by default. Real-provider tests are opt-in and must use synthetic inputs.
- PaddleOCR is optional. Scanned documents without it are marked `requires_review`; the application does not silently treat OCR-less output as verified text.

## Logging and errors

- Application logs are JSON, include a request ID, and redact bearer tokens, JWTs, API-key/password/secret/token fields, email addresses and long digit sequences. Do not add document text, form values, passwords or complete request bodies to log extras.
- API validation errors omit submitted values; unexpected errors return a generic message and request ID. Request logs contain method, path, status and duration, not query strings.
- Rate limits use the in-process SlowAPI limiter. In a multi-worker or multi-replica deployment, put shared rate limiting at the trusted edge or configure a shared limiter backend before relying on limits across instances.

## Data deletion and retention

MongoDB is the source of truth. Chroma stores derived document chunks and saved-answer embeddings and is filtered by `user_id`. Account/data deletion removes records from the current and legacy user-owned collections. Backups and provider-side copies have their own retention windows and must be deleted under the deployment's backup and storage policies.

The initial repository audit identified personal files and credentials in older commits. Those files were removed from the working tree; history was intentionally not rewritten. To remove the named files from a private clone's history, coordinate with all repository users first, then use `git filter-repo` and force-update every remote/clone. Example command for the audit's paths:

```bash
git filter-repo --invert-paths \
  --path backend/app/sample_passbook.png \
  --path backend/passbook.pdf \
  --path test-data/sanket_mali.pdf
```

History rewriting changes commit IDs and is not part of normal remediation. Rotate any credential that was ever committed; deleting the file from the current tree does not revoke it.
