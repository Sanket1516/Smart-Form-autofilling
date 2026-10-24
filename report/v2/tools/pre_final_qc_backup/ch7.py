# -*- coding: utf-8 -*-
from refs import c


def build(R):
    R.chapter(7, "Conclusion & Future Work")
    R.p("This chapter concludes the report and sets out the remaining limitations together with the directions for future work.")

    R.h2("7.1 Conclusion")
    R.p("This work addressed the problem of filling web forms from a person’s own documents while keeping every value traceable and every "
        "decision under the user’s control. It presented the Smart Form Auto-Filling System, a privacy-first framework that combines document "
        "understanding, a shared ontology of personal-data concepts and retrieval-augmented generation with a browser extension that fills only "
        "the values the user approves.")
    R.p("The approach rests on a small set of principles. Documents, including scanned images, are converted into structured facts that remain linked to their "
        "source and evidence. Disagreements between documents are presented to the user as conflicts instead of being resolved silently. Form "
        "fields are matched to ontology concepts by deterministic rules first, a language model is consulted only for ambiguous fields, and a "
        "value is accepted only when it is grounded in stored evidence.")
    R.p("The evaluation on synthetic documents and forms, together with the automated test suites, showed that the objectives of the project were "
        "achieved. Document facts were extracted with high accuracy, questions about the documents were answered with correct sources, forms were "
        "filled with few errors, and no form was submitted without the user. The system consistently favoured caution, holding uncertain or "
        "sensitive values for review instead of filling them.")
    R.p("The work shows that evidence-grounded, user-approved form filling is a practical alternative both to conventional autofill and to "
        "autonomous web agents. Applying deterministic rules before a language model keeps cost and risk low, and simple grounding checks prevent "
        "invented values. Because the evaluation used synthetic data, the results describe the behaviour of the system on these cases rather than "
        "its accuracy on real documents, and the limitations below set the direction for further work.")

    R.h2("7.2 Limitations and Future Work")
    R.p(R.t("limits") + " pairs each known limitation with the work proposed to address it.")
    R.table("limits", [
        ["Current limitation", "Proposed future work"],
        ["Accuracy measured only on synthetic documents and forms", "Build an anonymised benchmark of real documents and forms and report accuracy per concept"],
        ["Errors with similar fields (correspondence and permanent address, household relationships)", "Use section headings and the form’s structure more strongly, and ask the user when two concepts compete"],
        ["English OCR only, and Indian scripts and handwriting are not read", "Add multilingual OCR models and evaluate them on real scans"],
        ["Chrome only, and fields added after the scan need a new scan", "Port to other Manifest V3 browsers, and watch the page for new fields and multi-step forms"],
        ["Examination requirement profiles not verified against official bulletins", "Verify each profile against the current official notification before use"],
        ["No load, penetration or accessibility testing", "Add these tests and run the paid-provider tests with synthetic data"],
    ], [2.6, 3.17], font=9.5)
    R.p("Three further extensions are promising. First, a fully local language model would keep all document text on the user’s computer "
        "(an optional local fallback exists but is less accurate). Second, graph-based retrieval such "
        "as HippoRAG " + c("hipporag") + " could answer questions that combine several facts. Third, a per-site consent list would let the user "
        "trust selected portals while keeping the review step for every fill.")
