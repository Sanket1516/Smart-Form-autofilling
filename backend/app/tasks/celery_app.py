"""Celery application (only imported when PROCESSING_MODE=celery)."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "smart_form_documents",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.documents"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
