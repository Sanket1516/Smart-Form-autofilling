"""Corrections service for history and audit logging of manual edits."""

from datetime import UTC, datetime
from typing import Any

from app.models.documents import Correction
from app.repositories.collections import CorrectionsRepository
from app.schemas.profile import CorrectionCreateRequest, CorrectionData, CorrectionsListData


class CorrectionsService:
    def __init__(self, repository: CorrectionsRepository) -> None:
        self.repository = repository

    async def record_correction(
        self, user_id: str, request: CorrectionCreateRequest
    ) -> CorrectionData:
        correction = Correction(
            user_id=user_id,
            session_id=request.session_id,
            field_id=request.field_id,
            concept=request.concept,
            original_value=request.original_value,
            corrected_value=request.corrected_value,
            reason=request.reason,
            created_at=datetime.now(UTC),
        )
        saved = await self.repository.create(user_id, correction)
        return self._data(saved)

    async def list_corrections(
        self, user_id: str, concept: str | None = None
    ) -> CorrectionsListData:
        filters = {"concept": concept} if concept else None
        records = await self.repository.list(user_id, filters)
        return CorrectionsListData(corrections=[self._data(rec) for rec in records])

    @staticmethod
    def _data(record: dict[str, Any]) -> CorrectionData:
        return CorrectionData(
            correction_id=str(record["_id"]),
            user_id=record["user_id"],
            session_id=record.get("session_id"),
            field_id=record.get("field_id"),
            concept=record["concept"],
            original_value=record.get("original_value"),
            corrected_value=record.get("corrected_value"),
            reason=record["reason"],
            created_at=record["created_at"],
        )
