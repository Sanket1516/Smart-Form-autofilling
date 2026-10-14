# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    R.chapter(4, "Design")
    R.intro(
        "This chapter documents the design of the Smart Form Auto-Filling System as implemented. It moves from the architecture and deployment, through the "
        "flow of data and the behaviour of the system, to the database, class structure, core algorithms, security design and application programming "
        "interface. Each diagram is explained in the text, and each was drawn from the corresponding source modules named alongside it."
    )

    # ------------------------------------------------------------------ 4.1
    R.h2("4.1 Block Diagram and System Architecture")
    R.p(
        R.f("architecture") + " shows the architecture. The system is a three-tier design with an external-services ring. The **presentation tier** has two "
        "clients: a React 19 dashboard served by Nginx, and a Chrome Manifest V3 extension whose popup (React 18) and content script cooperate through "
        "extension messages. The **application tier** is a FastAPI service. Every request first passes middleware that applies cross-origin rules, "
        "request-identifier logging with redaction, rate limiting and bearer-token authentication. Eleven routers expose the REST interface and delegate to "
        "services, which in turn use the document pipeline, the form-fill LangGraph pipeline and the field ontology. The **data tier** consists of MongoDB, "
        "which is the source of truth for users, documents, facts and form sessions; ChromaDB, which holds the vector index of document chunks; a file store "
        "(a local volume by default, or Cloudinary); and Redis, which is used only as the Celery broker in Compose."
    )
    R.p(
        "The client never touches a database. All access to MongoDB, ChromaDB and the file store passes through services that receive the authenticated "
        "user identifier and scope every query by it. The external ring contains optional services: a language-model provider (Google, OpenAI or Anthropic, "
        "with a deterministic mock as the default), the sentence-transformer embedding model, an optional OCR engine and the Celery worker, which runs the same "
        "pipeline code as the API process."
    )
    R.fig("architecture")

    # ------------------------------------------------------------------ 4.2
    R.h2("4.2 Hardware and Software Description")
    R.h3("Deployment architecture")
    R.p(
        R.f("deployment") + " shows the Docker Compose deployment. Seven services share the network smart-form-internal: frontend (Nginx, host port 5173), "
        "backend (Uvicorn, port 8000), worker (Celery), mongodb (mongo:8.0), chromadb (host port 8001), redis (redis:7-alpine) and extension-builder, which "
        "builds the extension bundle. MongoDB, ChromaDB and Redis use named volumes. The browser reaches the dashboard through Nginx and the API directly with "
        "a bearer token. A separate Compose file, docker-compose.test.yml, defines an isolated project with its own ports and volumes so that the end-to-end "
        "test can run beside the development stack."
    )
    R.fig("deployment")
    R.h3("Hardware")
    R.p("The system runs on a general-purpose computer; no GPU is required because the embedding model runs on the CPU.")
    R.p(
        R.t("hw") + " records the machine on which the system was developed and the test run of Chapter 6 was made. These are measured facts about the "
        "development machine, not minimum requirements: no benchmark of smaller machines was performed."
    )
    R.table("hw", [
        ["Item", "Value used for development and testing"],
        ["Processor", "13th Gen Intel Core i5-13450HX, 10 cores, 16 logical processors"],
        ["Memory", "15.7 GB"],
        ["Operating system", "Microsoft Windows 11 Home Single Language"],
        ["Container runtime", "Docker 29.4.0 with Compose v2"],
        ["Python / Node.js", "Python 3.11.9 / Node.js 22.14.0"],
        ["Browser", "Google Chrome 155.0.8059.40 and Playwright-managed Chromium"],
        ["Disk", "Named volumes for MongoDB, ChromaDB and Redis; local upload directory"],
    ], [1.6, 4.1], font=10)
    R.h3("Software")
    R.p(
        "Backend dependencies are pinned to compatible ranges in requirements.txt: FastAPI, Pydantic 2, bcrypt, PyJWT, SlowAPI, httpx, Motor and PyMongo, "
        "LangGraph 1.x, pdfplumber, pypdfium2, python-docx, Pillow, OpenCV (headless), sentence-transformers and Celery with Redis. PaddleOCR and PaddlePaddle "
        "are in a separate optional file. The dashboard uses React 19, React Router 7, TypeScript and Vite; the extension uses React 18, TypeScript and Vite "
        "with a second build for the content script. Appendix IV lists the components in full."
    )

    # ------------------------------------------------------------------ 4.3
    R.h2("4.3 Backend Module Design")
    R.p(
        R.f("modules") + " shows the packages of the backend and the direction of their dependencies. Routers in app/api/v1 contain no business logic; they validate "
        "input, apply rate limits and call services. Services coordinate repositories, storage, the pipeline and the agent package. The agents package holds the "
        "form-fill graph, the field classifier, the LLM provider abstraction and value formatting. The processing and extraction packages implement document "
        "parsing, chunking, deterministic and LLM extraction and merging. The ontology package loads the YAML vocabulary. Cross-cutting security code "
        "(prompt-safety helpers, JWT and bcrypt, configuration, logging and rate limiting) is shown in red."
    )
    R.fig("modules")
    R.h3("Configuration")
    R.p(
        "app/core/config.py defines a validated Settings class. At start-up it rejects a placeholder or short JWT secret, an unknown JWT algorithm or "
        "LLM provider, a real provider without an API key, a chunk overlap that is not smaller than the chunk size, and Cloudinary storage without credentials. "
        "The thresholds that govern the pipeline are all configurable and are listed in " + R.t("thresholds") + "."
    )
    R.table("thresholds", [
        ["Setting", "Default", "Used for"],
        ["CLASSIFIER_CONFIDENCE_THRESHOLD", "0.75", "Minimum confidence for a classification to count as resolved"],
        ["AUTOFILL_MIN_CONFIDENCE", "0.85", "Minimum confidence for a value to be marked ready"],
        ["RAG_MIN_SIMILARITY", "0.35", "Cosine similarity cutoff for retrieved chunks"],
        ["RAG_TOP_K", "4", "Chunks retrieved per query"],
        ["RAG_CHUNK_SIZE / RAG_CHUNK_OVERLAP", "500 / 50", "Characters per chunk and overlap"],
        ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30", "Access-token lifetime"],
        ["AUTH_LOGIN_RATE_LIMIT_ATTEMPTS / WINDOW", "5 / 60 s", "Login limiter per key"],
        ["MAX_UPLOAD_SIZE_MB", "10", "Largest accepted upload"],
        ["LLM_MAX_RETRIES / LLM_TIMEOUT_SECONDS", "2 / 60", "Retry policy for non-interactive LLM calls"],
        ["Interactive LLM timeout", "20 s, no retry", "Field classification and field-value calls (fixed in code)"],
        ["LLM_EXTRACTION_MAX_CHARS", "18000", "Document text window per extraction call"],
    ], [2.85, 0.85, 2.05], font=9)
    R.h3("Document processing")
    R.p(
        "app/processing/pipeline.py runs six stages, recorded in the processing_records collection and reflected in the document’s progress "
        "(10, 30, 55, 75, 90 and 100 per cent for validation, parsing, extraction, storage, indexing and completed). The pipeline parses the file, "
        "runs the deterministic extractor, optionally runs the LLM extractor, merges candidates, replaces the document’s facts, and chunks, embeds and indexes the text. "
        "Reprocessing first deletes the document’s previous facts and chunks, so nothing is duplicated and nothing stale remains. An indexing failure "
        "does not lose the extracted facts: it is recorded as index_status failed so that the user can see RAG is unavailable for that document."
    )
    R.h3("Ontology")
    R.p(
        "The ontology (app/ontology/field_ontology.yaml, version 3.0.0) defines 91 concepts in 18 domains " + "(" + R.t("onto") + "). Each concept has a canonical name, a "
        "description, aliases (295 in total), a data type (string, date, email, phone, postal_code or boolean), a cardinality (56 single-valued and 35 multiple-valued "
        "concepts) and optional autocomplete tokens (16 concepts), a sensitivity flag (12 concepts), a fillable flag (the two legal concepts, consent and "
        "signature, are not fillable) and a derived_from link (first, middle and last name are derived from the full name)."
    )
    R.table("onto", [
        ["Domain", "Concepts", "Examples"],
        ["personal", "11", "full_name, first_name, date_of_birth, email, father_name, github"],
        ["financial", "9", "account_number, bank_name, annual_income, cif_number"],
        ["skills", "9", "backend, frontend, databases, cloud_devops, ai_ml"],
        ["education", "8", "degree, institution, field_of_study, cgpa, percentage, end_year"],
        ["identity", "7", "aadhaar_number, pan_number, national_id, nationality, gender"],
        ["address", "6", "street, city, state, country, zipcode, full_address"],
        ["experience", "6", "company, role, start_date, end_date, description, technologies"],
        ["project", "6", "name, description, role, technologies, architecture"],
        ["medical", "4", "blood_group, allergies, insurance_provider, history_description"],
        ["publication", "4", "title, conference, publisher, date"],
        ["Others (8 domains)", "21", "achievement, business, certification, contact, emergency_contact, event, legal, shipping"],
        ["Total", "91", "56 single-valued, 35 multiple-valued"],
    ], [1.5, 0.9, 3.35], font=10)
    R.p(
        "Matching works on word tokens. Text is split at camel-case and non-alphanumeric boundaries, lower-cased and stripped of stop-words. An alias matches "
        "only if all its tokens appear contiguously, and a shorter alias covered by a longer one is discarded, so “father name” never matches the concept for "
        "“name”. The score is 0.98 when the alias covers the whole text and otherwise 0.80 + 0.15 × (alias tokens / text tokens)."
    )

    # ------------------------------------------------------------------ 4.4
    R.h2("4.4 Data Flow and Context")
    R.h3("Context diagram (Level 0)")
    R.p(
        R.f("context") + " is the context diagram. The system is a single process with one human actor, the user, working through the dashboard and the "
        "extension, and one optional external actor, the language-model provider. The user supplies credentials, documents, fact edits, conflict choices, "
        "questions and review decisions, and receives facts with provenance, conflicts, recommendations, grounded answers and processing status. The web "
        "form is shown as a data source and sink for the extension: it supplies field descriptors, never field values, and receives approved values."
    )
    R.fig("context")
    R.h3("Data flow diagram (Level 1)")
    R.p(
        R.f("dfd1") + " decomposes the system into six processes and six data stores. Authentication (1.0) uses the users and token-revocation collections. "
        "Document management (2.0) writes document records and files and hands each stored file to fact extraction (3.0), which writes structured and "
        "discovered facts to D3 and chunk vectors to ChromaDB, calling the language model optionally. Profile and conflict resolution (4.0) reads and updates facts "
        "and records corrections. Field classification and recommendation (5.0) reads facts, retrieved evidence and saved memories and writes form "
        "sessions and recommendations. Question answering (6.0) reads chunks and calls the model."
    )
    R.fig("dfd1")
    R.h3("Data flow diagram (Level 2)")
    R.p(
        R.f("dfd2") + " expands process 3.0. A stored file is parsed (3.1); the deterministic extractor (3.2) and the optional LLM extractor (3.3) each "
        "produce candidate facts, using the ontology; the merge step (3.4) combines candidates with the same concept and value and keeps different values apart; "
        "the document’s old facts are replaced by the merged set (3.5); and the text is chunked, embedded and upserted (3.6). A document that cannot be read, "
        "or that needs OCR when none is installed, leaves the pipeline with status failed or requires_review."
    )
    R.fig("dfd2")

    # ------------------------------------------------------------------ 4.5
    R.h2("4.5 Behavioural Design")
    R.h3("Use case diagram")
    R.p(
        R.f("usecase") + " summarises the functionality from the user’s viewpoint. The system has a single authenticated role, so all use cases attach "
        "to one actor; there is no administrator. The language-model provider is shown as a secondary actor for the use cases that may call it: document "
        "upload (extraction), asking questions and reviewing recommendations. Scanning a page and filling approved values both include the review step, and "
        "resolving a conflict extends viewing and editing profile facts."
    )
    R.fig("usecase")
    R.h3("Activity diagrams")
    R.p(
        R.f("act_upload") + " models the upload workflow. Validation checks the extension, that the declared content type does not contradict the extension, "
        "that the file is not empty or larger than the limit, that its magic bytes match its type, and that a document with the same checksum has not already been "
        "uploaded by this user (a duplicate returns 409). A valid file is stored, a document record is created with status uploaded, and the job is dispatched. "
        "If no text can be read the document ends as failed or requires_review; otherwise facts are extracted and the text is indexed. A failure of "
        "indexing alone still yields a processed document whose index status is failed."
    )
    R.fig("act_upload")
    R.p(
        R.f("act_fill") + " models the form-filling workflow. The popup injects the content script on demand, the detector lists eligible fields, a form session is "
        "created and analysis is started. The popup polls until recommendations are ready, shows each with a status, and the user ticks, edits or skips fields. "
        "Decisions are sent, approved values are fetched, the content script writes them and re-reads the page to verify them, and the results are posted "
        "back. The workflow ends without submitting the form."
    )
    R.fig("act_fill")
    R.h3("Sequence diagrams")
    R.p(
        "The sequence diagrams show the time-ordered messages between components for the key scenarios. " + R.f("seq_register") + " and " + R.f("seq_login") +
        " cover authentication. Registration rejects an existing e-mail with 409, hashes the password with bcrypt and stores the user. Login first applies a "
        "limiter of five attempts per sixty seconds per key, always performs one bcrypt comparison (against a dummy hash if the e-mail is unknown) so that response "
        "time does not reveal whether an account exists, and returns a JWT with subject, unique identifier, issue time, expiry and type. Later requests "
        "send the token as a bearer header; the service checks the revocation store and that the user is active. Logout stores the token’s identifier "
        "until its natural expiry, after which a time-to-live index removes it. The system issues no refresh token."
    )
    R.fig("seq_register")
    R.fig("seq_login")
    R.p(
        R.f("seq_upload") + " shows the upload and processing exchange between the browser, the documents API, the pipeline runner, MongoDB and ChromaDB. "
        "The API answers 201 immediately; processing continues in the background (an inline task or a Celery job), and the browser polls the status endpoint "
        "for the current stage and progress."
    )
    R.fig("seq_upload")
    R.p(
        R.f("seq_fill") + " shows form analysis, review and fill. The content script extracts field descriptors without reading values. The popup creates a "
        "session and calls analyze, which returns 202; the pipeline resolves the profile view from active facts, classifies, retrieves evidence for empty "
        "fields and stores recommendations. After the user’s decisions are posted, approved values are returned in the form needed by the page "
        "(for example the selected option of a drop-down), the content script fills and verifies, and the verification results update the session’s counters. "
        "The session is closed as not submitted unless the user reports otherwise."
    )
    R.fig("seq_fill")
    R.p(
        R.f("seq_rag") + " shows grounded question answering. The query is embedded and the vector store is asked for the nearest chunks of the current user "
        "only. Chunks below the similarity cutoff or containing injection-like text are dropped. The remaining chunks are sent to the model inside tagged "
        "untrusted blocks; the response must cite chunk identifiers, and only cited chunks are returned as sources. If no adequate evidence exists, the "
        "service returns insufficient_evidence instead of an answer."
    )
    R.fig("seq_rag")
    R.p(
        R.f("seq_conflict") + " shows conflict handling. Conflicts are computed on request from the active facts: a single-valued concept with two or more distinct "
        "comparison keys is a conflict, classified as cross-document, intra-document or verified-versus-new. Resolving with a candidate confirms the chosen "
        "facts and supersedes the others; a custom value becomes a user-provided fact; rejecting marks all candidates rejected. A correction record is "
        "kept for the audit trail."
    )
    R.fig("seq_conflict")
