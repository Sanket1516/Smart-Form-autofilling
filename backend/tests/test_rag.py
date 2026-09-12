"""Tests for RAG text chunking, embedding generation, vector storage, and RAG retrieval endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.chroma_client import ChromaClient
from app.main import app
from app.processing.chunking import TextChunker
from app.processing.pipeline import DocumentPipeline
from app.processing.schemas import ExtractedSpan, NormalizedDocument, NormalizedPage
from app.retrieval.embeddings import DefaultEmbeddingProvider
from app.schemas.retrieval import RAGFilters, RAGRetrievalRequest
from app.services.retrieval import RAGRetrievalService


class FakeStageWriter:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, str]] = []

    async def record_stage(
        self,
        user_id: str,
        document_id: str,
        stage: str,
        status: str,
        error: str | None = None,
    ) -> None:
        self.records.append((stage, status, error or ""))


class FakeExtractor:
    def __init__(self, result: NormalizedDocument) -> None:
        self.result = result

    def extract(self, path: str) -> NormalizedDocument:
        return self.result


def sample_document() -> NormalizedDocument:
    return NormalizedDocument(
        pages=[
            NormalizedPage(
                page_number=1,
                width=612,
                height=792,
                spans=[
                    ExtractedSpan(
                        page_number=1,
                        text="Ada Lovelace was a mathematician and writer, known for work on Babbage's Analytical Engine.",
                        source_method="direct-parse",
                    )
                ],
            ),
            NormalizedPage(
                page_number=2,
                width=612,
                height=792,
                spans=[
                    ExtractedSpan(
                        page_number=2,
                        text="Previous employment details include project management and algorithm design responsibilities.",
                        source_method="ocr",
                    )
                ],
            ),
        ]
    )


def test_chunker_splits_text_with_metadata() -> None:
    chunker = TextChunker(chunk_size=40, chunk_overlap=10)
    doc = sample_document()
    chunks = chunker.chunk_document(doc, "user-1", "doc-1", "resume.pdf")

    assert len(chunks) >= 2
    assert chunks[0].metadata["user_id"] == "user-1"
    assert chunks[0].metadata["document_id"] == "doc-1"
    assert chunks[0].metadata["page_number"] == 1
    assert chunks[0].metadata["chunk_index"] == 0


def test_embedding_provider_generates_vectors() -> None:
    settings = Settings(embedding_model_name="BAAI/bge-m3")
    provider = DefaultEmbeddingProvider(settings)

    texts = ["Sample document chunk", "Another chunk text"]
    embeddings = provider.embed_texts(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1024

    query_vec = provider.embed_query("Sample query")
    assert len(query_vec) == 1024


@pytest.mark.asyncio
async def test_chroma_client_stores_queries_and_deletes_chunks() -> None:
    settings = Settings(chromadb_url="http://localhost:8001")
    client = ChromaClient(settings)
    provider = DefaultEmbeddingProvider(settings)

    chunker = TextChunker(chunk_size=100, chunk_overlap=10)
    doc = sample_document()
    chunks = chunker.chunk_document(doc, "user-a", "doc-100", "resume.pdf")
    embeddings = provider.embed_texts([c.text for c in chunks])

    await client.add_chunks(chunks, embeddings)

    query_vec = provider.embed_query("Babbage Analytical Engine")
    results = await client.query_rag(
        user_id="user-a",
        query_embedding=query_vec,
        top_k=2,
        filters={"language": "en"},
    )

    assert len(results) > 0
    assert results[0]["metadata"]["document_id"] == "doc-100"

    user_b_results = await client.query_rag(
        user_id="user-b",
        query_embedding=query_vec,
        top_k=2,
    )
    assert len(user_b_results) == 0

    await client.delete_document_chunks("user-a", "doc-100")
    post_delete_results = await client.query_rag(
        user_id="user-a",
        query_embedding=query_vec,
        top_k=2,
    )
    assert len(post_delete_results) == 0


@pytest.mark.asyncio
async def test_rag_retrieval_service_scopes_to_user() -> None:
    settings = Settings()
    client = ChromaClient(settings)
    provider = DefaultEmbeddingProvider(settings)
    service = RAGRetrievalService(client, provider)

    chunker = TextChunker()
    chunks = chunker.chunk_document(sample_document(), "user-x", "doc-x", "resume.pdf")
    embeddings = provider.embed_texts([c.text for c in chunks])
    await client.add_chunks(chunks, embeddings)

    req = RAGRetrievalRequest(query="algorithm design", top_k=3, filters=RAGFilters(language="en"))
    response = await service.search("user-x", req)

    assert len(response.results) > 0
    assert response.results[0].metadata.document_id == "doc-x"

    unauthorized_res = await service.search("user-y", req)
    assert len(unauthorized_res.results) == 0


@pytest.mark.asyncio
async def test_pipeline_runs_embedding_and_chromadb_storage_stages() -> None:
    writer = FakeStageWriter()
    settings = Settings()
    client = ChromaClient(settings)
    provider = DefaultEmbeddingProvider(settings)

    pipeline = DocumentPipeline(
        extractor=FakeExtractor(sample_document()),
        stage_writer=writer,
        chunker=TextChunker(),
        embedding_provider=provider,
        chroma_client=client,
    )

    await pipeline.run("user-1", "doc-1", "document.pdf", lambda _: _completed())
    stages = [stage for stage, status, _ in writer.records if status == "completed"]
    assert "embedding" in stages
    assert "chromadb_storage" in stages


async def _completed() -> None:
    return None


def test_post_retrieval_rag_endpoint(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    response = test_client.post(
        "/api/v1/retrieval/rag",
        json={
            "query": "mathematician",
            "top_k": 3,
            "filters": {"language": "en"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "results" in data["data"]
