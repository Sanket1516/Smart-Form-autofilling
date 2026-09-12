"""Document processing task."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.extraction.facts import CandidateFactExtractor
from app.processing.extractor import OCRUnavailableError, PaddleOCRAdapter, PDFExtractor
from app.processing.pipeline import DocumentPipeline, PipelineRetryableError
from app.repositories.collections import (
    DocumentsRepository,
    ProcessingRecordsRepository,
    StructuredFactsRepository,
)
from app.storage.local import LocalFileStorage
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _process(document_id: str, user_id: str) -> None:
    settings = get_settings()
    connection = MongoConnection(settings)
    storage = LocalFileStorage(settings.storage_root)
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
        if checksum != document["checksum"]:
            raise ValueError("stored file integrity check failed")

        async def on_update(values: dict[str, object]) -> None:
            await documents.update(user_id, document_id, values)

        pipeline = DocumentPipeline(
            PDFExtractor(
                PaddleOCRAdapter(language=settings.ocr_language),
                resolution=settings.ocr_resolution,
            ),
            processing,
            settings.processing_max_retries,
            fact_extractor=CandidateFactExtractor(),
            fact_writer=StructuredFactsRepository(connection.database),
        )
        normalized = await pipeline.run(
            user_id,
            document_id,
            str(Path(settings.storage_root) / document["storage_reference"]),
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
