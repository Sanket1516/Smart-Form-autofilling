"""Repository for Form Sessions (DATABASE_DESIGN §14)."""

from datetime import UTC, datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.api_errors import APIError


class FormSessionsRepository:
    """Manages form session persistence."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.form_sessions

    async def create_session(
        self, user_id: str, website_origin: str, page_url: str, form_id: str
    ) -> dict[str, Any]:
        """Creates a new form session."""
        now = datetime.now(UTC)
        doc = {
            "user_id": user_id,
            "website_origin": website_origin,
            "page_url": page_url,
            "form_id": form_id,
            "started_at": now,
            "status": "started",
            "total_fields": 0,
            "filled_fields": 0,
            "reviewed_fields": 0,
            "failed_fields": 0
        }
        
        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def get_session(self, user_id: str, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a form session by user and session id."""
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            doc = await self.collection.find_one({"_id": ObjectId(session_id), "user_id": user_id})
        except InvalidId:
            return None
            
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def update_session(self, user_id: str, session_id: str, updates: dict[str, Any]) -> bool:
        """Updates fields on a form session."""
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id), "user_id": user_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    async def complete_session(
        self, 
        user_id: str, 
        session_id: str, 
        total_fields: int, 
        filled_fields: int, 
        reviewed_fields: int, 
        failed_fields: int, 
        submission_status: str
    ) -> bool:
        """Marks a session as completed or failed with final stats."""
        from bson import ObjectId
        from bson.errors import InvalidId
        
        status = "completed" if submission_status == "user_submitted" else "cancelled"
        
        updates = {
            "total_fields": total_fields,
            "filled_fields": filled_fields,
            "reviewed_fields": reviewed_fields,
            "failed_fields": failed_fields,
            "submission_status": submission_status,
            "status": status,
            "completed_at": datetime.now(UTC)
        }
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id), "user_id": user_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except InvalidId:
            return False
