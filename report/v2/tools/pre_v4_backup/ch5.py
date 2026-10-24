# -*- coding: utf-8 -*-


def build(R):
    R.chapter(5, "Result Analysis: Snapshots")
    R.p("This chapter shows the working system and analyses its measured results. All screenshots were captured on 22 October 2026 from the "
        "running system with the Playwright browser-automation library. They use a dedicated demonstration account loaded with fifteen **synthetic** "
        "documents for a fictional applicant; no real personal data appears in this report. The measured results come from the evaluation run of "
        "16 October 2026 on the same data, using the Gemini model and the all-MiniLM-L6-v2 embedding model.")

    R.h2("5.1 Dashboard and Document Processing")
    R.fig("dashboard", width=5.77, intro=R.f("dashboard") + " shows the dashboard after all fifteen documents were processed. It reports 15 "
          "documents, 90 profile values (13 confirmed by the user), 11 conflicts to resolve and 19 field reviews pending. Each card links to the "
          "page where the user can act on it.")
    R.fig("document_details", width=5.77, intro=R.f("document_details") + " shows the details of the Class 12 mark sheet. The system identified "
          "the document type, and for each value it lists how the value was obtained (Extracted or Normalised), the confidence, and the exact "
          "evidence text with its page. This evidence trail is the basis of Objective 1.")

    R.h2("5.2 Profile and Conflicts")
    R.fig("profile", width=5.77, intro=R.f("profile") + " shows the Profile page, which groups values by topic. Each value lists the documents "
          "that support it; the father’s name, for example, is supported by eight documents. The user can confirm, edit or delete each value.")
    R.fig("conflicts", width=5.77, intro=R.f("conflicts") + " shows a real disagreement found by the system: the caste validity certificate "
          "contains two different dates (20/11/2025 and “Date of Issue 09/07/2025”). Both candidates are shown with their evidence, and nothing "
          "is filled until the user chooses (Objective 2).")

    R.h2("5.3 Ask Documents")
    R.fig("ask", width=5.77, intro=R.f("ask") + " shows the answer to “What was my Class 12 percentage, and which document states it?”. The "
          "answer (87.20%) comes from an exact fact, and the Sources panel quotes the cited passage of the Class 12 mark sheet (Objective 4).")

    R.h2("5.4 Browser Extension")
    R.fig("ext_pair", width=5.6, intro=R.f("ext_pair") + " shows the extension on a synthetic Class 12 application form. On the left, after "
          "analysis, 23 of 25 fields are ready and 2 need attention because the passing month and result are not in the documents. On the right, "
          "after the user chose Fill, all 23 values were filled and read back from the page, and the popup confirms that nothing was submitted.")
    R.fig("form_marks", width=5.0, intro=R.f("form_marks") + " shows part of the filled form. The subject-wise marks were filled and verified. "
          "The figure also shows one filling error: the “Elective language” row, which the mark sheet does not contain, received the total "
          "marks (500 and 436). Such errors are counted in Table 5.2.")

    R.h2("5.5 Measured Results")
    R.p(R.t("eval") + " summarises extraction, retrieval and question answering on the fifteen synthetic documents. The answers were compared with a "
        "hidden answer key that the system never reads.")
    R.table("eval", [
        ["Measure", "Result"],
        ["Document type identified correctly", "15 / 15 (100%)"],
        ["Expected fields extracted with the exact value", "128 / 132 (97.0%)"],
        ["Fields from scanned images / from digital PDFs", "97.8% / 96.6%"],
        ["Table rows exactly right (subject marks, transactions, members)", "40 / 40"],
        ["Documents stored in MongoDB / indexed in ChromaDB", "15 / 15 and 15 / 15"],
        ["Retrieval: correct document ranked first / within the top four", "93.3% / 100% (15 queries)"],
        ["Ask Documents questions answered correctly", "28 / 28"],
        ["Answers citing the correct source document", "100% (23 questions with an expected source)"],
        ["Forbidden or invented values in answers; median answer time", "0; 0.08 s"],
    ], [3.75, 2.02], font=10)
    R.table("autofill", [
        ["Outcome on 15 synthetic forms (real extension, real backend)", "Count"],
        ["Fields filled correctly", "112"],
        ["Fields filled incorrectly (including 3 filled when they should stay empty)", "9"],
        ["Expected values held for the user’s review (not filled)", "84"],
        ["Expected values missed silently", "0"],
        ["Expected fields not detected on the page", "2"],
        ["Fields whose value is absent from the documents, correctly left empty", "12 of 15"],
        ["Fields reserved for the user’s own choice that the system touched", "0"],
        ["Forms submitted by the system", "0"],
    ], [4.6, 1.17], font=10, align=["l", "c"],
        intro=R.t("autofill") + " gives the outcome of filling the fifteen matching forms through the browser extension.")
    R.p("Of the 121 values the system filled automatically, 112 were correct, a precision of 92.6%. The system favoured caution: 84 expected "
        "values were held for review instead of being filled (for example sensitive values, values from disagreeing documents and values below the "
        "0.85 confidence threshold), and no form was submitted. The OCR benchmark on 30 rendered documents gave field recall of 0.948 for clean scans, 0.850 for pages skewed by 3–4°, 0.948 "
        "for pages rotated by 90° and 0.855 for simulated phone photographs, at 2.6 to 7.8 seconds per page on a CPU. In a comparison of language "
        "models on six grounded questions and eight hard field-classification cases, Gemini answered 6/6 and 8/8, the local qwen2:7b model 4/6 and "
        "5/8, and gemma:2b 2/6 and 1/8, which is why Gemini is the primary model and the local model is only a fallback whose mappings always need "
        "review.")

    R.h2("5.6 Analysis")
    R.bullets([
        "Objectives 1 and 4:: extraction (97.0% exact fields) and question answering (28/28 with sources) met their goals on the synthetic set.",
        "Objective 2:: disagreements, such as the two issue dates in " + R.f("conflicts") + ", were shown to the user instead of being resolved "
        "silently.",
        "Objective 3:: 112 correct fills against 9 errors. Three of the errors mixed up the correspondence and permanent addresses (two PIN codes and "
        "one address), three gave the wrong relationship for household members, and three placed a value in a field that should have stayed "
        "empty, including the elective-language row of " + R.f("form_marks") + ".",
        "Objective 5:: no form was submitted, no field reserved for the user was touched, and every filled value was read back from the page.",
        "Scope of the evidence:: the documents are synthetic and the sets are small, so the percentages describe these cases rather than "
        "accuracy on real documents.",
    ])
    R.summary("Seven snapshots showed the working system from processed documents to a filled and verified form, including one real disagreement and "
              "one real filling error. On fifteen synthetic documents and forms, the system identified every document type, extracted 97.0% of "
              "expected fields, answered all 28 questions with sources and filled 112 fields correctly and 9 incorrectly, without submitting any form.")
