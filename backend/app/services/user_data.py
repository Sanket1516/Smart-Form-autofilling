"""Deletes everything a user owns (``DELETE /profile/data`` and ``DELETE /auth/me``)."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from app.core.api_errors import APIError
from app.db.chroma_client import ChromaClient, VectorStoreError
from app.storage.base import DocumentStorage

logger = logging.getLogger(__name__)

# Every collection holding user-owned records, including ones only written by
# earlier versions (profiles, discovered_conflicts, feedback).
USER_COLLECTIONS = (
    "structured_facts",
    "discovered_facts",
    "discovered_conflicts",
    "profiles",
    "recommendations",
    "form_sessions",
    "corrections",
    "feedback",
    "processing_records",
    "user_memories",
    "agent_runs",
)


class UserDataService:
    def __init__(self, database: Any, storage: DocumentStorage, vector_store: ChromaClient) -> None:
        self.database = database
        self.storage = storage
        self.vector_store = vector_store

    async def delete_all(self, user_id: str, *, delete_account: bool = False) -> dict[str, int]:
        try:
            await self.vector_store.delete_user_chunks(user_id)
        except VectorStoreError as error:
            raise APIError(
                "VECTOR_STORE_UNAVAILABLE",
                "The document index is unavailable, so nothing was deleted. Try again later.",
                503,
            ) from error
        deleted: dict[str, int] = {}
        documents = self.database["documents"]
        async for record in documents.find({"user_id": user_id}):
            for key in ("normalized_reference", "storage_reference"):
                reference = record.get(key)
                if reference:
                    try:
                        await self.storage.delete(reference)
                    except Exception:
                        logger.warning("storage_delete_failed_during_user_purge")
        deleted["documents"] = (await documents.delete_many({"user_id": user_id})).deleted_count
        for name in USER_COLLECTIONS:
            deleted[name] = (
                await self.database[name].delete_many({"user_id": user_id})
            ).deleted_count
        if delete_account:
            target = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            deleted["users"] = (
                await self.database["users"].delete_one({"_id": target})
            ).deleted_count
        logger.info(
            "user_data_deleted", extra={"collections": {k: v for k, v in deleted.items() if v}}
        )
        return deleted
