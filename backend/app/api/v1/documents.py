"""Authenticated document management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser
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
from app.core.rate_limit import limiter

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_fact_service(request: Request) -> FactService:
    return request.app.state.fact_service


User = Annotated[CurrentUser, Depends(get_current_user)]
Service = Annotated[DocumentService, Depends(get_document_service)]
FactServiceDependency = Annotated[FactService, Depends(get_fact_service)]


@router.get("/{document_id}/facts", response_model=SuccessResponse[FactsData])
async def document_facts(
    user: User, service: FactServiceDependency, document_id: str
) -> SuccessResponse[FactsData]:
    return SuccessResponse(data=await service.list_for_document(user.user_id, document_id))


@router.post("", response_model=SuccessResponse[DocumentData], status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_document(
    request: Request, user: User, service: Service, file: Annotated[UploadFile, File()]
) -> SuccessResponse[DocumentData]:
    return SuccessResponse(
        data=await service.upload(user.user_id, file), message="Document uploaded successfully"
    )


@router.get("", response_model=SuccessResponse[DocumentListData])
async def list_documents(
    user: User,
    service: Service,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    document_type: str | None = None,
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
        data=await service.start_processing(user.user_id, document_id),
        message="Document processing started",
    )


@router.get("/{document_id}/status", response_model=SuccessResponse[ProcessingStatusData])
async def document_status(
    user: User, service: Service, document_id: str
) -> SuccessResponse[ProcessingStatusData]:
    return SuccessResponse(data=await service.status(user.user_id, document_id))


@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(user: User, service: Service, document_id: str) -> MessageResponse:
    await service.delete(user.user_id, document_id)
    return MessageResponse(message="Document deleted successfully")


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
        data=await service.reprocess(user.user_id, document_id),
        message="Document processing started",
    )
