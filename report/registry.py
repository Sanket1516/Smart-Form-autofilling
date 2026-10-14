# -*- coding: utf-8 -*-
"""Ordered figure and table registries. Numbers are assigned per chapter in list order."""

# (key, file relative to report/figures, chapter, caption)
_FIGS = [
    ("overview", "diagrams/fig_overview.png", 3, "Proposed solution workflow: Phase A prepares the profile once; Phase B assists every web form"),
    ("architecture", "diagrams/fig_architecture.png", 4, "System architecture of the Smart Form Auto-Filling System"),
    ("deployment", "diagrams/fig_deployment.png", 4, "Docker Compose deployment architecture"),
    ("modules", "diagrams/fig_modules.png", 4, "Backend package structure and allowed dependencies"),
    ("context", "diagrams/fig_context.png", 4, "Context diagram (DFD Level 0)"),
    ("dfd1", "diagrams/fig_dfd1.png", 4, "Data flow diagram, Level 1"),
    ("dfd2", "diagrams/fig_dfd2_extract.png", 4, "Data flow diagram, Level 2: Extract and Store Facts (process 3.0)"),
    ("usecase", "diagrams/fig_usecase.png", 4, "Use case diagram"),
    ("act_upload", "diagrams/fig_act_upload.png", 4, "Activity diagram: document upload and processing"),
    ("act_fill", "diagrams/fig_act_fill.png", 4, "Activity diagram: filling a web form through the extension"),
    ("seq_register", "diagrams/seq_register.png", 4, "Sequence diagram: user registration"),
    ("seq_login", "diagrams/seq_login.png", 4, "Sequence diagram: login, authenticated request and logout"),
    ("seq_upload", "diagrams/seq_upload.png", 4, "Sequence diagram: document upload, processing and status polling"),
    ("seq_fill", "diagrams/seq_fill.png", 4, "Sequence diagram: form analysis, review and fill"),
    ("seq_rag", "diagrams/seq_rag.png", 4, "Sequence diagram: grounded document question answering"),
    ("seq_conflict", "diagrams/seq_conflict.png", 4, "Sequence diagram: conflict detection and resolution"),
    ("er", "diagrams/fig_er.png", 4, "Entity relationship diagram of the MongoDB collections and the ChromaDB chunk index"),
    ("state_doc", "diagrams/fig_state_doc.png", 4, "State diagram of a document's processing status"),
    ("state_fact", "diagrams/fig_state_fact.png", 4, "State diagram of a structured fact's status"),
    ("class_agent", "diagrams/fig_class_agent.png", 4, "Class diagram: form-fill agent, classifier, fact service and ontology"),
    ("class_pipeline", "diagrams/fig_class_pipeline.png", 4, "Class diagram: LLM providers, document pipeline and retrieval services"),
    ("langgraph", "diagrams/fig_langgraph.png", 4, "LangGraph state graph of the form-fill pipeline"),
    ("classify", "diagrams/fig_classify.png", 4, "Flowchart of deterministic field classification"),
    ("decide", "diagrams/fig_decide.png", 4, "Flowchart of the decide node"),
    ("rag", "diagrams/fig_rag.png", 4, "Retrieval-augmented question answering pipeline"),
    ("security", "diagrams/fig_security.png", 4, "Defence-in-depth layers of the implementation"),
    ("inject", "diagrams/fig_inject.png", 4, "Prompt-injection defence applied to every untrusted input"),
    ("state_ext", "diagrams/fig_state_ext.png", 4, "State diagram of the extension popup flow"),
    ("shot_login", "screens_c/fig5_1_login.png", 5, "Login screen of the dashboard"),
    ("shot_dash", "screens_c/fig5_2_dashboard.png", 5, "Dashboard overview"),
    ("shot_docs", "screens_c/fig5_3_upload.png", 5, "Documents page with upload area and processing status"),
    ("shot_profile", "screens_c/fig5_4_profile.png", 5, "Profile page listing extracted facts with provenance"),
    ("shot_conflicts", "screens_c/fig5_5_conflicts.png", 5, "Conflicts page with candidate values from different documents"),
    ("shot_scan", "screens_c/fig5_6_ext_scan.png", 5, "Extension popup after scanning a page"),
    ("shot_review", "screens_c/fig5_7_ext_review.png", 5, "Extension popup: review before fill"),
    ("shot_ask", "screens_c/fig5_8_ask.png", 5, "Ask page: grounded answer with cited source"),
    ("shot_settings", "screens_c/fig5_9_settings.png", 5, "Settings page with live service health"),
    ("testing_ci", "diagrams/fig_testing_ci.png", 6, "Continuous integration pipeline and test layers"),
]

# (key, chapter, caption)
_TABS = [
    ("domains", 1, "Application domains of the system"),
    ("lit", 2, "Summary of the surveyed literature and its relevance"),
    ("compare", 2, "Comparison of related approaches with the proposed system"),
    ("existing", 3, "Existing practice versus the proposed system"),
    ("freq", 3, "Functional requirements and where they are implemented"),
    ("nfreq", 3, "Non-functional requirements"),
    ("stack", 3, "Technology stack and justification"),
    ("status", 3, "Implementation status of features"),
    ("hw", 4, "Hardware requirements"),
    ("thresholds", 4, "Configured thresholds used by the pipeline"),
    ("onto", 4, "Field ontology: concepts per domain"),
    ("collections", 4, "MongoDB collections and their indexes"),
    ("statuses", 4, "Status vocabularies used by the system"),
    ("security", 4, "Security controls and where they are implemented"),
    ("api", 4, "Principal REST endpoints"),
    ("backend_tests", 6, "Backend test inventory (146 tests)"),
    ("front_tests", 6, "Dashboard test inventory (22 tests)"),
    ("ext_tests", 6, "Extension test inventory (24 tests)"),
    ("tc", 6, "Representative test cases"),
    ("results", 6, "Test results (run of 13 October 2026)"),
    ("limits", 7, "Current limitations and proposed work"),
    ("app_backend", "IV", "Backend dependencies"),
    ("app_front", "IV", "Dashboard and extension framework versions"),
]


def build():
    figs, tabs, cnt = {}, {}, {}
    for key, file, ch, cap in _FIGS:
        cnt[("f", ch)] = cnt.get(("f", ch), 0) + 1
        figs[key] = dict(file=file, chapter=ch, num=cnt[("f", ch)], caption=cap)
    for key, ch, cap in _TABS:
        cnt[("t", ch)] = cnt.get(("t", ch), 0) + 1
        tabs[key] = dict(chapter=ch, num=cnt[("t", ch)], caption=cap)
    return figs, tabs
