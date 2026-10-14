# -*- coding: utf-8 -*-
import os
import re

from docx.shared import Inches, Pt

from content_refs import REFS, c

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def snippet(rel, start_pat, end_pat=None, max_lines=60):
    """Return exact source lines from start_pat up to (excluding) end_pat. Fails loudly if a marker is missing."""
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        lines = f.read().split("\n")
    s = next(i for i, l in enumerate(lines) if re.search(start_pat, l))
    e = len(lines)
    if end_pat:
        e = next(i for i in range(s + 1, len(lines)) if re.search(end_pat, lines[i]))
    out = lines[s:e][:max_lines]
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


def references(R):
    R.h1_plain("References")
    for i, (key, text) in enumerate(REFS, 1):
        p = R.p(f"[{i}]  {text}")
        p.paragraph_format.left_indent = Inches(0.45)
        p.paragraph_format.first_line_indent = Inches(-0.45)
        p.paragraph_format.space_after = Pt(6)
        p.alignment = 0


def appendix_title(R, roman, title):
    R.h1_plain(f"Appendix {roman}: {title}")


def build(R):
    # ------------------------------------------------------------ Appendix I
    appendix_title(R, "I", "Source Code Excerpts")
    R.p(
        "The excerpts below are copied unchanged from the repository at the paths shown. They are chosen because they implement the main design decisions of "
        "Chapter 4. Code is set in a monospaced font for legibility."
    )
    items = [
        ("I.1 Prompt-injection helpers", "backend/app/security/prompt_safety.py", r"^_INJECTION_PATTERNS", None, 40,
         "detect_injection flags six patterns, sanitize_untrusted collapses whitespace and neutralises angle brackets, and wrap_untrusted places pre-sanitised text in a tagged data block whose delimiters cannot be forged by the content."),
        ("I.2 LangGraph construction", "backend/app/agents/graph.py", r"graph = StateGraph\(FillState\)", r"self\._graph = graph\.compile\(\)", 40,
         "The seven nodes and the two conditional edges of " + R.f("langgraph") + ". Classification is skipped when every field is resolved, and document retrieval is skipped when no field needs it."),
        ("I.3 Decision node", "backend/app/agents/graph.py", r"async def _decide", r"async def _persist", 60,
         "Applies formatting, sensitivity and confidence rules to give each field its final status (" + R.f("decide") + ")."),
        ("I.4 Concept view and conflict logic", "backend/app/services/facts.py", r"def _view\(self", r"# -+ conflicts", 60,
         "Groups active facts by comparison key; one group gives a resolved view, several groups give multiple or conflict depending on the concept’s cardinality."),
        ("I.5 Merging candidate facts", "backend/app/extraction/merge.py", r"def merge_candidates", None, 45,
         "Combines agreeing candidates, raises confidence slightly for agreement between extractors and keeps different values apart."),
        ("I.6 Field eligibility in the extension", "extension/src/content/detector.ts", r"export function isEligible", r"// -+ description", 40,
         "Skips protected input types, disabled and read-only controls, sensitive autocomplete tokens and descriptive text, and invisible or far off-screen controls."),
        ("I.7 Writing a value into a page", "extension/src/content/autofill.ts", r"function setNativeValue", r"function normalize\(", 40,
         "Uses the native value setter and input and change events so that framework-controlled inputs register the change, then verifies the result after a short delay."),
        ("I.8 Settings validators", "backend/app/core/config.py", r"@field_validator\(\"jwt_secret_key\"\)", r"@property", 50,
         "Rejects placeholder or short secrets, unsupported algorithms, unknown providers, a real provider without a key and inconsistent chunk settings at start-up."),
    ]
    for title, rel, sp, ep, ml, expl in items:
        R.h3(title)
        R.p(f"**File:** `{rel}`. {expl}")
        R.code(snippet(rel, sp, ep, ml))

    # ------------------------------------------------------------ Appendix II
    appendix_title(R, "II", "Ontology Excerpt")
    R.p(
        "The first concepts of backend/app/ontology/field_ontology.yaml (version 3.0.0), unchanged. The full file defines 91 concepts. A concept with an "
        "autocomplete list is matched by the HTML autocomplete token before any text matching."
    )
    R.code(snippet("backend/app/ontology/field_ontology.yaml", r"^version", None, 62))

    # ------------------------------------------------------------ Appendix III
    appendix_title(R, "III", "Configuration Reference")
    R.p(
        "The repository’s .env.example, unchanged. All values are placeholders or safe local defaults. JWT_SECRET_KEY=change-me is deliberately rejected by "
        "the application until it is replaced by a random value of at least 32 characters."
    )
    with open(os.path.join(ROOT, ".env.example"), encoding="utf-8") as f:
        env = "\n".join(l for l in f.read().split("\n") if l.strip())
    R.code(env)

    # ------------------------------------------------------------ Appendix IV
    appendix_title(R, "IV", "List of Technical Components")
    R.h3("Backend (Python 3.11)")
    R.p(R.t("app_backend") + " lists the backend packages and their version constraints from requirements.txt, requirements-ocr.txt and requirements-dev.txt.")
    R.table("app_backend", [
        ["Package", "Version constraint", "Role"],
        ["fastapi, uvicorn[standard]", ">=0.115,<1.0; >=0.30,<1.0", "Web framework and ASGI server"],
        ["pydantic, pydantic-settings, email-validator", ">=2.8,<3.0; >=2.6,<3.0; >=2.2,<3.0", "Models, settings, e-mail validation"],
        ["bcrypt, PyJWT", ">=4.2,<5.0; >=2.9,<3.0", "Password hashing; tokens"],
        ["slowapi", ">=0.1.9,<0.2.0", "Rate limiting"],
        ["httpx", ">=0.27,<1.0", "HTTP client for LLM providers and ChromaDB"],
        ["motor, pymongo", ">=3.6,<4.0; >=4.9,<5.0", "MongoDB access"],
        ["langgraph", ">=1.0,<2.0", "Form-fill state graph"],
        ["pdfplumber, pypdfium2, python-docx, Pillow, opencv-python-headless", "see requirements.txt", "Document parsing and image pre-processing"],
        ["sentence-transformers", ">=3.0,<6.0", "Embeddings (all-MiniLM-L6-v2)"],
        ["celery[redis]", ">=5.4,<6.0", "Background jobs in Compose"],
        ["cloudinary", ">=1.41.0,<2.0.0", "Optional file storage"],
        ["paddleocr, paddlepaddle", ">=2.7,<3.0; >=2.6,<3.0", "Optional OCR (requirements-ocr.txt)"],
        ["pytest, pytest-cov, ruff, black, pip-audit, reportlab", "see requirements-dev.txt", "Tests, lint, format, dependency audit, synthetic PDFs"],
    ], [2.2, 1.9, 1.65], font=9.5)
    R.h3("Dashboard and extension")
    R.p(R.t("app_front") + " lists the framework versions declared in the two package manifests.")
    R.table("app_front", [
        ["Component", "Dashboard", "Extension"],
        ["React", "19.2", "18.3"],
        ["TypeScript", "6.0", "5.5"],
        ["Vite", "8.3", "5.4"],
        ["Vitest", "5.0", "2.0"],
        ["jsdom", "29", "25"],
        ["Other", "React Router 7, lucide-react, Testing Library", "lucide-react, Playwright 1.63"],
    ], [1.5, 2.1, 2.15], font=10)
    R.h3("Services and tools")
    R.bullets([
        "MongoDB 8.0, ChromaDB (chromadb/chroma image), Redis 7 (alpine), Nginx (dashboard image), Docker Compose.",
        "Playwright with Chromium for the end-to-end test; GitHub Actions for continuous integration.",
        "Graphviz 16.1 and Pillow were used to draw the diagrams of this report from scripts kept with the report sources.",
    ])

    # ------------------------------------------------------------ Appendix V
    appendix_title(R, "V", "Installation and Test Commands")
    R.p("Commands from the repository README, for a Windows PowerShell session. Docker Desktop with Compose v2 is required for the stack.")
    R.code(
        "# 1. configuration\n"
        "Copy-Item .env.example .env\n"
        "# set JWT_SECRET_KEY to a random value of at least 32 characters, e.g.\n"
        "python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n\n"
        "# 2. start the stack (MongoDB, ChromaDB, Redis, API, worker, dashboard, extension builder)\n"
        "docker compose up --build\n"
        "# dashboard: http://localhost:5173   API: http://localhost:8000   docs: /docs\n\n"
        "# 3. development environment and checks\n"
        "python -m venv .venv ; .venv\\Scripts\\Activate.ps1\n"
        "python -m pip install -r backend/requirements-dev.txt\n"
        "npm ci\n"
        "python -m pytest\n"
        "npm run typecheck ; npm test ; npm run build\n\n"
        "# 4. isolated browser end-to-end test\n"
        ".\\scripts\\test-e2e.ps1",
    )
    R.p(
        "To use the extension, build it (the Compose stack does this) and load the extension/dist folder as an unpacked extension in Chrome, open a form, "
        "click the extension icon, choose Scan this page and then Suggest values, review the list and choose Fill. To read scanned documents, set INSTALL_OCR=true "
        "and rebuild, then choose Process again on the document."
    )

    # ------------------------------------------------------------ Appendix VI
    appendix_title(R, "VI", "List of Papers Presented and Published")
    R.p(
        "No paper presented or published from this project is recorded in the project repository. If the team has presented or published work, "
        "the details are to be entered here before submission."
    )
