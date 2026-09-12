"""Persistent JWT revocation records with automatic expiry."""

from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoRevocationStore:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database["auth_token_revocations"]

    async def ensure_index(self) -> None:
        await self._collection.create_index("jti", unique=True, name="auth_revocations_jti_unique")
        await self._collection.create_index(
            "expires_at", expireAfterSeconds=0, name="auth_revocations_expiry"
        )

    async def revoke(self, token_id: str, expires_at: datetime) -> None:
        await self._collection.update_one(
            {"jti": token_id},
            {"$set": {"jti": token_id, "expires_at": expires_at}},
            upsert=True,
        )

    async def is_revoked(self, token_id: str) -> bool:
        return await self._collection.find_one({"jti": token_id}) is not None
