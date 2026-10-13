"""Sentence-transformer embeddings.

The model is loaded lazily on first use. A load or encode failure raises
``EmbeddingUnavailableError``; there is no fallback to non-semantic vectors.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(RuntimeError):
    """The embedding model could not be loaded or failed to encode text."""


class EmbeddingProvider(Protocol):
    model_name: str

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, query: str) -> list[float]: ...


class SentenceTransformerEmbeddings:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Any | None = None
        self._error: str | None = None
        self._lock = threading.Lock()

    @property
    def status(self) -> str:
        if self._model is not None:
            return "loaded"
        return f"failed: {self._error}" if self._error else "not_loaded"

    @property
    def dimension(self) -> int | None:
        if self._model is None:
            return None
        return int(self._model.get_sentence_embedding_dimension())

    def _load(self) -> Any:
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(self.model_name)
                    self._error = None
                    logger.info("embedding_model_loaded", extra={"model_name": self.model_name})
                except Exception as error:
                    self._error = f"{type(error).__name__}"
                    raise EmbeddingUnavailableError(
                        f"Embedding model '{self.model_name}' could not be loaded"
                    ) from error
            return self._model

    def embed_texts_sync(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        try:
            vectors = model.encode(texts, normalize_embeddings=True)
        except Exception as error:
            raise EmbeddingUnavailableError("Embedding model failed to encode text") from error
        return [list(map(float, vector)) for vector in vectors]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_texts_sync, texts)

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]
