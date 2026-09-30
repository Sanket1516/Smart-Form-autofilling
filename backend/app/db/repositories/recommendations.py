"""Repository for the recommendations collection (DATABASE_DESIGN §10)."""

from typing import Any
from datetime import datetime, timezone
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel


class RecommendationsRepository:
    """Handles CRUD for the recommendations collection."""
    
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db["recommendations"]

    async def create_recommendation(
        self,
        user_id: str,
        session_id: str,
        field_id: str,
        field_label: str,
        concept: str,
        recommended_value: str,
        confidence: float,
        retrieval_type: str,
        source_fact_ids: list[str],
        status: str,
        decision_reason: str = "",
        required: bool = False,
        input_type: str = "text",
    ) -> str:
        """Creates a new recommendation document."""
        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": rec_id,
            "user_id": user_id,
            "session_id": session_id,
            "field_id": field_id,
            "field_label": field_label,
            "required": required,
            "input_type": input_type,
            "concept": concept,
            "recommended_value": recommended_value,
            "confidence": confidence,
            "retrieval_type": retrieval_type,
            "source_fact_ids": source_fact_ids,
            "status": status,
            "reason": decision_reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.collection.insert_one(doc)
        return rec_id

    async def get_pending_reviews(self, user_id: str) -> list[dict[str, Any]]:
        """Gets all recommendations in pending_review status for a user."""
        cursor = self.collection.find({"user_id": user_id, "status": "pending_review"})
        results = []
        async for doc in cursor:
            results.append(doc)
        return results

    async def get_recommendation(self, user_id: str, rec_id: str) -> dict[str, Any] | None:
        """Gets a single recommendation by ID, enforcing user_id scope."""
        return await self.collection.find_one({"_id": rec_id, "user_id": user_id})

    async def update_status(self, user_id: str, rec_id: str, status: str, value: str | None = None) -> bool:
        """Updates the status (and optionally value) of a recommendation."""
        update_doc: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if value is not None:
            update_doc["recommended_value"] = value
            
        result = await self.collection.update_one(
            {"_id": rec_id, "user_id": user_id},
            {"$set": update_doc}
        )
        return result.modified_count > 0
