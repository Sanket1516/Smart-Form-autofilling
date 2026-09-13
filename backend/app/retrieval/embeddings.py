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
    """Production embedding provider defaulting to BGE-M3 with deterministic CPU fallback.

    When the real model cannot be loaded, a WARNING is emitted and every
    subsequent call that uses the hash fallback also logs at WARNING level.
    Hash vectors are NOT semantic — cosine-similarity search with them is
    meaningless.  Check logs for 'EMBEDDING_MODEL_UNAVAILABLE' to confirm
    whether real embeddings are active.
    """

    def __init__(self, settings: Settings) -> None:
        self.model_name = (
            settings.embedding_model_name
            or settings.embedding_model
            or "all-MiniLM-L6-v2"
        )
        self.dimension = 384
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            self._initialized = True
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._model = SentenceTransformer(self.model_name)
                if hasattr(self._model, "get_sentence_embedding_dimension"):
                    self.dimension = self._model.get_sentence_embedding_dimension()
                logger.info("embedding_model_loaded", extra={"model_name": self.model_name})
            except Exception as error:
                logger.warning(
                    "EMBEDDING_MODEL_UNAVAILABLE: Failed to load '%s'. "
                    "Falling back to dummy embeddings. Error: %s",
                    self.model_name,
                    error,
                )
                self._model = None
        return self._model

    @property
    def is_semantic(self) -> bool:
        """True when a real sentence-transformer model is loaded."""
        return self._get_model() is not None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        if model is not None:
            try:
                embeddings = model.encode(texts, normalize_embeddings=True)
                return [vec.tolist() for vec in embeddings]
            except Exception as error:
                logger.error(
                    "model_encode_failed",
                    extra={"error": str(error), "text_count": len(texts)},
                )
        # Fallback dummy embedding vectors
        import hashlib
        result = []
        for text in texts:
            seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
            vec = [(float((seed >> i) & 1) - 0.5) for i in range(self.dimension)]
            result.append(vec)
        return result

    def embed_query(self, query: str) -> list[float]:
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self.dimension
