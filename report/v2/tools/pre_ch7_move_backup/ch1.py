# -*- coding: utf-8 -*-
from refs import c

OBJECTIVES = [
    "Document understanding with evidence:: read PDF, Word, text and scanned image documents, recognise the type of document, and extract "
    "personal facts into a fixed vocabulary, recording for every fact its source document, page, evidence text and confidence.",
    "A verified profile:: combine the facts from all documents into one profile, detect when documents disagree, and let the user resolve each "
    "disagreement.",
    "Semantic form filling:: recognise what each field of an unseen web form asks for, propose a value from the profile or from cited document "
    "text, and fill only the values the user approves.",
    "Grounded question answering:: answer the user’s questions about their own documents and show the document and page behind every answer.",
    "Safety and verification:: protect personal data (no automatic submission, sensitive fields skipped, defences against manipulated text, "
    "per-user isolation) and verify the system with automated tests and a measured evaluation.",
]


def build(R):
    R.chapter(1, "Introduction")
    R.p("This chapter introduces the Smart Form Auto-Filling System and explains why filling web forms from personal documents is worth "
        "automating. It then states the scope, problem, aim and objectives of the project, lists its main contributions and outlines how the "
        "report is organised.")

    R.h2("1.1 Background of the Project Topic")
    R.p("Almost every service that students and working adults use today starts with an online form. Admission and scholarship portals ask for "
        "marks, board names and addresses; examination portals ask again for the same name, date of birth and category details; banks ask for "
        "identity numbers and income. Most of these facts are already printed in documents the person holds, such as an Aadhaar or PAN card, Class "
        "10 and Class 12 mark sheets, a birth certificate, an income or domicile certificate, or a bank passbook.")
    R.p("Web browsers reduce part of this effort with **autofill**, which remembers values typed earlier and offers them again when a field looks "
        "similar. This works well for an e-mail or postal address, but autofill has three limits. It can only repeat values the user has typed "
        "before, so it cannot use the facts printed in documents. It matches fields mainly by their technical names, so a label such as “Year of "
        "passing (Class XII)” or “Father’s name” is easily confused with a similar field. It also keeps no record of where a value came from. In "
        "addition, Lin, Ilia and Polakis showed that web pages can hide fields that browser autofill then fills silently (Section 2.2.3).")
    R.p("Recent progress in artificial intelligence (AI) makes a better approach possible. A **large language model (LLM)** is an AI model trained on "
        "very large amounts of text that can read an unstructured document and return structured information. **Retrieval-augmented generation "
        "(RAG)** lets such a model answer from passages of the user’s own documents rather than from general knowledge (Section 2.1.1). Research "
        "on web agents (Section 2.2.1) shows that models can operate real web pages, but these agents act on their own. Form filling with personal "
        "data calls for a different design: an assistant that proposes values from verified documents, explains each proposal and leaves every "
        "decision to the user. This project builds such an assistant.")

    R.h2("1.2 Motivation and Scope of the Project")
    R.p("Typing the same details again and again is slow and error-prone. A wrong digit in an identity number, a date in the wrong format or marks "
        "copied from the wrong examination can lead to a rejected application. When two documents give different values, such as two spellings of "
        "a name, a simple autofill tool picks one without telling the user. The project therefore pursues three goals together: less typing, values "
        "that can be traced to evidence, and a user who stays in control. " + R.t("domains") + " lists the kinds of portal on which the same facts recur.")
    R.table("domains", [
        ["Domain", "Typical form", "Facts that recur"],
        ["Education", "Admission, scholarship and examination applications", "Name, date of birth, board, seat number, subject marks, percentage"],
        ["Government services", "Certificates, voter and passport services", "Name, parents’ names, address, identity numbers, category"],
        ["Banking", "Account opening and KYC (know-your-customer) update", "Identity numbers, address, income, account details"],
        ["Employment", "Recruitment portals", "Education, experience, skills, contact details"],
    ], [1.2, 2.1, 2.47])
    R.p("**In scope:** upload and processing of PDF, Word (DOCX), plain-text and image files; optical character recognition (OCR) for scanned "
        "images; seventeen common Indian document types; a profile with sources and conflict resolution; a Chrome browser extension that reads the "
        "fields of any web form, suggests values and fills the approved ones; and a question-answering page over the user’s documents.")
    R.p("**Out of scope:** automatic submission of forms; filling passwords, payment-card details, one-time passwords (OTPs) and CAPTCHAs; browsers "
        "other than Chrome; mobile applications; and text in Indian scripts, since the OCR models used read English text only.")

    R.h2("1.3 Problem Statement")
    R.p("Existing autofill tools cannot build a profile from a person’s documents or show evidence for the values they insert; they handle "
        "disagreeing sources poorly, and some designs even fill hidden or sensitive fields. This project addresses the problem of designing and "
        "implementing a system that (a) extracts structured facts with evidence from personal documents, (b) matches the fields of any web form to "
        "those facts by meaning rather than by exact field names, (c) detects and shows disagreements between documents, and (d) fills values only "
        "after the user approves them, without reading what the page already contains, touching sensitive fields or submitting the form.")

    R.h2("1.4 Aim and Objectives")
    R.p("The aim of the project is to build a privacy-first assistant that fills web forms from the user’s own documents, keeps every value "
        "traceable and leaves every decision to the user. The objectives are:")
    R.numbered(OBJECTIVES)

    R.h2("1.5 Salient Contributions")
    R.bullets([
        "One shared vocabulary:: an ontology of 220 concepts in 32 domains, with 645 alternative phrasings (aliases), is used by extraction, field "
        "matching and filling, so that all parts of the system mean the same thing by “Class 12 percentage” or “father’s name”.",
        "Evidence for every value:: each fact stores its document, page, the exact text it came from and a confidence score, and disagreements "
        "between documents become visible conflicts instead of silent choices.",
        "Rules before models:: fixed rules handle the common cases; the language model is called only for fields the rules cannot decide, and any "
        "value it proposes from a document must appear word for word in the cited text.",
        "User-approved filling:: the browser extension never reads existing values, skips sensitive fields, shows a reason and source for every "
        "suggestion, fills only ticked fields, checks that the page kept them, and never submits the form.",
        "Measured results:: 453 automated tests and an evaluation on 15 synthetic documents and 15 forms show what the system does well and "
        "where it can still improve.",
    ])

    R.h2("1.6 Organisation of the Report")
    R.p("Chapter 2 explains the basic concepts used in the project and surveys published research on web agents, document understanding, form "
        "filling and security, ending with the research gap. Chapter 3 defines the problem, compares existing practice with the proposed solution and "
        "lists the requirements and technologies. Chapter 4 presents the design: architecture, data flow, database, the form-filling pipeline and its "
        "decision rules. Chapter 5 shows snapshots of the working system and analyses the measured results. Chapter 6 describes testing and the test "
        "results. Chapter 7 gives the conclusion and future work, followed by the References and Appendices.")
    R.summary("Online forms repeatedly ask for facts that already exist in a person’s documents, yet browser autofill cannot use those documents, "
              "show evidence or handle disagreements. This project builds an assistant that extracts facts with evidence, matches form fields by "
              "meaning and fills only what the user approves. The chapter set out its scope, problem, five objectives and main contributions.")
