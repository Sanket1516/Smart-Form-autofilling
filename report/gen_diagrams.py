# -*- coding: utf-8 -*-
"""Generates all report diagrams (Graphviz) into report/figures/diagrams.

Every diagram is derived from the implemented code (see the report text for
the file each one models). Colour roles are fixed across the whole report:
  blue   = client / presentation      green = backend logic
  amber  = data stores                violet = external services
  red    = security controls          grey  = neutral / process
Shapes and line styles repeat the meaning so the figures stay readable in
grayscale.
"""
import os
import subprocess
import textwrap

DOT = r"C:\Program Files\Graphviz\bin\dot.exe"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "diagrams")
os.makedirs(OUT, exist_ok=True)
NL = "\\n"  # DOT line break

C = {
    "blue": ('"#DCE9F8"', '"#2F5D9B"'),
    "green": ('"#DDEFE0"', '"#3C7A4B"'),
    "amber": ('"#FBEBCB"', '"#A8741A"'),
    "violet": ('"#E9E1F2"', '"#6B4E9B"'),
    "red": ('"#F8DCDC"', '"#A33A3A"'),
    "grey": ('"#EEEEEE"', '"#555555"'),
    "white": ('"#FFFFFF"', '"#555555"'),
}

HEAD = (
    'digraph G {{\n'
    '  graph [fontname="Arial", fontsize=16, pad=0.2, {graph}];\n'
    '  node  [fontname="Arial", fontsize=16, style="filled,rounded", shape=box, penwidth=1.5, margin="0.14,0.08"];\n'
    '  edge  [fontname="Arial", fontsize=14, penwidth=1.4, arrowsize=0.8];\n'
)


def wrap(label, width):
    out = []
    for seg in label.split(NL):
        out.extend(textwrap.wrap(seg, width) or [""])
    return NL.join(out)


def n(name, label, color="grey", shape="box", extra="", width=None):
    fill, line = C[color]
    if width is None:
        width = 18 if shape in ("diamond", "ellipse", "circle") else 30
    label = wrap(label, width)
    style = "filled,rounded" if shape == "box" else "filled"
    return f'  {name} [label="{label}", fillcolor={fill}, color={line}, shape={shape}, style="{style}"{extra}];\n'


def term(name, end=False):
    shape = "doublecircle" if end else "circle"
    return f'  {name} [label="", shape={shape}, style=filled, fillcolor="#333333", width=0.22, fixedsize=true];\n'


def cluster(name, label, color, body):
    fill, line = C[color]
    return (f'  subgraph cluster_{name} {{ label="{label}"; labeljust=l; fontsize=16; fontname="Arial Bold"; '
            f'style="rounded,filled"; fillcolor={fill}; color={line}; penwidth=1.6;\n{body}  }}\n')


def render(name, dot_src):
    path = os.path.join(OUT, name + ".dot")
    with open(path, "w", encoding="utf-8") as f:
        f.write(dot_src)
    for fmt, extra in (("png", ["-Gdpi=200"]), ("svg", [])):
        subprocess.run([DOT, f"-T{fmt}", *extra, path, "-o", os.path.join(OUT, f"{name}.{fmt}")], check=True)


# ------------------------------------------------------------------ architecture
def d_architecture():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.25, ranksep=0.45, newrank=true')
    s += cluster("clients", "Presentation tier", "blue",
                 n("dash", "React 19 dashboard (served by Nginx)", "blue", width=20) +
                 n("popup", "Extension popup (React 18)", "blue", width=20) +
                 n("content", "Content script (detector, autofill)", "blue", width=20))
    s += cluster("api", "Application tier: FastAPI (Python 3.11)", "green",
                 n("mw", "Middleware: CORS, redacted logs, rate limits, JWT auth", "red", width=60) +
                 n("svc", "11 routers and services", "green", width=16) +
                 n("pipe", "Document pipeline", "green", width=16) +
                 n("lg", "Form-fill LangGraph (7 nodes)", "green", width=16) +
                 n("onto", "Field ontology (91 concepts)", "green", width=16))
    s += cluster("data", "Data tier", "amber",
                 n("mongo", "MongoDB 8", "amber", "cylinder") + n("chroma", "ChromaDB", "amber", "cylinder") +
                 n("store", "File storage", "amber", "cylinder") + n("redis", "Redis 7", "amber", "cylinder"))
    s += cluster("ext", "External / optional services", "violet",
                 n("llm", "LLM provider (mock by default)", "violet", width=16) + n("emb", "MiniLM-L6 embeddings", "violet", width=16) +
                 n("ocr", "PaddleOCR (optional)", "violet", width=16) + n("worker", "Celery worker", "violet", width=16))
    s += ('  {rank=same; dash; popup; content}\n  {rank=same; svc; pipe; lg; onto}\n  {rank=same; mongo; chroma; store; redis}\n  {rank=same; llm; emb; ocr; worker}\n'
          '  dash -> mw [label=" HTTPS + Bearer JWT"]; popup -> mw; content -> popup [dir=both, style=dashed, constraint=false];\n'
          '  mw -> svc; mw -> pipe [style=invis]; mw -> lg [style=invis]; mw -> onto [style=invis];\n'
          '  svc -> pipe [style=invis]; pipe -> lg [style=invis]; lg -> onto [style=invis];\n'
          '  svc -> mongo; svc -> chroma; pipe -> store; svc -> redis;\n'
          '  mongo -> llm [style=invis]; chroma -> emb [style=invis]; store -> ocr [style=invis]; redis -> worker [style=invis];\n'
          '  lg -> llm [style=dashed]; pipe -> emb [style=dashed]; pipe -> ocr [style=dashed]; redis -> worker [dir=none, constraint=false];\n'
          '  lg -> onto [style=dashed, constraint=false];\n}\n')
    render("fig_architecture", s)


def d_deployment():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.55')
    s += cluster("host", "User machine", "blue", n("chrome", "Chrome 120+: extension (MV3) and dashboard tab", "blue", width=40))
    s += cluster("compose", "Docker Compose project (network smart-form-internal)", "grey",
                 n("fe", "frontend: Nginx, host 5173 to 80, CSP headers", "blue", width=26) +
                 n("be", "backend: Uvicorn + FastAPI, port 8000", "green", width=26) +
                 n("wk", "worker: Celery (PROCESSING_MODE=celery)", "green", width=26) +
                 n("eb", "extension-builder: builds extension bundle", "grey", width=26) +
                 n("mg", "mongodb: mongo:8.0 + volume", "amber", "cylinder", width=20) +
                 n("ch", "chromadb: host 8001 to 8000 + volume", "amber", "cylinder", width=20) +
                 n("rd", "redis: redis:7-alpine + volume", "amber", "cylinder", width=20))
    s += cluster("cloud", "Optional external services", "violet",
                 n("llm", "LLM provider API (HTTPS)", "violet") + n("cld", "Cloudinary storage", "violet"))
    s += ('  chrome -> fe [label=" dashboard"]; chrome -> be [label=" REST + JWT"];\n  fe -> be [style=dashed];\n'
          '  be -> mg; be -> ch; be -> rd; rd -> wk; wk -> mg [constraint=false]; wk -> ch [constraint=false];\n'
          '  be -> llm [style=dashed]; be -> cld [style=dashed]; eb -> chrome [style=dotted, constraint=false];\n'
          '  fe -> eb [style=invis]; ch -> cld [style=invis];\n}\n')
    render("fig_deployment", s)


def d_modules():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.5')
    s += n("api", "app/api/v1: HTTP routers", "green")
    s += n("svc", "app/services: auth, documents, facts, profile, form_filling, retrieval, user_data, user_memories", "green", width=36)
    s += n("agents", "app/agents: graph, field_classifier, llm_provider, value_formatting", "green")
    s += n("proc", "app/processing: extractor, pipeline, chunking, runner", "green")
    s += n("ext", "app/extraction: deterministic, llm_extraction, merge, normalize", "green")
    s += n("onto", "app/ontology: loader + YAML", "green")
    s += n("sec", "app/security + app/core: prompt_safety, JWT/bcrypt, config, logging, rate limit", "red", width=34)
    s += n("repo", "app/repositories + app/db: Mongo repositories, ChromaClient, indexes", "amber", width=34)
    s += n("store", "app/storage: local / Cloudinary", "amber")
    s += n("tasks", "app/tasks: Celery tasks", "violet")
    s += ('  api -> svc; svc -> agents; svc -> proc; svc -> repo; svc -> store; agents -> onto; proc -> ext; ext -> onto;\n'
          '  agents -> sec [style=dashed]; api -> sec [style=dashed]; tasks -> proc; proc -> repo; agents -> repo [style=dashed];\n}\n')
    render("fig_modules", s)


# ------------------------------------------------------------------ data flow
def d_context():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.9, ranksep=0.85')
    s += n("user", "User (dashboard and extension)", "blue", "box", ', style="filled"')
    s += n("sys", "0 Smart Form Auto-Filling System", "green", "circle", ", width=2.4", width=14)
    s += n("llm", "LLM provider (optional)", "violet", "box", ', style="filled"')
    s += n("web", "Web form (page DOM)", "grey", "box", ', style="filled"')
    s += ('  user -> sys [label=" credentials, documents,\\n fact edits, questions,\\n review decisions"];\n'
          '  sys -> user [label=" facts, conflicts, recommendations,\\n grounded answers, status"];\n'
          '  sys -> llm [label=" sanitised prompts"]; llm -> sys [label=" JSON results"];\n'
          '  web -> user [label=" field descriptors (no values)", style=dashed, constraint=false];\n'
          '  user -> web [label=" approved values", style=dashed, constraint=false];\n  {rank=same; user; web}\n}\n')
    render("fig_context", s)


def d_dfd1():
    s = HEAD.format(graph='rankdir=LR, nodesep=0.25, ranksep=1.2')
    s += n("user", "User", "blue", "box", ', style="filled"')
    for k, l in [("p1", "1.0 Authenticate"), ("p2", "2.0 Manage documents"), ("p3", "3.0 Extract and store facts"),
                 ("p4", "4.0 Resolve profile and conflicts"), ("p5", "5.0 Classify fields and recommend"), ("p6", "6.0 Answer questions (RAG)")]:
        s += n(k, l, "green", "ellipse", width=15)
    for k, l in [("d1", "D1 users, token revocations"), ("d2", "D2 documents, files"), ("d3", "D3 structured and discovered facts"),
                 ("d4", "D4 sessions, recommendations"), ("d5", "D5 ChromaDB chunks"), ("d6", "D6 corrections, memories")]:
        s += n(k, l, "amber", "cylinder", width=16)
    s += n("llm", "LLM provider", "violet", "box", ', style="filled"')
    s += '  {rank=same; p1; p2; p3; p4; p5; p6}\n  {rank=same; d1; d2; d3; d4; d5; d6}\n'
    s += ('  user -> p1; user -> p2; user -> p4; user -> p5; user -> p6;\n'
          '  p1 -> d1; p2 -> d2; p2 -> p3; p3 -> d3; p3 -> d5; d3 -> p4 [dir=both]; p4 -> d6; d3 -> p5; d5 -> p5; d6 -> p5 [style=dashed];\n'
          '  p5 -> d4; d5 -> p6; p3 -> llm [style=dashed]; p5 -> llm [style=dashed]; p6 -> llm [style=dashed];\n}\n')
    render("fig_dfd1", s)


def d_dfd2():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.35, ranksep=0.4')
    s += n("f", "Stored file (PDF, DOCX, TXT, image)", "amber", "cylinder")
    for k, l in [("a", "3.1 Parse text (pdfplumber, pypdfium2, python-docx, Pillow; OCR if scanned)"),
                 ("b", "3.2 Deterministic extraction (regex + ontology alias labels)"),
                 ("c", "3.3 LLM extraction (optional, JSON mode)"),
                 ("d", "3.4 Merge candidates (same concept and value combined; different values kept)"),
                 ("e", "3.5 Replace this document's facts"),
                 ("g", "3.6 Chunk (500/50), embed, upsert")]:
        s += n(k, l, "green", width=32)
    s += n("o", "Field ontology", "green") + n("mf", "D3 facts", "amber", "cylinder") + n("ch", "D5 ChromaDB", "amber", "cylinder")
    s += n("llm", "LLM provider", "violet", "box", ', style="filled"') + n("err", "requires_review or failed", "red")
    s += ('  f -> a -> b -> c -> d -> e -> g;\n  o -> b [style=dashed, constraint=false]; c -> llm [dir=both, style=dashed, constraint=false];\n'
          '  e -> mf; g -> ch; a -> err [style=dashed, label=" unreadable /\\n no OCR"];\n}\n')
    render("fig_dfd2_extract", s)


# ------------------------------------------------------------------ behaviour
def d_usecase():
    s = HEAD.format(graph='rankdir=LR, nodesep=0.1, ranksep=0.7')
    s += n("user", "User", "blue", "box", ', style="filled"')
    s += n("llm", "LLM provider (external actor)", "violet", "box", ', style="filled"')
    uc = ["Register, log in, log out", "Upload document", "Monitor processing status", "Reprocess or delete document",
          "View and edit profile facts", "Resolve fact conflicts", "Ask question about documents",
          "Scan page for fields", "Review recommendations", "Fill approved values", "Save answer for future",
          "View activity and service health", "Delete all data or account"]
    body = "".join(n(f"u{i}", u, "green", "ellipse", ', style="filled"', width=22) for i, u in enumerate(uc))
    s += cluster("sys", "Smart Form Auto-Filling System", "grey", body)
    for i in range(len(uc)):
        s += f"  user -> u{i} [arrowhead=none];\n"
    s += ('  u1 -> llm [arrowhead=none, style=dashed]; u6 -> llm [arrowhead=none, style=dashed]; u8 -> llm [arrowhead=none, style=dashed];\n'
          '  u9 -> u8 [label="include", style=dashed, fontsize=12, constraint=false]; u7 -> u8 [label="include", style=dashed, fontsize=12, constraint=false]; u5 -> u4 [label="extend", style=dashed, fontsize=12, constraint=false];\n}\n')
    render("fig_usecase", s)


def d_act_upload():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.3')
    s += term("s") + n("a", "User selects a file on the Documents page", "blue")
    s += n("b", "Valid extension, magic bytes, size 10 MB or less?", "grey", "diamond", width=20)
    s += n("c", "Reject with 400 / 413 / 422", "red")
    s += n("d", "Store file, create document (uploaded), dispatch job", "green")
    s += n("e", "Parse text (OCR if needed)", "green") + n("f", "Text readable?", "grey", "diamond")
    s += n("g", "failed or requires_review", "red")
    s += n("h", "Extract (deterministic + optional LLM), merge, replace facts", "green")
    s += n("i", "Chunk, embed, index in ChromaDB", "green") + n("j", "Index succeeded?", "grey", "diamond")
    s += n("k", "processed, index_status indexed", "green") + n("l", "processed, index_status failed (facts kept)", "amber")
    s += term("z", True)
    s += ('  s -> a -> b; b -> c [label=" no"]; b -> d [label=" yes"]; d -> e -> f; f -> g [label=" no"]; f -> h [label=" yes"]; h -> i -> j;\n'
          '  j -> k [label=" yes"]; j -> l [label=" no"]; k -> z; l -> z; c -> z; g -> z;\n}\n')
    render("fig_act_upload", s)


def d_act_fill():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.3')
    s += term("s")
    for k, l, col in [("a", "User opens popup; content script injected on demand", "blue"),
                      ("b", "Detector lists eligible fields; skips sensitive, hidden, disabled", "blue"),
                      ("c", "Create form session; POST analyze (202)", "green"),
                      ("d", "LangGraph pipeline runs; popup polls recommendations", "green"),
                      ("e", "Review list: ready, needs_review, missing, blocked", "blue"),
                      ("f", "User ticks, edits or skips each field", "blue"),
                      ("g", "Submit decisions; GET approved values", "green"),
                      ("h", "Content script writes values (native setter + events)", "blue")]:
        s += n(k, l, col, width=34)
    s += n("i", "DOM kept each value?", "grey", "diamond")
    s += n("j", "POST verify results (applied, verified, reason)", "green", width=34) + n("k", "Show result; nothing is submitted", "blue", width=34) + term("z", True)
    s += '  s -> a -> b -> c -> d -> e -> f -> g -> h -> i; i -> j [label=" yes or no (both reported)"]; j -> k -> z;\n}\n'
    render("fig_act_fill", s)


def d_langgraph():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.45, ranksep=0.4')
    s += n("start", "START", "grey", "ellipse", ', style="filled"')
    nodes = [("san", "sanitize: block password, payment, OTP, hidden; quarantine injection-like text", "red"),
             ("det", "deterministic_classify: autocomplete, ontology phrase match, input type", "green"),
             ("llm", "llm_classify: one batched call for unresolved fields only", "violet"),
             ("prof", "resolve_profile: resolved / conflict / multiple view; derived first and last name", "green"),
             ("doc", "resolve_documents: ChromaDB top-k + one batched LLM call; value must appear in evidence", "violet"),
             ("dec", "decide: format to field, apply thresholds and sensitivity rules", "green"),
             ("per", "persist: upsert recommendations", "amber")]
    for k, l, c in nodes:
        s += n(k, l, c, width=36)
    s += n("end", "END", "grey", "ellipse", ', style="filled"')
    s += ('  start -> san -> det;\n  det -> llm [label=" a field is unresolved"];\n  det -> prof [label=" all resolved"];\n  llm -> prof;\n'
          '  prof -> doc [label=" empty, non-sensitive fields"];\n  prof -> dec [label=" none"];\n  doc -> dec -> per -> end;\n}\n')
    render("fig_langgraph", s)


def d_classify():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.35')
    s += n("a", "Field descriptor", "grey", "ellipse", ', style="filled"')
    s += n("b", "autocomplete token maps to a concept?", "grey", "diamond")
    s += n("c", "confidence 0.97, method autocomplete", "green")
    s += n("d", "Match aliases on question, label, aria-label (1.0), placeholder (0.95), name/id (0.9), nearby text (0.85)", "green", width=34)
    s += n("e", "Top two scores within 0.05?", "grey", "diamond")
    s += n("f", "Break tie with name or id (0.8), else ambiguous", "green")
    s += n("g", "Fallback: input type email (0.95) or tel (0.9)", "green")
    s += n("h", "Owner concept inside father / spouse / emergency section?", "grey", "diamond", width=22)
    s += n("i", "Do not use own value; send to LLM", "violet")
    s += n("j", "confidence at least 0.75 and not ambiguous?", "grey", "diamond")
    s += n("k", "Resolved", "green") + n("l", "Batched LLM call (known concept, confidence at least 0.6)", "violet")
    s += ('  a -> b; b -> c [label=" yes"]; b -> d [label=" no"]; d -> e; e -> f [label=" yes"]; e -> g [label=" no"];\n'
          '  f -> h; g -> h; h -> i [label=" yes"]; h -> j [label=" no"]; j -> k [label=" yes"]; j -> l [label=" no"]; i -> l; c -> k;\n}\n')
    render("fig_classify", s)


def d_decide():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.35')
    s += n("a", "Field with candidate value", "grey", "ellipse", ', style="filled"')
    s += n("b", "Already blocked, skipped, error or review?", "grey", "diamond", width=16)
    s += n("c", "Keep status", "grey") + n("d", "Value is None?", "grey", "diamond")
    s += n("e", "missing_information", "amber")
    s += n("f", "Format for field type (date, option, radio, length)", "green")
    s += n("g", "Formatting failed?", "grey", "diamond") + n("h", "needs_review (value shown as candidate)", "amber")
    s += n("i", "Sensitive or inferred?", "grey", "diamond", width=16) + n("j", "requires_confirmation = true", "red")
    s += n("k", "Confidence >= 0.85, no confirmation?", "grey", "diamond", width=16)
    s += n("l", "ready", "green") + n("m", "needs_review", "amber")
    s += ('  a -> b; b -> c [label=" yes"]; b -> d [label=" no"]; d -> e [label=" yes"]; d -> f [label=" no"]; f -> g; g -> h [label=" yes"]; g -> i [label=" no"];\n'
          '  i -> j [label=" yes"]; i -> k [label=" no"]; j -> k; k -> l [label=" yes"]; k -> m [label=" no"];\n}\n')
    render("fig_decide", s)


# ------------------------------------------------------------------ data models
def rec(name, fields, color):
    fill, line = C[color]
    rows = "".join(f'<TR><TD ALIGN="LEFT">{t}</TD></TR>' for t in fields)
    return (f'  {name} [shape=plain, label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" COLOR={line} BGCOLOR={fill}>'
            f'<TR><TD BGCOLOR={line}><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>{rows}</TABLE>>];\n')


def d_er():
    s = HEAD.format(graph='rankdir=LR, nodesep=0.2, ranksep=0.7')
    s += rec("users", ["<B>_id</B>", "full_name, email (unique)", "password_hash, status", "created_at, last_login_at"], "blue")
    s += rec("auth_token_revocations", ["<B>jti</B> (unique)", "expires_at (TTL)"], "red")
    s += rec("documents", ["<B>_id</B>, user_id (FK)", "file_name, file_type, file_size", "checksum (unique per user)", "status, current_stage, progress", "fact_count, index_status, chunk_count", "storage_reference"], "amber")
    s += rec("processing_records", ["<B>_id</B>", "user_id, document_id (FK)", "stage, status, retry_count"], "amber")
    s += rec("structured_facts", ["<B>_id</B>, user_id (FK)", "source_document_id (FK or user)", "concept, value, raw_value", "origin, status, method", "confidence, evidence_text", "source_page, is_user_confirmed"], "green")
    s += rec("discovered_facts", ["<B>_id</B>, user_id (FK)", "source_document_id (FK)", "field, semantic_type, value", "ontology, confidence, origin"], "green")
    s += rec("form_sessions", ["<B>_id</B>, user_id (FK)", "website_origin, page_url, form_id", "status, started_at", "field counters, fill_results[]"], "blue")
    s += rec("recommendations", ["<B>_id</B>, user_id (FK)", "session_id (FK), field_id", "concept, recommended_value", "status, confidence, reason", "requires_confirmation, candidates[]"], "blue")
    s += rec("corrections", ["<B>_id</B>, user_id (FK)", "concept, original, corrected", "reason"], "grey")
    s += rec("user_memories", ["<B>_id</B>, user_id (FK)", "label, concept, value, indexed"], "grey")
    s += rec("chroma_chunk", ["<B>chunk_id</B>", "text, 384-dim embedding", "user_id, document_id", "page_number, chunk_index", "source_type, document_type"], "violet")
    s += ('  users -> documents [label=" 1:N"]; users -> form_sessions [label=" 1:N"]; users -> structured_facts [label=" 1:N"];\n'
          '  users -> corrections; users -> user_memories; users -> auth_token_revocations [style=dashed, label=" jti"];\n'
          '  documents -> structured_facts [label=" 1:N"]; documents -> discovered_facts; documents -> processing_records;\n'
          '  documents -> chroma_chunk [style=dashed, label=" 1:N (index)"]; form_sessions -> recommendations [label=" 1:N"];\n'
          '  user_memories -> chroma_chunk [style=dashed];\n}\n')
    render("fig_er", s)


def cls(name, attrs, methods, color):
    fill, line = C[color]
    br = '<BR ALIGN="LEFT"/>'
    a = br.join(attrs) + br if attrs else " "
    m = br.join(methods) + br if methods else " "
    return (f'  {name} [shape=plain, label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" COLOR={line} BGCOLOR={fill}>'
            f'<TR><TD BGCOLOR={line}><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>'
            f'<HR/><TR><TD ALIGN="LEFT" BALIGN="LEFT">{a}</TD></TR><HR/><TR><TD ALIGN="LEFT" BALIGN="LEFT">{m}</TD></TR></TABLE>>];\n')


def d_class_agent():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.6')
    s += cls("FormFillGraph", ["- classifier: FieldClassifier", "- facts: FactService", "- retrieval: RAGRetrievalService", "- llm: LLMProvider"],
             ["+ run(user_id, session_id, fields)", "- _sanitize()", "- _deterministic_classify()", "- _llm_classify()", "- _resolve_profile()", "- _resolve_documents()", "- _decide()", "- _persist()"], "green")
    s += cls("FieldClassifier", ["- ontology: FieldOntology", "- threshold: float"], ["+ classify_deterministic(field)", "+ classify_with_llm(fields, prior)", "+ is_resolved(c)"], "green")
    s += cls("FactService", ["- repository"], ["+ resolve_view(user_id)", "+ list_conflicts(user_id)", "+ resolve_conflict(...)", "+ add_user_fact(...)"], "green")
    s += cls("FieldOntology", ["- concepts (91)"], ["+ match_text(text)", "+ concept_for_autocomplete(t)", "+ is_sensitive(c)", "+ is_fillable(c)", "+ is_single_valued(c)"], "green")
    s += cls("ConceptView", ["+ status: resolved | conflict | multiple", "+ value, confidence, origin", "+ candidates, sources"], [], "amber")
    s += cls("StructuredFact", ["+ concept, value, raw_value", "+ origin, status, confidence", "+ source_document_id, source_page", "+ evidence_text, is_user_confirmed"], [], "amber")
    s += ('  FormFillGraph -> FieldClassifier [arrowhead=diamond]; FormFillGraph -> FactService [arrowhead=diamond];\n'
          '  FieldClassifier -> FieldOntology [arrowhead=diamond]; FactService -> FieldOntology [arrowhead=diamond];\n'
          '  FactService -> StructuredFact [label=" 1..*", arrowhead=open]; FactService -> ConceptView [style=dashed, label=" creates"];\n}\n')
    render("fig_class_agent", s)


def d_class_pipeline():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.6')
    s += cls("LLMProvider", [], ["+ acomplete(prompt, system, task)"], "violet")
    s += cls("Providers", ["MockLLMProvider", "GoogleProvider", "OpenAIProvider", "AnthropicProvider"], [], "violet")
    s += cls("DocumentPipeline", ["- extractor, deterministic", "- llm_extractor, chunker", "- embeddings, vector_store"], ["+ run(user_id, document_id, path, name, on_update)"], "green")
    s += cls("RAGRetrievalService", ["- min_similarity: float"], ["+ search(user_id, query, top_k)"], "green")
    s += cls("RAGAnswerService", ["- retrieval, llm"], ["+ answer(user_id, question, top_k)"], "green")
    s += cls("FieldObject", ["+ field_id, input_type, label", "+ name, id, placeholder, section", "+ options[], has_value"], [], "blue")
    s += ('  Providers -> LLMProvider [arrowhead=empty, label=" extend"];\n'
          '  DocumentPipeline -> LLMProvider [arrowhead=open, label=" optional"]; RAGAnswerService -> LLMProvider [arrowhead=open];\n'
          '  RAGAnswerService -> RAGRetrievalService [arrowhead=diamond]; DocumentPipeline -> FieldObject [style=invis];\n}\n')
    render("fig_class_pipeline", s)


def d_state_doc():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.5, ranksep=0.5')
    s += term("start")
    for k, l, col in [("up", "uploaded", "grey"), ("pr", "processing", "green"), ("ok", "processed", "green"), ("fa", "failed", "red"), ("rr", "requires_review", "amber"), ("de", "deleted", "grey")]:
        s += n(k, l, col)
    s += ('  start -> up; up -> pr [label=" job starts"]; pr -> ok [label=" stages complete"]; pr -> fa [label=" read error /\\n internal error"];\n'
          '  pr -> rr [label=" OCR needed,\\n not installed"]; fa -> pr [label=" reprocess", style=dashed]; rr -> pr [label=" reprocess", style=dashed];\n'
          '  ok -> de [label=" delete"]; fa -> de; rr -> de; up -> de;\n}\n')
    render("fig_state_doc", s)


def d_state_fact():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.8, ranksep=0.9')
    s += term("start") + n("ac", "active", "green") + n("su", "superseded", "amber") + n("rj", "rejected", "red")
    s += ('  start -> ac [label=" extracted or user entered"]; ac -> su [label=" other candidate confirmed /\\n value edited / custom value"];\n'
          '  ac -> rj [label=" user rejects"]; ac -> ac [label=" confirm"];\n}\n')
    render("fig_state_fact", s)


def d_state_ext():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.6, ranksep=0.5')
    s += term("start")
    for k, l, col in [("idle", "idle", "grey"), ("sc", "scanned", "blue"), ("an", "analyzing", "green"), ("rv", "review", "blue"), ("fl", "filling", "blue"), ("dn", "done", "green")]:
        s += n(k, l, col)
    s += ('  start -> idle; idle -> sc [label=" Scan this page"]; sc -> an [label=" Suggest values"]; an -> rv [label=" recommendations returned"];\n'
          '  rv -> fl [label=" Fill approved"]; fl -> dn [label=" results verified"]; dn -> idle [label=" Start over", style=dashed, constraint=false];\n'
          '  an -> idle [label=" error / 401", style=dashed, color="#A33A3A", constraint=false];\n}\n')
    render("fig_state_ext", s)


# ------------------------------------------------------------------ security / testing
def d_security():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.2, ranksep=0.2')
    layers = ["Edge: Nginx CSP and security headers; CORS limited to dashboard origin; TLS at deployment edge",
              "Identity: bcrypt; JWT HS256, 30 min, Authorization header; jti revocation (TTL); login limiter 5 per 60 s; SlowAPI route limits",
              "Tenant isolation: every MongoDB and Chroma query or delete filtered by user_id",
              "Input handling: extension, magic-byte and size checks; validation errors never echo values",
              "LLM safety: UNTRUSTED blocks, bracket escaping, 6 injection patterns, quarantine, quote verification, JSON validation",
              "Browser safety: activeTab, on-demand injection, sensitive fields skipped, values never read, token kept out of page, no auto-submit",
              "Observability: JSON logs with request ID; redaction of tokens, emails, long digit runs"]
    for i, l in enumerate(layers, 1):
        s += n(f"l{i}", f"{i}. {l}", "red", width=58)
    s += '  l1 -> l2 -> l3 -> l4 -> l5 -> l6 -> l7 [style=invis];\n}\n'
    render("fig_security", s)


def d_testing():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.4, ranksep=0.4')
    s += n("c", "git push / pull request", "grey", "ellipse", ', style="filled"')
    s += n("j1", "CI job 1: ruff, black, pytest (mock LLM, MongoDB service), Chroma integration, frontend + extension typecheck/test/build, Compose config", "green", width=44)
    s += n("j2", "CI job 2: Playwright browser E2E with real Chromium on an isolated Compose stack", "blue", width=44)
    s += n("r", "Real-provider tests: opt-in, never in CI", "violet")
    s += '  c -> j1 -> j2; c -> r [style=dotted, label=" manual"];\n}\n'
    render("fig_testing_ci", s)


def d_inject():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.3')
    s += n("src", "Untrusted text: page labels, document text, retrieved chunks, question", "grey", width=34)
    s += n("d", "detect_injection: 6 regex patterns", "red") + n("q", "Quarantine or drop chunk (logged, never sent)", "red")
    s += n("s", "sanitize_untrusted: collapse whitespace, cap length, replace angle brackets", "red", width=34)
    s += n("w", "wrap_untrusted: UNTRUSTED block", "red")
    s += n("l", "LLM call (system prompt: never follow instructions in data)", "violet", width=34)
    s += n("p", "parse_model: JSON schema validation", "green")
    s += n("v", "Grounding check: value or quote must appear in the cited chunk", "green", width=34)
    s += '  src -> d; d -> q [label=" match"]; d -> s [label=" clean"]; s -> w -> l -> p -> v;\n}\n'
    render("fig_inject", s)


def d_rag():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.3')
    s += n("q", "Question or field text", "blue") + n("e", "Embed query (MiniLM, 384-dim)", "violet")
    s += n("c", "Chroma query: filter user_id, cosine, top-k 4", "amber", "cylinder", width=26)
    s += n("t", "Similarity at least 0.35; safe_for_llm filter", "green")
    s += n("l", "LLM answer with used_chunk_ids", "violet") + n("a", "Answer with cited sources, or insufficient_evidence", "blue", width=30)
    s += '  q -> e -> c -> t -> l -> a; t -> a [style=dashed, label=" no evidence"];\n}\n'
    render("fig_rag", s)


def d_overview():
    s = HEAD.format(graph='rankdir=TB, nodesep=0.3, ranksep=0.7, newrank=true')
    a = "".join([n("a1", "1. Upload PDF, DOCX, TXT, image", "blue", width=16), n("a2", "2. Parse text (OCR if scanned)", "green", width=16),
                 n("a3", "3. Extract facts: rules + optional LLM", "green", width=16), n("a4", "4. Merge, normalise, keep provenance", "green", width=16)])
    s += cluster("A", "Phase A: prepare the profile (once per document)", "grey", a)
    b = "".join([n("b1", "5. Scan page: field descriptors only", "blue", width=16), n("b2", "6. Classify each field to an ontology concept", "green", width=16),
                 n("b3", "7. Resolve value: profile facts, else RAG evidence", "green", width=16), n("b4", "8. User reviews every value", "blue", width=16),
                 n("b5", "9. Fill approved fields and verify; never submit", "blue", width=16)])
    s += cluster("B", "Phase B: assist a form (every page)", "grey", b)
    s += n("db", "Fact store (MongoDB) + vector index (ChromaDB)", "amber", "cylinder", width=26)
    s += ('  a1 -> a2 -> a3 -> a4; b1 -> b2 -> b3 -> b4 -> b5;\n  a4 -> db [label=" store"]; db -> b3 [label=" read", constraint=false];\n}\n')
    render("fig_overview", s)


FUNCS = [d_overview, d_architecture, d_deployment, d_modules, d_context, d_dfd1, d_dfd2, d_langgraph, d_classify, d_decide, d_usecase, d_act_upload,
         d_act_fill, d_er, d_class_agent, d_class_pipeline, d_state_doc, d_state_fact, d_state_ext, d_security, d_testing, d_inject, d_rag]

if __name__ == "__main__":
    from PIL import Image
    for f in FUNCS:
        f()
    for fn in sorted(os.listdir(OUT)):
        if fn.endswith(".png"):
            w, h = Image.open(os.path.join(OUT, fn)).size
            w, h = w / 200, h / 200
            sc = min(5.77 / w, 8.0 / h, 1.0)
            print(f"{fn:26s} {w:5.1f}x{h:5.1f}in  eff_font={16*sc:4.1f}pt")
