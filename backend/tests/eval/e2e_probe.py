"""End-to-end probe against a running stack (API + MongoDB + ChromaDB + worker).

    cd backend
    python -m tests.eval.render_documents --out ../test-data/rendered
    python -m tests.eval.e2e_probe --api http://localhost:8000 --out ../docs/eval/e2e.json

Registers a fresh synthetic user, uploads rendered synthetic documents through
the real upload API, waits for processing, then asks the Ask Documents
endpoint a set of questions with known answers and scores them. A second user
uploads a different document to check that answers never cross users.

Scoring per question:

* ``answered``: the endpoint returned an answer (not insufficient evidence);
* ``correct``: every expected value appears in the answer text or its facts;
* ``forbidden``: a value that must not appear (another user's, the wrong class) appears;
* ``cited``: at least one returned source/fact names an expected document.

All data is synthetic. Nothing here is mocked: failures are real failures.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

DOCUMENTS = [
    "class12_hsc_table.digital.pdf",
    "class10_cbse_table.clean.png",
    "caste_certificate_clean.digital.pdf",
    "caste_validity_clean.clean.png",
    "income_certificate_clean.digital.pdf",
    "aadhaar_front_bilingual.clean.png",
    "bank_passbook_table.digital.pdf",
]
OTHER_USER_DOCUMENT = "ho_cbse_class12.digital.pdf"

# (question, expected substrings (all), forbidden substrings, documents that should be cited)
QUESTIONS: list[dict[str, Any]] = [
    {
        "q": "What was my Class 12 passing year and percentage?",
        "expect": ["2025", "88.67"],
        "forbid": ["91.4"],
        "cite": ["class12_hsc_table"],
        "kind": "exact",
    },
    {
        # The CBSE marksheet prints grades and subject totals but no percentage or
        # maximum marks: the right answer says so instead of inventing one.
        "q": "What is my Class 10 percentage?",
        "expect": [],
        "forbid": ["88.67", "93%", "93.0%", "93 %"],
        "cite": ["class10_cbse_table"],
        "kind": "exact",
        "expect_status": ["partial", "insufficient_evidence"],
    },
    {
        "q": "What is my caste certificate number and what is my caste validity certificate number?",
        "expect": ["CC/2024/PUN/012345", "CVC/2025/PUN/009876"],
        "forbid": [],
        "cite": ["caste_certificate", "caste_validity"],
        "kind": "exact",
    },
    {
        "q": "What is my annual family income according to my income certificate?",
        "expect": ["450000"],
        "forbid": [],
        "cite": ["income_certificate"],
        "kind": "document",
    },
    {
        "q": "Compare the information in my uploaded marksheets.",
        "expect": ["88.67", "2025"],
        "forbid": [],
        "cite": ["class12_hsc_table", "class10_cbse_table"],
        "kind": "multi_document",
    },
    {
        "q": "How many marks did I get in Physics in Class 12?",
        "expect": ["91"],
        "forbid": [],
        "cite": ["class12_hsc_table"],
        "kind": "document",
    },
    {
        "q": "Which required information for NEET is missing from my profile?",
        "expect": [],
        "forbid": [],
        "cite": [],
        "kind": "missing",
    },
    {
        "q": "Am I eligible for NEET UG based on my uploaded documents?",
        "expect": [],
        "forbid": ["you are eligible"],
        "cite": ["class12_hsc_table"],
        "kind": "eligibility",
    },
    {
        "q": "What is my passport number?",
        "expect": [],
        "forbid": [],
        "cite": [],
        "kind": "missing_evidence",
        "expect_status": ["insufficient_evidence", "partial"],
    },
]


def _wait(
    client: httpx.Client, headers: dict[str, str], document_id: str, timeout: float
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        response = client.get(f"/documents/{document_id}", headers=headers)
        if response.status_code == 429:
            time.sleep(5)
            continue
        if response.status_code != 200:
            raise RuntimeError(
                f"status poll failed: HTTP {response.status_code} {response.text[:300]}"
            )
        data = response.json()["data"]
        if data["status"] in ("processed", "failed", "requires_review"):
            return data
        if time.monotonic() > deadline:
            return data
        time.sleep(2)


def _register(client: httpx.Client, name: str) -> dict[str, str]:
    email = f"probe.{secrets.token_hex(4)}@example.com"
    password = f"Probe-{secrets.token_hex(6)}1"
    response = client.post(
        "/auth/register",
        json={
            "full_name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    response.raise_for_status()
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["data"]
    token = token.get("access_token") or token.get("token")
    return {"Authorization": f"Bearer {token}"}


def _upload(
    client: httpx.Client, headers: dict[str, str], data_dir: Path, name: str, timeout: float
) -> dict[str, Any]:
    started = time.monotonic()
    path = data_dir / name
    mime = "application/pdf" if name.endswith(".pdf") else "image/png"
    response = client.post(
        "/documents", headers=headers, files={"file": (name, path.read_bytes(), mime)}
    )
    response.raise_for_status()
    document = response.json()["data"]
    final = _wait(client, headers, document["document_id"], timeout)
    final["seconds"] = round(time.monotonic() - started, 1)
    return final


def _text_of(answer: dict[str, Any]) -> str:
    return json.dumps(answer, ensure_ascii=False).casefold()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--data", default="../test-data/rendered")
    parser.add_argument("--out", default="")
    parser.add_argument("--endpoint", default="/retrieval/rag/answer")
    parser.add_argument("--timeout", type=float, default=240)
    args = parser.parse_args()
    data_dir = Path(args.data)
    client = httpx.Client(base_url=f"{args.api.rstrip('/')}/api/v1", timeout=180)

    user = _register(client, "Aarav Example Patil")
    other = _register(client, "Priya Example Sharma")
    uploads = []
    for name in DOCUMENTS:
        result = _upload(client, user, data_dir, name, args.timeout)
        uploads.append(
            {
                "file": name,
                "status": result["status"],
                "document_type": result.get("document_type"),
                "facts": result.get("fact_count"),
                "chunks": result.get("chunk_count"),
                "seconds": result["seconds"],
                "error": result.get("processing_error"),
            }
        )
        print("upload", uploads[-1], flush=True)
    other_upload = _upload(client, other, data_dir, OTHER_USER_DOCUMENT, args.timeout)
    print(
        "other user upload", other_upload["status"], other_upload.get("document_type"), flush=True
    )

    results = []
    for item in QUESTIONS:
        started = time.monotonic()
        response = client.post(args.endpoint, headers=user, json={"question": item["q"]})
        seconds = round(time.monotonic() - started, 2)
        body = response.json()
        data = body.get("data") or {}
        text = _text_of(data) if response.status_code == 200 else ""
        answer_text = str(data.get("answer", ""))
        status = (
            data.get("status") if response.status_code == 200 else f"HTTP {response.status_code}"
        )
        correct = bool(text) and all(e.casefold() in text for e in item["expect"])
        # "I cannot state that you are eligible" is a refusal, not a forbidden claim
        forbidden = [
            f
            for f in item["forbid"]
            if re.search(
                rf"(?<!state that )(?<!say that )(?<!not ){re.escape(f)}", answer_text, re.I
            )
        ]
        cited = not item["cite"] or any(c in text for c in item["cite"])
        if "expect_status" in item:
            correct = status in item["expect_status"]
        results.append(
            {
                "question": item["q"],
                "kind": item["kind"],
                "http": response.status_code,
                "status": status,
                "correct": correct,
                "forbidden": forbidden,
                "cited": cited,
                "seconds": seconds,
                "answer": answer_text[:600] or (body.get("error") or {}).get("message"),
            }
        )
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)

    leak = client.post(
        args.endpoint, headers=other, json={"question": "What was my Class 12 percentage?"}
    ).json()
    leaked = "88.67" in json.dumps(leak)
    summary = {
        "uploads_processed": sum(u["status"] == "processed" for u in uploads),
        "uploads": len(uploads),
        "questions": len(results),
        "correct": sum(r["correct"] for r in results),
        "cited": sum(r["cited"] for r in results),
        "forbidden_hits": sum(bool(r["forbidden"]) for r in results),
        "http_errors": sum(r["http"] != 200 for r in results),
        "median_seconds": statistics.median(r["seconds"] for r in results),
        "cross_user_leak": leaked,
    }
    print(json.dumps(summary, indent=1))
    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {"summary": summary, "uploads": uploads, "questions": results},
                indent=1,
                ensure_ascii=False,
            ),
            "utf-8",
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
