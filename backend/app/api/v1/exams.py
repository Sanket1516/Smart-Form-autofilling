"""Entrance-exam requirement profiles, readiness and upload checks."""

from typing import Any

from fastapi import APIRouter, File, Request, UploadFile

from app.api.v1.auth import User
from app.core.api_errors import APIError
from app.extraction.registry import get_registry
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Exams"])
_MAX_UPLOAD_CHECK_BYTES = 10 * 1024 * 1024


@router.get("/document-types", response_model=SuccessResponse[list[dict[str, Any]]])
async def list_document_types(user: User) -> SuccessResponse[list[dict[str, Any]]]:
    """Document types the extractor recognises."""
    return SuccessResponse(data=get_registry().describe())


@router.get("/exams", response_model=SuccessResponse[list[dict[str, Any]]])
async def list_exams(request: Request, user: User) -> SuccessResponse[list[dict[str, Any]]]:
    return SuccessResponse(data=request.app.state.exam_service.list())


@router.get("/exams/{exam_id}/readiness", response_model=SuccessResponse[dict[str, Any]])
async def exam_readiness(
    request: Request, exam_id: str, user: User
) -> SuccessResponse[dict[str, Any]]:
    """What the profile supplies for this exam, what needs confirmation and what is missing."""
    return SuccessResponse(
        data=await request.app.state.exam_service.readiness(user.user_id, exam_id)
    )


@router.post(
    "/exams/{exam_id}/uploads/{upload_id}/check", response_model=SuccessResponse[dict[str, Any]]
)
async def check_exam_upload(
    request: Request, exam_id: str, upload_id: str, user: User, file: UploadFile = File(...)
) -> SuccessResponse[dict[str, Any]]:
    """Check a photo, signature or certificate against the exam's upload rules. Nothing is stored."""
    content = await file.read(_MAX_UPLOAD_CHECK_BYTES + 1)
    if len(content) > _MAX_UPLOAD_CHECK_BYTES:
        raise APIError("FILE_TOO_LARGE", "Files larger than 10 MB cannot be checked.", 413)
    return SuccessResponse(
        data=request.app.state.exam_service.check_upload(
            exam_id, upload_id, file.filename or "upload", content
        )
    )
