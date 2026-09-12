"""Service health aggregation."""

import asyncio
from typing import Protocol

from app.schemas.health import ServiceHealthData


class HealthProbe(Protocol):
    async def is_healthy(self) -> bool: ...


class HealthService:
    def __init__(self, mongo: HealthProbe, chroma: HealthProbe) -> None:
        self._mongo = mongo
        self._chroma = chroma

    async def get_services(self) -> ServiceHealthData:
        mongo_healthy, chroma_healthy = await asyncio.gather(
            self._mongo.is_healthy(), self._chroma.is_healthy()
        )
        return ServiceHealthData(
            api="healthy",
            mongodb="healthy" if mongo_healthy else "unhealthy",
            chromadb="healthy" if chroma_healthy else "unhealthy",
            llm="not_configured",
            embedding_service="not_configured",
        )
