"""Authenticated document lifecycle service."""

import hashlib
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pymongo.errors import DuplicateKeyError

from app.core.api_errors import APIError
from app.core.config import Settings
from app.repositories.collections import DocumentsRepository
from app.schemas.documents import DocumentData, DocumentListData, ProcessingStatusData
from app.storage.local import LocalFileStorage
from app.tasks.documents import process_document

SUPPORTED_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".txt": {"text/plain"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
}
MAGIC = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".txt": (),
    ".docx": (b"PK\x03\x04",),
}


class DocumentService:
    def __init__(
        self, repository: DocumentsRepository, storage: LocalFileStorage, settings: Settings
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings

    async def upload(self, user_id: str, file: UploadFile) -> DocumentData:
        filename = Path(file.filename or "").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_TYPES or file.content_type not in SUPPORTED_TYPES[suffix]:
            raise APIError("INVALID_FILE", "Unsupported or invalid file", 400)
        chunks: list[bytes] = []
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > self.settings.max_upload_size_mb * 1024 * 1024:
                raise APIError("FILE_TOO_LARGE", "File exceeds the upload limit", 413)
            chunks.append(chunk)
        if not chunks or not self._integrity_ok(suffix, b"".join(chunks)):
            raise APIError("INVALID_FILE", "File integrity validation failed", 400)
        checksum = hashlib.sha256(b"".join(chunks)).hexdigest()
        if await self.repository.find_by_checksum(user_id, checksum):
            raise APIError("DUPLICATE_DOCUMENT", "Document has already been uploaded", 409)
        storage_reference, _ = await self.storage.save(filename, chunks)
        from datetime import UTC, datetime

        from app.models.documents import DocumentRecord

        document = DocumentRecord(
            user_id=user_id,
            file_name=filename,
            file_type=file.content_type or "application/octet-stream",
            file_size=total,
            storage_reference=storage_reference,
            document_type=self._document_type(filename),
            status="uploaded",
            uploaded_at=datetime.now(UTC),
            checksum=checksum,
        )
        try:
            created = await self.repository.create(user_id, document)
        except DuplicateKeyError as error:
            await self.storage.delete(storage_reference)
            raise APIError(
                "DUPLICATE_DOCUMENT", "Document has already been uploaded", 409
            ) from error
        return self._data(created)

    async def list(
        self, user_id: str, status: str | None, document_type: str | None, page: int, limit: int
    ) -> DocumentListData:
        filters = {
            key: value
            for key, value in {"status": status, "document_type": document_type}.items()
            if value
        }
        total = await self.repository.count(user_id, filters)
        records = await self.repository.list_page(user_id, filters, (page - 1) * limit, limit)
        return DocumentListData(
            documents=[self._data(record) for record in records],
            page=page,
            limit=limit,
            total=total,
        )

    async def get(self, user_id: str, document_id: str) -> DocumentData:
        record = await self.repository.get(user_id, document_id)
        if record is None or record.get("status") == "deleted":
            raise APIError("RESOURCE_NOT_FOUND", "Document not found", 404)
        return self._data(record)

    async def start_processing(self, user_id: str, document_id: str) -> dict[str, str]:
        record = await self.repository.get(user_id, document_id)
        if record is None or record.get("status") == "deleted":
            raise APIError("RESOURCE_NOT_FOUND", "Document not found", 404)
        await self.repository.update(
            user_id, document_id, {"status": "processing", "current_stage": "queued", "progress": 0}
        )
        if self.settings.celery_task_always_eager:
            process_document.apply(args=[document_id, user_id])
        else:
            process_document.delay(document_id, user_id)
        return {"document_id": document_id, "processing_status": "processing"}

    async def status(self, user_id: str, document_id: str) -> ProcessingStatusData:
        record = await self.repository.get(user_id, document_id)
        if record is None:
            raise APIError("RESOURCE_NOT_FOUND", "Document not found", 404)
        return ProcessingStatusData(
            document_id=document_id,
            status=record["status"],
            current_stage=record.get("current_stage"),
            progress=record.get("progress", 0),
            error=record.get("processing_error"),
        )

    async def delete(self, user_id: str, document_id: str) -> None:
        record = await self.repository.get(user_id, document_id)
        if record is None or record.get("status") == "deleted":
            raise APIError("RESOURCE_NOT_FOUND", "Document not found", 404)
        await self.storage.delete(record["storage_reference"])
        await self.repository.update(
            user_id, document_id, {"status": "deleted", "current_stage": "deleted", "progress": 100}
        )

    async def reprocess(self, user_id: str, document_id: str) -> dict[str, str]:
        return await self.start_processing(user_id, document_id)

    @staticmethod
    def _integrity_ok(suffix: str, content: bytes) -> bool:
        return suffix == ".txt" or any(content.startswith(magic) for magic in MAGIC[suffix])

    @staticmethod
    def _document_type(filename: str) -> str:
        stem = Path(filename).stem.lower()
        return "resume" if "resume" in stem else "unknown"

    @staticmethod
    def _data(record: dict[str, Any]) -> DocumentData:
        return DocumentData(
            document_id=str(record["_id"]),
            file_name=record["file_name"],
            file_type=record["file_type"],
            document_type=record.get("document_type"),
            status=record["status"],
            uploaded_at=record["uploaded_at"],
            processed_at=record.get("processed_at"),
            page_count=record.get("page_count"),
        )
