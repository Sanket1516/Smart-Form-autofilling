"""ChromaDB connectivity manager."""

import asyncio
from urllib.error import URLError
from urllib.request import urlopen

from app.core.config import Settings


class ChromaConnection:
    """Own ChromaDB connection settings and expose a heartbeat probe."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.chromadb_url.rstrip("/")
        self._timeout_seconds = settings.chromadb_timeout_seconds

    def _heartbeat(self) -> None:
        for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                with urlopen(
                    f"{self._base_url}{endpoint}", timeout=self._timeout_seconds
                ) as response:
                    if 200 <= response.status < 300:
                        return
            except (OSError, URLError):
                continue
        raise ConnectionError("ChromaDB heartbeat failed")

    async def is_healthy(self) -> bool:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._heartbeat), timeout=self._timeout_seconds + 0.5
            )
        except Exception:
            return False
        return True
