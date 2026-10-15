"""Shared fixtures.

The suite never touches the developer's database, cloud storage or paid APIs:
settings are forced *before* the app is imported to

* a throwaway MongoDB database (dropped at the end of the session),
* local file storage in a temporary directory,
* the offline mock LLM provider,
* inline document processing.

API tests need a reachable MongoDB (``MONGODB_URL``, default localhost) and are
skipped otherwise. ChromaDB and the embedding model are replaced by in-memory
test doubles here; ``tests/integration`` exercises the real services.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any

_RUN_ID = uuid.uuid4().hex[:10]
_STORAGE = tempfile.mkdtemp(prefix="smartform-test-")
_FORCED = {
    "APP_ENV": "test",
    "JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-123456",
    "LLM_PROVIDER": "mock",
    "LLM_API_KEY": "",
    "LLM_MODEL": "",
    "STORAGE_PROVIDER": "local",
    "STORAGE_ROOT": _STORAGE,
    "PROCESSING_MODE": "inline",
    "MONGODB_DATABASE": f"smart_form_test_{_RUN_ID}",
    "MONGODB_SERVER_SELECTION_TIMEOUT_MS": "1500",
    "CHROMADB_COLLECTION": f"test_chunks_{_RUN_ID}",
    "CORS_ORIGINS": "http://localhost:5173",
    "RAG_MIN_SIMILARITY": "0.1",
    "LOG_LEVEL": "WARNING",
}
os.environ.update(_FORCED)
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")

import pytest  # noqa: E402
from app.agents.llm_provider import MockLLMProvider  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.chroma_client import VectorStoreError  # noqa: E402
from app.processing.chunking import DocumentChunk  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

get_settings.cache_clear()


# ---------------------------------------------------------------------- test doubles


class FakeEmbeddings:
    """Deterministic bag-of-words vectors: similar wording gives similar vectors."""

    model_name = "test-bag-of-words"
    status = "loaded"
    dimension = 1024

    def __init__(self) -> None:
        self.fail = False

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            index = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.fail:
            from app.retrieval.embeddings import EmbeddingUnavailableError

            raise EmbeddingUnavailableError("test embedding failure")
        return [self._vector(text) for text in texts]

    async def embed_query(self, query: str) -> list[float]:
        return (await self.embed_texts([query]))[0]


class FakeVectorStore:
    """In-memory stand-in for ChromaClient with the same filtering semantics."""

    collection_name = "fake"

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self.down = False

    def _check(self) -> None:
        if self.down:
            raise VectorStoreError("fake vector store is down")

    async def is_healthy(self) -> bool:
        return not self.down

    async def ensure_collection(self) -> str:
        self._check()
        return "fake"

    async def upsert_chunks(
        self, chunks: list[DocumentChunk], embeddings: list[list[float]]
    ) -> None:
        self._check()
        for chunk, vector in zip(chunks, embeddings, strict=True):
            self.items[chunk.chunk_id] = {
                "text": chunk.text,
                "metadata": chunk.metadata,
                "vector": vector,
            }

    async def delete_document_chunks(self, user_id: str, document_id: str) -> None:
        self._check()
        self.items = {
            key: item
            for key, item in self.items.items()
            if not (
                item["metadata"]["user_id"] == user_id
                and item["metadata"]["document_id"] == document_id
            )
        }

    async def delete_user_chunks(self, user_id: str) -> None:
        self._check()
        self.items = {k: v for k, v in self.items.items() if v["metadata"]["user_id"] != user_id}

    async def query(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        document_type: str | None = None,
        document_ids: list[str] | None = None,
        document_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self._check()
        scored = []
        for key, item in self.items.items():
            meta = item["metadata"]
            if (
                meta["user_id"] != user_id
                or (document_type and meta.get("document_type") != document_type)
                or (document_types and meta.get("document_type") not in document_types)
                or (document_ids and meta.get("document_id") not in document_ids)
            ):
                continue
            similarity = sum(a * b for a, b in zip(query_embedding, item["vector"], strict=False))
            scored.append(
                {
                    "chunk_id": key,
                    "text": item["text"],
                    "similarity": round(similarity, 4),
                    "metadata": meta,
                }
            )
        return sorted(scored, key=lambda x: x["similarity"], reverse=True)[:top_k]

    def for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in self.items.values() if item["metadata"]["user_id"] == user_id]


class ScriptedLLM(MockLLMProvider):
    """Mock provider whose answers tests can script per task."""

    def __init__(self) -> None:
        super().__init__(responder=self._respond)
        self.handlers: dict[str, Callable[[str], str]] = {}
        self.calls: list[tuple[str, str]] = []

    def _respond(self, task: str, prompt: str) -> str:
        self.calls.append((task, prompt))
        handler = self.handlers.get(task)
        if handler is None:
            return MockLLMProvider()._complete(prompt, system=None, json_mode=True, task=task)
        return handler(prompt)

    def calls_for(self, task: str) -> list[str]:
        return [prompt for name, prompt in self.calls if name == task]


# ---------------------------------------------------------------------- fixtures


def _mongo_available() -> bool:
    try:
        client: MongoClient = MongoClient(os.environ["MONGODB_URL"], serverSelectionTimeoutMS=800)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False


MONGO_AVAILABLE = _mongo_available()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_mongo = pytest.mark.skip(reason="MongoDB is not reachable at MONGODB_URL")
    for item in items:
        if "mongo" in item.keywords and not MONGO_AVAILABLE:
            item.add_marker(skip_mongo)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if MONGO_AVAILABLE:
        client: MongoClient = MongoClient(os.environ["MONGODB_URL"], serverSelectionTimeoutMS=800)
        client.drop_database(os.environ["MONGODB_DATABASE"])
        client.close()


class Harness:
    def __init__(
        self,
        client: TestClient,
        llm: ScriptedLLM,
        vectors: FakeVectorStore,
        embeddings: FakeEmbeddings,
    ):
        self.client = client
        self.llm = llm
        self.vectors = vectors
        self.embeddings = embeddings

    def register(self, name: str = "Test User") -> dict[str, str]:
        email = f"user_{uuid.uuid4().hex[:12]}@example.com"
        password = "Str0ng-Passw0rd!"
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )
        assert response.status_code == 201, response.text
        login = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def upload(
        self, headers: dict[str, str], name: str, content: bytes, mime: str | None = None
    ) -> Any:
        return self.client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": (name, content, mime or "application/octet-stream")},
        )

    def wait_processed(
        self, headers: dict[str, str], document_id: str, timeout: float = 20
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            body = self.client.get(f"/api/v1/documents/{document_id}", headers=headers).json()[
                "data"
            ]
            if body["status"] != "processing":
                return body
            time.sleep(0.1)
        raise AssertionError(f"document {document_id} still processing after {timeout}s")


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
    """A running app backed by the throwaway MongoDB and in-memory test doubles."""
    if not MONGO_AVAILABLE:
        pytest.skip("MongoDB is not reachable at MONGODB_URL")
    import app.main as main

    llm = ScriptedLLM()
    vectors = FakeVectorStore()
    embeddings = FakeEmbeddings()
    monkeypatch.setattr(main, "get_llm_provider", lambda settings: llm)
    monkeypatch.setattr(main, "ChromaClient", lambda settings: vectors)
    monkeypatch.setattr(
        main,
        "SentenceTransformerEmbeddings",
        lambda name, expected_dimension=384: embeddings,
    )
    limiter.enabled = False
    with TestClient(main.app) as client:
        yield Harness(client, llm, vectors, embeddings)
    limiter.enabled = True
