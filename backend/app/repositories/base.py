"""User-scoped MongoDB repository primitives."""

from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel

DocumentT = TypeVar("DocumentT", bound=BaseModel)


def _mongo_id(value: str) -> ObjectId | str:
    return ObjectId(value) if ObjectId.is_valid(value) else value


class UserScopedRepository(Generic[DocumentT]):
    """CRUD operations whose every query is constrained by user_id."""

    def __init__(self, collection: AsyncIOMotorCollection, model: type[DocumentT]) -> None:
        self.collection = collection
        self.model = model

    def _owner_filter(self, user_id: str, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not user_id.strip():
            raise ValueError("user_id is required")
        query = dict(extra) if extra else {}
        query["user_id"] = user_id
        return query

    async def create(self, user_id: str, document: DocumentT) -> dict[str, Any]:
        if document.user_id != user_id:
            raise ValueError("document user_id must match the requested user_id")
        payload = document.model_dump(exclude_none=True)
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return payload

    async def get(self, user_id: str, document_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            self._owner_filter(user_id, {"_id": _mongo_id(document_id)})
        )

    async def list(
        self, user_id: str, filters: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        cursor = self.collection.find(self._owner_filter(user_id, filters))
        return await cursor.to_list(length=None)

    async def update(self, user_id: str, document_id: str, updates: Mapping[str, Any]) -> bool:
        if "user_id" in updates:
            raise ValueError("user_id cannot be changed")
        result = await self.collection.update_one(
            self._owner_filter(user_id, {"_id": _mongo_id(document_id)}),
            {"$set": dict(updates)},
        )
        return result.modified_count == 1

    async def delete(self, user_id: str, document_id: str) -> bool:
        result = await self.collection.delete_one(
            self._owner_filter(user_id, {"_id": _mongo_id(document_id)})
        )
        return result.deleted_count == 1


class UsersRepository:
    """Repository for account records, identified independently of an owner."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def create(self, document: DocumentT) -> dict[str, Any]:
        payload = document.model_dump(exclude_none=True)
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return payload

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"email": email})

    async def get(self, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": _mongo_id(user_id)})
