# -*- coding: utf-8 -*-
from content_refs import c


def build(R):
    R.chapter(2, "Literature Survey")
    R.intro(
        "This chapter reviews published work that bears on document-driven form filling. It first sets out the background concepts, then reviews nineteen "
        "papers grouped by theme, compares the approaches with the proposed system, and concludes with the gap that motivates the project. Bibliographic "
        "details of every paper were checked against the publisher, proceedings or arXiv record; where only a preprint record could be confirmed, the "
        "reference says so."
    )

    R.h2("2.1 Introduction to the Overall Topic")
    R.p(
        "Automatic form filling sits at the junction of four research areas. **Information extraction** turns unstructured documents into structured "
        "facts; recent surveys of form understanding show a move from layout rules to transformer models " + c("formunderstanding") + ". **Retrieval-augmented "
        "generation** grounds a language model’s output in retrieved passages " + c("rag") + ", using dense sentence embeddings such as Sentence-BERT "
        + c("sbert") + " and compact models such as MiniLM " + c("minilm") + " to find relevant text. **Web agents** use language or vision-language models to act on "
        "web pages " + c("webarena", "mind2web", "seeact", "webvoyager") + ", and surveys organise them into perception, reasoning, planning and action "
        + c("guisurvey", "llmagents") + ". Finally, **security and privacy** research examines how autofill and LLM-integrated applications can be abused "
        + c("autofill", "injection") + "."
    )
    R.p(
        "A form-filling assistant must use all four areas, and it has constraints that general web agents do not. The values it inserts are personal; they "
        "must be correct and attributable; the page it reads is controlled by a third party and may be hostile; and the user must remain the decision-maker. "
        "These constraints shape both the choice of techniques and the gap identified at the end of the chapter."
    )

    R.h3("Background concepts used in this project")
    R.bullets([
        "Autofill:: Browser feature that stores values previously typed and replays them in fields matched by attributes such as name and autocomplete tokens. It is the baseline against which the project is positioned.",
        "Ontology:: A controlled vocabulary of concepts (for example personal.date_of_birth) with aliases, data types and flags. The project uses it so that extraction, classification and filling share meaning.",
        "Retrieval-augmented generation:: A language model answers from passages retrieved from an index rather than from its parameters alone " + c("rag") + ".",
        "Agent orchestration:: A graph of steps with shared state, here implemented with LangGraph " + c("langgraph") + ".",
        "Prompt injection:: Instructions hidden in data that a model reads, which can make an LLM-integrated application act against its user " + c("injection") + ", " + c("owasp") + ".",
    ])

    R.h2("2.2 Exhaustive Literature Survey")
    R.h3("2.2.1 Web Agents and Benchmarks")
    R.p(
        "WebArena " + c("webarena") + " provides a self-hostable web environment containing realistic functional websites and a set of long-horizon tasks, "
        "against which language-model agents are scored by whether the task’s goal is reached. It showed that agents were far from human performance on realistic web "
        "tasks. Mind2Web " + c("mind2web") + " contributes a dataset of more than two thousand open-ended tasks collected from 137 real websites across 31 "
        "domains, and a two-stage approach in which a small model first filters page elements before a larger model chooses the action. Together these "
        "benchmarks establish how web agents are evaluated, but neither addresses personal data or user approval."
    )
    R.p(
        "SeeAct " + c("seeact") + " studies whether GPT-4V can act as a web agent. With a human mapping the model’s plan onto page elements it completed 51.1% "
        "of tasks on live sites, and the authors identify **grounding**, linking a textual plan to the correct element, as the main bottleneck. "
        "WebVoyager " + c("webvoyager") + " builds an end-to-end multimodal agent that works on fifteen live websites and reports a 59.1% task success rate. "
        "CogAgent " + c("cogagent") + " is an 18-billion-parameter vision-language model that reads screenshots at 1120 by 1120 resolution, and SeeClick "
        + c("seeclick") + " introduces GUI-grounding pre-training and the ScreenSpot benchmark. Ferret-UI " + c("ferretui") + " extends grounded UI "
        "understanding to mobile screens with an any-resolution design. WorkArena " + c("workarena") + " measures agents on common enterprise knowledge-work "
        "tasks on the ServiceNow platform and introduces the BrowserGym environment, concluding that agents are promising but short of full automation. "
        "LCoW " + c("lcow") + " learns a module that contextualises complex web pages so that a decision-making model can act on them more reliably."
    )
    R.p(
        "**Relevance and limits.** These works show that models can find the right element on a page and that grounding is hard. The project borrows the "
        "lesson that precise grounding matters, but it avoids the problem for form fields by using the DOM directly: each field is a descriptor with a stable "
        "identifier and the fill action targets that identifier. Unlike an autonomous agent, the project’s extension takes no action that the user has not approved."
    )

    R.h3("2.2.2 LLM Agent Frameworks, Knowledge and Memory")
    R.p(
        "Wang et al. " + c("llmagents") + " survey LLM-based autonomous agents and propose a unified framework covering profile, memory, planning and action modules, "
        "together with applications and evaluation methods. A companion survey on the memory mechanism of LLM agents " + c("memory") + " organises memory "
        "by source, form and operation, which is a useful lens for the project’s own memory: the profile of facts is persistent, evidence-linked memory, "
        "and saved answers are explicitly user-initiated memories. Pan et al. " + c("llmkg") + " present a roadmap for combining large language models with "
        "knowledge graphs, arguing that explicit, structured knowledge complements the black-box parametric knowledge of a model. HippoRAG " + c("hipporag") + " "
        "proposes a retrieval framework inspired by long-term memory that combines a language model, a knowledge graph and a graph-ranking step to improve "
        "retrieval for knowledge integration."
    )
    R.p(
        "**Relevance and limits.** The project’s ontology plays the role of a small, explicit knowledge structure: each fact is a typed, sourced assertion, "
        "which is the benefit that Pan et al. attribute to structured knowledge. The project does not build a knowledge graph or multi-hop retrieval; its "
        "questions are short factual lookups, for which single-step dense retrieval with a similarity cutoff is adequate."
    )

    R.h3("2.2.3 Form Understanding, Autofill and Form Security")
    R.p(
        "Abdallah et al. " + c("formunderstanding") + " review transformer and language-model approaches to understanding forms in scanned documents, "
        "including key-information extraction, and the benchmark datasets used to evaluate them. This is the extraction side of the problem; the review "
        "supports the project’s use of an optional OCR step and of a language model to read unstructured documents, but it treats forms as inputs to be read, "
        "not as targets to be filled."
    )
    R.p(
        "Lin, Ilia and Polakis " + c("autofill") + " analyse the privacy threats of browser form autofill and show that pages can exploit hidden fields and the "
        "autofill preview mechanism to obtain personal information, in all Chromium-based browsers they tested. This directly motivates three design rules "
        "in the project: sensitive and hidden fields are skipped, the extension never reads existing field values, and nothing is filled until the user approves it."
    )
    R.p(
        "FormLM " + c("formlm") + " recommends question and option ideas for the *creation* of online forms by augmenting a pre-trained language model with form "
        "structure, trained on a dataset of 62 thousand forms. LAFF " + c("laff") + " suggests values for categorical fields in data-entry forms by learning "
        "dependencies between fields with Bayesian networks from historical input, reporting a mean reciprocal rank above 0.73. FormNexus " + c("formnexus")
        + " derives semantic insights from the text, DOM structure and visual proximity of form elements, stores them in a form entity-relation graph, and uses an "
        "LLM in a feedback loop to infer input constraints for test generation."
    )
    R.p(
        "**Relevance and limits.** FormLM models forms from the designer’s side; LAFF predicts categorical values from earlier entries rather than from "
        "documents; FormNexus targets test generation. All three show that field semantics can be inferred from text and structure, which the project does "
        "with ontology aliases and nearby-text cues. None of them builds a personal profile from documents or involves the user in a review step."
    )

    R.h3("2.2.4 Supporting Techniques")
    R.p(
        "Lewis et al. " + c("rag") + " introduced retrieval-augmented generation for knowledge-intensive tasks, pairing a sequence-to-sequence model with a dense index. "
        "Sentence-BERT " + c("sbert") + " showed that siamese BERT networks produce sentence embeddings that can be compared by cosine similarity at "
        "a fraction of the cost of pairwise BERT scoring, and MiniLM " + c("minilm") + " compresses transformers by distilling self-attention, which is the "
        "family of model that the project’s default embedding model (all-MiniLM-L6-v2, 384 dimensions) belongs to. Greshake et al. " + c("injection") + " "
        "demonstrate indirect prompt injection against LLM-integrated applications, in which instructions placed in retrieved or web content hijack the "
        "application; the OWASP guidance " + c("owasp") + " lists prompt injection first among its risks for LLM applications. These works justify the "
        "project’s RAG design and its treatment of every page, document and chunk as untrusted input."
    )

    R.p(R.t("lit") + " summarises the nineteen surveyed works, the main idea of each and the reason it does not by itself solve the problem of this project.")
    R.table("lit", [
        ["Ref.", "Work (venue, year)", "Main idea", "Limitation for this project"],
        [c("webarena"), "WebArena (ICLR 2024)", "Realistic, self-hostable web tasks", "Task automation; no personal data or user approval"],
        [c("mind2web"), "Mind2Web (NeurIPS D&B 2023)", "2,000+ tasks, 137 sites, two-stage agent", "Benchmark of agent actions, not form values"],
        [c("seeact"), "SeeAct (ICML 2024)", "GPT-4V web agent; grounding bottleneck", "Visual grounding needed; autonomous action"],
        [c("webvoyager"), "WebVoyager (ACL 2024)", "End-to-end multimodal agent, 15 live sites", "Autonomous; evaluation by model judge"],
        [c("cogagent"), "CogAgent (CVPR 2024)", "18B screenshot-based VLM", "Heavy model; screenshot-only"],
        [c("seeclick"), "SeeClick (ACL 2024)", "GUI-grounding pre-training, ScreenSpot", "Element location, not field meaning"],
        [c("ferretui"), "Ferret-UI (ECCV 2024)", "Mobile UI understanding", "Mobile screens, not web forms"],
        [c("workarena"), "WorkArena (ICML 2024)", "Enterprise knowledge-work benchmark", "Benchmark; agents short of full automation"],
        [c("lcow"), "LCoW (ICLR 2025)", "Learned page contextualisation", "Aids agents; no profile or evidence"],
        [c("guisurvey"), "GUI Agents survey (ACL Findings 2025)", "Perception, reasoning, planning, acting", "Survey only"],
        [c("llmagents"), "LLM agents survey (Front. Comput. Sci. 2024)", "Unified agent framework", "Survey only"],
        [c("llmkg"), "LLMs + KGs roadmap (IEEE TKDE 2024)", "Structured knowledge for LLMs", "No form-filling application"],
        [c("hipporag"), "HippoRAG (NeurIPS 2024)", "Graph-based long-term memory retrieval", "Multi-hop retrieval not needed here"],
        [c("memory"), "Agent memory survey (arXiv 2024)", "Memory by source, form, operation", "Survey only"],
        [c("formunderstanding"), "Form understanding review (arXiv 2024)", "Transformers for scanned forms", "Reads forms; does not fill them"],
        [c("autofill"), "Fill in the Blanks (CCS 2020)", "Privacy threats of browser autofill", "Analysis of threats, not a solution"],
        [c("formlm"), "FormLM (EMNLP 2022)", "Recommends form creation ideas", "Form design, not filling"],
        [c("laff"), "LAFF (ACM TOSEM)", "Bayesian suggestion of categorical values", "Uses earlier entries, not documents"],
        [c("formnexus"), "FormNexus (ISSTA 2024)", "LLM constraint inference for form tests", "Testing, not assistance"],
    ], [0.45, 1.55, 1.75, 2.0], font=9.5)

    R.h2("2.3 Comparative Analysis")
    R.p(
        "Table " + R.t("compare").split()[-1] + " compares four families of approach on the properties that matter to this project. The comparison is based on the capabilities "
        "described in the cited papers and on documented browser behaviour; “not reported” means the reviewed papers do not describe the property."
    )
    R.table("compare", [
        ["Property", "Browser autofill", "Web agents [1]-[10]", "Form-field prediction [17]-[19]", "Proposed system"],
        ["Reads user documents", "No", "Not reported", "No", "Yes (PDF, DOCX, TXT, image)"],
        ["Stores evidence for each value", "No", "Not reported", "No", "Yes (source, page, text, confidence)"],
        ["Handles conflicting sources", "No", "Not reported", "No", "Yes (computed conflicts, user resolves)"],
        ["Matches fields by meaning", "Heuristics", "Model-based", "Yes", "Ontology aliases, then LLM"],
        ["User approval before action", "Partial", "Typically autonomous", "Not applicable", "Mandatory, per field"],
        ["Avoids sensitive / hidden fields", "Known weaknesses [16]", "Not reported", "Not applicable", "Skipped in extension and backend"],
        ["Prompt-injection defence", "Not applicable", "Not reported", "Not reported", "Tagged data, patterns, quote checks"],
    ], [1.3, 0.95, 1.05, 1.1, 1.4], font=9.5)

    R.h2("2.4 Research and Development Gap")
    R.p(
        "The surveyed work leaves the following gap. Web agents " + c("webarena", "seeact", "webvoyager") + " demonstrate action on pages, but they are designed for "
        "autonomy rather than for review of personal data. Form-oriented research " + c("formlm", "laff", "formnexus") + " infers field semantics or values for form "
        "design, value suggestion and testing, but not from a user’s own documents. Extraction research " + c("formunderstanding") + " reads documents but does not "
        "connect them to forms. Security research " + c("autofill", "injection") + " documents risks but does not offer an integrated assistant that avoids them. "
        "**Among the works reviewed, none combines document-derived profile building with evidence, cross-document conflict handling, semantic field "
        "matching, injection-aware model use and mandatory user review in one deployable system.** This project addresses that combination."
    )
    R.h2("2.5 Proposed Approach")
    R.p(
        "The proposed approach keeps the language model in a supporting role. Facts enter the system through a deterministic extractor and an optional LLM "
        "extractor and are stored with evidence. A field is classified by rules first; the model sees only ambiguous fields, in one batch, with sanitised "
        "descriptions. A value comes from the stored profile, and only if the profile lacks it does the system retrieve document passages and ask the model "
        "for a value that it must quote from a cited passage. Every proposal reaches the user with a reason and a source, and the extension writes only approved "
        "values and then verifies that the page kept them. Chapters 3 and 4 detail this design."
    )
    R.summary(
        "The literature shows that models can understand and act on web pages, that grounding is the main difficulty, that autofill carries privacy risks, "
        "and that retrieval and structured knowledge improve factual reliability. No reviewed work provides evidence-preserving, conflict-aware, "
        "user-approved filling from personal documents. That gap defines the problem addressed in Chapter 3."
    )
