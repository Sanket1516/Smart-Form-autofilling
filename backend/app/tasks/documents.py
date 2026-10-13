"""Celery task wrapper used when PROCESSING_MODE=celery."""

import asyncio

from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.processing.runner import context_from_settings, process_document
from app.tasks.celery_app import celery_app


@celery_app.task(name="documents.process")
def process_document_task(document_id: str, user_id: str) -> None:
    asyncio.run(_run(document_id, user_id))


async def _run(document_id: str, user_id: str) -> None:
    settings = get_settings()
    connection = MongoConnection(settings)
    try:
        context = context_from_settings(settings, connection.database)
        await process_document(context, user_id, document_id)
    finally:
        connection.close()
