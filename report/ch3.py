# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    R.chapter(3, "Problem Definition and Proposed Solution")
    R.intro(
        "This chapter turns the gap identified in Chapter 2 into a precise problem, states the requirements that a solution must meet, and describes the "
        "proposed solution at the level of workflow and technology choice. It closes with an honest account of which features are implemented, which are "
        "optional, and which belong to future work."
    )

    R.h2("3.1 Problem Definition")
    R.p(
        "Let *D* be the set of documents uploaded by a user *u*. Let *K* be a finite ontology of concepts, each with a data type, a cardinality (single or "
        "multiple valued), and flags marking it sensitive or not fillable. The system must derive from *D* a set of facts *F(u)*, where each fact is a tuple "
        "(concept, value, origin, source document, page, evidence text, confidence), and must, for any web form with fields *X* presented to the user, produce "
        "for each field *x* in *X* a recommendation *r(x)* consisting of a status, an optional value, a confidence, a reason and a source."
    )
    R.p("A solution is acceptable only if it satisfies the following constraints:")
    R.numbered([
        "**Evidence.** A value is proposed only if it is stored in *F(u)* or appears verbatim in a retrieved passage of *D* that the system can cite.",
        "**Conflict transparency.** If *F(u)* contains two or more distinct values for a single-valued concept, no value is filled automatically; the candidates are shown.",
        "**Sensitivity.** Passwords, payment details, one-time codes and CAPTCHAs are never filled. Concepts flagged sensitive, and values the system only inferred, require confirmation.",
        "**Consent.** The page is changed only after the user approves each field, and the form is never submitted by the system.",
        "**Isolation.** No operation on one user’s data may read, return or affect another user’s data.",
        "**Untrusted input.** Text from web pages and documents is treated as data, never as instructions to the language model.",
    ])

    R.h2("3.2 Challenges")
    R.bullets([
        "Heterogeneous forms:: Labels, placeholders, names and identifiers vary between sites, and the same concept may be phrased as “DOB”, “Date of Birth” or “Birth date”. Rule-based matching must be precise, and ambiguity must be resolved without guessing.",
        "Context-dependent fields:: A field labelled “Name” inside a “Father’s details” section is not the user’s name. The system must recognise this and avoid filling the user’s own value.",
        "Conflicting sources:: Two documents may spell a name or write an address differently. Choosing silently would hide an error.",
        "Language-model risks:: Models can invent values and can be manipulated by text they read " + c("injection") + ". Every model output must be validated and grounded.",
        "Browser security model:: A Manifest V3 extension has limited, permission-gated access to pages " + c("mv3") + ". Tokens must not reach scripts running in the page.",
        "Framework-controlled inputs:: Pages built with React or similar libraries ignore naive assignments to the value property, so a fill must emulate user input and verify the outcome.",
        "Unreadable documents:: Scanned files without OCR cannot yield text. The system must say so rather than treat empty output as a result.",
    ])

    R.h2("3.3 Existing System and Its Limitations")
    R.p(
        "In current practice a person either types every value by hand, copies from a résumé or document, or relies on browser autofill. Table "
        + R.t("existing").split()[-1] + " contrasts this practice with the proposed system on the properties that matter to the problem definition."
    )
    R.table("existing", [
        ["Aspect", "Existing practice (manual / browser autofill)", "Proposed system"],
        ["Source of values", "Typed by the user, or values saved from earlier forms", "Facts extracted from the user’s uploaded documents, plus user-entered facts"],
        ["Field matching", "Attribute names and heuristics", "Ontology aliases, autocomplete tokens and nearby text, then one batched LLM call for the rest"],
        ["Evidence for a value", "None", "Source document, page, evidence text, method, confidence"],
        ["Conflicting values", "One value is chosen without notice", "Conflict is computed and shown; the user chooses"],
        ["Sensitive and hidden fields", "Filled by indiscriminate matching " + c("autofill"), "Skipped in the extension and blocked again in the backend"],
        ["User control", "Preview or one-click fill", "Per-field review with reason and source; user can edit or skip"],
        ["After filling", "No verification", "DOM re-read to confirm the page kept each value; results reported"],
        ["Submission", "User or page script", "Never submitted by the system"],
    ], [1.25, 2.1, 2.4], font=10)

    R.h2("3.4 Proposed Solution Overview")
    R.p(
        "The solution has two phases, shown in " + R.f("overview") + ". In **Phase A** the user uploads documents once. The backend parses each document, extracts "
        "facts and merges them, stores the facts in MongoDB with their provenance, and indexes document chunks in ChromaDB. In **Phase B**, on any web page, "
        "the extension describes the form’s fields, the backend classifies them and proposes values, the user reviews the proposals, and the extension fills the "
        "approved values and verifies the result."
    )
    R.fig("overview")
    R.h3("Workflow summary")
    R.p(
        "Upload, parse, extract, merge, index; then scan, classify, resolve, decide, review, fill, verify. Upload and processing are asynchronous, so the "
        "dashboard polls the document’s status. Form analysis is also asynchronous: the analyze endpoint returns immediately with status 202 and the "
        "popup polls the recommendations until they are ready. The same batch pipeline serves the extension, the synchronous recommendation endpoints and the "
        "agent endpoints, so behaviour is identical for every client (architecture decision AD-002)."
    )
    R.h3("Advantages of the proposed solution")
    R.bullets([
        "Traceable values:: every proposal states where it came from and how certain the system is.",
        "Less typing, fewer errors:: values are normalised and formatted to the target field (dates, options, radio groups).",
        "Safe by construction:: sensitive and hidden controls are skipped in two places, and a fill never submits a form.",
        "Predictable cost:: the language model is called only when rules cannot decide, and the default provider is a deterministic mock that makes no network call.",
        "Portable deployment:: the whole stack starts with one Compose command.",
    ])

    R.h2("3.5 Requirements")
    R.h3("Functional requirements")
    R.p("Table " + R.t("freq").split()[-1] + " lists the functional requirements and the module in which each is implemented.")
    R.table("freq", [
        ["ID", "Requirement", "Implemented in"],
        ["FR1", "Register, log in, log out, delete account", "services/auth.py; api/v1/auth.py"],
        ["FR2", "Upload PDF, DOCX, TXT, PNG, JPG with extension, magic-byte, size and duplicate checks", "services/documents.py"],
        ["FR3", "Process documents in the background with visible stage and progress", "processing/runner.py; processing/pipeline.py"],
        ["FR4", "Parse text; use OCR if installed; otherwise mark requires_review", "processing/extractor.py"],
        ["FR5", "Extract facts by deterministic rules over the ontology", "extraction/deterministic.py"],
        ["FR6", "Optionally extract facts with an LLM and merge both tracks", "extraction/llm_extraction.py; extraction/merge.py"],
        ["FR7", "Store provenance: origin, raw value, evidence, page, method, confidence", "models/documents.py (StructuredFact)"],
        ["FR8", "View, add, edit, confirm and delete profile facts", "services/facts.py; services/profile.py"],
        ["FR9", "Detect cross-document conflicts and let the user resolve them", "services/facts.py"],
        ["FR10", "Answer questions from the user’s documents with cited sources", "services/retrieval.py"],
        ["FR11", "Detect form fields in the page, skipping sensitive and hidden controls", "extension/src/content/detector.ts"],
        ["FR12", "Classify fields to ontology concepts", "agents/field_classifier.py"],
        ["FR13", "Recommend values with status, reason, source and candidates", "agents/graph.py"],
        ["FR14", "Record approve, edit, reject, skip decisions; save answers on request", "services/form_filling.py; popup AutofillFlow.tsx"],
        ["FR15", "Fill approved values and verify them; never submit", "extension/src/content/autofill.ts"],
        ["FR16", "Delete all user data (vectors, facts, files) with or without the account", "services/user_data.py"],
        ["FR17", "Report service health and form-session activity", "services/health.py; dashboard Settings and Activity pages"],
    ], [0.5, 3.3, 1.95], font=10)
    R.h3("Non-functional requirements")
    R.p(R.t("nfreq") + " lists the non-functional requirements and how the implementation meets them.")
    R.table("nfreq", [
        ["Category", "Requirement", "How it is met"],
        ["Security", "Authenticated, isolated, revocable access", "bcrypt, JWT with jti revocation, user_id filter on every query (Section 4.9)"],
        ["Privacy", "Minimal collection from pages", "Descriptors only, has_value flag instead of values, activeTab on demand"],
        ["Reliability", "Failures are explicit", "Typed errors; no silent fallback to hash vectors or other providers"],
        ["Responsiveness", "Interactive analysis must not hang", "Interactive LLM calls capped at 20 s with no retry; popup poll timeout 180 s"],
        ["Maintainability", "Verifiable changes", "196 automated tests, ruff, black, type checks, CI workflow"],
        ["Portability", "Reproducible environment", "Docker Compose; configuration through environment variables"],
        ["Observability", "Diagnosable without leaking data", "Structured JSON logs with request ID and redaction"],
        ["Usability", "User can understand every proposal", "Reason and source on each recommendation; Ready or Check status"],
    ], [1.05, 2.0, 2.7], font=10)

    R.h2("3.6 Technology Stack and Justification")
    R.p(R.t("stack") + " lists the technologies used in each layer and the reason for each choice; the architecture decisions cited (AD-003 to AD-008) are recorded in the repository.")
    R.table("stack", [
        ["Layer", "Technology", "Justification"],
        ["API", "FastAPI, Pydantic v2, Uvicorn " + c("fastapi"), "Async I/O, typed request and response models, generated OpenAPI documentation"],
        ["Fact store", "MongoDB 8 via Motor " + c("mongodb"), "Heterogeneous fact shapes; per-user queries; TTL indexes for revoked tokens"],
        ["Vector index", "ChromaDB over HTTP v2 " + c("chroma"), "Self-hostable; collection metadata records model and dimension (AD-004, AD-005)"],
        ["Embeddings", "all-MiniLM-L6-v2, 384 dimensions " + c("sbert", "minilm"), "Small, CPU-friendly default; mismatch with the collection is reported"],
        ["Agent graph", "LangGraph " + c("langgraph"), "Explicit state graph with conditional edges; deterministic order of steps"],
        ["LLM access", "Google, OpenAI, Anthropic through httpx; mock default", "No SDK lock-in; one interface; deterministic offline mock for tests (AD-007)"],
        ["Jobs", "Celery with Redis; inline asyncio mode", "Docker processing outlives API requests; local runs need no queue (AD-003)"],
        ["Documents", "pdfplumber, pypdfium2, python-docx, Pillow, OpenCV; optional PaddleOCR", "Parsing and image pre-processing; OCR optional to avoid a heavy dependency (AD-008)"],
        ["Auth", "bcrypt " + c("bcrypt") + ", PyJWT " + c("jwt"), "Salted adaptive hashing; short-lived bearer tokens"],
        ["Dashboard", "React 19, TypeScript, Vite, React Router " + c("react"), "Component model; typed API client"],
        ["Extension", "Chrome Manifest V3, React 18, Vite " + c("mv3"), "Current extension platform; on-demand injection with activeTab"],
        ["Delivery", "Docker Compose, Nginx " + c("docker"), "Single-command stack; production-style static serving with security headers"],
        ["Testing", "pytest, Vitest, Testing Library, Playwright " + c("playwright"), "Unit, integration and real-browser tests"],
    ], [0.95, 2.15, 2.65], font=9.5)

    R.h2("3.7 Feasibility Analysis")
    R.bullets([
        "Technical:: every component is open source and runs on a single developer machine; the embedding model runs on CPU. The project was built and tested on a Windows 11 laptop with a 13th-generation Intel Core i5-13450HX (10 cores, 16 threads) and 15.7 GB of memory.",
        "Economic:: the default configuration uses the mock provider and local storage, so running and testing the system incurs no API charges. A real LLM provider is optional and billed by that provider; real-provider tests are opt-in.",
        "Operational:: the user uploads documents once and then uses a popup; no administrative role is needed.",
        "Legal and ethical:: the system stores identity data. The security design (Section 4.9) and the documented retention and deletion behaviour are therefore part of feasibility, not an afterthought.",
    ])

    R.h2("3.8 Implementation Status and Limitations")
    R.p(
        "Table " + R.t("status").split()[-1] + " separates implemented features from optional, partial and future ones, as recorded in the repository documentation and verified "
        "by the tests of Chapter 6."
    )
    R.table("status", [
        ["Feature", "Status", "Note"],
        ["Authentication, token revocation, rate limits", "Implemented", "30-minute JWT; logout and deletion revoke the token"],
        ["Document upload and processing (PDF, DOCX, TXT, images)", "Implemented", "Inline mode locally; Celery with Redis in Compose"],
        ["Deterministic extraction and merge", "Implemented", "Precision-first; heuristic name line marked inferred"],
        ["LLM extraction and classification", "Implemented, opt-in", "Default provider is mock; real providers need a key"],
        ["Conflict detection and resolution", "Implemented", "Computed from active facts"],
        ["RAG retrieval and grounded answers", "Implemented", "Similarity cutoff 0.35; cited sources only"],
        ["Seven-node LangGraph pipeline", "Implemented", "Used by all recommendation endpoints"],
        ["Chrome extension scan, review, fill, verify", "Implemented", "Verified in a real Chromium test"],
        ["Dashboard (11 routes)", "Implemented", "Login, register, dashboard, documents, document details, profile, discovered facts, conflicts, reviews, ask, activity, settings"],
        ["OCR for scanned documents", "Optional", "Needs INSTALL_OCR=true; otherwise requires_review"],
        ["Cloudinary storage", "Optional", "STORAGE_PROVIDER=cloudinary"],
        ["Real-provider LLM tests", "Opt-in, not run", "May incur charges; synthetic data only"],
        ["Other browsers, mobile, multi-step wizard re-scan", "Future", "Chapter 7"],
    ], [2.5, 1.1, 2.15], font=10)
    R.p(
        "The principal limitations are: dependence on OCR for scans; a vocabulary limited to 91 concepts, so a field with no matching concept is left for the "
        "user; a static scan model in which fields added after the scan need a re-scan; in-process rate limiting that does not span multiple replicas; and a "
        "dashboard token kept in browser local storage, which is protected by a restrictive Content Security Policy and a short expiry but would be exposed by "
        "a successful script injection (architecture decision AD-010)."
    )
    R.summary(
        "The problem was defined formally with six acceptance constraints. Challenges were identified, existing practice was contrasted with the proposed "
        "two-phase solution, seventeen functional and eight non-functional requirements were tabulated, technology choices were justified, and the status "
        "of every feature was recorded together with the principal limitations."
    )
