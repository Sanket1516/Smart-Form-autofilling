# -*- coding: utf-8 -*-
from refs import c


def build(R):
    R.chapter(3, "Problem Definition & Proposed Solution")
    R.p("This chapter turns the gap found in Chapter 2 into a precise problem, compares current practice with the proposed solution, describes the "
        "solution’s workflow, and lists the requirements and the technologies chosen to meet them.")

    R.h2("3.1 Problem Definition")
    R.p("A user uploads a set of personal documents. The system must derive from them a set of **facts**, where each fact records a concept from the "
        "ontology (for example *Class 12 percentage*), its value, the source document and page, the evidence text and a confidence score. Later, "
        "for any web form the user opens, the system must produce for each field a **recommendation**: a status (ready, needs review, missing or "
        "blocked), an optional value, a reason and a source. A solution is acceptable only if it meets the following constraints:")
    R.numbered([
        "Evidence:: a value is proposed only if it is a stored fact or appears word for word in a document passage that the system can cite.",
        "Conflict transparency:: if documents give different values for a single-valued concept, nothing is filled automatically; the candidates are shown.",
        "Sensitivity:: passwords, payment details, OTPs and CAPTCHAs are never filled, and identity or financial values always need confirmation.",
        "Consent:: the page changes only after the user approves each field, and the system never submits the form.",
        "Isolation and untrusted input:: no user can see another user’s data, and text from web pages and documents is treated as data, never as instructions.",
    ])

    R.h2("3.2 Existing System and Its Limitations")
    R.p("Today a person types every value by hand, copies values from documents, or relies on browser autofill. " + R.t("existing") + " compares "
        "this practice with the proposed system on the points that matter for the problem definition.")
    R.table("existing", [
        ["Aspect", "Existing practice (manual typing or browser autofill)", "Proposed system"],
        ["Source of values", "Typed by the user or remembered from earlier forms", "Facts extracted from the user’s own documents"],
        ["Matching fields", "Technical field names and simple rules", "Ontology aliases and nearby text, then an LLM for unclear fields"],
        ["Evidence", "None", "Document, page, evidence text and confidence"],
        ["Disagreeing values", "One value chosen without notice", "Conflict shown; the user chooses"],
        ["Sensitive and hidden fields", "May be filled silently " + c("autofill"), "Skipped by the extension and blocked again by the server"],
        ["After filling", "No check", "Each value read back from the page and reported"],
        ["Submission", "By the user or the page", "Never by the system"],
    ], [1.35, 2.15, 2.27], font=10)

    R.h2("3.3 Proposed Solution")
    R.p("The solution works in two phases, shown in " + R.f("overview") + ". Phase A (steps 1–5) runs once for each uploaded document and "
        "builds the user’s profile. Phase B (steps 6–10) runs every time the user opens a web form and turns the profile into reviewed, filled "
        "values. Both phases share one knowledge store.")
    R.h3("3.3.1 Workflow Summary")
    R.p("**Phase A: build the user profile.** (1) The user uploads a PDF, DOCX, TXT or image file. (2) The text is extracted; scanned images "
        "and image-only PDF pages are read by OCR (RapidOCR with PP-OCR models). (3) The type of document is identified, for example a PAN card, "
        "a passport or a Class 12 mark sheet. (4) Facts are extracted by rules, with an optional LLM call for structured information. (5) The "
        "facts are merged with those already stored and kept, with their evidence, as the user’s profile. Because this processing can take "
        "several seconds, it runs in the background, and the dashboard shows its progress.")
    R.p("**Knowledge storage.** Phase A stores the structured facts in MongoDB and the document text, split into chunks, in ChromaDB for "
        "semantic search. Phase B retrieves from both.")
    R.p("**Phase B: fill a form.** When the user opens a web form, (6) the extension scans the form’s fields and sends their description, but "
        "never their current values, to the server. (7) The server classifies each field, for example as a name, a date of birth or an address, "
        "using rules first and an LLM only for unclear fields. (8) It finds the best value in the profile and, if needed, in the document text "
        "through semantic retrieval (RAG), and decides whether the value is ready or needs review. (9) The user reviews the suggestions in the "
        "extension popup and approves each field. (10) The extension fills only the approved fields and reads each value back to verify that "
        "the page kept it. The form is never submitted by the system; the user presses the form’s own Submit button.")
    R.fig("overview", width=5.6)
    R.h3("3.3.2 Advantages of the Proposed Solution")
    R.bullets([
        "Traceable:: every suggestion states where it came from and how certain the system is.",
        "Fewer errors:: values are formatted to what each field expects, such as a date pattern or one option of a drop-down list.",
        "Safe by design:: sensitive and hidden fields are skipped in two places, and the form is never submitted by the system.",
        "Low cost:: the LLM is called only when the rules cannot decide, and the system still works, with fewer features, without any LLM.",
    ])

    R.h2("3.4 Requirements")
    R.p(R.t("freq") + " lists the functional requirements and the part of the system that implements each.")
    R.table("freq", [
        ["ID", "Functional requirement", "Implemented in"],
        ["FR1", "Register, sign in, sign out and delete the account", "Authentication service"],
        ["FR2", "Upload PDF, DOCX, TXT, PNG or JPG files with type, size and duplicate checks", "Document service"],
        ["FR3", "Process documents in the background and show stage and progress", "Celery worker and pipeline"],
        ["FR4", "Read text, using OCR for scanned images", "Text extractor (RapidOCR)"],
        ["FR5", "Identify the document type (17 Indian types)", "Document registry"],
        ["FR6", "Extract facts with source, page, evidence and confidence", "Rule-based and LLM extractors"],
        ["FR7", "View, add, edit and confirm profile values; resolve conflicts", "Fact service and dashboard"],
        ["FR8", "Answer questions about the documents with cited sources", "Ask Documents service"],
        ["FR9", "Detect form fields, skipping sensitive and hidden ones", "Extension content script"],
        ["FR10", "Map fields to concepts and recommend values with reasons", "Form-fill LangGraph pipeline"],
        ["FR11", "Record the user’s decisions; fill approved values and verify them", "Extension popup and content script"],
        ["FR12", "Delete all data, with or without the account; report service health", "User-data and health services"],
    ], [0.5, 3.3, 1.97], font=10)
    R.p("The main non-functional requirements are: **security** (hashed passwords, short-lived tokens, per-user isolation); **privacy** (the "
        "extension reads field descriptions, never field values); **reliability** (failures are reported, never hidden behind invented values); "
        "**responsiveness** (form analysis returns at once and the popup checks progress every second); **maintainability** (automated tests and a "
        "continuous-integration workflow); and **portability** (the whole system starts with one Docker Compose command).")

    R.h2("3.5 Technology Stack and Justification")
    R.p(R.t("stack") + " lists the technology used in each layer and the reason for choosing it. MongoDB, defined in Section 2.1.1, was chosen "
        "because each fact has a different shape and every query is made for one user. Software products are not cited; their versions are "
        "listed in Appendix C.")
    R.table("stack", [
        ["Layer", "Technology", "Reason for the choice"],
        ["Server (API)", "Python 3.11, FastAPI, Pydantic", "Fast asynchronous web framework with typed, validated requests"],
        ["Fact store", "MongoDB 8", "Flexible documents; efficient per-user queries"],
        ["Search index", "ChromaDB with all-MiniLM-L6-v2 " + c("sbert", "minilm"), "Self-hosted vector search; small embedding model that runs on a CPU"],
        ["OCR", "RapidOCR on ONNX Runtime (PP-OCR models, DB text detection " + c("dbnet") + ")", "Accurate English OCR with low memory use"],
        ["Form pipeline", "LangGraph", "Explicit graph of steps with conditions"],
        ["Language model", "Google Gemini; optional local model through Ollama", "Best measured accuracy; local fallback keeps working offline"],
        ["Background jobs", "Celery with Redis", "Long processing does not block the user"],
        ["Security", "bcrypt " + c("bcrypt") + ", JSON Web Tokens", "Salted password hashing; short-lived signed tokens"],
        ["Dashboard", "React 19, TypeScript, Vite", "Component-based, type-checked user interface"],
        ["Extension", "Chrome Manifest V3, React 18", "Current extension platform with on-demand page access"],
        ["Deployment", "Docker Compose, Nginx", "One command starts every service"],
        ["Testing", "pytest, Vitest, Playwright", "Unit, integration and real-browser tests"],
    ], [1.1, 2.1, 2.57], font=9.5)

    R.h2("3.6 Assumptions and Constraints")
    R.bullets([
        "Documents are in English (Indian bilingual documents are read from their English half); handwriting and Indian scripts are not read.",
        "A configured LLM improves classification of unusual fields and the wording of answers; without one, rule-based extraction, matching and "
        "filling still work.",
        "The system runs on one computer: development and all tests used a laptop with an Intel Core i5-13450HX processor and 16 GB of memory (15.7 GB usable), with "
        "no graphics processor needed.",
        "The user is responsible for the final content of every form; the system assists but never submits.",
    ])
    R.summary("The problem was defined with five acceptance constraints. Current practice was compared with the proposed two-phase solution, whose "
              "workflow and advantages were explained. Twelve functional requirements, the non-functional requirements and the technology stack "
              "with its justification were listed, together with the main assumptions.")
