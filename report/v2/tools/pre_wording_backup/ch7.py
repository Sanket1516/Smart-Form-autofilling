# -*- coding: utf-8 -*-
from refs import c


def build(R):
    R.chapter(7, "Conclusion & Future Work")
    R.p("This chapter gives the single conclusion of the report: what was built, how far the five objectives of Chapter 1 were met, what was "
        "learned, which limitations remain, and what should be done next.")

    R.h2("7.1 Conclusion")
    R.p("The project set out to build a privacy-first assistant that fills web forms from a person’s own documents while keeping every value "
        "traceable and every decision with the user. The resulting Smart Form Auto-Filling System consists of a FastAPI backend with MongoDB and "
        "ChromaDB, a React dashboard and a Chrome extension, and starts with a single Docker Compose command. Documents in PDF, Word, text and image "
        "form are read, classified into seventeen Indian document types and converted into facts from a 220-concept ontology, each with its "
        "evidence. A seven-step LangGraph pipeline matches form fields to these facts, and the extension fills only the values the user approves.")
    R.h3("7.1.1 Achievement of Objectives")
    R.table("objectives", intro=R.t("objectives") + " compares each objective with the evidence from Chapters 5 and 6.", rows=[
        ["Objective", "Status", "Evidence"],
        ["1. Document understanding with evidence", "Achieved", "Type identified for 15/15 documents; 97.0% of fields exact (" + R.t("eval") + ")"],
        ["2. Verified profile with conflicts", "Achieved", "Conflicts shown with sources (" + R.f("conflicts") + "); test TC-06"],
        ["3. Semantic form filling", "Achieved, with errors", "112 correct and 9 incorrect fills; 84 held for review (" + R.t("autofill") + ")"],
        ["4. Grounded question answering", "Achieved", "28/28 questions correct with sources (" + R.t("eval") + ")"],
        ["5. Safety and verification", "Achieved", "No form submitted; 453/453 tests passed (" + R.t("results") + ")"],
    ], widths=[2.05, 1.05, 2.67], font=10)
    R.h3("7.1.2 Principal Findings")
    R.bullets([
        "Rules before models:: deterministic matching over a shared ontology resolves most fields, so the language model is needed only for the "
        "unclear remainder, which keeps cost, delay and risk low.",
        "Disagreements must be visible:: real document sets disagree; showing the conflict was more reliable than any automatic choice.",
        "Grounding checks are cheap and effective:: requiring a value to appear in the cited text removes a class of invented answers without a "
        "second model call.",
        "Caution has a price:: holding 84 values for review avoided wrong fills but asks more of the user; the remaining errors show where field "
        "matching needs more context.",
    ])

    R.h2("7.2 Limitations and Future Work")
    R.p(R.t("limits") + " pairs each known limitation with the work proposed to address it.")
    R.table("limits", [
        ["Current limitation", "Proposed future work"],
        ["Accuracy measured only on synthetic documents and forms", "Build an anonymised benchmark of real documents and forms and report accuracy per concept"],
        ["Errors with similar fields (correspondence and permanent address, household relationships)", "Use section headings and the form’s structure more strongly, and ask the user when two concepts compete"],
        ["English OCR only; Indian scripts and handwriting are not read", "Add multilingual OCR models and evaluate them on real scans"],
        ["Chrome only; fields added after the scan need a new scan", "Port to other Manifest V3 browsers; watch the page for new fields and multi-step forms"],
        ["Examination requirement profiles not verified against official bulletins", "Verify each profile against the current official notification before use"],
        ["No load, penetration or accessibility testing", "Add these tests and run the paid-provider tests with synthetic data"],
    ], [2.6, 3.17], font=9.5)
    R.p("Three further extensions are promising. First, a fully local language model would keep all document text on the user’s computer "
        "(an optional local fallback exists but is less accurate). Second, graph-based retrieval such "
        "as HippoRAG " + c("hipporag") + " could answer questions that combine several facts. Third, a per-site consent list would let the user "
        "trust selected portals while keeping the review step for every fill.")
    R.summary("All five objectives were met and all 453 executed tests passed. The main limitations, synthetic-only evaluation, "
              "confusion between similar fields and English-only OCR, define the future work.")
