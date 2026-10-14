# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    # ------------------------------------------------------------------ 4.6
    R.h2("4.6 Database Design")
    R.h3("MongoDB collections")
    R.p(
        "MongoDB is the source of truth. " + R.f("er") + " shows the entity relationships. Almost every record carries user_id, and repository queries and "
        "deletes include it. A user owns documents, structured facts, discovered facts, form sessions, corrections and saved memories. A document owns "
        "its processing records and its facts. A form session owns recommendations, one per field, enforced by a unique index on (user_id, session_id, "
        "field_id). The ChromaDB chunk index is a parallel structure keyed by user_id and document_id and is not a MongoDB collection. " + R.t("collections")
        + " lists each collection, its purpose and its indexes."
    )
    R.fig("er")
    R.table("collections", [
        ["Collection", "Purpose and principal fields", "Indexes"],
        ["users", "full_name, email, password_hash, status, timestamps", "unique email"],
        ["documents", "file_name, file_type, file_size, storage_reference, checksum, status, current_stage, progress, page_count, fact_count, index_status, chunk_count", "user_id; (user_id, status); unique (user_id, checksum)"],
        ["structured_facts", "One sourced value: concept, value, raw_value, origin, status, source_document_id, source_page, evidence_text, extraction_method, confidence, is_user_confirmed", "(user_id, concept); (user_id, status, concept); (user_id, source_document_id)"],
        ["discovered_facts", "All extractor output, including unmapped values: field, semantic_type, value, ontology, confidence, evidence_text", "(user_id, source_document_id); (user_id, semantic_type)"],
        ["recommendations", "One result per field: concept, recommended_value, status, confidence, reason, source, requires_confirmation, candidates", "unique (user_id, session_id, field_id); (user_id, status)"],
        ["form_sessions", "website_origin, page_url, form_id, status, field counters, fill_results", "(user_id, started_at desc)"],
        ["corrections", "Concept, original and corrected value, reason", "(user_id, concept)"],
        ["processing_records", "Stage, status, retry count, safe error message per document", "(user_id, document_id)"],
        ["user_memories", "Explicitly saved answers: label, concept, value, indexed", "(user_id, updated_at desc)"],
        ["auth_token_revocations", "Revoked token identifier and expiry", "unique jti; TTL on expires_at"],
    ], [1.3, 2.9, 1.55], font=9.5)
    R.p(
        "Conflict lists are not stored. They are computed from active structured facts (architecture decision AD-013), so a deleted or reprocessed document "
        "cannot leave a stale conflict. Legacy collection names (profiles, discovered_conflicts, feedback, agent_runs) are included in deletion cleanup "
        "for compatibility with older data only."
    )
    R.h3("ChromaDB index")
    R.p(
        "The application writes to the collection user_document_chunks_v2 through ChromaDB’s HTTP v2 API. The collection uses cosine distance and "
        "records the embedding model and dimension in its metadata; a mismatch between the configured model and the collection is reported rather than "
        "tolerated. Each chunk stores user_id, document_id, document_name, document_type, page_number, language, chunk_index and source_type (document or "
        "user_memory). Every query and delete filters by user_id. If ChromaDB is unavailable there is no in-memory fallback: errors surface as 503 "
        "(architecture decision AD-005). A reindex command rebuilds a collection from the stored source documents without touching other collections."
    )
    R.h3("Status vocabularies")
    R.p(
        R.t("statuses") + " collects the status values used by the system. " + R.f("state_doc") + " shows the lifecycle of a document, and " + R.f("state_fact")
        + " shows the lifecycle of a fact. A document ends as processed, failed (unreadable or internal error) or requires_review (OCR needed but not installed); "
        "reprocessing returns it to processing. A fact is active until another candidate is confirmed, the value is edited or a custom value is chosen "
        "(superseded), or the user rejects it (rejected)."
    )
    R.table("statuses", [
        ["Object", "Values"],
        ["Document status", "uploaded, processing, processed, failed, requires_review, deleted"],
        ["Document index status", "pending, indexed, failed, empty"],
        ["Fact status", "active, superseded, rejected"],
        ["Fact origin", "extracted, normalized, inferred, derived, user_provided"],
        ["Recommendation status", "ready, needs_review, missing_information, security_blocked, skipped, error, approved, edited, rejected"],
        ["Concept view status", "resolved, conflict, multiple"],
        ["Conflict type", "CROSS_DOCUMENT, INTRA_DOCUMENT, VERIFIED_VS_NEW"],
        ["Form decision", "approve, edit, reject, skip"],
        ["Submission status", "user_submitted, not_submitted, cancelled"],
    ], [1.8, 3.95], font=10)
    R.fig("state_doc")
    R.fig("state_fact")

    # ------------------------------------------------------------------ 4.7
    R.h2("4.7 Structural Design: Class Diagrams")
    R.p(
        R.f("class_agent") + " shows the classes behind form filling. FormFillGraph owns the seven node methods and depends on FieldClassifier, FactService and "
        "the retrieval service. FieldClassifier and FactService both depend on FieldOntology. FactService builds ConceptView objects from StructuredFact "
        "records; a ConceptView is resolved when all active facts agree, conflict when a single-valued concept has distinct values, and multiple when a "
        "multi-valued concept has several."
    )
    R.fig("class_agent")
    R.p(
        R.f("class_pipeline") + " shows the language-model and retrieval classes. LLMProvider is an abstract class with one asynchronous method; the Google, OpenAI, "
        "Anthropic and mock providers extend it. The HTTP providers share retry logic: a 429 or 5xx response or a timeout is retried with exponential back-off for "
        "non-interactive tasks, while the two interactive tasks (field classification and field values) use a 20-second timeout and no retry. "
        "The provider never returns a sentinel string and never silently switches provider or model. The mock provider is deterministic, makes no network "
        "call and answers every task with an empty, schema-valid result unless a test supplies a responder."
    )
    R.fig("class_pipeline")

    # ------------------------------------------------------------------ 4.8
    R.h2("4.8 Core Algorithms")
    R.h3("Fact extraction and merging")
    R.p(
        "The deterministic extractor favours precision over recall. It takes a value only when it has a distinctive format (an e-mail address, a LinkedIn or "
        "GitHub profile, a phone number next to a phone-like label) or when it follows a label whose ontology match scores 0.98, which means the whole label "
        "is an alias of exactly one concept. Typed values that do not parse (for example a date) are discarded. Labelled values receive confidence 0.92, "
        "format matches 0.95 to 0.97, and the single heuristic, a capitalised name line near the top of the first page, is marked inferred with confidence 0.6."
    )
    R.p(
        "The optional LLM extractor splits the document text into windows of up to 18,000 characters (at most four windows), wraps each in an UNTRUSTED_DOCUMENT "
        "block and asks for JSON with the concept, value, page, exact evidence text and confidence. Each returned value is accepted as extracted or normalized "
        "only if it literally appears in the document and so does its evidence; otherwise it is marked inferred and its confidence is capped at 0.5. "
        "If the provider fails, a warning is recorded and the deterministic facts are still saved."
    )
    R.p(
        "merge_candidates combines candidates with the same concept (or semantic type) and the same comparison key. When both extractors agree, confidence "
        "rises by 0.03 up to a cap of 0.99, and the better origin (extracted before normalized before derived before inferred) is kept. Candidates "
        "with different values are never merged; they remain separate facts and may later form a conflict."
    )
    R.code(
        "merge(candidates):\n"
        "  merged = {}\n"
        "  for c in candidates:\n"
        "    key = (c.concept or c.semantic_type,\n"
        "           comparison_key(c.type, c.value))\n"
        "    if key.value is empty: continue\n"
        "    if key not in merged: merged[key] = c\n"
        "    else:\n"
        "      methods = union(merged[key].methods, c.methods)\n"
        "      agree = len(methods) > 1\n"
        "      best = lower_rank_origin(merged[key], c)\n"
        "      merged[key] = best\n"
        "      merged[key].confidence = min(0.99, max(conf) + (0.03 if agree else 0))\n"
        "  return values(merged)",
        "Algorithm 4.1: Merging candidate facts",
    )
    R.p(
        "The comparison key makes two spellings of the same fact equal: phone numbers by their last ten digits, dates by their ISO form, and other values "
        "by lower-cased, punctuation-stripped words. The cost of merging is linear in the number of candidates."
    )

    R.h3("Form-fill pipeline")
    R.p(
        R.f("langgraph") + " shows the seven-node LangGraph state graph, defined in agents/graph.py. State carries the user, the session, the unique fields, the "
        "per-field work items, the classifications and the profile views. Two conditional edges avoid unnecessary work: llm_classify runs only if some "
        "field is unresolved, and resolve_documents runs only if some non-sensitive field still has no value."
    )
    R.fig("langgraph")
    R.bullets([
        "sanitize:: Marks fields security_blocked when the input type is password, hidden, file, submit, button, reset or image, when the autocomplete token is a payment, one-time-code or password token, or when the label, name or placeholder mentions OTP, CVV, CAPTCHA, card number, password, security code and similar terms. Fields whose text matches an injection pattern are quarantined and kept away from the LLM.",
        "deterministic_classify:: Applies the algorithm of " + R.f("classify") + " to each remaining field.",
        "llm_classify:: Sends one batched request with a sanitised description of each unresolved field and the catalogue of fillable concepts. A returned concept is accepted only if it is a known ontology concept, its confidence is at least 0.6, it is among the tied candidates if the field was ambiguous, and it is not the user’s own value for a field about another person.",
        "resolve_profile:: Builds the resolved view of every concept from active facts. A resolved concept supplies value, confidence (1.0 if user confirmed), origin and source; a conflict or multiple-valued concept becomes needs_review with candidates; a first, middle or last name is derived from a resolved full name, with lower confidence and a confirmation requirement if the name has other than two parts. Non-fillable concepts such as consent and signature are skipped with the reason that the user must give them.",
        "resolve_documents:: For fields still empty and not sensitive, retrieves the top-k chunks for the field text and concept description and sends one batched request. The model must return the chunk identifier and, for open questions, a quotation. A factual value must literally appear in the cited chunk and its confidence is capped at 0.8 (or the chunk similarity plus 0.3, if smaller); prose answers need a quotation that appears in the chunk and are capped at 0.7. Anything ungrounded is discarded.",
        "decide:: Applies the algorithm of " + R.f("decide") + ".",
        "persist:: Upserts one recommendation per field for the session.",
    ])
    R.h3("Deterministic field classification")
    R.p(
        R.f("classify") + " shows the classification rules. The HTML autocomplete token is the strongest signal (confidence 0.97). Otherwise the field’s texts are "
        "matched against ontology aliases in a fixed priority order with weights: question and label 1.0, aria-label 1.0, placeholder 0.95, name and id 0.9, nearby "
        "text 0.85. If the two best matches differ by 0.05 or less the field is ambiguous; the name or id attribute can break the tie (confidence 0.8). If still "
        "unclassified, an input of type email or tel falls back to the e-mail or phone concept. A match on one of seven owner concepts (own name, e-mail, "
        "phone, date of birth) inside a section whose text mentions a father, mother, guardian, spouse, emergency contact, referee, nominee, sibling or child is "
        "withdrawn, so that the user’s own value is not used for another person. A classification is resolved when its concept is known, it is not ambiguous and "
        "its confidence reaches 0.75."
    )
    R.fig("classify")
    R.h3("Decision rules")
    R.p(
        R.f("decide") + " shows how the final status is chosen. Fields already blocked, skipped, in error or in review keep their status. A field without a value "
        "becomes missing_information. Otherwise the value is formatted for the field (a date is rewritten to the pattern the field expects, a drop-down or "
        "radio group is matched to one of its options); if formatting fails, the value is shown as a candidate with the reason. A value for a sensitive concept "
        "(the ontology flag or the configured list of eight identity and finance concepts) or of origin inferred always requires confirmation. A field is ready only if its "
        "confidence is at least 0.85 and no confirmation is required; every other field is needs_review. Nothing is filled from conflicting, inferred or sensitive "
        "data without the user’s explicit approval."
    )
    R.fig("decide")
    R.code(
        "decide(item):\n"
        "  if item.status in {blocked, skipped, error, needs_review}: return\n"
        "  if item.value is None: item.status = missing_information; return\n"
        "  formatted = format_for_field(field, data_type(concept), item.value)\n"
        "  if formatted.failed: item.status = needs_review; item.candidates = [value]; return\n"
        "  if sensitive(concept) or item.origin == 'inferred':\n"
        "    item.requires_confirmation = True\n"
        "  ok = item.confidence >= 0.85 and not item.requires_confirmation\n"
        "  item.status = 'ready' if ok else 'needs_review'",
        "Algorithm 4.2: Final decision for one field",
    )
    R.h3("Conflict resolution")
    R.p(
        "For each concept, active facts are grouped by comparison key. One group gives a resolved view. For a multiple-valued concept several groups give a "
        "multiple view, which is shown but is not a conflict. For a single-valued concept several groups give a conflict. Candidates are ordered with "
        "user-confirmed values first, then by confidence. Resolving with a candidate confirms its facts and supersedes the rest, so the choice persists "
        "and the same conflict does not reappear. The work is linear in the number of active facts of the user."
    )
    R.h3("Retrieval-augmented question answering")
    R.p(
        R.f("rag") + " summarises the RAG path used both by the Ask page and by resolve_documents. A query is embedded with the sentence-transformer model; ChromaDB "
        "returns the nearest chunks of the current user by cosine similarity; chunks below 0.35 or containing injection-like text are dropped; the rest "
        "are labelled and sent to the model. Text is chunked per page into windows of 500 characters with an overlap of 50, so a chunk never crosses a "
        "page boundary and a citation always names the correct page."
    )
    R.fig("rag")

    # ------------------------------------------------------------------ 4.9
    R.h2("4.9 Security Design")
    R.p(
        "Security is designed in layers (" + R.f("security") + "). " + R.t("security") + " maps each control to the module that implements it. The threat "
        "model has four principal threats: a malicious web page that tries to read personal data or to push instructions to the model; a malicious or "
        "malformed document; another authenticated user; and leakage through logs or error messages."
    )
    R.fig("security")
    R.table("security", [
        ["Control", "Threat addressed", "Implementation"],
        ["bcrypt password hashing; 72-byte limit enforced", "Credential theft", "core/security.py; services/auth.py"],
        ["JWT HS256, 30 minutes, jti revocation with TTL", "Token reuse after logout", "core/security.py; db/revocations.py"],
        ["Login limiter and SlowAPI route limits", "Brute force, abuse", "services/auth.py; core/rate_limit.py; api/v1/*"],
        ["user_id filter on every MongoDB and Chroma operation", "Cross-user access", "repositories; db/chroma_client.py"],
        ["Extension, content-type and magic-byte checks; size limit; checksum", "Malicious or mismatched upload", "services/documents.py"],
        ["UNTRUSTED blocks, bracket escaping, six injection patterns, quarantine", "Prompt injection via page or document", "security/prompt_safety.py"],
        ["Quote and literal-presence checks; JSON schema validation", "Hallucinated values", "agents/graph.py; agents/json_output.py"],
        ["Sensitive and hidden fields skipped (extension) and blocked (backend)", "Autofill abuse " + c("autofill"), "content/detector.ts; agents/graph.py"],
        ["activeTab and scripting on demand; host permission limited to backend", "Overbroad extension access", "public/manifest.json"],
        ["Token held in popup and background only", "Token theft by page scripts", "extension/src/shared/api.ts"],
        ["Redacting JSON logs; validation errors omit values; generic 500 message", "Leakage through logs and errors", "core/logging.py; core/exceptions.py"],
        ["Strict secret validation at start-up", "Weak or placeholder secrets", "core/config.py"],
        ["Cache-Control no-store and nosniff on previews and downloads", "Cached or sniffed documents", "api/v1/documents.py"],
    ], [2.5, 1.5, 1.75], font=9.5)
    R.p(
        R.f("inject") + " shows how every untrusted string is handled before a model sees it. The helper detect_injection tests six regular expressions "
        "covering phrases such as “ignore previous instructions”, requests to reveal stored or system data, “you are now a…”, “new instructions:”, "
        "references to a system or developer prompt, and attempts to close the delimiter tags. A match quarantines a field or drops a chunk. Clean text "
        "has its whitespace collapsed, its length capped and its angle brackets replaced, so it cannot close the block, and is wrapped in a tagged block that "
        "the system prompt declares to be data. Model output is parsed against a schema, and for values from documents it must be traceable to a cited "
        "chunk. This follows the recommendations of the OWASP guidance " + c("owasp") + " and addresses the indirect-injection risk described by Greshake et al. "
        + c("injection") + ". It reduces, but does not eliminate, the risk: pattern matching cannot recognise every phrasing, which is why the grounding checks "
        "and mandatory user review are also required."
    )
    R.fig("inject")
    R.p(
        "Residual risks are documented in the repository: the dashboard stores its token in local storage (a script injected into the dashboard origin could "
        "read it); in-process rate limiting does not span replicas; backups and provider-side copies have their own retention; and personal documents "
        "that were committed in earlier versions of the repository were removed from the working tree but the history was deliberately not rewritten "
        "(AD-012), so any credential that was ever committed must be rotated."
    )

    # ------------------------------------------------------------------ 4.10
    R.h2("4.10 API Design")
    R.p(
        "The backend exposes a versioned REST interface under /api/v1. Successful responses use the envelope {success, data, message} and errors use "
        "{success: false, error: {code, message, details}}; validation errors do not echo submitted values. All routes except health, registration and login "
        "require a bearer token, and tokens in query strings are not accepted. " + R.t("api") + " lists the principal endpoints; the complete schema is "
        "published by FastAPI at /docs and /openapi.json."
    )
    R.table("api", [
        ["Group", "Method and path", "Purpose"],
        ["Auth", "POST /auth/register, POST /auth/login", "Create an account; obtain a token"],
        ["Auth", "GET /auth/me, POST /auth/logout, DELETE /auth/me", "Current user; revoke token; delete account and data"],
        ["Documents", "POST /documents; GET /documents; GET /documents/{id}", "Upload; list with filters; read one"],
        ["Documents", "GET /documents/{id}/status; /facts; POST /process, /reprocess", "Progress; extracted facts; (re)run processing"],
        ["Documents", "GET /documents/{id}/download, /preview; DELETE /documents/{id}", "Header-authenticated file access; delete with cascade"],
        ["Facts", "GET/POST /profile/facts; PUT/DELETE /profile/facts/{id}", "List, add, edit or confirm, delete or reject facts"],
        ["Facts", "GET /profile/facts/conflicts; PATCH .../conflicts/{id}/resolve", "Computed conflicts; resolve by candidate, custom value or reject"],
        ["Profile", "GET/PUT /profile; GET /profile/concepts; DELETE /profile/data", "Aggregated profile; ontology concepts; delete data, keep account"],
        ["Forms", "POST /forms/sessions; POST /forms/sessions/{id}/analyze (202)", "Create session; start batch analysis"],
        ["Forms", "GET .../recommendations; POST .../decisions; GET .../approved-values", "Read results; record decisions; values to fill"],
        ["Forms", "POST .../verify; POST .../complete; POST .../answers", "Fill results; close session; supply missing answers"],
        ["Forms", "POST /forms/classify-field(s), /forms/recommend(ations); POST /agent/run", "Synchronous and agent wrappers of the same pipeline"],
        ["Retrieval", "POST /retrieval/rag; /retrieval/rag/answer; /retrieval/structured", "Similar chunks; grounded answer; facts by concept"],
        ["Reviews", "GET /reviews/pending; POST /reviews/{id}/decision", "Pending recommendations; decide"],
        ["Health", "GET /health; GET /health/services", "Readiness; MongoDB, Chroma, LLM and embedding state"],
    ], [0.8, 2.75, 2.2], font=9.5)
    R.p(
        "Rate limits are applied per route and per process: for example 10 per minute for registration and login, 20 per minute for uploads of documents, 60 "
        "per minute for single-field classification, and 20 to 30 per minute for analysis, recommendation and RAG routes."
    )

    # ------------------------------------------------------------------ 4.11
    R.h2("4.11 Client Design")
    R.h3("Chrome extension")
    R.p(
        "The manifest declares Manifest V3 with the permissions activeTab, scripting and storage, a host permission limited to the local backend origins and "
        "optional host permissions for http and https that the user grants on demand. The popup does not run a persistent content script; it injects "
        "content.js into the active tab with chrome.scripting when needed, after pinging to see whether it is already present. The content script "
        "answers three messages only: SFA_PING, SFA_EXTRACT and SFA_FILL, and only from this extension’s own identifier."
    )
    R.p(
        "The detector selects input, select and textarea elements; skips types hidden, submit, button, reset, image, file, password, range and color; skips "
        "disabled and read-only controls, controls whose autocomplete token or descriptive text indicates payment, password or one-time-code, and invisible "
        "controls (display none, visibility hidden, zero opacity, zero size, or positioned far off-screen, which is a common honeypot technique). Each remaining "
        "field is described by label, accessible name, placeholder, name, id, autocomplete, pattern, section heading, nearby text, required, maximum length "
        "and options, plus a has_value flag; **values are never read**. Radio buttons are grouped into one field with the group’s question. Field identifiers "
        "come from stable attributes (id, then name within form scope, then DOM path), so they survive reopening the popup."
    )
    R.p(
        "The writer sets values through the element’s native property setter and dispatches input and change events so that framework-controlled inputs "
        "register the change. Checkboxes and radios are clicked. Drop-downs are matched by the option recommended by the backend, then by value, then by an "
        "exactly one label match. After a short settling delay, each field is re-read: the result reports whether the value was applied and whether the page kept it. "
        "Disabled, read-only or hidden controls are left alone and reported as not applied."
    )
    R.p(
        R.f("state_ext") + " shows the popup’s state machine: idle, scanned, analyzing, review, filling and done. State is stored in chrome.storage.session per "
        "tab so that reopening the popup resumes the flow; an authentication failure (401) returns to sign-in. The popup polls recommendations every "
        "second for up to 180 seconds. Decisions are built so that only ticked fields with a value become approve or edit decisions, an unticked ready "
        "field becomes skip, and blocked fields are never sent."
    )
    R.fig("state_ext")
    R.h3("Dashboard")
    R.p(
        "The dashboard is a React single-page application with protected routes: Login and Register are public; Dashboard, Documents, Document details, Profile, "
        "Discovered facts, Conflicts, Reviews, Ask, Activity and Settings require a token. A single typed API client unwraps the response envelope, converts "
        "errors to a typed exception, builds readable messages from validation errors, and emits a global event on a 401 response so that the user is signed "
        "out in one place. Document previews and downloads use header-authenticated blobs rather than tokens in URLs. In production the dashboard is "
        "served by Nginx with a restrictive Content Security Policy and security headers."
    )
    R.summary(
        "The design was presented from architecture and deployment through data flow, behaviour and structure to algorithms, security and interfaces. "
        "Twenty-seven figures and seven tables document the implemented system. The principal design decisions are: a single ontology vocabulary, deterministic "
        "classification before any model call, grounded and quoted model output, conflicts computed rather than stored, tenant scoping on every query, and a "
        "review step that the extension cannot bypass."
    )
