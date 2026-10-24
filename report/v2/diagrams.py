# -*- coding: utf-8 -*-
"""Renders the diagrams used by the revised black book (report/v2).

New in this version: the end-to-end architecture (reviewer note: the old Figure 4.1 stopped at
embedding storage) and the decision flowchart with Start/End terminators (reviewer note on the
old Figure 4.23). The DFD, ER and LangGraph diagrams reuse the checked sources from report/figures,
re-set in Times New Roman. Run: python report/v2/diagrams.py
"""
import os
import re
import subprocess

DOT = r"C:\Program Files\Graphviz\bin\dot.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures", "diagrams")
OLD = os.path.join(HERE, "..", "figures", "diagrams")
FONT = "Times New Roman,"
BOLD = "Times New Roman, Bold"

HEAD = f"""
  graph [fontname="{FONT}", fontsize=17, pad=0.15, nodesep=0.28, ranksep=0.42, newrank=true];
  node  [fontname="{FONT}", fontsize=17, style="filled,rounded", shape=box, penwidth=1.4, margin="0.12,0.06", fillcolor="#FFFFFF", color="#333333"];
  edge  [fontname="{FONT}", fontsize=15, penwidth=1.3, arrowsize=0.8, color="#333333"];
"""


def render(name, src):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".dot")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    subprocess.run([DOT, "-Tpng", "-Gdpi=220", path, "-o", os.path.join(OUT, name + ".png")], check=True)


def architecture():
    blue, green, amber, violet, grey = "#DCE9F8", "#DDEFE0", "#FBEBCB", "#E9E1F2", "#EFEFEF"
    src = f"""digraph G {{ rankdir=TB; {HEAD}
  graph [nodesep=0.22, ranksep=0.36];
  subgraph cluster_c {{ label="1. Clients"; labeljust=l; fontname="{BOLD}"; style="rounded,filled"; fillcolor="{blue}"; color="#2F5D9B";
    dash [label="Web dashboard\n(React)"];
    ext [label="Chrome extension\n(popup + content\nscript)"];
    form [label="Web form on\nany website", fillcolor="{grey}"];
  }}
  api [label="2. FastAPI backend: REST API, JWT login,\nrate limits, per-user data isolation", fillcolor="#F8DCDC", color="#A33A3A"];
  subgraph cluster_a {{ label="3. Document ingestion (background)"; labeljust=l; fontname="{BOLD}"; style="rounded,filled"; fillcolor="{green}"; color="#3C7A4B";
    q [label="Redis queue →\nCelery worker"];
    p1 [label="Read text\n(RapidOCR\nfor images)"];
    p2 [label="Identify\ndocument type\n(17 types)"];
    p3 [label="Extract facts\n(rules + optional\nLLM)"];
    p4 [label="Merge; keep\npage and\nevidence"];
    p5 [label="Chunk text;\nembed\n(MiniLM)"];
  }}
  subgraph cluster_d {{ label="4. Storage"; labeljust=l; fontname="{BOLD}"; style="rounded,filled"; fillcolor="{amber}"; color="#A8741A";
    files [label="File\nstorage", shape=cylinder, style=filled, fillcolor="#FFFFFF"];
    mongo [label="MongoDB\n(facts,\nsessions)", shape=cylinder, style=filled, fillcolor="#FFFFFF"];
    chroma [label="ChromaDB\n(chunk\nvectors)", shape=cylinder, style=filled, fillcolor="#FFFFFF"];
  }}
  subgraph cluster_u {{ label="5. Using the stored data"; labeljust=l; fontname="{BOLD}"; style="rounded,filled"; fillcolor="{violet}"; color="#6B4E9B";
    qa [label="Ask Documents:\nexact facts +\nsemantic search\n→ cited answer"];
    llm [label="LLM provider\n(Gemini or\nlocal model)", style="filled,rounded,dashed", fillcolor="{grey}"];
    lg [label="Form-fill LangGraph:\nclassify fields →\nresolve from profile\n→ evidence → decide"];
  }}
  review [label="6. Popup review: the user approves each value;\napproved values are filled into the form and\nread back to verify; the form is never submitted", fillcolor="{blue}", color="#2F5D9B"];

  {{rank=same; dash; ext; form}}
  form -> ext [label=" scan", constraint=false];
  dash -> api [label=" upload,\n ask"]; ext -> api [label=" analyze"];
  api -> q [label=" new document"];
  {{rank=same; q; p1; p2}}
  {{rank=same; p3; p4; p5}}
  q -> p1 -> p2; p2 -> p3 [constraint=false]; p3 -> p4 -> p5;
  q -> p3 [style=invis]; p1 -> p4 [style=invis]; p2 -> p5 [style=invis];
  {{rank=same; files; mongo; chroma}}
  files -> p1 [style=dashed, constraint=false];
  p4 -> mongo [label=" facts"]; p5 -> chroma [label=" vectors"];
  p3 -> files [style=invis];
  {{rank=same; qa; llm; lg}}
  mongo -> qa; chroma -> qa; mongo -> lg [label=" profile"]; chroma -> lg [label=" evidence"];
  qa -> llm [style=dashed, dir=both, constraint=false]; llm -> lg [style=dashed, dir=both, constraint=false];
  lg -> review [label=" recommendations"]; qa -> review [style=invis];
}}"""
    render("architecture", src)


def decide():
    src = f"""digraph G {{ rankdir=TB; {HEAD}
  graph [ranksep=0.22, nodesep=0.5];
  node [fontsize=19]; edge [fontsize=17];
  s [label="Start: field with a\ncandidate value", shape=oval, style=filled, fillcolor="#DCE9F8"];
  cap [label="If the LLM chose the field’s\nconcept, cap the confidence"];
  d1 [label="Blocked, skipped,\nerror or in review?", shape=diamond, style=filled, fillcolor="#EFEFEF"];
  keep [label="Keep earlier\nstatus"];
  d2 [label="Value\nfound?", shape=diamond, style=filled, fillcolor="#EFEFEF"];
  miss [label="missing_information\n(+ document to upload)", fillcolor="#FBEBCB"];
  fmt [label="Format for the field\n(date, option, radio)"];
  d3 [label="Formatted?", shape=diamond, style=filled, fillcolor="#EFEFEF"];
  rev1 [label="needs_review\n(shown as candidate)", fillcolor="#FBEBCB"];
  d4 [label="Sensitive or\ninferred?", shape=diamond, style=filled, fillcolor="#EFEFEF"];
  conf [label="requires_confirmation\n= true", fillcolor="#F8DCDC"];
  d5 [label="Confidence ≥ 0.85\nand no confirmation\nneeded?", shape=diamond, style=filled, fillcolor="#EFEFEF"];
  ready [label="ready\n(pre-ticked)", fillcolor="#DDEFE0"];
  rev2 [label="needs_review\n(user confirms)", fillcolor="#FBEBCB"];
  e [label="End: store the\nrecommendation", shape=oval, style=filled, fillcolor="#DCE9F8"];
  s -> cap -> d1;
  d1 -> d2 [label=" no"]; d1 -> keep [label=" yes"];
  d2 -> fmt [label=" yes"]; d2 -> miss [label=" no"];
  fmt -> d3; d3 -> d4 [label=" yes"]; d3 -> rev1 [label=" no"];
  d4 -> d5 [label=" no"]; d4 -> conf [label=" yes"]; conf -> d5;
  d5 -> ready [label=" yes"]; d5 -> rev2 [label=" no"];
  {{rank=same; d1; keep}} {{rank=same; d2; miss}} {{rank=same; d3; rev1}} {{rank=same; d4; conf}}
  {{rank=same; ready; rev2}}
  ready -> e; rev2 -> e;
  keep -> e [constraint=false]; miss -> e [constraint=false]; rev1 -> e [constraint=false];
}}"""
    render("decide", src)


def overview():
    src = f"""digraph G {{ rankdir=TB; {HEAD}
  graph [ranksep=0.55];
  subgraph cluster_A {{ label="Phase A: build the profile"; labeljust=l; fontname="{BOLD}"; style="rounded,filled"; fillcolor="#EFEFEF"; color="#555555";
    a1 [label="1. Upload PDF,\\nDOCX, TXT or\\nimage", fillcolor="#DCE9F8"];
    a2 [label="2. Read text\\n(OCR for\\nscans)", fillcolor="#DDEFE0"];
    a3 [label="3. Identify the\\ndocument type", fillcolor="#DDEFE0"];
    a4 [label="4. Extract facts\\n(rules + optional\\nLLM)", fillcolor="#DDEFE0"];
    a5 [label="5. Merge and keep\\nthe evidence", fillcolor="#DDEFE0"];
  }}
  subgraph cluster_B {{ label="Phase B: fill a form"; labeljust=l; fontname="{BOLD}"; style="rounded,filled"; fillcolor="#EFEFEF"; color="#555555";
    b1 [label="6. Scan the\\nform's fields", fillcolor="#DCE9F8"];
    b2 [label="7. Classify each\\nfield", fillcolor="#DDEFE0"];
    b3 [label="8. Find a value:\\nprofile, then\\ndocument text", fillcolor="#DDEFE0"];
    b4 [label="9. User reviews\\nevery value", fillcolor="#DCE9F8"];
    b5 [label="10. Fill approved\\nfields and verify", fillcolor="#DCE9F8"];
  }}
  db [label="MongoDB (facts) +\\nChromaDB (text chunks)", shape=cylinder, style=filled, fillcolor="#FBEBCB"];
  a1 -> a2 -> a3 -> a4 -> a5; b1 -> b2 -> b3 -> b4 -> b5;
  a5 -> db [label=" store"]; db -> b3 [label=" read", constraint=false];
}}"""
    render("overview", src)


def refont(name, new_name, subs=()):
    with open(os.path.join(OLD, name + ".dot"), encoding="utf-8") as f:
        src = f.read()
    src = src.replace('"Arial Bold"', f'"{BOLD}"').replace('"Arial"', f'"{FONT}"')
    for a, b in subs:
        src = re.sub(a, b, src)
    render(new_name, src)


if __name__ == "__main__":
    architecture()
    decide()
    overview()
    refont("fig_dfd1", "dfd1")
    refont("fig_er", "er")
    refont("fig_langgraph", "langgraph")
    print("diagrams written to", OUT)
