"""Resume demo: load the fictional resume into its own account and run the demo form against the real API.

    python -m demo.cli resume generate     # profile -> frontend/public/demo/resume/DEMO_RESUME_kavya_deshpande.pdf
    python -m demo.cli resume load         # upload + process it (idempotent)
    python -m demo.cli resume check        # run the 34-field demo form through the real pipeline, print evidence
    python -m demo.cli resume status|cleanup [--delete-account]

Isolation: a separate account (demo.resume@example.com) and file prefix (DEMO_RESUME_), so the 15-document
judge demo and its evaluation are never affected. `check` calls the same public API the Chrome extension uses.
"""

from __future__ import annotations

import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from demo import loader
from demo.client import DEFAULT_API, DemoClient
from demo.resume_gen import FILE_NAME, PREFIX

RESUME_EMAIL = "demo.resume@example.com"
RESUME_PASSWORD = "Demo-Resume-2026!"
RESUME_NAME = "Kavya Suresh Deshpande"

PUBLIC = Path(__file__).resolve().parent.parent / "frontend" / "public" / "demo" / "resume"
FORM_FILE = PUBLIC / "graduate-software-engineer-application.html"
RESUME_PDF = PUBLIC / FILE_NAME


def client(api: str = DEFAULT_API) -> DemoClient:
    c = DemoClient(api=api, email=RESUME_EMAIL, password=RESUME_PASSWORD, full_name=RESUME_NAME)
    c.sign_in()
    return c


def load(c: DemoClient, log=print) -> list[dict[str, Any]]:
    if not RESUME_PDF.exists():
        raise FileNotFoundError(f"{RESUME_PDF} is missing. Run: python -m demo.cli resume generate")
    return loader.load(c, files=[RESUME_PDF], log=log)


def cleanup(c: DemoClient, log=print) -> int:
    removed = 0
    for doc in c.documents():
        if doc["file_name"].startswith(PREFIX):
            c.delete(doc["document_id"])
            removed += 1
            log(f"  deleted {doc['file_name']}")
    return removed


# ---------------------------------------------------------------- form field extraction (test harness)

class _FormParser(HTMLParser):
    """Reads label, type, options and section from the demo form, the way the extension's detector does."""

    def __init__(self) -> None:
        super().__init__()
        self.fields: list[dict[str, Any]] = []
        self._labels: dict[str, str] = {}
        self._section = ""
        self._capture: str | None = None
        self._buffer = ""
        self._select: dict[str, Any] | None = None
        self._option: dict[str, str] | None = None
        self._label_for: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "h2":
            self._capture, self._buffer = "h2", ""
        elif tag in ("label", "legend"):
            self._label_for = a.get("for") or None
            self._capture, self._buffer = "label", ""
        elif tag in ("input", "textarea", "select"):
            if tag == "input" and a.get("type") in ("submit", "button", "reset", "hidden"):
                return
            field = {
                "field_id": a.get("id") or a.get("name"), "tag": tag, "id": a.get("id", ""), "name": a.get("name", ""),
                "input_type": "select" if tag == "select" else ("textarea" if tag == "textarea" else a.get("type", "text")),
                "placeholder": a.get("placeholder", ""), "required": "required" in a, "section": self._section,
                "options": [],
            }
            self.fields.append(field)
            if tag == "select":
                self._select = field
        elif tag == "option" and self._select is not None:
            self._option = {"value": a.get("value", ""), "label": ""}
            self._capture, self._buffer = "option", ""

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer += data

    def handle_endtag(self, tag: str) -> None:
        text = " ".join(self._buffer.split())
        if tag == "h2" and self._capture == "h2":
            self._section, self._capture = text, None
        elif tag in ("label", "legend") and self._capture == "label":
            if self._label_for:
                self._labels[self._label_for] = text
            self._capture = None
        elif tag == "option" and self._option is not None:
            self._option["label"] = text
            if self._option["value"]:
                self._select["options"].append(self._option)
            self._option, self._capture = None, None
        elif tag == "select":
            self._select = None


def extract_fields(html: str) -> list[dict[str, Any]]:
    parser = _FormParser()
    parser.feed(html)
    fields = []
    for field in parser.fields:
        label = parser._labels.get(field["id"], "")
        if not label:
            continue  # the declaration checkbox is wrapped in a legend; it is a user decision anyway
        fields.append({**field, "label": label, "question": label})
    return fields


def run_form(c: DemoClient, timeout: float = 240) -> list[dict[str, Any]]:
    """Create a form session, analyse the demo form, wait, and return the recommendations."""
    fields = extract_fields(FORM_FILE.read_text("utf-8"))
    base = "http://localhost:5173/demo/resume/graduate-software-engineer-application.html"
    session = c._call("POST", "/forms/sessions", json={
        "website_origin": "http://localhost:5173", "page_url": base, "form_id": "graduate-software-engineer"})["data"]
    sid = session["session_id"]
    c._call("POST", f"/forms/sessions/{sid}/analyze", json={"fields": fields})
    deadline = time.monotonic() + timeout
    while True:
        data = c._call("GET", f"/forms/sessions/{sid}")["data"]
        if data.get("status") != "processing" or time.monotonic() > deadline:
            break
        time.sleep(2)
    recs = c._call("GET", f"/forms/sessions/{sid}/recommendations")["data"]["recommendations"]
    order = {f["field_id"]: i for i, f in enumerate(fields)}
    return sorted(recs, key=lambda r: order.get(r["field_id"], 999))


def render(recs: list[dict[str, Any]]) -> str:
    lines = [f"{'field':<22} {'category/concept':<30} {'mode':<8} {'status':<20} value / reason"]
    for r in recs:
        value = r.get("recommended_value")
        shown = (str(value)[:70] + "…") if value and len(str(value)) > 70 else (value if value is not None else "")
        src = r.get("source") or {}
        lines.append(f"{r['field_id']:<22} {str(r.get('concept') or '-'):<30} {r.get('retrieval_type', ''):<8} "
                     f"{r['status']:<20} {shown!s}" + ("" if value else f"  [{r.get('reason', '')[:80]}]"))
        if value and src.get("snippet"):
            lines.append(f"{'':<22} evidence: {src.get('document_name') or src.get('type')} p{src.get('page') or '-'}: "
                         f"{' '.join(src['snippet'].split())[:110]}")
    return "\n".join(lines)
