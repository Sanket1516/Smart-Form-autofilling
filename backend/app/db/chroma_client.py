"""Async HTTP client for the ChromaDB server."""

import asyncio
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ChromaClient:
    """Manage the configured ChromaDB collection through its HTTP API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.chromadb_url.rstrip("/")
        self._tenant = settings.chromadb_tenant
        self._database = settings.chromadb_database
        self.collection_name = settings.chromadb_collection
        self._timeout = settings.chromadb_timeout_seconds

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None) -> object:
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=self._timeout) as response:
            content = response.read()
            return json.loads(content.decode()) if content else None

    async def is_healthy(self) -> bool:
        try:
            await asyncio.to_thread(self._heartbeat)
        except Exception:
            return False
        return True

    def _heartbeat(self) -> None:
        for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                self._request("GET", endpoint)
                return
            except (HTTPError, URLError, TimeoutError):
                continue
        raise ConnectionError("ChromaDB heartbeat failed")

    async def ensure_collection(self) -> None:
        path = f"/api/v2/tenants/{self._tenant}/databases/{self._database}/collections"
        payload = {
            "name": self.collection_name,
            "metadata": {
                "schema": "user_id,document_id,document_name,page_number,language,chunk_index"
            },
            "get_or_create": True,
        }
        try:
            await asyncio.to_thread(self._request, "POST", path, payload)
            logger.info(
                "chroma_collection_initialized",
                extra={"collection": self.collection_name},
            )
        except Exception:
            logger.exception(
                "chroma_collection_initialization_failed",
                extra={"collection": self.collection_name},
            )
            raise
