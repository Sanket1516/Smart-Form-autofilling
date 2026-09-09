import asyncio
from urllib.parse import urlparse

import chromadb

from app.core.config import Settings
from app.database.models import DatabaseHealth


class ChromaDBManager:
    def __init__(self, settings: Settings) -> None:
        parsed_url = urlparse(settings.chromadb_url)
        self._client = chromadb.HttpClient(
            host=parsed_url.hostname or "localhost",
            port=parsed_url.port or 8000,
            ssl=parsed_url.scheme == "https",
        )

    async def health_check(self) -> DatabaseHealth:
        try:
            await asyncio.wait_for(asyncio.to_thread(self._client.heartbeat), timeout=2.5)
            return DatabaseHealth(name="chromadb", available=True)
        except Exception as error:  # Connection details are intentionally not exposed.
            return DatabaseHealth(name="chromadb", available=False, detail=type(error).__name__)

