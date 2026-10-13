"""User-scoped repositories for the MongoDB collections."""

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.documents import (
    Correction,
    DiscoveredFact,
    DocumentRecord,
    ProcessingRecord,
    StructuredFact,
)
from app.repositories.base import UserScopedRepository, UsersRepository


class UsersCollectionRepository(UsersRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["users"])


class DocumentsRepository(UserScopedRepository[DocumentRecord]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["documents"], DocumentRecord)

    async def find_by_checksum(self, user_id: str, checksum: str) -> dict | None:
        return await self.collection.find_one(self._owner_filter(user_id, {"checksum": checksum}))

    async def count(self, user_id: str, filters: dict | None = None) -> int:
        return await self.collection.count_documents(self._owner_filter(user_id, filters))

    async def list_page(
        self, user_id: str, filters: dict | None, skip: int, limit: int
    ) -> list[dict]:
        cursor = self.collection.find(self._owner_filter(user_id, filters))
        cursor = cursor.sort("uploaded_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)


class StructuredFactsRepository(UserScopedRepository[StructuredFact]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["structured_facts"], StructuredFact)

    async def list_active(self, user_id: str, concept: str | None = None) -> list[dict]:
        filters: dict[str, Any] = {"status": {"$nin": ["rejected", "superseded"]}}
        if concept:
            filters["concept"] = concept
        cursor = self.collection.find(self._owner_filter(user_id, filters)).sort("created_at", 1)
        return await cursor.to_list(length=None)

    async def list_for_document(self, user_id: str, document_id: str) -> list[dict]:
        return await self.list(user_id, {"source_document_id": document_id})

    async def insert_many(self, user_id: str, facts: list[StructuredFact]) -> int:
        payload = []
        for fact in facts:
            if fact.user_id != user_id:
                raise ValueError("fact user_id must match the requested user_id")
            payload.append(fact.model_dump())
        if payload:
            await self.collection.insert_many(payload)
        return len(payload)

    async def delete_for_document(self, user_id: str, document_id: str) -> int:
        result = await self.collection.delete_many(
            self._owner_filter(user_id, {"source_document_id": document_id})
        )
        return result.deleted_count

    async def set_status(self, user_id: str, fact_ids: list[Any], status: str) -> None:
        if fact_ids:
            await self.collection.update_many(
                self._owner_filter(user_id, {"_id": {"$in": fact_ids}}),
                {"$set": {"status": status, "updated_at": datetime.now(UTC)}},
            )


class DiscoveredFactsRepository(UserScopedRepository[DiscoveredFact]):
    """Everything extracted from each document, including unmapped attributes."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["discovered_facts"], DiscoveredFact)

    async def list_filtered(
        self,
        user_id: str,
        document_id: str | None = None,
        semantic_type: str | None = None,
        ontology: str | None = None,
    ) -> list[dict]:
        filters = {
            key: value
            for key, value in {
                "source_document_id": document_id,
                "semantic_type": semantic_type,
                "ontology": ontology,
            }.items()
            if value
        }
        cursor = self.collection.find(self._owner_filter(user_id, filters)).sort("created_at", 1)
        return await cursor.to_list(length=None)

    async def insert_many(self, user_id: str, facts: list[DiscoveredFact]) -> int:
        payload = []
        for fact in facts:
            if fact.user_id != user_id:
                raise ValueError("fact user_id must match the requested user_id")
            payload.append(fact.model_dump())
        if payload:
            await self.collection.insert_many(payload)
        return len(payload)

    async def delete_for_document(self, user_id: str, document_id: str) -> int:
        result = await self.collection.delete_many(
            self._owner_filter(user_id, {"source_document_id": document_id})
        )
        return result.deleted_count


class CorrectionsRepository(UserScopedRepository[Correction]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["corrections"], Correction)


class ProcessingRecordsRepository(UserScopedRepository[ProcessingRecord]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["processing_records"], ProcessingRecord)

    async def record_stage(
        self,
        user_id: str,
        document_id: str,
        stage: str,
        status: str,
        error: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        await self.create(
            user_id,
            ProcessingRecord(
                user_id=user_id,
                document_id=document_id,
                stage=stage,
                status=status,
                started_at=now,
                completed_at=now if status in {"completed", "failed", "skipped"} else None,
                retry_count=0,
                error=error,
            ),
        )

    async def delete_for_document(self, user_id: str, document_id: str) -> int:
        result = await self.collection.delete_many(
            self._owner_filter(user_id, {"document_id": document_id})
        )
        return result.deleted_count
