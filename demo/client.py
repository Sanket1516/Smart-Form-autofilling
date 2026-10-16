"""Thin HTTP client for the real backend API, used by the demo CLI and the evaluation.

Nothing here talks to a database or the vector store directly: every call goes
through the same public API the web app and the Chrome extension use.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo.applicant@example.com")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Demo-Applicant-2026!")
DEMO_NAME = "Kavya Suresh Deshpande"
DEFAULT_API = os.environ.get("DEMO_API", "http://localhost:8000")


class InfrastructureError(RuntimeError):
    """The stack (API, database, vector store, LLM) was unavailable: not a model-quality failure."""


class DemoClient:
    def __init__(self, api: str = DEFAULT_API, email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD,
                 timeout: float = 180) -> None:
        self.http = httpx.Client(base_url=f"{api.rstrip('/')}/api/v1", timeout=timeout)
        self.email, self.password = email, password
        self.headers: dict[str, str] = {}

    # ------------------------------------------------------------------ plumbing
    def _call(self, method: str, url: str, **kw: Any) -> dict[str, Any]:
        for attempt in range(6):
            try:
                response = self.http.request(method, url, headers={**self.headers, **kw.pop("headers", {})}, **kw)
            except httpx.TransportError as exc:
                if attempt < 3:  # a container restarting mid-run: wait and retry before calling it an outage
                    time.sleep(6)
                    continue
                raise InfrastructureError(f"API unreachable: {exc}") from exc
            if response.status_code == 429:  # rate limited: wait it out instead of failing the run
                time.sleep(5 + attempt * 5)
                continue
            if response.status_code >= 500:
                raise InfrastructureError(f"{method} {url} -> HTTP {response.status_code}: {response.text[:200]}")
            if response.status_code >= 400:
                raise RuntimeError(f"{method} {url} -> HTTP {response.status_code}: {response.text[:300]}")
            return response.json()
        raise InfrastructureError(f"{method} {url} kept returning HTTP 429")

    def health(self) -> dict[str, Any]:
        return self._call("GET", "/health/services")["data"]

    # ---------------------------------------------------------------------- auth
    def sign_in(self) -> None:
        """Log in as the dedicated demo account, registering it on first use."""
        try:
            data = self._call("POST", "/auth/login", json={"email": self.email, "password": self.password})
        except RuntimeError:
            self._call("POST", "/auth/register", json={
                "full_name": DEMO_NAME, "email": self.email, "password": self.password,
                "confirm_password": self.password})
            data = self._call("POST", "/auth/login", json={"email": self.email, "password": self.password})
        token = data["data"].get("access_token") or data["data"].get("token")
        self.headers = {"Authorization": f"Bearer {token}"}

    # ----------------------------------------------------------------- documents
    def documents(self) -> list[dict[str, Any]]:
        return self._call("GET", "/documents?limit=100")["data"]["documents"]

    def upload(self, path: Path) -> dict[str, Any]:
        mime = "application/pdf" if path.suffix.lower() == ".pdf" else "image/png"
        return self._call("POST", "/documents", files={"file": (path.name, path.read_bytes(), mime)})["data"]

    def wait(self, document_id: str, timeout: float = 600) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            doc = self._call("GET", f"/documents/{document_id}")["data"]
            if doc["status"] in ("processed", "failed", "requires_review") and doc.get("index_status") != "pending":
                return doc
            if doc["status"] in ("failed",):
                return doc
            if time.monotonic() > deadline:
                return doc
            time.sleep(2)

    def delete(self, document_id: str) -> None:
        self._call("DELETE", f"/documents/{document_id}")

    def doc_facts(self, document_id: str) -> list[dict[str, Any]]:
        return self._call("GET", f"/documents/{document_id}/facts")["data"]["facts"]

    def profile_facts(self) -> list[dict[str, Any]]:
        return self._call("GET", "/profile/facts")["data"]["facts"]

    def discovered_facts(self) -> list[dict[str, Any]]:
        return self._call("GET", "/profile/discovered-facts")["data"]

    def confirm_fact(self, fact: dict[str, Any]) -> None:
        self._call("PUT", f"/profile/facts/{fact['fact_id']}", json={"value": fact["value"]})

    # ---------------------------------------------------------------------- RAG
    def ask(self, question: str, *, document_ids: list[str] | None = None,
            history: list[dict[str, str]] | None = None, exam_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"question": question, "history": history or []}
        if document_ids:
            body["document_ids"] = document_ids
        if exam_id:
            body["exam_id"] = exam_id
        return self._call("POST", "/retrieval/rag/answer", json=body)["data"]

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self._call("POST", "/retrieval/rag", json={"query": query, "top_k": top_k})["data"]["results"]
