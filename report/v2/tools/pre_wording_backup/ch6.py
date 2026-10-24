# -*- coding: utf-8 -*-


def build(R):
    R.chapter(6, "Testing")
    R.p("This chapter describes how the system was tested: the strategy and environment, the test inventory, representative test cases, and the "
        "results. Every number is taken from an actual test run; nothing was estimated. Tests that were not run are stated as such.")

    R.h2("6.1 Testing Strategy")
    R.p("Testing is organised in four levels. **Unit and API tests** check one module or one server endpoint at a time. **Integration tests** run "
        "against a real ChromaDB service with the real embedding model. **Browser end-to-end tests** load the built extension into a real Chromium "
        "browser with Playwright and fill a test form through the whole system. Finally, the **evaluation** of Chapter 5 "
        "measures accuracy on synthetic documents and forms.")
    R.p("The default backend test run never touches the developer’s own data and never calls a paid service. The test configuration forces a "
        "*mock* language model (a stand-in that returns fixed, valid answers), a temporary file store and a randomly named database that is deleted "
        "afterwards. Tests that need ChromaDB or a real LLM provider are marked and run only on request. A continuous-integration workflow runs the "
        "unit, integration, dashboard, extension and browser tests on every change pushed to the repository.")

    R.h2("6.2 Test Environment")
    R.p("All tests were run on a laptop with an Intel Core i5-13450HX processor (10 cores) and 16 GB of memory (15.7 GB usable), running Windows 11 Home, Python "
        "3.11.9, Node.js 22.14.0, Docker 29.4.0 with Compose v2, MongoDB 8 and ChromaDB in Docker containers, and Playwright-managed Chromium. "
        "Backend tests use pytest; dashboard and extension tests use Vitest with a simulated browser page (jsdom).")

    R.h2("6.3 Test Inventory")
    R.p(R.t("inventory") + " groups the 301 backend tests by area, with the number of tests in each area, and lists the dashboard and extension "
        "suites. The counts were collected from the test runner itself.")
    R.table("inventory", [
        ["Area", "What is tested", "Tests"],
        ["Accounts and configuration", "Registration, login, token expiry and revocation, rate limits, unsafe settings rejected", "21"],
        ["Documents and processing", "Valid and invalid uploads, duplicates, corrupted files, reprocessing, deletion, isolation", "19"],
        ["Indian documents and OCR", "17 document types, identifiers, mark-sheet tables, OCR layout, chunking", "93"],
        ["Extraction and ontology", "Rule-based extraction, normalisation, merging, alias matching", "32"],
        ["Profile and conflicts", "Conflict detection, resolution, corrections, deleting all data", "10"],
        ["Form filling", "Field classification, recommendations, formatting, decisions, exam forms", "62"],
        ["Ask Documents and RAG", "Question planning, grounded answers, sources, cross-user protection", "41"],
        ["LLM and prompt safety", "Injection patterns, untrusted blocks, provider errors and retries", "16"],
        ["Platform", "Health checks, error format, cross-origin rules, extension manifest", "7"],
        ["Backend total", "", "301"],
        ["Dashboard (7 files)", "Sign-in, documents, profile, Ask page, exam readiness, demo data, badges", "30"],
        ["Extension (8 files)", "Field detection, filling, uploads, document types, API client, popup flow", "112"],
    ], [1.6, 3.55, 0.62], font=9.5, align=["l", "l", "c"])

    R.h2("6.4 Test Cases")
    R.p(R.t("cases") + " lists representative test cases. The expected result is the assertion made by the named automated test, and the actual "
        "result is the outcome of the run of 22 October 2026.")
    R.table("cases", [
        ["ID", "Test case (automated test)", "Expected result", "Actual result", "Status"],
        ["TC-01", "Wrong password and unknown e-mail", "Same error for both", "Same 401 error", "Pass"],
        ["TC-02", "Token sent in the query string", "Request refused", "Refused", "Pass"],
        ["TC-03", "Upload a renamed executable or fake PDF", "Rejected; nothing stored", "Rejected", "Pass"],
        ["TC-04", "Upload the same file twice", "Duplicate reported", "Duplicate reported", "Pass"],
        ["TC-05", "Index fails during processing", "Facts kept; index marked failed", "As expected", "Pass"],
        ["TC-06", "Two documents disagree on a value", "Conflict listed with sources", "Listed with sources", "Pass"],
        ["TC-07", "“Name” inside a father’s section", "User’s own name not used", "Not used", "Pass"],
        ["TC-08", "Field with no fact and no evidence", "Missing; no value invented", "Missing", "Pass"],
        ["TC-09", "Field text says “ignore previous instructions”", "Field quarantined; not sent to LLM", "Quarantined", "Pass"],
        ["TC-10", "LLM value not present in cited text", "Value discarded", "Discarded", "Pass"],
        ["TC-11", "Class 12 question with both mark sheets", "Never answered from Class 10", "Correct mark sheet", "Pass"],
        ["TC-12", "User B asks for user A’s data", "Refused or not found", "Refused", "Pass"],
        ["TC-13", "Page with password, hidden and honeypot fields", "Those fields not listed", "Not listed", "Pass"],
        ["TC-14", "Fill a framework-controlled input", "Value kept and verified", "Kept and verified", "Pass"],
        ["TC-15", "Complete fill in real Chromium", "Values filled; form not submitted", "Not submitted", "Pass"],
    ], [0.5, 1.75, 1.45, 1.27, 0.55], font=9, align=["l", "l", "l", "l", "c"])

    R.h2("6.5 Test Results")
    R.p(R.t("results") + " summarises the results. For each suite it shows the total number of test cases, how many passed and failed, and the pass "
        "percentage, as the reviewer requested. Seven backend tests are deselected by default: three need ChromaDB and are run separately (row 2), "
        "and four call a paid LLM provider and were not run.")
    R.table("results", [
        ["Test suite (tool)", "Run date", "Total", "Passed", "Failed", "Pass %"],
        ["Backend unit and API (pytest, mock LLM)", "22 Oct 2026", "301", "301", "0", "100%"],
        ["Vector-database integration (pytest, real ChromaDB)", "22 Oct 2026", "3", "3", "0", "100%"],
        ["Dashboard (Vitest)", "22 Oct 2026", "30", "30", "0", "100%"],
        ["Extension (Vitest)", "22 Oct 2026", "112", "112", "0", "100%"],
        ["Browser end-to-end (Playwright, Chromium)", "15 Oct 2026", "7", "7", "0", "100%"],
        ["Real LLM provider tests (opt-in)", "Not run", "4", "–", "–", "–"],
        ["**Total executed**", "", "**453**", "**453**", "**0**", "**100%**"],
    ], [2.35, 0.95, 0.6, 0.62, 0.6, 0.65], font=9.5, align=["l", "c", "c", "c", "c", "c"])
    R.p("All 446 tests run on 22 October 2026 passed, and the seven browser tests passed in their recorded run of 15 October 2026; they were not "
        "repeated for this report. The evaluation of Chapter 5 is a separate measurement of accuracy and is not counted as test cases here.")

    R.h2("6.6 Discussion")
    R.p("The tests are strongest where the design makes promises: refusal paths, per-user isolation, grounding of LLM output and the rule that "
        "nothing is filled or submitted without the user. Penetration testing, load testing, accessibility testing and tests with the paid LLM "
        "provider were not carried out, and OCR was evaluated only on rendered synthetic images, not on real scans. These gaps are listed as "
        "future work in Chapter 7.")
    R.summary("The system was tested at four levels. On 22 October 2026, 301 backend, 3 vector-database, 30 dashboard and 112 extension tests all "
              "passed; the 7 browser end-to-end tests passed in the recorded run of 15 October 2026. In total 453 of 453 executed test cases "
              "passed and none failed. Real-provider, load and penetration tests were not run.")
