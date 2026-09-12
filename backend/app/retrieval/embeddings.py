"""Pluggable embedding provider implementation (SRS §35.5)."""

import hashlib
import logging
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Abstract interface for embedding generation."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class DefaultEmbeddingProvider:
    """Production embedding provider defaulting to BGE-M3 with deterministic CPU fallback."""

    def __init__(self, settings: Settings) -> None:
        self.model_name = (
            settings.embedding_model_name
            or settings.embedding_model
            or "BAAI/bge-m3"
        )
        self.dimension = 1024
        self._model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self.model_name)
            logger.info("embedding_model_loaded", extra={"model_name": self.model_name})
        except Exception as error:
            logger.info(
                "embedding_model_fallback",
                extra={
                    "model_name": self.model_name,
                    "reason": str(error),
                    "fallback": "deterministic_vector_generator",
                },
            )
            self._model = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is not None:
            try:
                embeddings = self._model.encode(texts, normalize_embeddings=True)
                return [vec.tolist() for vec in embeddings]
            except Exception as error:
                logger.warning(
                    "model_encode_failed_using_fallback", extra={"error": str(error)}
                )

        return [self._deterministic_embedding(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self.dimension

    def _deterministic_embedding(self, text: str) -> list[float]:
        """Generate a deterministic normalized embedding vector derived from text digest."""
        vec: list[float] = []
        for i in range(self.dimension):
            digest = hashlib.sha256(f"{text}:{i}:{self.model_name}".encode("utf-8")).digest()
            val = (int.from_bytes(digest[:4], "big") / 4294967295.0) * 2.0 - 1.0
            vec.append(val)
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
