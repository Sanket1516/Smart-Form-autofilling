"""Async HTTP client for the ChromaDB v2 API.

Every query is filtered by ``user_id``. Failures raise ``VectorStoreError``;
there is no in-memory fallback, so an outage is visible instead of silently
producing empty or process-local results.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.processing.chunking import DocumentChunk

logger = logging.getLogger(__name__)


class VectorStoreError(RuntimeError):
    """ChromaDB is unreachable, misconfigured or rejected a request."""


class ChromaClient:
    def __init__(self, settings: Settings, embedding_model: str | None = None) -> None:
        self._base_url = settings.chromadb_url.rstrip("/")
        self._prefix = (
            f"/api/v2/tenants/{settings.chromadb_tenant}/databases/{settings.chromadb_database}"
        )
        self.collection_name = settings.chromadb_collection
        self._timeout = settings.chromadb_timeout_seconds
        self._embedding_model = embedding_model or settings.embedding_model_name
        self._embedding_dimension = settings.embedding_dimension
        self._collection_id: str | None = None

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, f"{self._base_url}{path}", json=payload)
        except httpx.HTTPError as error:
            raise VectorStoreError(f"ChromaDB is unreachable at {self._base_url}") from error
        if response.status_code >= 400:
            raise VectorStoreError(
                f"ChromaDB returned HTTP {response.status_code} for {method} {path.split('/')[-1]}"
            )
        return response.json() if response.content else None

    async def is_healthy(self) -> bool:
        try:
            await self._request("GET", "/api/v2/heartbeat")
        except VectorStoreError:
            return False
        return True

    async def ensure_collection(self) -> str:
        """Create or open the collection and verify it matches the embedding model."""
        if self._collection_id:
            return self._collection_id
        payload = {
            "name": self.collection_name,
            "metadata": {
                "hnsw:space": "cosine",
                "embedding_model": self._embedding_model,
                "embedding_dimension": self._embedding_dimension,
            },
            "get_or_create": True,
        }
        collection = await self._request("POST", f"{self._prefix}/collections", payload)
        if not isinstance(collection, dict) or "id" not in collection:
            raise VectorStoreError("ChromaDB did not return a collection id")
        stored_model = (collection.get("metadata") or {}).get("embedding_model")
        if stored_model and stored_model != self._embedding_model:
            raise VectorStoreError(
                f"Collection '{self.collection_name}' was built with embedding model "
                f"'{stored_model}', but EMBEDDING_MODEL_NAME is '{self._embedding_model}'. "
                "Use a new CHROMADB_COLLECTION and run the reindex command."
            )
        stored_dimension = (collection.get("metadata") or {}).get("embedding_dimension")
        if stored_dimension is not None:
            try:
                dimension_matches = int(stored_dimension) == self._embedding_dimension
            except (TypeError, ValueError):
                dimension_matches = False
            if not dimension_matches:
                raise VectorStoreError(
                    f"Collection '{self.collection_name}' has embedding dimension "
                    f"'{stored_dimension}', but EMBEDDING_DIMENSION is "
                    f"'{self._embedding_dimension}'. Use a new CHROMADB_COLLECTION and run "
                    "the reindex command."
                )
        self._collection_id = str(collection["id"])
        logger.info("chroma_collection_ready", extra={"collection": self.collection_name})
        return self._collection_id

    async def upsert_chunks(
        self, chunks: list[DocumentChunk], embeddings: list[list[float]]
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        collection_id = await self.ensure_collection()
        await self._request(
            "POST",
            f"{self._prefix}/collections/{collection_id}/upsert",
            {
                "ids": [chunk.chunk_id for chunk in chunks],
                "embeddings": embeddings,
                "documents": [chunk.text for chunk in chunks],
                "metadatas": [chunk.metadata for chunk in chunks],
            },
        )

    async def delete_document_chunks(self, user_id: str, document_id: str) -> None:
        collection_id = await self.ensure_collection()
        await self._request(
            "POST",
            f"{self._prefix}/collections/{collection_id}/delete",
            {
                "where": {
                    "$and": [{"user_id": {"$eq": user_id}}, {"document_id": {"$eq": document_id}}]
                }
            },
        )

    async def delete_user_chunks(self, user_id: str) -> None:
        collection_id = await self.ensure_collection()
        await self._request(
            "POST",
            f"{self._prefix}/collections/{collection_id}/delete",
            {"where": {"user_id": {"$eq": user_id}}},
        )

    async def query(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        document_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return chunks for this user only, best first, with cosine similarity in [0, 1]."""
        collection_id = await self.ensure_collection()
        conditions: list[dict[str, Any]] = [{"user_id": {"$eq": user_id}}]
        if document_type:
            conditions.append({"document_type": {"$eq": document_type}})
        where = conditions[0] if len(conditions) == 1 else {"$and": conditions}
        result = await self._request(
            "POST",
            f"{self._prefix}/collections/{collection_id}/query",
            {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "where": where,
                "include": ["documents", "metadatas", "distances"],
            },
        )
        if not isinstance(result, dict) or not result.get("ids") or not result["ids"][0]:
            return []
        ids = result["ids"][0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        chunks = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] or {}
            if metadata.get("user_id") != user_id:  # defence in depth
                continue
            distance = float(distances[index]) if index < len(distances) else 1.0
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": documents[index] or "",
                    "similarity": round(max(0.0, min(1.0, 1.0 - distance)), 4),
                    "metadata": metadata,
                }
            )
        return chunks
