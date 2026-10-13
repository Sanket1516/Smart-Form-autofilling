"""Authenticated document management endpoints."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import Response

from app.api.v1.auth import User
from app.core.api_errors import APIError
from app.core.rate_limit import limiter
from app.schemas.documents import (
    DocumentData,
    DocumentListData,
    ProcessingData,
    ProcessingStatusData,
)
from app.schemas.facts import FactsData
from app.schemas.responses import MessageResponse, SuccessResponse
from app.services.documents import DocumentService
from app.services.facts import FactService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_fact_service(request: Request) -> FactService:
    return request.app.state.fact_service


Service = Annotated[DocumentService, Depends(get_document_service)]
Facts = Annotated[FactService, Depends(get_fact_service)]


@router.post("", response_model=SuccessResponse[DocumentData], status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_document(
    request: Request, user: User, service: Service, file: Annotated[UploadFile, File()]
) -> SuccessResponse[DocumentData]:
    limit = service.settings.max_upload_size_mb * 1024 * 1024
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit + 64 * 1024:
        raise APIError(
            "FILE_TOO_LARGE",
            f"File exceeds the {service.settings.max_upload_size_mb} MB limit",
            413,
        )
    return SuccessResponse(
        data=await service.upload(user.user_id, file), message="Document uploaded"
    )


@router.get("", response_model=SuccessResponse[DocumentListData])
async def list_documents(
    user: User,
    service: Service,
    status_filter: Annotated[str | None, Query(alias="status", max_length=30)] = None,
    document_type: Annotated[str | None, Query(max_length=60)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SuccessResponse[DocumentListData]:
    return SuccessResponse(
        data=await service.list(user.user_id, status_filter, document_type, page, limit)
    )


@router.get("/{document_id}", response_model=SuccessResponse[DocumentData])
async def get_document(
    user: User, service: Service, document_id: str
) -> SuccessResponse[DocumentData]:
    return SuccessResponse(data=await service.get(user.user_id, document_id))


@router.get("/{document_id}/status", response_model=SuccessResponse[ProcessingStatusData])
async def document_status(
    user: User, service: Service, document_id: str
) -> SuccessResponse[ProcessingStatusData]:
    return SuccessResponse(data=await service.status(user.user_id, document_id))


@router.get("/{document_id}/facts", response_model=SuccessResponse[FactsData])
async def document_facts(
    user: User, service: Service, facts: Facts, document_id: str
) -> SuccessResponse[FactsData]:
    await service.get(user.user_id, document_id)  # 404 for unknown or foreign documents
    return SuccessResponse(data=await facts.list_for_document(user.user_id, document_id))


@router.post(
    "/{document_id}/process",
    response_model=SuccessResponse[ProcessingData],
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def process_document(
    request: Request, user: User, service: Service, document_id: str
) -> SuccessResponse[ProcessingData]:
    return SuccessResponse(
        data=await service.start_processing(user.user_id, document_id), message="Processing started"
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=SuccessResponse[ProcessingData],
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def reprocess_document(
    request: Request, user: User, service: Service, document_id: str
) -> SuccessResponse[ProcessingData]:
    return SuccessResponse(
        data=await service.start_processing(user.user_id, document_id), message="Processing started"
    )


@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(user: User, service: Service, document_id: str) -> MessageResponse:
    await service.delete(user.user_id, document_id)
    return MessageResponse(message="Document and its extracted data were deleted")


def _disposition(kind: str, file_name: str) -> str:
    ascii_name = "".join(
        ch if ch.isascii() and ch.isprintable() and ch not in '"\\;' else "_" for ch in file_name
    )
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name)}"


@router.get("/{document_id}/download")
async def download_document_file(user: User, service: Service, document_id: str) -> Response:
    content, file_name, file_type = await service.get_file_content(user.user_id, document_id)
    return Response(
        content=content,
        media_type=file_type,
        headers={
            "Content-Disposition": _disposition("attachment", file_name),
            "Cache-Control": "no-store",
        },
    )


@router.get("/{document_id}/preview")
async def preview_document_file(user: User, service: Service, document_id: str) -> Response:
    content, file_name, file_type = await service.get_file_content(user.user_id, document_id)
    return Response(
        content=content,
        media_type=file_type,
        headers={
            "Content-Disposition": _disposition("inline", file_name),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        },
    )
