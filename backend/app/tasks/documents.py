"""Celery task wrapper used when PROCESSING_MODE=celery."""

import asyncio
import logging

from bson import ObjectId
from celery.signals import task_failure
from pymongo import MongoClient

from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.processing.runner import context_from_settings, process_document
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="documents.process")
def process_document_task(document_id: str, user_id: str) -> None:
    asyncio.run(_run(document_id, user_id))


@task_failure.connect
def _mark_document_failed(sender: object = None, args: tuple = (), **_: object) -> None:
    """A worker killed mid-task (e.g. out of memory) must not leave the document 'processing'."""
    if getattr(sender, "name", "") != "documents.process" or len(args or ()) < 2:
        return
    document_id, user_id = args[0], args[1]
    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=3000)
    try:
        client[settings.mongodb_database]["documents"].update_one(
            {
                "_id": ObjectId(document_id) if ObjectId.is_valid(document_id) else document_id,
                "user_id": user_id,
                "status": "processing",
            },
            {
                "$set": {
                    "status": "failed",
                    "current_stage": "failed",
                    "processing_error": (
                        "Processing stopped unexpectedly (the worker crashed or ran out of "
                        "memory). Try processing the document again."
                    ),
                }
            },
        )
    except Exception:  # never let bookkeeping crash the worker
        logger.exception("mark_document_failed_error")
    finally:
        client.close()


async def _run(document_id: str, user_id: str) -> None:
    settings = get_settings()
    connection = MongoConnection(settings)
    try:
        context = context_from_settings(settings, connection.database)
        await process_document(context, user_id, document_id)
    finally:
        connection.close()
