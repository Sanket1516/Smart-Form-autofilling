# -*- coding: utf-8 -*-
import json
import os

from content_refs import c

HERE = os.path.dirname(os.path.abspath(__file__))


def _rerun():
    p = os.path.join(HERE, "rerun.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf8"))
    return None


def build(R):
    R.chapter(6, "Testing")
    R.intro(
        "This chapter describes how the system was tested and records the results. Every number below is taken from the repository’s test inventory and "
        "from the recorded test runs; no figure was estimated. Where a test category was not run, the report says so."
    )

    R.h2("6.1 Testing Strategy")
    R.p(
        "The strategy follows the repository’s testing documentation. Each test belongs to exactly one category: **mocked** (fakes or the mock LLM stand in for "
        "external services), **real-service** (a real local MongoDB or ChromaDB) or **real-provider** (a paid external LLM). The default run never touches the "
        "developer’s own database, never calls a paid API and uses only synthetic personal data. To guarantee this, the backend test configuration forces the "
        "LLM provider to mock, storage to a temporary directory, processing to inline, a randomly named MongoDB database that is dropped at the end of the session, "
        "and a randomly named Chroma collection. Markers select the real-service and real-provider categories: tests marked mongo or chroma are skipped with a reason "
        "if the service is unavailable, and real_llm tests run only when RUN_REAL_LLM_TESTS=1 is set and a provider and key are configured."
    )
    R.p(
        R.f("testing_ci") + " shows the continuous-integration workflow. On every push and pull request, the first job runs ruff and black on the backend, the mocked "
        "backend suite with a MongoDB service, the ChromaDB integration suite with a ChromaDB service, the type checks, tests and builds of the dashboard and the "
        "extension, and validation of both Compose files. A second job installs Chromium and runs the Playwright end-to-end test on an isolated Compose "
        "stack. Real-provider tests never run in CI."
    )
    R.fig("testing_ci")

    R.h2("6.2 Backend Tests")
    R.p(
        "The backend suite uses pytest. " + R.t("backend_tests") + " lists the inventory by file. The counts are the numbers collected by pytest for the default "
        "run (146 tests, of which two live in the extension-manifest check) and are derived from the test files, not estimated."
    )
    R.table("backend_tests", [
        ["File", "Scope", "Representative scenarios", "Tests"],
        ["test_auth.py", "Authentication", "register, login, me, logout; password stored hashed; weak, mismatched or over-long passwords rejected; duplicate e-mail; same error for wrong password and unknown user; missing, malformed, expired and wrong-type tokens; token in query string refused; login rate limit; account deletion revokes the token", "12"],
        ["test_config.py", "Configuration", "weak or placeholder secret rejected; unknown provider not silently mocked; real provider needs a key; unsupported JWT algorithm; Cloudinary credentials; chunk overlap smaller than size", "9"],
        ["test_documents_api.py", "Upload and processing", "PDF processed into facts and indexed; DOCX and TXT; executables, fake PDF or DOCX, binary text, empty and content-type-mismatched files rejected; oversize and duplicate upload; corrupted PDF; scanned file without OCR requires review; LLM facts merged; indexing failure keeps facts; reprocessing replaces facts and chunks; delete cascades; delete refused when the vector store is down; cross-user access; safe download headers", "18"],
        ["test_end_to_end.py", "Backend acceptance flow", "register, upload a synthetic PDF, inline processing, facts, conflict resolution, session, analyze, recommendations, verify", "1"],
        ["test_extraction.py", "Extraction and merge", "date normalisation (seven forms including invalid dates); value normalisers; labelled facts with provenance; no invented values; LLM values absent from text marked inferred; invalid JSON and provider failure reported; untrusted document wrapping; merge of agreeing and conflicting extractors", "14"],
        ["test_facts_profile_api.py", "Facts, conflicts, profile", "conflict detected with sources; resolve by candidate, custom value, reject; foreign or unknown conflict returns 404; new document disagreeing with a confirmed value flagged; editing creates a user value and a correction; profile update; memories; delete all data keeps account; concept catalogue", "10"],
        ["test_field_classifier.py", "Field classification", "obvious fields by label, autocomplete, placeholder, input type, name; ambiguous label not resolved deterministically; name attribute breaks a tie; name in another person’s section; one batched LLM call with validated output; invalid LLM output and provider failure marked as errors", "13"],
        ["test_forms_api.py", "Recommendation pipeline", "validated explainable recommendations; missing information never fabricated; conflicts go to review with candidates; one batched LLM call with minimal data; LLM failure reported as error; injection in field text quarantined; RAG values grounded in cited evidence and dropped otherwise; review decisions, approved values, verify, complete; reanalysis upserts; private sessions; same pipeline for all endpoints; payload validation", "14"],
        ["test_health.py", "Platform", "success envelope and request ID; unsafe request ID replaced; real component state; 404 envelope; CORS allows the dashboard and PATCH only for allowed origins", "5"],
        ["test_llm_and_prompt_safety.py", "LLM and injection safety", "injection patterns detected; ordinary labels not flagged; untrusted content cannot close its block; JSON parsing; mock provider empty answers; key sent in header; client errors not retried, server errors retried for three providers; empty completion is an error; factory", "16"],
        ["test_ontology.py", "Ontology", "phrase matching for thirteen label variants; longer alias beats shorter; substrings do not match; ambiguous label reports both concepts; metadata; tokenisation", "18"],
        ["test_rag_api.py", "RAG", "only the caller’s chunks; unrelated query returns nothing above cutoff; grounded answer with cited sources only; no evidence means no LLM call; uncited answer insufficient; failures return errors not fake answers; structured retrieval scoped; injected chunks never reach the LLM", "8"],
        ["test_value_formatting.py", "Value formatting", "date formatted for control; select matching exact, never substring; radio duplicates left for review; checkbox ticked only for explicit yes; typed values validated; multiple values need a choice", "6"],
        ["tests/test_extension_manifest.py", "Extension manifest", "Manifest V3 with minimal permissions; build produces a classic content script", "2"],
        ["Total", "", "", "146"],
    ], [1.7, 0.85, 2.7, 0.5], font=9, align=["l", "l", "l", "c"])

    R.h2("6.3 Dashboard and Extension Tests")
    R.p(
        "The dashboard tests use Vitest, Testing Library and jsdom with a stubbed fetch (" + R.t("front_tests") + "). The extension tests use Vitest and jsdom "
        "(" + R.t("ext_tests") + "). Both suites include tests for failure paths, not only for success."
    )
    R.table("front_tests", [
        ["File", "Scenarios", "Tests"],
        ["auth.test.tsx", "sign in stores token and redirects; clear messages for wrong credentials and rate limiting; validation before calling the server; expired token signs out; registration; weak and mismatched passwords and duplicate e-mail", "6"],
        ["documents.test.tsx", "client-side type and size validation; upload and listing with status; server error on a rejected upload; confirmation before delete; processing failures and facts with provenance; error for a failed document", "6"],
        ["profile.test.tsx", "values with provenance, masked sensitive values, confirm and edit; API failures; resolving a conflict by candidate; editing a suggestion and saving it; real counts from the API", "5"],
        ["ConfidenceBadge.test.tsx", "high, medium, low and conflict badges; text override", "5"],
        ["Total", "", "22"],
    ], [1.45, 3.85, 0.45], font=9.5, align=["l", "l", "c"])
    R.table("ext_tests", [
        ["File", "Scenarios", "Tests"],
        ["detector.test.ts", "controls described without reading values; aria-labelledby, aria-describedby, sections, nearby text; skipping of password, payment, one-time-code, CAPTCHA, hidden, disabled and read-only controls; zero-size and off-screen honeypots; stable identifiers; radio grouping; select options; long attributes capped; hidden prompt-injection field in an adversarial fixture ignored", "9"],
        ["autofill.test.ts", "text and textarea through the native setter; framework-controlled inputs; select by exact value or label, never substring; checkboxes by click; radio by option; vanished, disabled or unknown fields reported; page-rejected values reported; form never submitted", "8"],
        ["api.test.ts", "bearer token and unwrapping; error envelope to ApiError and token cleared on 401; GET retried on server errors, POST never retried; network failure and timeout messages; refusal without a token", "5"],
        ["flow.test.ts", "only ready values pre-selected; decisions map to approve, edit, skip and ignore protected fields", "2"],
        ["Total", "", "24"],
    ], [1.45, 3.85, 0.45], font=9.5, align=["l", "l", "c"])

    R.h2("6.4 Integration and Browser End-to-End Tests")
    R.p(
        "Three integration tests (marker chroma) run against a real ChromaDB service with real all-MiniLM-L6-v2 embeddings. They verify that indexing, querying "
        "and deletion are isolated per user, that a collection created with a different embedding model is detected, and that an unreachable ChromaDB "
        "raises an error instead of falling back to another store."
    )
    R.p(
        "One Playwright test runs the built extension in real Chromium against the isolated Compose stack (mock LLM, test database). It uploads a "
        "synthetic document, opens the fixture sample-application-form.html, drives the popup through scan, analysis and review, approves the fill, "
        "asserts the values in the page and asserts that the form was not submitted. A second fixture, adversarial-form.html, contains a hidden "
        "prompt-injection field that the detector must ignore; it is covered by a detector unit test."
    )

    R.h2("6.5 Test Cases")
    R.p(
        R.t("tc") + " lists representative test cases in the conventional format. The expected results are the assertions of the named automated tests, and the actual "
        "result is the outcome recorded in the run of " + R.t("results") + ". The identifiers are for this report."
    )
    R.table("tc", [
        ["ID", "Module", "Steps", "Expected result", "Result"],
        ["TC-01", "Auth", "Log in with a wrong password and with an unknown e-mail", "Same 401 error for both; no account enumeration", "Pass"],
        ["TC-02", "Auth", "Send a token in the query string", "Request refused", "Pass"],
        ["TC-03", "Upload", "Upload an .exe renamed or a PDF whose bytes are not PDF", "400 invalid file; nothing stored", "Pass"],
        ["TC-04", "Upload", "Upload the same file twice", "Second upload returns a duplicate error", "Pass"],
        ["TC-05", "Processing", "Upload a scanned PDF with no OCR installed", "Status requires_review with message", "Pass"],
        ["TC-06", "Processing", "Make the vector store fail during indexing", "Document processed, facts kept, index_status failed", "Pass"],
        ["TC-07", "Conflicts", "Two documents give different dates of birth", "Conflict listed with both candidates and sources", "Pass"],
        ["TC-08", "Classifier", "Label “Name” inside a father’s section", "User’s own name is not used", "Pass"],
        ["TC-09", "Pipeline", "Field with no matching fact and no evidence", "Status missing_information; no value invented", "Pass"],
        ["TC-10", "Pipeline", "Field text contains “ignore previous instructions”", "Field quarantined; not sent to the LLM", "Pass"],
        ["TC-11", "RAG", "Model returns a value absent from the cited chunk", "Value discarded", "Pass"],
        ["TC-12", "RAG", "Chunk contains injected instructions", "Chunk never reaches the LLM", "Pass"],
        ["TC-13", "Isolation", "User B requests user A’s document, facts, session", "Not found or refused", "Pass"],
        ["TC-14", "Deletion", "Delete a document while Chroma is down", "503 before any MongoDB record is removed", "Pass"],
        ["TC-15", "Extension", "Scan a page with password, hidden and honeypot fields", "Those controls are not listed", "Pass"],
        ["TC-16", "Extension", "Fill a framework-controlled input and a drop-down", "Value kept; option chosen by exact match; verified", "Pass"],
        ["TC-17", "Extension", "Run the full flow in Chromium", "Values filled; form not submitted", "Pass"],
    ], [0.55, 0.8, 1.75, 1.8, 0.65], font=9, align=["l", "l", "l", "l", "c"])

    R.h2("6.6 Test Results")
    rr = _rerun()
    R.p(
        R.t("results") + " reproduces the recorded run in docs/TEST_RESULTS.md (13 October 2026, Windows, Python 3.11, Node 22, Docker Compose and Chromium; backend tests "
        "used the mock LLM). All executed tests passed. The real-provider tests were not run because they are opt-in and can incur charges."
    )
    R.table("results", [
        ["Check", "Environment", "Result"],
        ["ruff check backend tests", "Local", "Passed"],
        ["black --check backend tests", "Local", "Passed (111 files unchanged)"],
        ["pytest (default)", "Mock LLM, temporary database", "146 passed, 7 deselected"],
        ["Real ChromaDB integration (marker chroma)", "Compose Chroma, real embeddings", "3 passed"],
        ["Dashboard Vitest", "jsdom", "22 passed"],
        ["Extension Vitest", "jsdom", "24 passed"],
        ["Type check; build", "Dashboard and extension", "Passed"],
        ["Playwright browser end-to-end", "Real Chromium, isolated Compose stack", "1 passed"],
        ["Compose configuration (development and test)", "docker compose config", "Both parsed"],
        ["Real-provider LLM tests", "Opt-in", "Not run"],
        ["Total executed automated tests", "", "196 passed, 0 failed"],
    ], [2.4, 2.0, 1.35], font=10)
    if rr:
        R.p(rr["text"])
    else:
        R.p(
            "The repository was extended after that recorded run by a commit that integrates optional PaddleOCR support. This report does not claim a "
            "recorded re-run for the final commit beyond what is stated above."
        )
    R.p(
        "No timing or performance measurements were taken for the test runs, so the report gives none. Likewise, no measurement of extraction accuracy "
        "on a corpus of real documents was made: the tests check behaviour on synthetic examples, and the accuracy of the language-model tracks on real "
        "documents has not been evaluated."
    )

    R.h2("6.7 Security-Related Verification")
    R.bullets([
        "Authentication:: wrong and unknown credentials give one error; expired, malformed, revoked and wrong-type tokens and tokens in query strings are refused; the login limiter returns 429; account deletion revokes the token.",
        "Isolation:: tests confirm that documents, facts, conflicts, sessions, recommendations, memories, RAG search and structured retrieval are scoped to the caller, and the Chroma integration tests confirm isolation in the real vector store.",
        "Input validation:: executable, forged, binary, empty, oversized, duplicate and content-type-mismatched uploads are rejected.",
        "Injection:: patterns are detected without flagging ordinary labels; untrusted content cannot close its block; injected field text and injected chunks never reach the model.",
        "Grounding:: values absent from the cited evidence are discarded, and uncited answers become insufficient evidence.",
        "Browser safety:: sensitive, hidden, off-screen and honeypot controls are skipped, no value is read, nothing is submitted, and the real-browser test confirms the form was not submitted.",
        "Not tested:: penetration testing, load testing, fuzzing of the parsers and accessibility testing were not carried out.",
    ])
    R.h2("6.8 Discussion")
    R.p(
        "The suite is strongest on behaviours the design promises: refusal paths, isolation, grounding and the user-approval rule each have named tests. "
        "It is weaker on measurements: there is no accuracy benchmark for extraction or classification on real documents, no performance test and no test "
        "of the optional OCR path, because the OCR engine is optional and was added in the final commit. These gaps are listed in Chapter 7 as future work."
    )
    R.summary(
        "The system was tested at four levels: 146 backend tests with a mock LLM, 3 integration tests against real ChromaDB, 22 dashboard tests, 24 extension "
        "tests and one browser end-to-end test on an isolated stack. All 196 executed tests passed in the recorded run. Real-provider tests, performance tests "
        "and accuracy benchmarks were not run, and the report claims nothing about them."
    )
