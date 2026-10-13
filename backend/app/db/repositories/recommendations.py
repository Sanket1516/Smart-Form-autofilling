"""Repository for field recommendations (one per user, session and field)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

# Statuses that may be filled into the page.
FILLABLE_STATUSES = ("ready", "approved", "edited")
REVIEW_STATUSES = ("needs_review",)
# Values written by earlier versions, normalised on read.
_LEGACY_STATUS = {
    "READY_TO_FILL": "ready",
    "pending_review": "needs_review",
    "PENDING_REVIEW": "needs_review",
    "MISSING_INFORMATION": "missing_information",
}


def normalize_status(status: str | None) -> str:
    return _LEGACY_STATUS.get(status or "", status or "missing_information")


class RecommendationsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db["recommendations"]

    async def upsert(
        self, user_id: str, session_id: str, field_id: str, data: dict[str, Any]
    ) -> str:
        """Create or replace the recommendation for one field, keeping its id stable."""
        now = datetime.now(UTC)
        query = {"user_id": user_id, "session_id": session_id, "field_id": field_id}
        existing = await self.collection.find_one(query, {"_id": 1})
        rec_id = existing["_id"] if existing else f"rec_{uuid.uuid4().hex[:16]}"
        document = {**data, **query, "_id": rec_id, "updated_at": now}
        document.setdefault("created_at", now)
        await self.collection.replace_one(
            {"_id": rec_id, "user_id": user_id}, document, upsert=True
        )
        return rec_id

    async def list_for_session(self, user_id: str, session_id: str) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id, "session_id": session_id}).sort(
            "order", 1
        )
        return [_normalized(doc) async for doc in cursor]

    async def get_for_field(
        self, user_id: str, session_id: str, field_id: str
    ) -> dict[str, Any] | None:
        doc = await self.collection.find_one(
            {"user_id": user_id, "session_id": session_id, "field_id": field_id}
        )
        return _normalized(doc) if doc else None

    async def get_recommendation(self, user_id: str, rec_id: str) -> dict[str, Any] | None:
        doc = await self.collection.find_one({"_id": rec_id, "user_id": user_id})
        return _normalized(doc) if doc else None

    async def get_pending_reviews(
        self, user_id: str, session_id: str | None = None
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {
            "user_id": user_id,
            "status": {"$in": [*REVIEW_STATUSES, "pending_review"]},
        }
        if session_id:
            query["session_id"] = session_id
        cursor = self.collection.find(query).sort("updated_at", -1)
        return [_normalized(doc) async for doc in cursor]

    async def update_fields(self, user_id: str, rec_id: str, updates: dict[str, Any]) -> bool:
        result = await self.collection.update_one(
            {"_id": rec_id, "user_id": user_id},
            {"$set": {**updates, "updated_at": datetime.now(UTC)}},
        )
        return result.matched_count == 1

    async def count_by_status(self, user_id: str, session_id: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        async for doc in self.collection.find(
            {"user_id": user_id, "session_id": session_id}, {"status": 1, "required": 1}
        ):
            status = normalize_status(doc.get("status"))
            counts[status] = counts.get(status, 0) + 1
            if status == "missing_information" and doc.get("required"):
                counts["missing_required"] = counts.get("missing_required", 0) + 1
        return counts

    async def delete_for_document(self, user_id: str, document_id: str) -> int:
        result = await self.collection.delete_many(
            {"user_id": user_id, "source.document_id": document_id}
        )
        return result.deleted_count


def _normalized(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    doc["status"] = normalize_status(doc.get("status"))
    return doc
