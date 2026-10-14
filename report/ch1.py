# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    R.chapter(1, "Introduction")
    R.intro(
        "This chapter introduces the Smart Form Auto-Filling System. It explains why filling web forms from personal documents is a problem worth solving, "
        "what the project set out to do and what it deliberately leaves out, and how the remaining chapters of the report are organised. Every statement "
        "about the system in this report describes the implementation in the project repository, and features that are optional, partial or future are "
        "labelled as such."
    )

    R.h2("1.1 Background of the Project Topic")
    R.p(
        "Almost every service that a student or a working adult uses today starts with a web form. Admission portals ask for marks, board names and "
        "addresses; banks and insurers ask for identity numbers and income; government portals ask for the same name and date of birth that other "
        "portals asked for yesterday; and employers ask applicants to retype a résumé that they have already uploaded. The facts that these forms request are "
        "largely the same, and most of them already exist in documents the user holds: a mark sheet, an identity card, a résumé, a salary slip."
    )
    R.p(
        "Browsers try to reduce this effort with built-in autofill, which stores values a user has typed before and offers them again when a field looks "
        "similar. This helps with a postal address or an e-mail address, but it has three structural limits. It can only replay values that the user once "
        "typed into a form, so it cannot use the many facts that sit in uploaded documents. It matches fields mostly by HTML attributes and simple "
        "heuristics, so a label such as “Name of the guardian” or “Year of passing, Class XII” is easily mismatched. And it keeps no record of where a "
        "value came from or how reliable it is. There is also a security dimension: Lin, Ilia and Polakis showed that browser autofill can be abused by "
        "pages that include hidden fields, which makes indiscriminate filling a privacy risk "
        + c("autofill") + "."
    )
    R.p(
        "Recent advances in language models make a different approach feasible. Models can read unstructured documents and return structured facts, "
        "and retrieval-augmented generation (RAG) " + c("rag") + " lets a model answer from a user’s own text rather than from general knowledge. "
        "Research on web agents " + c("webarena", "mind2web", "webvoyager") + " has shown that models can operate real web pages, but it has largely "
        "focused on task automation, for which the agent is given broad control of a browser. Form filling needs the opposite design: a narrow, "
        "auditable assistant that proposes values from the user’s verified data, explains each proposal, and leaves the decision to the user. "
        "This project builds such an assistant."
    )

    R.h2("1.2 Motivation and Scope of the Project")
    R.p(
        "The motivation is practical. Re-entering the same details is slow, and it is also error-prone: a transposed digit in an identity number or a "
        "wrongly formatted date can lead to a rejected application. Where a person has two documents that give different values for the same attribute, "
        "for example two spellings of a name or two addresses, a typical autofill tool simply picks one without telling the user. The project therefore "
        "aims at three things at once: reduce typing, keep every filled value traceable to evidence, and keep the user in control."
    )
    R.p(
        "The system is aimed at individuals who fill forms on behalf of themselves. Table " + R.t("domains").split()[-1] + " lists the kinds of portal where the same facts recur. "
        "The system does not depend on any one portal: it works on the structure of an HTML form and on a fixed vocabulary of concepts."
    )
    R.table("domains", [
        ["Domain", "Typical form", "Facts that recur"],
        ["Education", "College and scholarship applications", "Name, date of birth, board, marks, address, parent details"],
        ["Banking and insurance", "Account opening, KYC update, policy application", "Identity numbers, address, income, nominee"],
        ["Government services", "Registration and certificate portals", "Name, date of birth, address, identity numbers"],
        ["Employment", "Recruitment portals", "Education, experience, skills, links, contact details"],
        ["Healthcare", "Hospital registration", "Name, date of birth, blood group, emergency contact"],
    ], [1.25, 2.2, 2.3])
    R.p("The scope of the implemented system is defined by five functional pillars:")
    R.numbered([
        "**Document intake and processing.** Upload of PDF, DOCX, TXT, PNG and JPG files, parsing, optional OCR, and background processing with visible progress.",
        "**Fact extraction with provenance.** A deterministic extractor and an optional LLM extractor produce facts whose origin, evidence text, source page and confidence are stored.",
        "**Profile and conflict management.** The user sees one resolved value per concept, can edit or confirm values, and resolves disagreements between documents.",
        "**Semantic form assistance.** A browser extension describes the fields of the current page; a LangGraph pipeline maps fields to concepts and proposes values for review.",
        "**Grounded question answering.** A RAG module answers questions about the user’s own documents and cites the source passage.",
    ])
    R.p(
        "The following are explicitly **out of scope**: automatic submission of forms, filling of password, payment-card, one-time-code and CAPTCHA fields, "
        "browsers other than Chrome, mobile clients, and a multi-user or multi-tenant administration console. Scanned documents are supported only when the "
        "optional PaddleOCR engine is installed."
    )

    R.h2("1.3 Problem Statement")
    R.p(
        "Existing autofill tools cannot build a user profile from the user’s documents, cannot explain or evidence the values they insert, handle conflicting "
        "sources poorly, and in some designs act on hidden or sensitive fields. The problem addressed by this project is to design and implement a system "
        "that (a) extracts structured, evidence-backed facts from personal documents, (b) maps the fields of an arbitrary web form to those facts by meaning "
        "rather than by exact attribute names, (c) detects and surfaces disagreements between sources, and (d) fills values only after explicit user "
        "approval, without reading existing field values, touching sensitive controls or submitting the form."
    )

    R.h2("1.4 Aim and Objectives")
    R.p("The aim of the project is to build a privacy-first, human-in-the-loop form-filling assistant driven by the user’s own documents. The objectives are:")
    R.numbered([
        "to parse PDF, DOCX, TXT and image documents and extract facts that conform to a fixed ontology of personal concepts;",
        "to store, for every fact, its source document, page, evidence text, extraction method and confidence;",
        "to compute cross-document conflicts from the active facts and let the user resolve them;",
        "to classify the fields of a web form into ontology concepts using deterministic rules first and a language model only for the remainder;",
        "to resolve each field’s value from the profile and, when absent, from retrieved document evidence that the model must quote;",
        "to apply confidence and sensitivity rules so that nothing uncertain or sensitive is filled without confirmation;",
        "to defend against prompt injection and to isolate every user’s data from every other user’s; and",
        "to verify the implementation with automated unit, integration and browser end-to-end tests.",
    ])

    R.h2("1.5 Salient Contributions")
    R.p("The project’s contribution is the integration of several known techniques into one auditable pipeline whose design choices favour privacy and traceability:")
    R.bullets([
        "Ontology-driven semantics:: A YAML ontology of 91 concepts with 295 aliases, autocomplete tokens, cardinality, data type and sensitivity flags is the single vocabulary shared by extraction, classification and filling.",
        "Dual-track extraction with provenance:: Deterministic rules run first; an LLM track is optional; results are merged so that agreement raises confidence slightly and disagreement becomes a user-visible conflict.",
        "Batch LangGraph pipeline:: One seven-node graph serves every recommendation endpoint. Classification is deterministic first, one batched LLM call handles only ambiguous fields, and values from document retrieval must be quoted from the evidence.",
        "Conflict computation without a second source of truth:: Conflicts are derived from active facts, so deleting or reprocessing a document cannot leave a stale conflict.",
        "Privacy-first Manifest V3 extension:: On-demand access through activeTab, no reading of field values, skipping of sensitive controls, a review step before every fill, and no submission.",
        "Injection-aware design:: Page text, document text and retrieved chunks are treated as untrusted data in every model call.",
        "Reproducible deployment and verification:: A single Docker Compose project and 196 automated tests, including a Playwright test of the built extension in real Chromium.",
    ])
    R.p("Some of these properties echo individual ideas in the surveyed literature. The project’s own claim is limited to the combination, which Chapter 2 shows is not offered by the works reviewed.")

    R.h2("1.6 Organisation of the Report")
    R.p(
        "The report follows the college’s seven-chapter format. Chapter 2 surveys the literature on web agents, language-model memory and retrieval, form "
        "understanding and automated form filling, and ends with the gap this project addresses. Chapter 3 states the problem formally, compares existing "
        "practice with the proposed solution, lists functional and non-functional requirements, and records which features are implemented, optional or "
        "future. Chapter 4 documents the design through architecture, data-flow, behavioural and structural diagrams, the database design, the principal "
        "algorithms and the security design. Chapter 5 presents snapshots of the running system. Chapter 6 describes the testing strategy and records the "
        "results. Chapter 7 concludes and lists future work. The References and five appendices follow."
    )
    R.summary(
        "Form filling is a repetitive task whose data already exists in the user’s documents, but native autofill cannot use those documents, cannot "
        "evidence a value and cannot arbitrate between sources. The project builds an assistant that extracts evidence-backed facts, maps form fields "
        "to them by meaning, surfaces conflicts, and fills only what the user approves. The scope, objectives and contributions were stated, and the "
        "organisation of the report was outlined."
    )
