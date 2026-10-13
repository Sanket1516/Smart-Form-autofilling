"""Repository for form-filling sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def _oid(session_id: str) -> ObjectId | None:
    return ObjectId(session_id) if ObjectId.is_valid(session_id) else None


class FormSessionsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db["form_sessions"]

    async def create_session(
        self, user_id: str, website_origin: str, page_url: str, form_id: str
    ) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "user_id": user_id,
            "website_origin": website_origin,
            "page_url": page_url,
            "form_id": form_id,
            "started_at": datetime.now(UTC),
            "status": "started",
            "total_fields": 0,
            "filled_fields": 0,
            "reviewed_fields": 0,
            "failed_fields": 0,
            "fill_results": [],
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def get_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        oid = _oid(session_id)
        if oid is None:
            return None
        doc = await self.collection.find_one({"_id": oid, "user_id": user_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def list_sessions(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}).sort("started_at", -1).limit(limit)
        sessions = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            sessions.append(doc)
        return sessions

    async def update_session(self, user_id: str, session_id: str, updates: dict[str, Any]) -> bool:
        oid = _oid(session_id)
        if oid is None:
            return False
        result = await self.collection.update_one(
            {"_id": oid, "user_id": user_id}, {"$set": updates}
        )
        return result.matched_count == 1

    async def record_fill_results(
        self, user_id: str, session_id: str, results: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Store the extension's per-field fill outcome and update the counters."""
        filled = sum(1 for r in results if r.get("applied") and r.get("verified"))
        failed = sum(1 for r in results if not (r.get("applied") and r.get("verified")))
        await self.update_session(
            user_id,
            session_id,
            {
                "fill_results": results,
                "filled_fields": filled,
                "failed_fields": failed,
                "status": "filled",
                "filled_at": datetime.now(UTC),
            },
        )
        return {"filled_fields": filled, "failed_fields": failed}

    async def complete_session(
        self, user_id: str, session_id: str, submission_status: str, counts: dict[str, int]
    ) -> bool:
        status = "completed" if submission_status == "user_submitted" else "closed"
        return await self.update_session(
            user_id,
            session_id,
            {
                **counts,
                "submission_status": submission_status,
                "status": status,
                "completed_at": datetime.now(UTC),
            },
        )
