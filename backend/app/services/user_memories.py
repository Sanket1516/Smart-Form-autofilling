"""Free-form answers the user explicitly approved for reuse ("save for future forms").

Answers to recognised ontology concepts are stored as user-provided structured
facts instead (see ``FactService.add_user_fact``). Memories cover everything
else, e.g. "Why do you want to join?", and are embedded for RAG so similar
future questions can reuse them.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db.chroma_client import ChromaClient, VectorStoreError
from app.processing.chunking import DocumentChunk
from app.retrieval.embeddings import EmbeddingProvider, EmbeddingUnavailableError

logger = logging.getLogger(__name__)


class UserMemoryService:
    def __init__(self, database: Any, chroma: ChromaClient, embeddings: EmbeddingProvider) -> None:
        self.collection = database["user_memories"]
        self.chroma = chroma
        self.embeddings = embeddings

    async def save(self, user_id: str, label: str, concept: str, value: str) -> dict[str, Any]:
        memory_id = uuid4().hex
        now = datetime.now(UTC)
        record = {
            "_id": memory_id,
            "user_id": user_id,
            "label": label[:200],
            "concept": concept[:160],
            "value": str(value)[:10000],
            "indexed": False,
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.insert_one(record)
        text = f"Question: {record['label']}\nUser's saved answer: {record['value']}"
        try:
            vectors = await self.embeddings.embed_texts([text])
            await self.chroma.upsert_chunks(
                [
                    DocumentChunk(
                        chunk_id=f"user_memory_{memory_id}",
                        text=text,
                        metadata={
                            "user_id": user_id,
                            "document_id": memory_id,
                            "document_name": "Saved answer",
                            "document_type": "profile_memory",
                            "source_type": "user_memory",
                            "page_number": 1,
                            "language": "en",
                            "chunk_index": 0,
                        },
                    )
                ],
                vectors,
            )
            await self.collection.update_one({"_id": memory_id}, {"$set": {"indexed": True}})
            record["indexed"] = True
        except (EmbeddingUnavailableError, VectorStoreError) as error:
            logger.warning("memory_indexing_failed", extra={"error": str(error)})
        return self._serialize(record)

    async def list(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1)
        return [self._serialize(item) async for item in cursor]

    async def delete(self, user_id: str, memory_id: str) -> bool:
        result = await self.collection.delete_one({"_id": memory_id, "user_id": user_id})
        if result.deleted_count:
            try:
                await self.chroma.delete_document_chunks(user_id, memory_id)
            except VectorStoreError as error:
                logger.warning("memory_vector_delete_failed", extra={"error": str(error)})
        return bool(result.deleted_count)

    @staticmethod
    def _serialize(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "memory_id": str(record["_id"]),
            "label": record.get("label", ""),
            "concept": record.get("concept", ""),
            "value": record.get("value", ""),
            "indexed": bool(record.get("indexed", False)),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }
