# -*- coding: utf-8 -*-
from refs import c


def build(R):
    R.chapter(4, "Design")
    R.p("This chapter presents the design of the system as implemented: the overall architecture and the flow of data, the database design, the "
        "form-filling pipeline and its decision rules, and the security design. Each diagram is explained beside it.")

    R.h2("4.1 System Architecture")
    R.p("The system follows a three-tier structure. The **presentation tier** consists of the two clients that the user sees: the web dashboard "
        "and the Chrome extension. The **application tier** is the FastAPI backend together with a background worker, which together carry out "
        "every operation on the user’s data. The **data tier** holds the uploaded files, the facts and the searchable document chunks. External "
        "services, the LLM provider and the OCR models, are used only by the application tier and never receive more data than a task needs. "
        "The clients never access a database directly: every request passes through the backend, which checks who is asking before any data is "
        "read or written.")
    R.fig("architecture", max_h=6.3, intro=R.f("architecture") + " shows the complete architecture, from the clients through document ingestion "
          "and storage to the services that use the stored data. The numbered regions are described below the figure.")
    R.numbered([
        "Clients:: the user works through a web dashboard (upload, profile, questions) and a Chrome extension. The extension reads only the "
        "descriptions of a form’s fields, never their current values.",
        "Backend:: a FastAPI server checks the user’s token, applies rate limits and passes the user’s identifier into every database query, so that "
        "one user can never read another user’s data.",
        "Ingestion:: a new document is queued in Redis and processed by a Celery worker: its text is read (with OCR for images), its type is "
        "identified, facts are extracted and merged with their evidence, and the text is split into chunks and embedded.",
        "Storage:: the original file is kept in file storage, the facts and form sessions in MongoDB, and the chunk embeddings in ChromaDB.",
        "Using the stored data:: Ask Documents answers questions from exact facts first and from semantic search over the chunks second; the "
        "form-fill pipeline classifies form fields, takes values from the profile and, where needed, from cited document evidence. Both may call "
        "the LLM, but neither accepts an answer that is not supported by the stored data.",
        "Review:: the recommendations return to the extension popup, where the user approves, edits or skips each value before anything is filled.",
    ])

    R.h2("4.2 Data Flow")
    R.fig("dfd1", width=4.4, intro=R.f("dfd1") + " is the level-1 data-flow diagram. It shows six processes, the data stores they read and "
          "write, and the optional LLM provider as an external entity.")
    R.p("The user signs in (1.0) and uploads documents (2.0). Each stored file is passed to fact extraction (3.0), which writes facts to the fact "
        "store D3 and chunk embeddings to D5. Profile and conflict resolution (4.0) lets the user confirm or correct facts and records each "
        "correction in D6. Field classification and recommendation (5.0) reads the facts, the document chunks and saved answers, and writes form "
        "sessions and recommendations to D4. Question answering (6.0) reads the chunks and facts. Only processes 3.0, 5.0 and 6.0 may call the LLM.")

    R.h2("4.3 Database Design")
    R.p("As explained in Section 2.1.1, MongoDB stores records as flexible documents grouped into collections. Almost every record carries the "
        "owner’s `user_id`, and every query and deletion includes it. A separate ChromaDB collection holds the chunk embeddings, labelled with the "
        "same `user_id` and `document_id` so that search results always belong to the person asking.")
    R.fig("er", width=5.77, intro=R.f("er") + " shows the entity–relationship diagram. A user owns documents, structured facts, form sessions, "
          "corrections and saved answers; a document owns its processing records and facts; a form session owns one recommendation per field.")
    R.p("Two design decisions keep the data consistent. First, conflicts are not stored: they are computed when needed from the active facts, so "
        "deleting or reprocessing a document can never leave an out-of-date conflict behind. Second, reprocessing a document first deletes its old "
        "facts and chunks, so nothing is duplicated. Tables extracted from documents, such as subject-wise marks or bank transactions, are kept as "
        "*discovered facts*, while form-fillable concepts become *structured facts*.")

    R.h2("4.4 Form-Filling Pipeline")
    R.p("Form analysis is implemented as a LangGraph state graph of seven steps that share one state object. Two conditional "
        "steps are skipped when they are not needed, which keeps most analyses free of LLM calls:")
    R.numbered([
        "sanitize:: blocks password, payment, OTP, CAPTCHA, hidden and file fields, and sets aside fields whose text looks like an injected "
        "instruction.",
        "deterministic_classify:: maps each field to a concept using its autocomplete attribute, label, placeholder, name and nearby text, matched "
        "against the ontology aliases. A label inside a “Father’s details” section is not given the user’s own name.",
        "llm_classify (only if needed):: sends one batched request for the fields the rules could not resolve; the answer is accepted only if it "
        "names a known concept with enough confidence.",
        "resolve_profile:: takes values from the user’s profile, marking a concept with disagreeing documents as needing review.",
        "resolve_documents (only if needed):: retrieves document chunks for fields still empty and asks the LLM for a value that must appear word "
        "for word in a cited chunk; anything else is discarded.",
        "decide and persist:: the decide step applies the rules of Section 4.5, and the persist step stores one recommendation per field.",
    ])

    R.h2("4.5 Decision Rules")
    R.fig("decide", width=4.1, intro=R.f("decide") + " is the flowchart of the decide step, which gives every field its final status. Each path "
          "ends at a single End terminator, where the recommendation is stored.")
    R.p("A field that was already blocked keeps its status, and a field without a value becomes *missing information*, with a hint about which "
        "document usually contains it. Otherwise the value is formatted for the field; if this fails, the value is only shown as a candidate. "
        "Sensitive concepts and inferred values always require confirmation. A field is *ready*, and therefore pre-ticked in the popup, only when "
        "its confidence is at least 0.85 and no confirmation is required; every other field is *needs review*. When the LLM chose the field’s "
        "concept, the value’s confidence is capped by the confidence of that choice, so an uncertain mapping cannot produce a ready value.")

    R.h2("4.6 Security Design")
    R.bullets([
        "Accounts:: passwords are hashed with bcrypt " + c("bcrypt") + "; access tokens are JSON Web Tokens valid for 30 minutes "
        "and revoked on sign-out; repeated failed logins are rate-limited.",
        "Isolation:: every MongoDB and ChromaDB operation is filtered by the user’s identifier.",
        "Uploads:: the file extension, declared type, content signature (magic bytes), size limit of 10 MB and duplicate checksum are all checked.",
        "Prompt injection:: page and document text is wrapped in clearly marked data blocks, six injection patterns are detected, and LLM output "
        "must cite stored evidence " + c("injection", "pibench") + ".",
        "Browser:: the extension uses on-demand page access, keeps its token away from page scripts, never reads field values and never submits.",
    ])
    R.summary("The design was presented through the end-to-end architecture, the level-1 data flow, the database design, the seven-step form-filling "
              "pipeline, the decision flowchart and the security controls. The main design decisions are a single ontology, rules before models, "
              "answers grounded in stored evidence, conflicts computed rather than stored, per-user isolation and mandatory user review.")
