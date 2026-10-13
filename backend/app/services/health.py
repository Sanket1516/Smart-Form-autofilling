"""Dependency health reporting."""

from __future__ import annotations

import asyncio

from app.agents.llm_provider import LLMProvider
from app.db.chroma_client import ChromaClient, VectorStoreError
from app.db.mongo import MongoConnection
from app.retrieval.embeddings import SentenceTransformerEmbeddings
from app.schemas.health import ServiceHealthData


class HealthService:
    def __init__(
        self,
        mongo: MongoConnection,
        chroma: ChromaClient,
        llm: LLMProvider,
        embeddings: SentenceTransformerEmbeddings,
    ) -> None:
        self._mongo = mongo
        self._chroma = chroma
        self._llm = llm
        self._embeddings = embeddings

    async def ready(self) -> bool:
        return await self._mongo.is_healthy()

    async def get_services(self) -> ServiceHealthData:
        mongo_ok, chroma_ok = await asyncio.gather(
            self._mongo.is_healthy(), self._chroma.is_healthy()
        )
        details: dict[str, str] = {
            "llm_provider": self._llm.name,
            "llm_model": self._llm.model,
            "embedding_model": self._embeddings.model_name,
            "embedding_status": self._embeddings.status,
            "embedding_dimension": str(
                self._embeddings.dimension or self._embeddings.expected_dimension or "unknown"
            ),
            "vector_collection": self._chroma.collection_name,
        }
        chroma_state = "healthy" if chroma_ok else "unhealthy"
        if chroma_ok:
            try:
                await self._chroma.ensure_collection()
            except VectorStoreError as error:
                chroma_state = "unhealthy"
                details["vector_collection_error"] = str(error)
        status = self._embeddings.status
        embedding_state = (
            "unhealthy"
            if status.startswith("failed")
            else ("healthy" if status == "loaded" else "not_loaded")
        )
        return ServiceHealthData(
            api="healthy",
            mongodb="healthy" if mongo_ok else "unhealthy",
            chromadb=chroma_state,
            llm="mock" if self._llm.is_mock else "configured",
            embedding_service=embedding_state,
            details=details,
        )
