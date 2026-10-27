"""Load the demo documents into a *dedicated demo account* and remove them again.

* Idempotent: a document is uploaded only when no document with that file name
  exists in the account yet, so running it twice creates no duplicates.
* Isolated: only files named ``DEMO_*.pdf`` are ever touched, and the default
  account is ``demo.applicant@example.com``, separate from real user accounts.
* Everything goes through the public upload API (OCR, extraction, MongoDB and
  vector indexing run exactly as for a real upload).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from demo.client import DemoClient
from demo.documents_gen import PREFIX

DOC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "demo" / "documents"


def demo_files() -> list[Path]:
    return sorted(DOC_DIR.glob(f"{PREFIX}*.pdf"))


def load(client: DemoClient, *, wait: bool = True, timeout: float = 900, log=print,
         files: list[Path] | None = None) -> list[dict[str, Any]]:
    existing = {d["file_name"]: d for d in client.documents()}
    results = []
    pending = []
    for path in (demo_files() if files is None else files):
        found = existing.get(path.name)
        if found and found["status"] != "failed":
            log(f"  skip   {path.name} (already {found['status']})")
            pending.append((path, found, False))
            continue
        if found:  # a failed earlier attempt is replaced, not duplicated
            client.delete(found["document_id"])
        started = time.monotonic()
        doc = client.upload(path)
        log(f"  upload {path.name}")
        pending.append((path, doc, True))
        results.append({"file": path.name, "started": started})
    out = []
    for path, doc, uploaded in pending:
        started = time.monotonic()
        final = client.wait(doc["document_id"], timeout) if wait else doc
        retries = 0
        # A transient LLM outage (HTTP 503/403 from the provider) leaves "AI extraction was unavailable":
        # reprocess a couple of times so an infrastructure blip does not look like an extraction failure.
        while wait and retries < 2 and any("AI extraction was unavailable" in w for w in final.get("warnings") or []):
            retries += 1
            log(f"  retry  {path.name}: LLM was unavailable, reprocessing ({retries}/2)")
            time.sleep(8)
            client._call("POST", f"/documents/{doc['document_id']}/reprocess")
            time.sleep(2)
            final = client.wait(doc["document_id"], timeout)
        out.append({"file": path.name, "document_id": doc["document_id"], "uploaded_now": uploaded,
                    "status": final["status"], "document_type": final.get("document_type"),
                    "facts": final.get("fact_count"), "chunks": final.get("chunk_count"),
                    "index_status": final.get("index_status"), "error": final.get("processing_error"),
                    "warnings": final.get("warnings") or [], "llm_retries": retries,
                    "llm_unavailable": any("AI extraction was unavailable" in w for w in final.get("warnings") or []),
                    "wait_seconds": round(time.monotonic() - started, 1)})
        log(f"  {final['status']:<9} {path.name}  type={final.get('document_type')} facts={final.get('fact_count')} "
            f"chunks={final.get('chunk_count')} index={final.get('index_status')}")
    return out


def cleanup(client: DemoClient, log=print) -> int:
    """Delete only DEMO_* documents (their extracted facts and vectors go with them)."""
    removed = 0
    for doc in client.documents():
        if doc["file_name"].startswith(PREFIX):
            client.delete(doc["document_id"])
            removed += 1
            log(f"  deleted {doc['file_name']}")
    return removed
