"""Structured candidate fact persistence and presentation."""

from typing import Any

from app.core.api_errors import APIError
from app.repositories.collections import StructuredFactsRepository
from app.schemas.facts import FactData, FactsData, FactUpdateRequest


class FactService:
    def __init__(self, repository: StructuredFactsRepository) -> None:
        self.repository = repository

    async def list(
        self,
        user_id: str,
        concept: str | None = None,
        source_document_id: str | None = None,
        confirmed: bool | None = None,
    ) -> FactsData:
        records = await self.repository.list_filtered(
            user_id, concept, source_document_id, confirmed
        )
        return FactsData(facts=[self._data(record) for record in records])

    async def list_for_document(self, user_id: str, document_id: str) -> FactsData:
        records = await self.repository.list_for_document(user_id, document_id)
        return FactsData(facts=[self._data(record) for record in records])

    async def update(self, user_id: str, fact_id: str, request: FactUpdateRequest) -> FactData:
        record = await self.repository.get(user_id, fact_id)
        if record is None:
            raise APIError("RESOURCE_NOT_FOUND", "Fact not found", 404)
        await self.repository.update(
            user_id,
            fact_id,
            {"value": request.value, "is_user_confirmed": request.is_user_confirmed},
        )
        updated = await self.repository.get(user_id, fact_id)
        if updated is None:
            raise APIError("RESOURCE_NOT_FOUND", "Fact not found", 404)
        return self._data(updated)

    @staticmethod
    def _data(record: dict[str, Any]) -> FactData:
        return FactData(
            fact_id=str(record["_id"]),
            concept=record["concept"],
            value=record["value"],
            value_type=record["value_type"],
            source_document_id=record["source_document_id"],
            source_page=record["source_page"],
            confidence=record["confidence"],
            provenance=record.get("provenance", {}),
            is_user_confirmed=record["is_user_confirmed"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )
