"""Document upload and lifecycle tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from app.core.api_errors import APIError
from app.core.config import Settings
from app.services.documents import DocumentService
from app.storage.local import LocalFileStorage
from starlette.datastructures import Headers, UploadFile


class FakeDocuments:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.next_id = 1

    async def find_by_checksum(self, user_id: str, checksum: str) -> dict | None:
        return next(
            (
                record
                for record in self.records.values()
                if record["user_id"] == user_id and record["checksum"] == checksum
            ),
            None,
        )

    async def create(self, user_id: str, document: Any) -> dict[str, Any]:
        document_id = f"document-{self.next_id}"
        self.next_id += 1
        record = {"_id": document_id, **document.model_dump(exclude_none=True)}
        self.records[document_id] = record
        return record

    async def get(self, user_id: str, document_id: str) -> dict | None:
        record = self.records.get(document_id)
        return record if record and record["user_id"] == user_id else None

    async def update(self, user_id: str, document_id: str, updates: dict[str, Any]) -> bool:
        record = await self.get(user_id, document_id)
        if record is None:
            return False
        record.update(updates)
        return True

    async def count(self, user_id: str, filters: dict | None = None) -> int:
        return len(await self.list_page(user_id, filters, 0, 100))

    async def list_page(
        self, user_id: str, filters: dict | None, skip: int, limit: int
    ) -> list[dict]:
        records = [record for record in self.records.values() if record["user_id"] == user_id]
        for key, value in (filters or {}).items():
            if isinstance(value, dict) and "$ne" in value:
                records = [record for record in records if record.get(key) != value["$ne"]]
            else:
                records = [record for record in records if record.get(key) == value]
        return records[skip : skip + limit]


async def make_upload(name: str, content_type: str, content: bytes) -> UploadFile:
    from io import BytesIO

    return UploadFile(
        BytesIO(content), filename=name, headers=Headers({"content-type": content_type})
    )


@pytest.fixture
def document_service() -> tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]]:
    temporary = TemporaryDirectory()
    repository = FakeDocuments()
    settings = Settings(max_upload_size_mb=1, storage_root=temporary.name)
    return (
        DocumentService(repository, LocalFileStorage(temporary.name), settings),
        repository,
        temporary,
    )


@pytest.mark.asyncio
async def test_upload_validates_and_stores_pdf(
    document_service: tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]],
) -> None:
    service, repository, temporary = document_service
    file = await make_upload("resume.pdf", "application/pdf", b"%PDF-1.7 test")
    result = await service.upload("user-a", file)
    assert result.status == "uploaded"
    assert repository.records["document-1"]["checksum"]
    assert list(Path(temporary.name).rglob("resume.pdf"))
    temporary.cleanup()


@pytest.mark.asyncio
async def test_duplicate_upload_is_rejected(
    document_service: tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]],
) -> None:
    service, _, temporary = document_service
    content = b"%PDF-1.7 duplicate"
    await service.upload("user-a", await make_upload("a.pdf", "application/pdf", content))
    with pytest.raises(APIError) as error:
        await service.upload("user-a", await make_upload("b.pdf", "application/pdf", content))
    assert error.value.code == "DUPLICATE_DOCUMENT"
    temporary.cleanup()


@pytest.mark.asyncio
async def test_invalid_file_and_size_are_rejected(
    document_service: tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]],
) -> None:
    service, _, temporary = document_service
    with pytest.raises(APIError) as invalid:
        await service.upload("user-a", await make_upload("bad.pdf", "application/pdf", b"not pdf"))
    assert invalid.value.code == "INVALID_FILE"
    with pytest.raises(APIError) as oversized:
        await service.upload(
            "user-a", await make_upload("large.txt", "text/plain", b"x" * (1024 * 1024 + 1))
        )
    assert oversized.value.code == "FILE_TOO_LARGE"
    temporary.cleanup()


@pytest.mark.asyncio
async def test_status_and_delete_are_user_scoped(
    document_service: tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]],
) -> None:
    service, _, temporary = document_service
    result = await service.upload(
        "user-a", await make_upload("a.pdf", "application/pdf", b"%PDF-1.7 test")
    )
    with pytest.raises(APIError) as missing:
        await service.get("user-b", result.document_id)
    assert missing.value.code == "RESOURCE_NOT_FOUND"
    await service.delete("user-a", result.document_id)
    assert (await service.status("user-a", result.document_id)).status == "deleted"
    temporary.cleanup()


@pytest.mark.asyncio
async def test_list_omits_soft_deleted_documents(
    document_service: tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]],
) -> None:
    service, _, temporary = document_service
    document = await service.upload(
        "user-a", await make_upload("a.pdf", "application/pdf", b"%PDF-1.7 test")
    )
    await service.delete("user-a", document.document_id)

    result = await service.list("user-a", None, None, 1, 20)

    assert result.documents == []
    assert result.total == 0
    temporary.cleanup()


@pytest.mark.asyncio
async def test_deleted_document_can_be_uploaded_again(
    document_service: tuple[DocumentService, FakeDocuments, TemporaryDirectory[str]],
) -> None:
    service, _, temporary = document_service
    content = b"%PDF-1.7 reusable file"
    document = await service.upload("user-a", await make_upload("a.pdf", "application/pdf", content))
    await service.delete("user-a", document.document_id)

    replacement = await service.upload("user-a", await make_upload("a.pdf", "application/pdf", content))

    assert replacement.document_id != document.document_id
    assert replacement.status == "uploaded"
    temporary.cleanup()
