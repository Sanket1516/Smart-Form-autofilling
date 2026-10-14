# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    R.chapter(7, "Conclusion and Future Work")
    R.intro(
        "This chapter summarises the work, states how far the objectives of Chapter 1 were met, records the limitations that remain, and proposes future "
        "work. As the college format requires, the report has a single conclusion, and it is given here."
    )

    R.h2("7.1 Conclusion")
    R.p(
        "The project set out to build a privacy-first assistant that fills web forms from the user’s own documents while keeping every value traceable and every "
        "decision with the user. The resulting Smart Form Auto-Filling System consists of a FastAPI backend with MongoDB and ChromaDB, a React dashboard with "
        "eleven routes, and a Chrome Manifest V3 extension, deployable with a single Docker Compose project. Documents in four formats are parsed, facts are extracted "
        "by deterministic rules over a 91-concept ontology and, optionally, by a language model, and each fact keeps its origin, evidence text, page, method and "
        "confidence. Disagreements between documents are computed as conflicts and resolved by the user. A seven-node LangGraph pipeline classifies form fields "
        "and resolves values from the profile or from quoted document evidence, and the extension fills only the values that the user approves, verifies what the page kept, "
        "and never submits the form."
    )
    R.h3("Achievement of objectives")
    R.bullets([
        "Objective 1, parsing and extraction:: achieved for PDF, DOCX, TXT, PNG and JPG; scanned input needs the optional OCR engine.",
        "Objective 2, provenance:: achieved; every fact stores origin, evidence text, page, method and confidence.",
        "Objective 3, conflicts:: achieved; computed from active facts, resolved by the user, verified by tests and demonstrated in Chapter 5.",
        "Objective 4, classification:: achieved; deterministic rules first and one batched model call for the unresolved remainder.",
        "Objective 5, grounded values:: achieved; a value comes from the profile or from a quoted passage, and ungrounded values are discarded.",
        "Objective 6, thresholds and sensitivity:: achieved; confidence 0.75 for classification and 0.85 for ready, with confirmation for sensitive and inferred values.",
        "Objective 7, security:: achieved and tested for injection, isolation and token handling; residual risks are documented in Section 4.9.",
        "Objective 8, verification:: achieved; 196 automated tests passed in the recorded run. Real-provider tests, performance tests and accuracy benchmarks were not run.",
    ])
    R.h3("Principal findings")
    R.bullets([
        "Rules before models:: deterministic matching over a small ontology resolves the common fields, so the language model is needed only for the ambiguous remainder, which keeps cost and risk low.",
        "Conflicts must be first-class:: realistic users hold documents that disagree; surfacing the disagreement was more useful than any attempt to pick the right value automatically.",
        "Grounding checks are cheap and effective:: requiring a value or quotation to appear in the cited chunk removes a class of fabricated answers without a second model call.",
        "Verification after filling matters:: framework-controlled pages can discard a naive assignment, so the extension re-reads each field and reports the outcome.",
        "Honest limits:: the name heuristic and the conflict-unaware RAG answer showed in Chapter 5 that the evidence trail lets the user catch the system’s mistakes, which is the intended role of the design.",
    ])
    R.p(
        "In short, the project demonstrates that a document-driven, evidence-preserving and human-approved autofill assistant can be built from open-source "
        "components and verified by automated tests. It does not claim measured accuracy on real-world documents or on arbitrary websites; that evaluation "
        "remains to be done."
    )

    R.h2("7.2 Limitations")
    R.p(
        "The limitations stated in Section 3.8 and discovered during testing and snapshotting are summarised here together with the proposed work. "
        + R.t("limits") + " pairs each limitation with a proposed improvement."
    )
    R.table("limits", [
        ["Current limitation", "Proposed future work"],
        ["No accuracy evaluation of extraction, classification or OCR on a corpus of real documents and real forms", "Build a labelled benchmark of anonymised documents and forms; report precision and recall per concept; compare rule-only, LLM-only and combined tracks"],
        ["Scanned documents need the optional PaddleOCR engine, which is large and not covered by a real-engine test", "Add an OCR integration test and measure accuracy; consider a lighter engine"],
        ["Ontology of 91 concepts; fields with no concept are left for the user", "Extend and localise the ontology, including regional languages; let the user map unknown fields and learn the mapping"],
        ["Static scan: fields added after the scan need a manual re-scan", "Observe DOM mutations and support multi-step forms and iframes"],
        ["Chrome-only extension", "Port to Firefox and other Manifest V3 browsers; consider a mobile companion"],
        ["Name heuristic can propose a title line as a name", "Strengthen header-word rules or require confirmation before using any inferred name"],
        ["RAG answers are not aware of conflicts", "Warn in the answer when the retrieved concept has a conflict, and link to the Conflicts page"],
        ["In-process rate limiting does not span replicas", "Use a shared limiter backend or edge rate limiting"],
        ["Dashboard token in local storage", "Move to an HttpOnly cookie with CSRF protection, or add refresh-token rotation"],
        ["No performance, load or accessibility tests", "Add load tests for upload and analysis, and accessibility audits of the dashboard and popup"],
        ["Real-provider tests not run", "Run the opt-in suite with synthetic data and record provider-specific behaviour"],
        ["Personal files committed earlier remain in Git history", "Rewrite history in a coordinated clean-up and rotate any credential that was ever committed"],
    ], [2.9, 2.85], font=9.5)

    R.h2("7.3 Future Work")
    R.numbered([
        "**Evaluation first.** Build the benchmark described above, because every other improvement should be judged against measured accuracy.",
        "**Smarter conflict handling.** Suggest the more recent or more authoritative document type for a concept (for example a passport over a résumé for a date of birth) while still asking the user to confirm.",
        "**Richer retrieval.** Evaluate graph-based memory such as HippoRAG-style retrieval " + c("hipporag") + " for questions that need several facts, and add a conflict-aware answer step.",
        "**Privacy-stronger models.** Support a local or on-device language model so that no document text leaves the machine, and local embedding is already the default.",
        "**Per-site consent.** Let the user keep a list of sites on which the extension may run without re-granting permission, while keeping review before fill.",
        "**More forms.** Handle multi-step wizards, iframes, date pickers and custom drop-down widgets, and extend value formatting to more input conventions.",
        "**Operational hardening.** Shared rate limiting, backup and retention policy, secret scanning in CI, and a hardened production deployment with TLS in front.",
    ])
    R.summary(
        "The work met its objectives: an auditable, human-approved pipeline from personal documents to filled forms, verified by 196 passing automated tests. "
        "The remaining limitations were listed with proposed work, led by an evaluation of accuracy on real documents and forms."
    )
