from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import Settings
from app.database.models import DatabaseHealth


class MongoDBManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )

    async def health_check(self) -> DatabaseHealth:
        try:
            await self._client.admin.command("ping")
            return DatabaseHealth(name="mongodb", available=True)
        except Exception as error:  # Connection details are intentionally not exposed.
            return DatabaseHealth(name="mongodb", available=False, detail=type(error).__name__)

    def close(self) -> None:
        self._client.close()
