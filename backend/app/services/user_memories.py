"""Free-form answers the user explicitly approved for reuse ("save for future forms").

Answers to recognised ontology concepts are stored as user-provided structured
facts instead (see ``FactService.add_user_fact``). Memories cover everything
else, e.g. "Why do you want to join?", and are embedded for RAG so similar
future questions can reuse them.
"""

from __future__ import annotations

import logging
import re
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

    @staticmethod
    def label_key(label: str) -> str:
        """Comparable form of a field label: case, punctuation and "*" markers ignored."""
        return re.sub(r"[\W_]+", " ", (label or "").casefold()).strip()

    async def answers_by_label(self, user_id: str) -> dict[str, dict[str, Any]]:
        """The user's saved answers keyed by normalised field label (newest wins)."""
        answers: dict[str, dict[str, Any]] = {}
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1)
        async for item in cursor:
            key = self.label_key(item.get("label", ""))
            if key and item.get("value") and key not in answers:
                answers[key] = self._serialize(item)
        return answers

    async def save(self, user_id: str, label: str, concept: str, value: str) -> dict[str, Any]:
        """Save an answer; saving the same question again replaces the earlier answer."""
        now = datetime.now(UTC)
        key = self.label_key(label)
        existing = None
        if key:
            async for item in self.collection.find({"user_id": user_id}).sort("updated_at", -1):
                if self.label_key(item.get("label", "")) == key:
                    existing = item
                    break
        memory_id = str(existing["_id"]) if existing else uuid4().hex
        record = {
            "_id": memory_id,
            "user_id": user_id,
            "label": label[:200],
            "concept": concept[:160],
            "value": str(value)[:10000],
            "indexed": False,
            "created_at": existing.get("created_at", now) if existing else now,
            "updated_at": now,
        }
        if existing:
            await self.collection.replace_one({"_id": memory_id, "user_id": user_id}, record)
        else:
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
