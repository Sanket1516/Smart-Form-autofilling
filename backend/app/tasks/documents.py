"""Document processing task.

Wires both extraction tracks:
  Track A: DynamicDocumentExtractor → DiscoveredFactsRepository + DiscoveredConflictsRepository
  Track B: DocumentOntologyExtractor → StructuredFactsRepository (backward compat)
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.extraction.dynamic_extractor import DynamicDocumentExtractor
from app.extraction.llm_extractor import DocumentOntologyExtractor
from app.agents.llm_provider import get_llm_provider
from app.ontology.loader import FieldOntology
from app.processing.extractor import OCRUnavailableError, PaddleOCRAdapter, UniversalDocumentExtractor
from app.processing.pipeline import DocumentPipeline, PipelineRetryableError
from app.repositories.collections import (
    DiscoveredConflictsRepository,
    DiscoveredFactsRepository,
    DocumentsRepository,
    ProcessingRecordsRepository,
    StructuredFactsRepository,
)
from app.storage.base import DocumentStorage
from app.storage.local import LocalFileStorage
from app.storage.cloudinary_storage import CloudinaryStorage
from app.tasks.celery_app import celery_app

from app.db.chroma_client import ChromaClient
from app.processing.chunking import TextChunker
from app.retrieval.embeddings import DefaultEmbeddingProvider

logger = logging.getLogger(__name__)


async def _process(document_id: str, user_id: str) -> None:
    settings = get_settings()
    connection = MongoConnection(settings)
    if settings.storage_provider == "cloudinary":
        storage: DocumentStorage = CloudinaryStorage(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )
    else:
        storage: DocumentStorage = LocalFileStorage(settings.storage_root)

    documents = DocumentsRepository(connection.database)
    processing = ProcessingRecordsRepository(connection.database)

    try:
        await documents.update(
            user_id,
            document_id,
            {"status": "processing", "current_stage": "validation", "progress": 10},
        )
        document = await documents.get(user_id, document_id)
        if document is None:
            return
        checksum = await storage.checksum(document["storage_reference"])
        if checksum != document.get("checksum"):
            logger.info("checksum_auto_updated doc_id=%s", document_id)
            try:
                await documents.update(user_id, document_id, {"checksum": checksum})
            except Exception:
                pass

        async def on_update(values: dict[str, object]) -> None:
            await documents.update(user_id, document_id, values)

        # Shared infra
        chunker = TextChunker(chunk_size=settings.rag_chunk_size, chunk_overlap=settings.rag_chunk_overlap)
        embedding_provider = DefaultEmbeddingProvider(settings)
        chroma_client = ChromaClient(settings)
        llm_provider = get_llm_provider(settings)

        # Track A: Dynamic extractor (primary — document-agnostic)
        ontology = FieldOntology()
        dynamic_extractor = DynamicDocumentExtractor(llm_provider, ontology=ontology)
        discovered_facts_repo = DiscoveredFactsRepository(connection.database)
        discovered_conflicts_repo = DiscoveredConflictsRepository(connection.database)

        # Track B: Ontology-mapped extractor (secondary — backward compat)
        llm_extractor = DocumentOntologyExtractor(llm_provider, ontology)

        pipeline = DocumentPipeline(
            UniversalDocumentExtractor(
                PaddleOCRAdapter(language=settings.ocr_language),
                resolution=settings.ocr_resolution,
            ),
            processing,
            settings.processing_max_retries,
            # Track B
            fact_extractor=llm_extractor,
            fact_writer=StructuredFactsRepository(connection.database),
            # Track A
            dynamic_extractor=dynamic_extractor,
            discovered_fact_writer=discovered_facts_repo,
            discovered_conflict_writer=discovered_conflicts_repo,
            # Shared
            chunker=chunker,
            embedding_provider=embedding_provider,
            chroma_client=chroma_client,
        )
        async with storage.get_local_path(document["storage_reference"]) as local_path:
            normalized = await pipeline.run(
                user_id,
                document_id,
                local_path,
                on_update,
                document_name=document["file_name"],
            )
        normalized_reference = f"{document['storage_reference']}.normalized.json"
        await storage.save_bytes(
            normalized_reference,
            json.dumps(normalized.model_dump(), ensure_ascii=False).encode("utf-8"),
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
                "page_count": normalized.page_count,
                "normalized_reference": normalized_reference,
            },
        )
    except (OCRUnavailableError, PipelineRetryableError):
        raise
    except Exception as error:
        logger.exception("document_processing_failed", extra={"document_id": document_id})
        await documents.update(
            user_id,
            document_id,
            {
                "status": "failed",
                "current_stage": "failed",
                "processing_error": str(error),
            },
        )
    finally:
        connection.close()


@celery_app.task(bind=True, name="documents.process", max_retries=5)
def process_document(task: object, document_id: str, user_id: str) -> None:
    settings = get_settings()
    try:
        asyncio.run(_process(document_id, user_id))
    except (OCRUnavailableError, PipelineRetryableError) as error:
        retries = getattr(getattr(task, "request", None), "retries", 0)
        if retries < settings.processing_max_retries:
            raise task.retry(exc=error, countdown=2**retries) from error
        asyncio.run(_mark_requires_review(document_id, user_id, str(error)))


async def _mark_requires_review(document_id: str, user_id: str, error: str) -> None:
    settings = get_settings()
    connection = MongoConnection(settings)
    try:
        await DocumentsRepository(connection.database).update(
            user_id,
            document_id,
            {"status": "requires_review", "current_stage": "failed", "processing_error": error},
        )
    finally:
        connection.close()
