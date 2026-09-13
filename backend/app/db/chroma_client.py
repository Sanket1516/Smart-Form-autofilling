"""Async HTTP client for the ChromaDB server with vector storage and RAG query support."""

import asyncio
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.processing.chunking import DocumentChunk

logger = logging.getLogger(__name__)


class ChromaClient:
    """Manage the configured ChromaDB collection through its HTTP API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.chromadb_url.rstrip("/")
        self._tenant = settings.chromadb_tenant
        self._database = settings.chromadb_database
        self.collection_name = settings.chromadb_collection
        self._timeout = settings.chromadb_timeout_seconds
        self._collection_id: str | None = None
        self._in_memory_fallback: list[dict[str, Any]] = []

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

    async def get_collection_id(self) -> str:
        if self._collection_id:
            return self._collection_id
        path = f"/api/v2/tenants/{self._tenant}/databases/{self._database}/collections/{self.collection_name}"
        try:
            res = await asyncio.to_thread(self._request, "GET", path)
            if isinstance(res, dict) and "id" in res:
                self._collection_id = str(res["id"])
                return self._collection_id
        except Exception:
            pass

        await self.ensure_collection()
        path = f"/api/v2/tenants/{self._tenant}/databases/{self._database}/collections"
        try:
            res = await asyncio.to_thread(self._request, "GET", path)
            if isinstance(res, list):
                for col in res:
                    if isinstance(col, dict) and col.get("name") == self.collection_name:
                        self._collection_id = str(col["id"])
                        return self._collection_id
        except Exception:
            pass

        self._collection_id = f"local-{self.collection_name}"
        return self._collection_id

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
            res = await asyncio.to_thread(self._request, "POST", path, payload)
            if isinstance(res, dict) and "id" in res:
                self._collection_id = str(res["id"])
            logger.info(
                "chroma_collection_initialized",
                extra={"collection": self.collection_name},
            )
        except Exception:
            logger.warning(
                "chroma_collection_initialization_fallback",
                extra={"collection": self.collection_name},
            )

    async def add_chunks(
        self, chunks: list[DocumentChunk], embeddings: list[list[float]]
    ) -> None:
        if not chunks:
            return
        collection_id = await self.get_collection_id()
        payload = {
            "ids": [c.chunk_id for c in chunks],
            "embeddings": embeddings,
            "documents": [c.text for c in chunks],
            "metadatas": [c.metadata for c in chunks],
        }
        path = f"/api/v2/tenants/{self._tenant}/databases/{self._database}/collections/{collection_id}/upsert"
        try:
            await asyncio.to_thread(self._request, "POST", path, payload)
            logger.info("chroma_chunks_added", extra={"count": len(chunks)})
        except Exception as error:
            logger.warning(
                "chroma_add_failed_using_in_memory_fallback",
                extra={"error": str(error), "chunk_count": len(chunks)},
            )
            logger.error(
                "CHROMADB_INSERT_FAILED: %d chunks not persisted to ChromaDB — "
                "RAG retrieval will NOT work. Check ChromaDB service. Error: %s",
                len(chunks),
                error,
            )
            for c, emb in zip(chunks, embeddings):
                self._in_memory_fallback.append(
                    {
                        "id": c.chunk_id,
                        "document": c.text,
                        "embedding": emb,
                        "metadata": c.metadata,
                    }
                )

    async def delete_document_chunks(self, user_id: str, document_id: str) -> None:
        collection_id = await self.get_collection_id()
        where_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document_id}},
            ]
        }
        payload = {"where": where_filter}
        path = f"/api/v2/tenants/{self._tenant}/databases/{self._database}/collections/{collection_id}/delete"
        try:
            await asyncio.to_thread(self._request, "POST", path, payload)
            logger.info(
                "chroma_chunks_deleted",
                extra={"user_id": user_id, "document_id": document_id},
            )
        except Exception:
            pass

        self._in_memory_fallback = [
            item
            for item in self._in_memory_fallback
            if not (
                item["metadata"].get("user_id") == user_id
                and item["metadata"].get("document_id") == document_id
            )
        ]

    async def query_rag(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        collection_id = await self.get_collection_id()
        where_conditions: list[dict[str, Any]] = [{"user_id": {"$eq": user_id}}]
        if filters:
            if filters.get("document_type"):
                where_conditions.append({"document_type": {"$eq": filters["document_type"]}})
            if filters.get("language"):
                where_conditions.append({"language": {"$eq": filters["language"]}})

        where_filter = (
            where_conditions[0]
            if len(where_conditions) == 1
            else {"$and": where_conditions}
        )
        payload = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "where": where_filter,
            "include": ["documents", "metadatas", "distances"],
        }
        path = f"/api/v2/tenants/{self._tenant}/databases/{self._database}/collections/{collection_id}/query"
        try:
            res = await asyncio.to_thread(self._request, "POST", path, payload)
            if (
                isinstance(res, dict)
                and "ids" in res
                and res["ids"]
                and res["ids"][0]
            ):
                ids = res["ids"][0]
                documents = res.get("documents", [[]])[0]
                metadatas = res.get("metadatas", [[]])[0]
                distances = res.get("distances", [[]])[0]

                results = []
                for i in range(len(ids)):
                    dist = distances[i] if i < len(distances) else 0.0
                    similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                    results.append(
                        {
                            "chunk_id": ids[i],
                            "text": documents[i] if i < len(documents) else "",
                            "similarity": round(similarity, 4),
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                        }
                    )
                return results
        except Exception as error:
            logger.warning(
                "chroma_query_failed_using_in_memory_fallback", extra={"error": str(error)}
            )

        return self._query_in_memory_fallback(
            user_id, query_embedding, top_k, filters
        )

    def _query_in_memory_fallback(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        candidates = []
        for item in self._in_memory_fallback:
            meta = item["metadata"]
            if meta.get("user_id") != user_id:
                continue
            if filters:
                if (
                    filters.get("document_type")
                    and meta.get("document_type") != filters["document_type"]
                ):
                    continue
                if (
                    filters.get("language")
                    and meta.get("language") != filters["language"]
                ):
                    continue

            emb = item["embedding"]
            similarity = self._cosine_similarity(query_embedding, emb)
            candidates.append(
                {
                    "chunk_id": item["id"],
                    "text": item["document"],
                    "similarity": round(similarity, 4),
                    "metadata": {
                        "document_id": meta.get("document_id"),
                        "page_number": meta.get("page_number", 1),
                        "language": meta.get("language", "en"),
                    },
                }
            )

        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:top_k]

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.5
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 <= 0 or norm2 <= 0:
            return 0.0
        sim = dot / (norm1 * norm2)
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))
