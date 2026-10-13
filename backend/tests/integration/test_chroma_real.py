"""Real ChromaDB + real sentence-transformer embeddings (marker: chroma).

Run with:  pytest -m chroma   (needs ChromaDB at CHROMADB_URL; downloads the
embedding model on first run). Uses a throwaway collection that is deleted
afterwards.
"""

import asyncio
import uuid

import httpx
import pytest
from app.core.config import Settings
from app.db.chroma_client import ChromaClient, VectorStoreError
from app.processing.chunking import TextChunker
from app.processing.schemas import ExtractedSpan, NormalizedDocument, NormalizedPage
from app.retrieval.embeddings import SentenceTransformerEmbeddings
from app.services.retrieval import RAGRetrievalService

pytestmark = pytest.mark.chroma


def _settings(collection: str, model: str = "all-MiniLM-L6-v2") -> Settings:
    return Settings(
        jwt_secret_key="x" * 40,
        chromadb_collection=collection,
        embedding_model_name=model,
    )


def _doc(text: str) -> NormalizedDocument:
    return NormalizedDocument(
        pages=[
            NormalizedPage(
                page_number=1,
                spans=[ExtractedSpan(page_number=1, text=text, source_method="direct-parse")],
            )
        ]
    )


@pytest.fixture(scope="module")
def embeddings() -> SentenceTransformerEmbeddings:
    return SentenceTransformerEmbeddings("all-MiniLM-L6-v2")


@pytest.fixture
def collection() -> str:
    name = f"it_{uuid.uuid4().hex[:10]}"
    yield name
    settings = _settings(name)
    httpx.delete(
        f"{settings.chromadb_url}/api/v2/tenants/{settings.chromadb_tenant}/databases/"
        f"{settings.chromadb_database}/collections/{name}",
        timeout=10,
    )


def test_index_query_isolation_and_delete(
    collection: str, embeddings: SentenceTransformerEmbeddings
) -> None:
    async def scenario() -> None:
        settings = _settings(collection)
        client = ChromaClient(settings)
        if not await client.is_healthy():
            pytest.skip("ChromaDB is not reachable at CHROMADB_URL")
        chunker = TextChunker(500, 50)
        alice = chunker.chunk_document(
            _doc("Avery worked as a data analyst at Example Corp, building reporting dashboards."),
            "alice",
            "doc-a",
            "resume.pdf",
            "RESUME",
        )
        bob = chunker.chunk_document(
            _doc("Bob holds a bachelor's degree in mechanical engineering from Example State."),
            "bob",
            "doc-b",
            "degree.pdf",
            "ACADEMIC_CERTIFICATE",
        )
        for chunks in (alice, bob):
            await client.upsert_chunks(
                chunks, await embeddings.embed_texts([c.text for c in chunks])
            )

        retrieval = RAGRetrievalService(client, embeddings, min_similarity=0.3)
        hits = await retrieval.search("alice", "Which company did I work for as an analyst?", 5)
        assert hits and hits[0].metadata.document_id == "doc-a"
        assert all(hit.metadata.document_id == "doc-a" for hit in hits)  # never Bob's chunks
        assert hits[0].similarity > 0.3

        assert await retrieval.search("alice", "favourite pizza toppings in Naples", 5) == []

        await client.delete_document_chunks("alice", "doc-a")
        assert (
            await retrieval.search("alice", "data analyst at Example Corp", 5, min_similarity=0.0)
            == []
        )
        assert await retrieval.search("bob", "mechanical engineering degree", 5)

    asyncio.run(scenario())


def test_collection_model_mismatch_is_detected(collection: str) -> None:
    async def scenario() -> None:
        first = ChromaClient(_settings(collection))
        if not await first.is_healthy():
            pytest.skip("ChromaDB is not reachable at CHROMADB_URL")
        await first.ensure_collection()
        other = ChromaClient(_settings(collection, model="some-other-model"))
        with pytest.raises(VectorStoreError, match="embedding model"):
            await other.ensure_collection()

    asyncio.run(scenario())


def test_unreachable_chroma_raises_instead_of_falling_back() -> None:
    async def scenario() -> None:
        settings = Settings(
            jwt_secret_key="x" * 40, chromadb_url="http://127.0.0.1:9", chromadb_timeout_seconds=1
        )
        client = ChromaClient(settings)
        assert not await client.is_healthy()
        with pytest.raises(VectorStoreError):
            await client.query("u", [0.0] * 384, 3)

    asyncio.run(scenario())
