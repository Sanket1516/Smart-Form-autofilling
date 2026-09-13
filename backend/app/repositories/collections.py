"""Repositories for every MongoDB collection in DATABASE_DESIGN section 4.1."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.documents import (
    Correction,
    DocumentRecord,
    Feedback,
    FormSession,
    ProcessingRecord,
    ProfileDocument,
    Recommendation,
    StructuredFact,
)
from app.repositories.base import UserScopedRepository, UsersRepository


class UsersCollectionRepository(UsersRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["users"])


class ProfilesRepository(UserScopedRepository[ProfileDocument]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["profiles"], ProfileDocument)

    async def get_for_user(self, user_id: str) -> dict | None:
        return await self.collection.find_one(self._owner_filter(user_id))


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

    async def list_filtered(
        self,
        user_id: str,
        concept: str | None = None,
        source_document_id: str | None = None,
        confirmed: bool | None = None,
    ) -> list[dict]:
        filters = {
            key: value
            for key, value in {
                "concept": concept,
                "source_document_id": source_document_id,
                "is_user_confirmed": confirmed,
            }.items()
            if value is not None
        }
        return await self.list(user_id, filters)

    async def list_for_document(self, user_id: str, document_id: str) -> list[dict]:
        return await self.list(user_id, {"source_document_id": document_id})

    async def upsert_fact(self, user_id: str, fact: StructuredFact) -> dict:
        SINGLETON_PREFIXES = (
            "personal.",
            "identity.",
            "contact.",
            "demographics.",
            "address.",
            "passport.",
            "visa.",
        )
        c = fact.concept or ""
        v = str(fact.value or "").strip().lower()

        if any(c.startswith(prefix) for prefix in SINGLETON_PREFIXES):
            filter_doc = self._owner_filter(user_id, {"concept": fact.concept})
        else:
            filter_doc = self._owner_filter(user_id, {"concept": fact.concept, "value": fact.value})

        existing = await self.collection.find_one(filter_doc)
        if existing:
            update_data = {
                "confidence": max(existing.get("confidence", 0.0), fact.confidence),
                "source_document_id": fact.source_document_id,
                "source_page": fact.source_page,
                "provenance": fact.provenance,
                "updated_at": fact.updated_at,
            }
            if fact.value is not None:
                update_data["value"] = fact.value
            if fact.is_user_confirmed:
                update_data["is_user_confirmed"] = True
            await self.collection.update_one({"_id": existing["_id"]}, {"$set": update_data})
            existing.update(update_data)
            return existing
        else:
            return await self.create(user_id, fact)


class RecommendationsRepository(UserScopedRepository[Recommendation]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["recommendations"], Recommendation)


class CorrectionsRepository(UserScopedRepository[Correction]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["corrections"], Correction)


class FeedbackRepository(UserScopedRepository[Feedback]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["feedback"], Feedback)


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
        from datetime import UTC, datetime

        await self.create(
            user_id,
            ProcessingRecord(
                user_id=user_id,
                document_id=document_id,
                stage=stage,
                status=status,
                started_at=datetime.now(UTC),
                completed_at=(
                    datetime.now(UTC) if status in {"completed", "failed", "skipped"} else None
                ),
                retry_count=0,
                error=error,
            ),
        )


class FormSessionsRepository(UserScopedRepository[FormSession]):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        super().__init__(database["form_sessions"], FormSession)
