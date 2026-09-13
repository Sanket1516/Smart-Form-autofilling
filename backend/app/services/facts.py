"""Structured candidate fact persistence and presentation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.api_errors import APIError
from app.models.documents import Correction
from app.repositories.collections import CorrectionsRepository, StructuredFactsRepository
from app.schemas.facts import FactData, FactsData, FactUpdateRequest


class FactService:
    def __init__(
        self,
        repository: StructuredFactsRepository,
        corrections_repository: CorrectionsRepository | None = None,
    ) -> None:
        self.repository = repository
        self.corrections_repository = corrections_repository

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
        deduped = self._deduplicate_facts(records)
        return FactsData(facts=[self._data(record) for record in deduped])

    async def list_for_document(self, user_id: str, document_id: str) -> FactsData:
        records = await self.repository.list_for_document(user_id, document_id)
        deduped = self._deduplicate_facts(records)
        return FactsData(facts=[self._data(record) for record in deduped])

    @staticmethod
    def _deduplicate_facts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        SINGLETON_PREFIXES = (
            "personal.",
            "identity.",
            "contact.",
            "demographics.",
            "address.",
            "passport.",
            "visa.",
        )
        grouped: dict[str, dict[str, Any]] = {}
        for r in records:
            c = r.get("concept", "")
            v = str(r.get("value", "") or "").strip().lower()

            if any(c.startswith(prefix) for prefix in SINGLETON_PREFIXES):
                key = f"singleton:{c}"
            else:
                key = f"multi:{c}:{v}"

            existing = grouped.get(key)
            if existing is None:
                grouped[key] = r
            else:
                cur_confirmed = existing.get("is_user_confirmed", False)
                new_confirmed = r.get("is_user_confirmed", False)
                if new_confirmed and not cur_confirmed:
                    grouped[key] = r
                elif new_confirmed == cur_confirmed:
                    cur_conf = existing.get("confidence", 0.0)
                    new_conf = r.get("confidence", 0.0)
                    if new_conf > cur_conf:
                        grouped[key] = r
                    elif new_conf == cur_conf:
                        if str(r.get("updated_at", "")) > str(existing.get("updated_at", "")):
                            grouped[key] = r
        return list(grouped.values())

    async def update(self, user_id: str, fact_id: str, request: FactUpdateRequest) -> FactData:
        record = await self.repository.get(user_id, fact_id)
        if record is None:
            raise APIError("RESOURCE_NOT_FOUND", "Fact not found", 404)

        if self.corrections_repository is not None and record["value"] != request.value:
            correction = Correction(
                user_id=user_id,
                session_id=None,
                field_id=fact_id,
                concept=record["concept"],
                original_value=record["value"],
                corrected_value=request.value,
                reason=request.reason or "User fact edit",
                created_at=datetime.now(UTC),
            )
            await self.corrections_repository.create(user_id, correction)

        now = datetime.now(UTC)
        await self.repository.update(
            user_id,
            fact_id,
            {
                "value": request.value,
                "is_user_confirmed": request.is_user_confirmed,
                "updated_at": now,
            },
        )
        updated = await self.repository.get(user_id, fact_id)
        if updated is None:
            raise APIError("RESOURCE_NOT_FOUND", "Fact not found", 404)
        return self._data(updated)

    @staticmethod
    def _data(record: dict[str, Any]) -> FactData:
        doc_id = record["source_document_id"]
        page = record["source_page"]
        return FactData(
            fact_id=str(record["_id"]),
            concept=record["concept"],
            value=record["value"],
            value_type=record["value_type"],
            source_document_id=doc_id,
            source_page=page,
            confidence=record["confidence"],
            provenance=record.get("provenance", {}),
            is_user_confirmed=record["is_user_confirmed"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            source={"document_id": doc_id, "page": page},
        )
