"""Authenticated document lifecycle: upload, processing dispatch, status, deletion."""

from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pymongo.errors import DuplicateKeyError

from app.core.api_errors import APIError
from app.core.config import Settings
from app.db.chroma_client import ChromaClient, VectorStoreError
from app.models.documents import DocumentRecord
from app.repositories.collections import (
    DiscoveredFactsRepository,
    DocumentsRepository,
    ProcessingRecordsRepository,
    StructuredFactsRepository,
)
from app.schemas.documents import DocumentData, DocumentListData, ProcessingStatusData
from app.storage.base import DocumentStorage

logger = logging.getLogger(__name__)

# Extension -> canonical MIME type. The browser-supplied content type is not
# trusted; the file content is verified instead.
SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_GENERIC_CONTENT_TYPES = {"", "application/octet-stream", "binary/octet-stream"}

Dispatcher = Callable[[str, str], None]


class DocumentService:
    def __init__(
        self,
        repository: DocumentsRepository,
        storage: DocumentStorage,
        settings: Settings,
        *,
        facts: StructuredFactsRepository,
        discovered: DiscoveredFactsRepository,
        stages: ProcessingRecordsRepository,
        vector_store: ChromaClient,
        recommendations: Any,
        dispatcher: Dispatcher | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.settings = settings
        self.facts = facts
        self.discovered = discovered
        self.stages = stages
        self.vector_store = vector_store
        self.recommendations = recommendations
        self.dispatcher = dispatcher

    # ------------------------------------------------------------------ upload

    async def upload(self, user_id: str, file: UploadFile) -> DocumentData:
        filename = Path(file.filename or "").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_TYPES:
            raise APIError(
                "INVALID_FILE",
                "Unsupported file type. Upload a PDF, DOCX, TXT, PNG or JPG file.",
                400,
            )
        declared = (file.content_type or "").split(";")[0].strip().lower()
        if declared not in _GENERIC_CONTENT_TYPES and declared != SUPPORTED_TYPES[suffix]:
            raise APIError("INVALID_FILE", "The file type does not match its extension.", 400)
        limit = self.settings.max_upload_size_mb * 1024 * 1024
        chunks: list[bytes] = []
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise APIError(
                    "FILE_TOO_LARGE",
                    f"File exceeds the {self.settings.max_upload_size_mb} MB limit",
                    413,
                )
            chunks.append(chunk)
        content = b"".join(chunks)
        if not content:
            raise APIError("INVALID_FILE", "The file is empty.", 400)
        if not content_matches(suffix, content):
            raise APIError("INVALID_FILE", "The file content does not match its type.", 400)
        checksum = hashlib.sha256(content).hexdigest()
        if await self.repository.find_by_checksum(user_id, checksum):
            raise APIError("DUPLICATE_DOCUMENT", "This document has already been uploaded.", 409)

        storage_reference, _ = await self.storage.save(filename, [content])
        document = DocumentRecord(
            user_id=user_id,
            file_name=filename,
            file_type=SUPPORTED_TYPES[suffix],
            file_size=total,
            storage_reference=storage_reference,
            status="uploaded",
            uploaded_at=datetime.now(UTC),
            checksum=checksum,
        )
        try:
            created = await self.repository.create(user_id, document)
        except DuplicateKeyError as error:
            await self.storage.delete(storage_reference)
            raise APIError(
                "DUPLICATE_DOCUMENT", "This document has already been uploaded.", 409
            ) from error
        document_id = str(created["_id"])
        try:
            await self.start_processing(user_id, document_id)
        except APIError as error:
            logger.warning(
                "auto_start_processing_failed",
                extra={"document_id": document_id, "code": error.code},
            )
        return await self.get(user_id, document_id)

    # ------------------------------------------------------------------ reads

    async def list(
        self, user_id: str, status: str | None, document_type: str | None, page: int, limit: int
    ) -> DocumentListData:
        filters: dict[str, Any] = {"status": status if status else {"$ne": "deleted"}}
        if document_type:
            filters["document_type"] = document_type
        total = await self.repository.count(user_id, filters)
        records = await self.repository.list_page(user_id, filters, (page - 1) * limit, limit)
        return DocumentListData(
            documents=[document_data(record) for record in records],
            page=page,
            limit=limit,
            total=total,
        )

    async def get(self, user_id: str, document_id: str) -> DocumentData:
        return document_data(await self._get(user_id, document_id))

    async def status(self, user_id: str, document_id: str) -> ProcessingStatusData:
        record = await self._get(user_id, document_id)
        return ProcessingStatusData(
            document_id=document_id,
            status=record["status"],
            current_stage=record.get("current_stage"),
            progress=record.get("progress", 0),
            error=record.get("processing_error"),
            warnings=record.get("warnings", []),
            fact_count=record.get("fact_count", 0),
            index_status=record.get("index_status", "pending"),
            index_error=record.get("index_error"),
        )

    async def get_file_content(self, user_id: str, document_id: str) -> tuple[bytes, str, str]:
        record = await self._get(user_id, document_id)
        content = await self.storage.read_bytes(record["storage_reference"])
        return content, record["file_name"], record.get("file_type") or "application/octet-stream"

    # ------------------------------------------------------------------ processing

    async def start_processing(self, user_id: str, document_id: str) -> dict[str, str]:
        record = await self._get(user_id, document_id)
        if record["status"] == "processing":
            started = record.get("processing_started_at")
            if started is not None and started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            stale_after = timedelta(minutes=self.settings.processing_stale_after_minutes)
            if started is not None and datetime.now(UTC) - started < stale_after:
                raise APIError(
                    "ALREADY_PROCESSING", "This document is already being processed.", 409
                )
        await self.repository.update(
            user_id,
            document_id,
            {
                "status": "processing",
                "current_stage": "queued",
                "progress": 0,
                "processing_started_at": datetime.now(UTC),
                "processing_error": None,
                "warnings": [],
            },
        )
        try:
            self._dispatch(user_id, document_id)
        except Exception as error:
            logger.error("processing_dispatch_failed", extra={"document_id": document_id})
            await self.repository.update(
                user_id,
                document_id,
                {
                    "status": "failed",
                    "current_stage": "failed",
                    "processing_error": "The processing queue is unavailable. Try again later.",
                },
            )
            raise APIError(
                "PROCESSING_UNAVAILABLE", "The processing queue is unavailable.", 503
            ) from error
        return {"document_id": document_id, "processing_status": "processing"}

    def _dispatch(self, user_id: str, document_id: str) -> None:
        if self.settings.processing_mode == "celery":
            from app.tasks.documents import process_document_task

            process_document_task.delay(document_id, user_id)
            return
        if self.dispatcher is None:
            raise RuntimeError("inline processing dispatcher is not configured")
        self.dispatcher(user_id, document_id)

    # ------------------------------------------------------------------ deletion

    async def delete(self, user_id: str, document_id: str) -> None:
        """Delete a document and everything derived from it.

        Vectors are removed first: if the vector store is unreachable the delete
        is refused, so no orphaned chunks can remain searchable.
        """
        record = await self._get(user_id, document_id)
        if record.get("index_status") == "indexed" or record.get("chunk_count", 0):
            try:
                await self.vector_store.delete_document_chunks(user_id, document_id)
            except VectorStoreError as error:
                raise APIError(
                    "VECTOR_STORE_UNAVAILABLE",
                    "The document index is unavailable, so the document was not deleted. Try again later.",
                    503,
                ) from error
        else:
            try:
                await self.vector_store.delete_document_chunks(user_id, document_id)
            except VectorStoreError:
                logger.info("vector_cleanup_skipped", extra={"document_id": document_id})
        await self.facts.delete_for_document(user_id, document_id)
        await self.discovered.delete_for_document(user_id, document_id)
        await self.stages.delete_for_document(user_id, document_id)
        await self.recommendations.delete_for_document(user_id, document_id)
        if record.get("normalized_reference"):
            await self._delete_object(record["normalized_reference"])
        await self._delete_object(record["storage_reference"])
        await self.repository.delete(user_id, document_id)

    async def _delete_object(self, reference: str) -> None:
        try:
            await self.storage.delete(reference)
        except Exception:
            logger.warning("storage_delete_failed", extra={"reference_suffix": reference[-12:]})

    async def _get(self, user_id: str, document_id: str) -> dict[str, Any]:
        record = await self.repository.get(user_id, document_id)
        if record is None or record.get("status") == "deleted":
            raise APIError("RESOURCE_NOT_FOUND", "Document not found", 404)
        return record


def content_matches(suffix: str, content: bytes) -> bool:
    """Verify the file content really is the type its extension claims."""
    if suffix == ".pdf":
        return content.lstrip()[:5] == b"%PDF-"
    if suffix == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in (".jpg", ".jpeg"):
        return content.startswith(b"\xff\xd8\xff")
    if suffix == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            return False
        return "word/document.xml" in names and "[Content_Types].xml" in names
    if suffix == ".txt":
        if b"\x00" in content:
            return False
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return False
        return True
    return False


def document_data(record: dict[str, Any]) -> DocumentData:
    return DocumentData(
        document_id=str(record["_id"]),
        file_name=record["file_name"],
        file_type=record["file_type"],
        file_size=record.get("file_size", 0),
        document_type=record.get("document_type"),
        document_type_confidence=record.get("document_type_confidence"),
        status=record["status"],
        current_stage=record.get("current_stage"),
        progress=record.get("progress", 0),
        processing_error=record.get("processing_error"),
        warnings=record.get("warnings", []),
        uploaded_at=record["uploaded_at"],
        processed_at=record.get("processed_at"),
        page_count=record.get("page_count"),
        fact_count=record.get("fact_count", 0),
        index_status=record.get("index_status", "pending"),
        chunk_count=record.get("chunk_count", 0),
        index_error=record.get("index_error"),
    )
