# -*- coding: utf-8 -*-
from refs import c


def build(R):
    R.chapter(2, "Literature Survey")
    R.p("This chapter first explains, in simple terms, the concepts on which the project is built. It then reviews published research grouped by "
        "theme, compares the main approaches with the proposed system, and ends with the gap that the project addresses.")

    R.h2("2.1 Introduction to the Overall Topic")
    R.p("Automatic form filling from documents combines four research areas. **Document understanding** turns scanned or digital documents into "
        "structured facts. **Retrieval-augmented generation** grounds a language model’s answer in passages retrieved from the user’s documents. "
        "**Web agents** use language or vision-language models to act on web pages, and **security research** shows how autofill and LLM-based "
        "applications can be abused. Section 2.1.1 explains the basic concepts these areas rely on, and Section 2.2 reviews the published work in "
        "each area. References are numbered in the order in which they are first cited.")
    R.h3("2.1.1 Basic Concepts Used in This Project")
    R.p("**Database and MongoDB.** A database is an organised store of data that a program can save, search and update reliably. Traditional "
        "relational databases keep data in tables with fixed columns. MongoDB is a *document database*: it stores each record as a flexible "
        "document of field–value pairs, similar to JSON (JavaScript Object Notation), and groups similar documents into collections " + c("mongodb")
        + ". Records of different shapes can therefore sit side by side, which suits facts as varied as a date of birth and a table of subject marks. "
        "In this project MongoDB stores user accounts, uploaded-document records, extracted facts with their evidence, and form-filling sessions.")
    R.p("**Embeddings and vector databases.** An embedding is a list of numbers that represents the meaning of a piece of text; texts with similar "
        "meaning have nearby embeddings. Sentence-BERT " + c("sbert") + " produces such sentence embeddings, which can be compared quickly by cosine "
        "similarity. A vector database stores these lists and quickly finds the ones closest to a query. The project uses ChromaDB " + c("chroma")
        + " to store embeddings of short passages (chunks) of each document, so that a question such as “What was my Class 12 percentage?” finds "
        "the right passage even if the words differ.")
    R.p("**Large language models and RAG.** An LLM predicts text and can therefore answer questions or turn text into structured data, but it can "
        "also invent facts. Lewis *et al.* " + c("rag") + " introduced retrieval-augmented generation (RAG), which reduces this risk by pairing the "
        "model with a searchable index of passages and asking it to answer from the passages it retrieves. The project goes one step further: a "
        "value proposed from a document must appear word for word in the passage the model cites.")
    R.p("**Other building blocks.** *OCR* converts an image of text into characters; PP-OCR " + c("ppocr") + " describes lightweight text detection "
        "and recognition models that run on ordinary computers. An *ontology* is a controlled list of concepts, such as `personal.date_of_birth`, "
        "with their alternative names and data types. A *REST API* (Representational State Transfer Application Programming Interface) lets the "
        "dashboard and the extension talk to the server over HTTP; the project builds it with FastAPI " + c("fastapi") + ". *LangGraph* runs a "
        "program as a graph of steps that share a state " + c("langgraph") + ". A *Chrome extension* is a small program added to the browser; "
        "Manifest V3 is the current, permission-controlled extension platform " + c("mv3") + ". Finally, *prompt injection* is text hidden in "
        "data that tries to give instructions to an LLM: Greshake *et al.* " + c("injection") + " demonstrated *indirect* prompt injection, in "
        "which instructions placed in web pages or documents take control of an LLM-based application.")

    R.h2("2.2 Exhaustive Literature Survey")
    R.h3("2.2.1 Web Agents and Benchmarks")
    R.p("WebArena " + c("webarena") + " provides a self-hosted environment of realistic websites and long tasks, and showed that LLM agents were far "
        "below human performance. Mind2Web " + c("mind2web") + " collected more than 2,000 tasks from 137 real websites and proposed a two-stage "
        "method in which a small model first filters page elements before a larger model chooses an action. SeeAct " + c("seeact") + " studied "
        "GPT-4V as a web agent and found that *grounding*, linking a textual plan to the correct element on the page, is the main difficulty. "
        "WebVoyager " + c("webvoyager") + " built an end-to-end multimodal agent for fifteen live websites. CogAgent " + c("cogagent") + " is an "
        "18-billion-parameter vision-language model that reads high-resolution screenshots, and SeeClick " + c("seeclick") + " pre-trains models "
        "to locate interface elements from screenshots. Ferret-UI " + c("ferretui") + " extends this to mobile screens. WorkArena " + c("workarena")
        + " measures agents on enterprise knowledge-work tasks and concludes that they are promising but not yet reliable, while LCoW " + c("lcow")
        + " learns to simplify complex pages so that an agent decides better.")
    R.p("**Relevance and limits.** These works show that models can act on web pages and that finding the correct element is hard. The project "
        "avoids the grounding problem for form fields by reading the page structure directly: each field has a stable identifier, and filling "
        "targets that identifier. Unlike an autonomous agent, the extension performs no action the user has not approved.")

    R.h3("2.2.2 Agents, Knowledge and Memory")
    R.p("Wang *et al.* " + c("llmagents") + " survey LLM-based agents and describe them in terms of profile, memory, planning and action modules, and "
        "Nguyen *et al.* " + c("guisurvey") + " survey agents that operate graphical interfaces. Zhang *et al.* " + c("memory") + " organise agent "
        "memory by source, form and operation; in these terms, the project’s profile is a persistent memory in which every item is linked to "
        "evidence. Pan *et al.* " + c("llmkg") + " argue that explicit, structured knowledge complements the knowledge hidden inside a model, and "
        "HippoRAG " + c("hipporag") + " combines a model, a knowledge graph and graph ranking to improve retrieval across several facts. The "
        "project’s ontology plays the role of a small explicit knowledge structure, while its questions are mostly direct look-ups for which "
        "single-step retrieval is sufficient.")

    R.h3("2.2.3 Form Understanding, Form Filling and Form Security")
    R.p("Abdallah *et al.* " + c("formunderstanding") + " review transformer models for understanding scanned forms, including key-information "
        "extraction and benchmark datasets; this is the reading side of the problem. FormLM " + c("formlm") + " helps designers *create* online forms "
        "by modelling their structure and text. LAFF " + c("laff") + " suggests values for categorical fields in data-entry forms by learning "
        "dependencies between fields from earlier entries. FormNexus " + c("formnexus") + " infers the meaning and constraints of web-form fields "
        "from their text, structure and position, using an LLM, in order to generate tests. Lin *et al.* " + c("autofill") + " show that browser "
        "autofill can be exploited through hidden fields and its preview feature in Chromium-based browsers.")
    R.p("**Relevance and limits.** These studies show that the meaning of a field can be inferred from its label and surroundings, which the project "
        "does with ontology aliases and nearby text. None of them builds a personal profile from documents or asks the user to review each value, "
        "and the autofill study directly motivates three rules of the project: sensitive and hidden fields are skipped, existing values are never "
        "read, and nothing is filled before approval.")

    R.h3("2.2.4 Supporting Techniques and Security")
    R.p("MiniLM " + c("minilm") + " compresses large transformer models into small, fast encoders; the project’s embedding model, all-MiniLM-L6-v2, "
        "belongs to this family and works with the Sentence-BERT method described in Section 2.1.1. The PP-OCR models of Section 2.1.1 run in the "
        "project through RapidOCR " + c("rapidocr") + ", an open-source toolkit for ONNX Runtime that needs no graphics processor. On the security "
        "side, the OWASP guidance " + c("owasp") + " lists prompt injection as the first risk for LLM applications. Together with the indirect "
        "injection attacks described in Section 2.1.1, it justifies the project’s treatment of every page and document as untrusted input. "
        + R.t("lit") + " summarises the surveyed papers in the order of their reference numbers.")
    lit_rows = [
        [c("webarena"), "WebArena (ICLR 2024)", "Realistic self-hosted web tasks", "Task automation; no personal data or approval"],
        [c("mind2web"), "Mind2Web (NeurIPS 2023)", "2,000+ tasks on 137 websites", "Agent actions, not form values"],
        [c("seeact"), "SeeAct (ICML 2024)", "GPT-4V web agent; grounding is hard", "Autonomous; visual grounding"],
        [c("webvoyager"), "WebVoyager (ACL 2024)", "Multimodal agent on live sites", "Autonomous; no evidence trail"],
        [c("cogagent"), "CogAgent (CVPR 2024)", "Screenshot-based 18B model", "Heavy model; screenshots only"],
        [c("seeclick"), "SeeClick (ACL 2024)", "GUI grounding pre-training", "Locates elements, not meaning"],
        [c("workarena"), "WorkArena (ICML 2024)", "Enterprise task benchmark", "Benchmark; agents not reliable"],
        [c("hipporag"), "HippoRAG (NeurIPS 2024)", "Graph-based memory retrieval", "Multi-step retrieval not needed"],
        [c("formunderstanding"), "Form understanding review (2024)", "Models for scanned forms", "Reads forms; does not fill them"],
        [c("autofill"), "Fill in the Blanks (CCS 2020)", "Privacy threats of autofill", "Analyses threats; no solution"],
        [c("formlm"), "FormLM (EMNLP 2022)", "Helps create online forms", "Form design, not filling"],
        [c("laff"), "LAFF (ACM TOSEM 2023)", "Predicts categorical values", "Uses past entries, not documents"],
        [c("formnexus"), "FormNexus (ISSTA 2024)", "LLM infers field constraints", "Testing, not user assistance"],
        [c("injection"), "Indirect injection (AISec 2023)", "Attacks via retrieved content", "Shows the risk; no assistant"],
    ]
    lit_rows.sort(key=lambda r: int(r[0].strip("[]")))
    R.table("lit", [["Ref.", "Work (venue, year)", "Main idea", "Limitation for this project"]] + lit_rows,
            [0.5, 1.75, 1.75, 1.77], font=9.5)

    R.h2("2.3 Comparative Analysis")
    R.table("compare", [
        ["Property", "Browser autofill", "Web agents " + c("webarena", "seeact", "webvoyager"), "Form research " + c("formlm", "laff", "formnexus"), "Proposed system"],
        ["Reads the user’s documents", "No", "No", "No", "Yes, including scans"],
        ["Keeps evidence for each value", "No", "No", "No", "Document, page, text"],
        ["Handles disagreeing sources", "No", "No", "No", "Shows conflict; user decides"],
        ["Matches fields by meaning", "Partly", "Yes (model)", "Yes", "Ontology rules, then LLM"],
        ["User approves before action", "Partly", "Usually not", "Not applicable", "Always, per field"],
        ["Skips sensitive or hidden fields", "Known weakness " + c("autofill"), "Not reported", "Not applicable", "Yes, twice"],
    ], [1.5, 0.95, 1.05, 1.1, 1.17], font=9.5,
        intro=R.t("compare") + " compares the main families of approach on the properties that matter for this project, based on what the cited "
        "papers report.")

    R.h2("2.4 Research Gap")
    R.p("Web agents act on pages but are designed for autonomy, not for reviewing personal data. Form-related research infers field meaning for form "
        "design, value prediction or testing, but not from a person’s own documents. Document-understanding research reads documents but does not "
        "connect them to forms, and security research documents the risks without offering a safe assistant. **Among the works reviewed, none "
        "combines a document-derived profile with evidence, conflict handling between documents, field matching by meaning, protection against "
        "prompt injection and mandatory user review in one deployable system.** This project addresses that combination.")
    R.summary("The basic concepts used in the project were explained, including databases and MongoDB, embeddings, RAG and OCR. Twenty-four published works, "
              "most of them peer-reviewed journal and conference papers, were reviewed: they show that models can understand and act on web pages, that grounding is hard, that autofill has privacy risks and "
              "that retrieval improves factual answers. No reviewed work offers evidence-based, conflict-aware and user-approved form filling from "
              "personal documents, which defines the problem of Chapter 3.")
