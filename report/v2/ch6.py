# -*- coding: utf-8 -*-


def build(R):
    R.chapter(6, "Testing")
    R.p("This chapter describes how the system was tested, covering the strategy and environment, the test inventory, representative test cases and the "
        "results. It then assesses how far the objectives of Chapter 1 were achieved and states the principal findings. Every reported figure "
        "is taken from the recorded test runs.")

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
        "Backend tests use pytest, and dashboard and extension tests use Vitest with a simulated browser page (jsdom).")

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
        "result is the outcome recorded for that test.")
    R.table("cases", [
        ["ID", "Test case (automated test)", "Expected result", "Actual result", "Status"],
        ["TC-01", "Wrong password and unknown e-mail", "Same error for both", "Same 401 error", "Pass"],
        ["TC-02", "Token sent in the query string", "Request refused", "Refused", "Pass"],
        ["TC-03", "Upload a renamed executable or fake PDF", "Rejected, nothing stored", "Rejected", "Pass"],
        ["TC-04", "Upload the same file twice", "Duplicate reported", "Duplicate reported", "Pass"],
        ["TC-05", "Index fails during processing", "Facts kept, index marked failed", "As expected", "Pass"],
        ["TC-06", "Two documents disagree on a value", "Conflict listed with sources", "Listed with sources", "Pass"],
        ["TC-07", "“Name” inside a father’s section", "User’s own name not used", "Not used", "Pass"],
        ["TC-08", "Field with no fact and no evidence", "Missing, no value invented", "Missing", "Pass"],
        ["TC-09", "Field text says “ignore previous instructions”", "Field quarantined, not sent to LLM", "Quarantined", "Pass"],
        ["TC-10", "LLM value not present in cited text", "Value discarded", "Discarded", "Pass"],
        ["TC-11", "Class 12 question with both mark sheets", "Never answered from Class 10", "Correct mark sheet", "Pass"],
        ["TC-12", "User B asks for user A’s data", "Refused or not found", "Refused", "Pass"],
        ["TC-13", "Page with password, hidden and honeypot fields", "Those fields not listed", "Not listed", "Pass"],
        ["TC-14", "Fill a framework-controlled input", "Value kept and verified", "Kept and verified", "Pass"],
        ["TC-15", "Complete fill in real Chromium", "Values filled, form not submitted", "Not submitted", "Pass"],
    ], [0.5, 1.75, 1.45, 1.27, 0.55], font=9, align=["l", "l", "l", "l", "c"])

    R.h2("6.5 Test Results")
    R.p(R.t("results") + " summarises the recorded results of the executed test suites. For each suite it gives the number of test cases, the "
        "number that passed and failed, and the pass percentage, calculated as the number passed divided by the number executed, multiplied by "
        "100. The vector-database tests need a running ChromaDB service and are therefore run as a separate suite (row 2).")
    R.table("results", [
        ["Test suite (tool)", "Total", "Passed", "Failed", "Pass %"],
        ["Backend unit and API (pytest, mock LLM)", "301", "301", "0", "100%"],
        ["Vector-database integration (pytest, real ChromaDB)", "3", "3", "0", "100%"],
        ["Dashboard (Vitest)", "30", "30", "0", "100%"],
        ["Extension (Vitest)", "112", "112", "0", "100%"],
        ["**Subtotal (final recorded test run)**", "**446**", "**446**", "**0**", "**100%**"],
        ["Browser end-to-end (Playwright, Chromium), earlier recorded run", "7", "7", "0", "100%"],
        ["**Total of recorded results**", "**453**", "**453**", "**0**", "**100%**"],
    ], [2.87, 0.7, 0.75, 0.7, 0.75], font=9.5, align=["l", "c", "c", "c", "c"])
    R.p("All 446 unit, API, integration, dashboard and extension tests passed in the final recorded test run (301 + 3 + 30 + 112 = 446). The "
        "seven browser end-to-end tests, which exercise the built extension in a real Chromium browser, passed in an earlier recorded run and are "
        "reported from that record. Together, the recorded results comprise 453 test cases, all of which passed, a pass percentage of "
        "453\u00a0/\u00a0453\u00a0=\u00a0100%. Four optional tests that call a paid LLM provider were not executed and are therefore not "
        "included in these figures. The accuracy evaluation of Chapter 5 is reported separately and is not counted here.")

    R.h2("6.6 Discussion")
    R.p("The test suites validate the guarantees on which the design relies, namely refusal of invalid requests, per-user isolation, grounding of LLM "
        "output and the rule that nothing is filled or submitted without the user. The consistent success of these suites shows that the "
        "implemented functionality behaves as specified. Penetration, load and accessibility testing and OCR evaluation on real scans lie beyond "
        "the scope of this phase and are addressed as future work in Chapter 7.")

    R.h2("6.7 Achievement of Objectives")
    R.table("objectives", intro=R.t("objectives") + " compares each objective with the evidence from Chapter 5 and from the tests of this chapter.", rows=[
        ["Objective", "Status", "Evidence"],
        ["1. Document understanding with evidence", "Achieved", "Type identified for 15/15 documents, 97.0% of fields exact (" + R.t("eval") + ")"],
        ["2. Verified profile with conflicts", "Achieved", "Conflicts shown with sources (" + R.f("conflicts") + "), test TC-06"],
        ["3. Semantic form filling", "Achieved, with errors", "112 correct and 9 incorrect fills, 84 held for review (" + R.t("autofill") + ")"],
        ["4. Grounded question answering", "Achieved", "28/28 questions correct with sources (" + R.t("eval") + ")"],
        ["5. Safety and verification", "Achieved", "No form submitted, all 453 recorded test cases passed (" + R.t("results") + ")"],
    ], widths=[2.05, 1.05, 2.67], font=10)

    R.h2("6.8 Principal Findings")
    R.bullets([
        "Rules before models:: deterministic matching over a shared ontology resolves most fields, so the language model is needed only for the "
        "unclear remainder, which keeps cost, delay and risk low.",
        "Disagreements must be visible:: real document sets often disagree, and showing the conflict proved more reliable than any automatic choice.",
        "Grounding checks are cheap and effective:: requiring a value to appear in the cited text removes a class of invented answers without a "
        "second model call.",
        "Caution needs balance:: holding 84 values for review avoided wrong fills but asks more of the user, and the remaining errors show where "
        "field matching needs more context.",
    ])
    R.summary("The system was tested at four levels. All 446 unit, API, integration, dashboard and extension tests passed in the final recorded "
              "test run, and the seven browser end-to-end tests passed in an earlier recorded run, giving 453 passed test cases with no failures. "
              "Measured against this evidence and the results of Chapter 5, all five objectives were achieved, with a small number of form-filling "
              "errors identified for further improvement.")
