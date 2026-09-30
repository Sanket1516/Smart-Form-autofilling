"""Persistence for information the user explicitly approved for future retrieval."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db.chroma_client import ChromaClient
from app.processing.chunking import DocumentChunk
from app.retrieval.embeddings import EmbeddingProvider


class UserMemoryService:
    def __init__(self, database: Any, chroma: ChromaClient, embeddings: EmbeddingProvider) -> None:
        self.collection = database["user_memories"]
        self.chroma = chroma
        self.embeddings = embeddings

    async def save(self, user_id: str, label: str, concept: str, value: str) -> dict[str, Any]:
        # A newly approved structured value supersedes the previous one. Keep
        # narrative memories additive so past roles and experiences remain searchable.
        if concept.startswith(("personal.", "contact.", "address.")):
            cursor = self.collection.find({"user_id": user_id, "concept": concept}, {"_id": 1})
            old_ids = [str(item["_id"]) async for item in cursor]
            for old_id in old_ids:
                await self.chroma.delete_document_chunks(user_id, old_id)
                await self.collection.delete_one({"_id": old_id, "user_id": user_id})

        memory_id = uuid4().hex
        now = datetime.now(UTC)
        value_text = str(value)
        text = (
            f"User profile information. {concept}. Form question: {label}. "
            f"User-provided answer: {value_text}"
        )
        record = {
            "_id": memory_id,
            "user_id": user_id,
            "label": label[:200],
            "concept": concept[:160],
            "value": value_text,
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.insert_one(record)
        chunk = DocumentChunk(
            chunk_id=f"user_memory_{memory_id}",
            text=text,
            metadata={
                "user_id": user_id,
                "document_id": memory_id,
                "document_name": "User-approved profile information",
                "document_type": "profile_memory",
                "source_type": "user_memory",
                "page_number": 1,
                "language": "en",
                "chunk_index": 0,
            },
        )
        await self.chroma.add_chunks([chunk], self.embeddings.embed_texts([text]))
        return self._serialize(record)

    async def list(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1)
        return [self._serialize(item) async for item in cursor]

    async def delete(self, user_id: str, memory_id: str) -> bool:
        result = await self.collection.delete_one({"_id": memory_id, "user_id": user_id})
        if result.deleted_count:
            await self.chroma.delete_document_chunks(user_id, memory_id)
        return bool(result.deleted_count)

    async def delete_all(self, user_id: str) -> None:
        cursor = self.collection.find({"user_id": user_id}, {"_id": 1})
        async for item in cursor:
            await self.chroma.delete_document_chunks(user_id, str(item["_id"]))
        await self.collection.delete_many({"user_id": user_id})

    @staticmethod
    def _serialize(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "memory_id": str(record["_id"]),
            "label": record.get("label", ""),
            "concept": record.get("concept", ""),
            "value": record.get("value", ""),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }
