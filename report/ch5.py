# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    R.chapter(5, "Result Analysis: Snapshots")
    R.intro(
        "This chapter presents snapshots of the running system. All screenshots were captured on 14 October 2026 from the running application with "
        "Playwright, using one test account and two synthetic text documents (resume.txt and passport.txt) created for testing. Nothing in the figures "
        "was edited. The documents deliberately disagree on the date of birth, so that the conflict workflow can be shown. Each snapshot is described "
        "and related to the design of Chapter 4."
    )

    R.h2("5.1 Registration and Login")
    R.p(
        R.f("shot_login") + " shows the sign-in screen with an e-mail and password. Registration is a sibling screen that adds the full name and a confirmation "
        "field; the client validates the input before calling the server and shows a clear message for wrong credentials, for rate limiting and for a duplicate "
        "e-mail (tests in Section 6.3). On success the token is stored and the user is taken to the dashboard. An expired or revoked token signs the user out "
        "from a single place."
    )
    R.fig("shot_login", force_landscape=False, max_w=4.6)

    R.h2("5.2 Dashboard")
    R.p(
        R.f("shot_dash") + " shows the dashboard. Four cards summarise the account from live API data: two documents (none processing), six profile values "
        "(none yet confirmed by the user), two conflicts awaiting resolution and no pending field reviews. The recent-documents list shows each file with the number "
        "of facts extracted (eight from the résumé, five from the passport record) and a Processed status. The side panel summarises how to fill a form with the "
        "extension and states that the user submits the form personally."
    )
    R.fig("shot_dash", force_landscape=False)

    R.h2("5.3 Document Upload and Processing")
    R.p(
        R.f("shot_docs") + " shows the Documents page. The upload area accepts PDF, DOCX, TXT, PNG and JPG files up to 10 MB and notes that scanned documents "
        "need the optional OCR engine. The table lists each document with its processing status, the number of facts, whether it is searchable (indexed in ChromaDB), "
        "and the upload time. A document whose processing failed shows the error message, and deletion asks for confirmation and removes facts, vectors and file."
    )
    R.fig("shot_docs", force_landscape=False)

    R.h2("5.4 Profile with Provenance")
    R.p(
        R.f("shot_profile") + " shows the Identity and Personal groups of the Profile page (the Address and Education groups above them are cropped out to keep the text legible), which groups the resolved values by domain. Each value carries a pill for its origin (Extracted, Normalised), "
        "the source document and page, and the actions Confirm, Edit and delete. The passport number is flagged Sensitive and masked until the user reveals "
        "it. The date of birth and the full legal name show Conflicting values with a link to resolve them, because the two documents disagree. The telephone number "
        "was rewritten to a normalised international form, which is why it is marked Normalised. The form at the bottom adds a value by choosing an ontology "
        "concept, and the Saved answers section lists answers the user chose to keep."
    )
    R.fig("shot_profile", force_landscape=False)

    R.h2("5.5 Conflict Detection and Resolution")
    R.p(
        R.f("shot_conflicts") + " shows the Conflicts page. For the date of birth the résumé gives 14/03/2004 and the passport record 13/03/2004; both were extracted "
        "with 99 per cent confidence and each is shown with the verbatim text it came from. The user can choose a candidate, enter another value, or reject all values. "
        "For the full legal name, the candidate “Ashmit Patil” is supported by both documents, whereas “Passport Record” (the title line of the second document) "
        "has only 60 per cent confidence. This is the name heuristic of Section 4.8 at work: it is marked inferred with confidence 0.6, and because it disagrees "
        "with a better-supported value it is surfaced for the user instead of being used silently."
    )
    R.fig("shot_conflicts", force_landscape=False)

    R.h2("5.6 Extension: Scan")
    R.p(
        R.f("shot_scan") + " shows the extension popup after the user chose Scan this page on a test form. Six fillable fields were found and two hidden, disabled "
        "or sensitive fields were ignored. The popup states this explicitly. Suggest values starts the analysis; Scan again repeats the scan, which is the "
        "current way to handle fields added to the page after the first scan."
    )
    R.fig("shot_scan", force_landscape=False, max_w=2.6)

    R.h2("5.7 Extension: Review Before Fill")
    R.p(
        R.f("shot_review") + " shows the review list. The instruction at the top reads “Only ticked fields are filled; nothing is submitted.” The full legal name is "
        "unticked with the status Check, because the documents disagree; the two candidates are offered with their source file, together with a box to type "
        "the correct value. The e-mail address and phone number are ticked with the status Ready, their source document and page and a confidence of 99 per cent. "
        "The Fill button reports how many fields will be filled (three in this view) and Cancel leaves the page unchanged."
    )
    R.fig("shot_review", force_landscape=False, max_w=2.6)

    R.h2("5.8 Grounded Question Answering")
    R.p(
        R.f("shot_ask") + " shows the Ask page. The question “What is my date of birth and which document is it from?” returns an answer with a Sources panel "
        "that quotes the cited passage and names the document and page. The page states that answers come only from the user’s own documents and saved "
        "answers. The example also shows a limitation: the retrieval step is not aware of conflicts, so the answer reports the passport’s value and cites it, "
        "while the Conflicts page shows that the résumé disagrees. The citation lets the user see where the value came from, but the user must still "
        "resolve the conflict in the profile."
    )
    R.fig("shot_ask", force_landscape=False)

    R.h2("5.9 Settings and Service Health")
    R.p(
        R.f("shot_settings") + " shows the Settings page. The system status panel reports the database, document search (ChromaDB), the AI provider (configured) "
        "and the embedding model, from the /health/services endpoint. Below are two confirmation-gated destructive actions: Delete all data removes documents, "
        "extracted values, saved answers, search entries and form history while keeping the account, and Delete account removes the account as well."
    )
    R.fig("shot_settings", force_landscape=False)

    R.h2("5.10 Observations")
    R.bullets([
        "Provenance is visible everywhere:: every value on the profile, conflict, review and answer screens shows its source and, where relevant, its confidence.",
        "Uncertainty is routed to the user:: the date-of-birth and name conflicts blocked automatic filling in both the dashboard and the popup.",
        "Sensitive values are guarded:: the passport number is masked in the dashboard, and the extension’s scan ignored sensitive fields.",
        "Known rough edges:: the name heuristic can propose a title line as a name (shown above) and RAG answers do not yet reflect conflicts. Both are recorded as limitations in Chapter 7.",
    ])
    R.summary(
        "Nine snapshots of the dashboard and the extension demonstrated the workflow from sign-in to a reviewed fill: document intake with processing status, "
        "profile values with provenance and sensitivity masking, conflict resolution, on-demand page scan, per-field review, grounded answers and service health. "
        "The snapshots also exposed two honest limitations, which Chapter 7 carries forward."
    )
