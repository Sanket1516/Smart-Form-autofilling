import asyncio
from urllib.error import URLError
from urllib.request import urlopen

from app.core.config import Settings
from app.database.models import DatabaseHealth


class ChromaDBManager:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.chromadb_url.rstrip("/")
        self._timeout_seconds = settings.chromadb_timeout_seconds

    def _heartbeat(self) -> None:
        """Use Chroma's documented server heartbeat without creating collections."""
        for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                with urlopen(
                    f"{self._base_url}{endpoint}", timeout=self._timeout_seconds
                ) as response:
                    if 200 <= response.status < 300:
                        return
            except URLError:
                continue
        raise ConnectionError("ChromaDB heartbeat failed")

    async def health_check(self) -> DatabaseHealth:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._heartbeat), timeout=self._timeout_seconds + 0.5
            )
            return DatabaseHealth(name="chromadb", available=True)
        except Exception as error:  # Connection details are intentionally not exposed.
            return DatabaseHealth(name="chromadb", available=False, detail=type(error).__name__)
