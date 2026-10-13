"""Runs the document pipeline for one document and records the outcome.

``PROCESSING_MODE=inline`` runs this coroutine as a task inside the API process
(reusing the API's database client, models and stores). ``celery`` runs the same
coroutine in a worker, which builds its own context from settings.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.agents.llm_provider import LLMProvider, get_llm_provider
from app.core.config import Settings
from app.db.chroma_client import ChromaClient
from app.extraction.deterministic import DeterministicExtractor
from app.extraction.llm_extraction import LLMFactExtractor
from app.ontology.loader import FieldOntology
from app.processing.chunking import TextChunker
from app.processing.extractor import (
    DocumentReadError,
    OCRUnavailableError,
    PaddleOCRAdapter,
    UniversalDocumentExtractor,
)
from app.processing.pipeline import DocumentPipeline
from app.repositories.collections import (
    DiscoveredFactsRepository,
    DocumentsRepository,
    ProcessingRecordsRepository,
    StructuredFactsRepository,
)
from app.retrieval.embeddings import EmbeddingProvider, SentenceTransformerEmbeddings
from app.storage.base import DocumentStorage

logger = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    settings: Settings
    database: Any
    storage: DocumentStorage
    llm: LLMProvider
    embeddings: EmbeddingProvider
    vector_store: ChromaClient
    ontology: FieldOntology

    def pipeline(self) -> DocumentPipeline:
        return DocumentPipeline(
            extractor=UniversalDocumentExtractor(
                PaddleOCRAdapter(language=self.settings.ocr_language),
                resolution=self.settings.ocr_resolution,
            ),
            ontology=self.ontology,
            deterministic=DeterministicExtractor(self.ontology),
            llm_extractor=LLMFactExtractor(
                self.llm, self.ontology, max_chars=self.settings.llm_extraction_max_chars
            ),
            facts=StructuredFactsRepository(self.database),
            discovered=DiscoveredFactsRepository(self.database),
            stages=ProcessingRecordsRepository(self.database),
            chunker=TextChunker(self.settings.rag_chunk_size, self.settings.rag_chunk_overlap),
            embeddings=self.embeddings,
            vector_store=self.vector_store,
        )


def build_storage(settings: Settings) -> DocumentStorage:
    if settings.storage_provider == "cloudinary":
        from app.storage.cloudinary_storage import CloudinaryStorage

        return CloudinaryStorage(
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        )
    from app.storage.local import LocalFileStorage

    return LocalFileStorage(settings.storage_root)


def context_from_settings(settings: Settings, database: Any) -> ProcessingContext:
    """Build a standalone context (used by the Celery worker)."""
    return ProcessingContext(
        settings=settings,
        database=database,
        storage=build_storage(settings),
        llm=get_llm_provider(settings),
        embeddings=SentenceTransformerEmbeddings(settings.embedding_model_name),
        vector_store=ChromaClient(settings),
        ontology=FieldOntology(),
    )


async def process_document(context: ProcessingContext, user_id: str, document_id: str) -> None:
    documents = DocumentsRepository(context.database)
    document = await documents.get(user_id, document_id)
    if document is None or document.get("status") == "deleted":
        return

    async def on_update(values: dict[str, object]) -> None:
        await documents.update(user_id, document_id, values)

    try:
        async with context.storage.get_local_path(document["storage_reference"]) as local_path:
            result = await context.pipeline().run(
                user_id, document_id, local_path, document["file_name"], on_update
            )
        normalized_reference = f"{document['storage_reference']}.normalized.json"
        normalized_reference = await context.storage.save_bytes(
            normalized_reference,
            json.dumps(result.normalized.model_dump(), ensure_ascii=False).encode("utf-8"),
        )
        await documents.update(
            user_id,
            document_id,
            {
                "status": "processed",
                "current_stage": "completed",
                "progress": 100,
                "processed_at": datetime.now(UTC),
                "processing_error": None,
                "warnings": result.warnings,
                "page_count": result.normalized.page_count,
                "document_type": (
                    result.document_type
                    if result.document_type != "UNKNOWN"
                    else document.get("document_type")
                ),
                "normalized_reference": normalized_reference,
                "fact_count": result.fact_count,
                "index_status": result.index_status,
                "chunk_count": result.chunk_count,
                "index_error": result.index_error,
            },
        )
        logger.info(
            "document_processed",
            extra={
                "document_id": document_id,
                "facts": result.fact_count,
                "chunks": result.chunk_count,
            },
        )
    except OCRUnavailableError as error:
        await _finish(documents, user_id, document_id, "requires_review", str(error))
    except DocumentReadError as error:
        await _finish(documents, user_id, document_id, "failed", str(error))
    except Exception:
        logger.exception("document_processing_failed", extra={"document_id": document_id})
        await _finish(
            documents,
            user_id,
            document_id,
            "failed",
            "Processing failed because of an internal error.",
        )


async def _finish(
    documents: DocumentsRepository, user_id: str, document_id: str, status: str, message: str
) -> None:
    await documents.update(
        user_id,
        document_id,
        {"status": status, "current_stage": status, "processing_error": message},
    )
