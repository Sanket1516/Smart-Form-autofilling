"""RAG Retrieval service enforcing authenticated user isolation."""

from typing import Any

from app.db.chroma_client import ChromaClient
from app.retrieval.embeddings import EmbeddingProvider
from app.schemas.retrieval import (
    RAGChunkMetadata,
    RAGRetrievalData,
    RAGRetrievalRequest,
    RAGSearchResult,
)


class RAGRetrievalService:
    """Service managing text query embedding and ChromaDB vector search."""

    def __init__(
        self, chroma_client: ChromaClient, embedding_provider: EmbeddingProvider
    ) -> None:
        self.chroma_client = chroma_client
        self.embedding_provider = embedding_provider

    async def search(self, user_id: str, request: RAGRetrievalRequest) -> RAGRetrievalData:
        query_embedding = self.embedding_provider.embed_query(request.query)
        filters_dict: dict[str, Any] | None = None
        if request.filters:
            filters_dict = request.filters.model_dump(exclude_none=True)

        raw_results = await self.chroma_client.query_rag(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=request.top_k,
            filters=filters_dict,
        )

        results: list[RAGSearchResult] = []
        for item in raw_results:
            meta = item.get("metadata", {})
            metadata_obj = RAGChunkMetadata(
                document_id=str(meta.get("document_id", "")),
                page_number=int(meta.get("page_number", 1)),
                language=str(meta.get("language", "en")),
            )
            results.append(
                RAGSearchResult(
                    chunk_id=item["chunk_id"],
                    text=item["text"],
                    similarity=item["similarity"],
                    metadata=metadata_obj,
                )
            )

        return RAGRetrievalData(results=results)
