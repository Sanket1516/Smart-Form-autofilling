"""MongoDB connectivity manager."""

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import Settings


class MongoConnection:
    """Own the MongoDB client and expose a connectivity probe."""

    def __init__(self, settings: Settings) -> None:
        self._database_name = settings.mongodb_database
        self._client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )

    @property
    def database(self):
        return self._client[self._database_name]

    async def is_healthy(self) -> bool:
        try:
            await self._client.admin.command("ping")
        except Exception:
            return False
        return True

    def close(self) -> None:
        self._client.close()
