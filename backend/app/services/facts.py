"""Structured facts: listing, review, conflicts and the resolved profile view.

Facts are stored per source (one record per document value, plus user-provided
records). This service computes, from the *active* facts:

* the resolved value of each concept (``resolve_view``),
* conflicts: a single-valued concept with two or more distinct values,
* resolution: confirming one candidate supersedes the others; a custom value
  becomes a user-provided fact; rejecting marks every candidate rejected.

Because conflicts are computed rather than stored, deleting or re-processing a
document can never leave a stale conflict behind.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.core.api_errors import APIError
from app.extraction.normalize import comparison_key, normalize_value, same_address
from app.extraction.registry import get_registry
from app.models.documents import Correction, StructuredFact
from app.ontology.loader import FieldOntology
from app.repositories.collections import CorrectionsRepository, StructuredFactsRepository
from app.schemas.facts import (
    ConceptView,
    ConflictCandidate,
    ConflictData,
    ConflictResolutionRequest,
    FactData,
    FactsData,
    FactSource,
    FactUpdateRequest,
)

USER_SOURCE = "user"


class FactService:
    def __init__(
        self,
        repository: StructuredFactsRepository,
        ontology: FieldOntology,
        corrections_repository: CorrectionsRepository | None = None,
    ) -> None:
        self.repository = repository
        self.ontology = ontology
        self.corrections_repository = corrections_repository

    # ------------------------------------------------------------------ listing

    async def list(
        self,
        user_id: str,
        concept: str | None = None,
        source_document_id: str | None = None,
        confirmed: bool | None = None,
    ) -> FactsData:
        records = await self.repository.list_active(user_id, concept)
        if source_document_id:
            records = [r for r in records if r.get("source_document_id") == source_document_id]
        if confirmed is not None:
            records = [r for r in records if bool(r.get("is_user_confirmed")) == confirmed]
        return FactsData(facts=[fact_data(record) for record in records])

    async def list_for_document(self, user_id: str, document_id: str) -> FactsData:
        records = await self.repository.list_for_document(user_id, document_id)
        records = [r for r in records if r.get("status", "active") == "active"]
        return FactsData(facts=[fact_data(record) for record in records])

    # ------------------------------------------------------------------ edits

    async def update(self, user_id: str, fact_id: str, request: FactUpdateRequest) -> FactData:
        record = await self._get(user_id, fact_id)
        concept = record["concept"]
        data_type = self.ontology.data_type(concept)
        new_value, _ = normalize_value(data_type, request.value)
        if new_value in (None, ""):
            raise APIError("INVALID_VALUE", "A value is required", 422)
        same = comparison_key(data_type, new_value) == comparison_key(
            data_type, record.get("value")
        )
        now = datetime.now(UTC)
        if same:
            await self.repository.update(
                user_id,
                fact_id,
                {"is_user_confirmed": request.is_user_confirmed, "updated_at": now},
            )
            if request.is_user_confirmed:
                await self._supersede_others(
                    user_id, concept, keep_key=comparison_key(data_type, new_value)
                )
            return fact_data(await self._get(user_id, fact_id))
        await self._record_correction(
            user_id, concept, record.get("value"), new_value, request.reason
        )
        created = await self.add_user_fact(user_id, concept, new_value)
        await self.repository.set_status(user_id, [record["_id"]], "superseded")
        return created

    async def add_user_fact(self, user_id: str, concept: str, value: Any) -> FactData:
        if not self.ontology.is_known(concept):
            raise APIError("UNKNOWN_CONCEPT", f"Unknown concept: {concept}", 422)
        if self.ontology.is_abstract(concept):
            raise APIError(
                "AMBIGUOUS_CONCEPT",
                f"{concept} needs context; use a specific field (e.g. the Class 12 value)",
                422,
            )
        data_type = self.ontology.data_type(concept)
        normalized, _ = normalize_value(data_type, value)
        if normalized in (None, ""):
            raise APIError("INVALID_VALUE", "A value is required", 422)
        now = datetime.now(UTC)
        fact = StructuredFact(
            user_id=user_id,
            concept=concept,
            value=normalized,
            raw_value=value,
            value_type=data_type,
            origin="user_provided",
            source_document_id=USER_SOURCE,
            document_name="Entered by you",
            extraction_method="user",
            confidence=1.0,
            is_user_confirmed=True,
            created_at=now,
            updated_at=now,
        )
        created = await self.repository.create(user_id, fact)
        if self.ontology.is_single_valued(concept):
            await self._supersede_others(
                user_id,
                concept,
                keep_key=comparison_key(data_type, normalized),
                keep_id=created["_id"],
            )
        return fact_data(created)

    async def delete(self, user_id: str, fact_id: str) -> None:
        record = await self._get(user_id, fact_id)
        if record.get("source_document_id") == USER_SOURCE:
            await self.repository.delete(user_id, fact_id)
        else:
            await self.repository.set_status(user_id, [record["_id"]], "rejected")

    # ------------------------------------------------------------------ resolved view

    async def resolve_view(
        self, user_id: str, document_ids: list[str] | None = None
    ) -> dict[str, ConceptView]:
        """Resolved value per concept; ``document_ids`` limits it to those documents'
        facts (values the user entered are always included)."""
        records = await self.repository.list_active(user_id)
        if document_ids is not None:
            allowed = set(document_ids) | {USER_SOURCE}
            records = [r for r in records if str(r.get("source_document_id")) in allowed]
        by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if record.get("value") not in (None, ""):
                by_concept[record["concept"]].append(record)
        return {concept: self._view(concept, items) for concept, items in by_concept.items()}

    def _view(self, concept: str, records: list[dict[str, Any]]) -> ConceptView:
        data_type = self.ontology.data_type(concept)
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            groups[comparison_key(data_type, record["value"])].append(record)
        merged_groups = (
            _merge_addresses(list(groups.values()))
            if data_type == "address"
            else list(groups.values())
        )
        candidates = [_candidate(items) for items in merged_groups]
        candidates.sort(key=lambda c: (c.is_user_confirmed, c.confidence), reverse=True)
        label = self.ontology.description(concept)
        if len(candidates) == 1:
            best = candidates[0]
            return ConceptView(
                concept=concept,
                label=label,
                status="resolved",
                value=best.value,
                values=[best.value],
                confidence=best.confidence,
                is_user_confirmed=best.is_user_confirmed,
                origin=_best_origin(best.sources),
                sources=best.sources,
                candidates=candidates,
            )
        if not self.ontology.is_single_valued(concept):
            return ConceptView(
                concept=concept,
                label=label,
                status="multiple",
                values=[c.value for c in candidates],
                confidence=max(c.confidence for c in candidates),
                sources=[s for c in candidates for s in c.sources],
                candidates=candidates,
            )
        official = _official_candidate(concept, candidates)
        if official is not None:
            others = sorted(
                {
                    s.document_name or "another document"
                    for c in candidates
                    if c is not official
                    for s in c.sources
                }
            )
            return ConceptView(
                concept=concept,
                label=label,
                status="resolved",
                value=official.value,
                values=[official.value],
                confidence=round(official.confidence * 0.95, 3),
                is_user_confirmed=False,
                origin=_best_origin(official.sources),
                sources=official.sources,
                candidates=candidates,
                note=(
                    f"Taken from the official document ({official.document_name}); "
                    f"{', '.join(others[:3])} show a different value."
                ),
            )
        return ConceptView(
            concept=concept,
            label=label,
            status="conflict",
            confidence=max(c.confidence for c in candidates),
            sources=[s for c in candidates for s in c.sources],
            candidates=candidates,
        )

    # ------------------------------------------------------------------ conflicts

    async def list_conflicts(self, user_id: str) -> list[ConflictData]:
        views = await self.resolve_view(user_id)
        conflicts = []
        for concept, view in sorted(views.items()):
            if view.status != "conflict":
                continue
            documents = {s.document_id for c in view.candidates for s in c.sources}
            if any(c.is_user_confirmed for c in view.candidates):
                conflict_type = "VERIFIED_VS_NEW"
            elif len(documents) > 1:
                conflict_type = "CROSS_DOCUMENT"
            else:
                conflict_type = "INTRA_DOCUMENT"
            short = concept.split(".", 1)[-1]
            conflicts.append(
                ConflictData(
                    id=concept,
                    concept=concept,
                    ontology=concept,
                    field=short,
                    semantic_type=short.upper(),
                    label=view.label,
                    conflict_type=conflict_type,  # type: ignore[arg-type]
                    candidates=view.candidates,
                )
            )
        return conflicts

    async def resolve_conflict(
        self, user_id: str, concept: str, request: ConflictResolutionRequest
    ) -> ConceptView | None:
        views = await self.resolve_view(user_id)
        view = views.get(concept)
        if view is None or view.status != "conflict":
            raise APIError("RESOURCE_NOT_FOUND", "Conflict not found", 404)
        all_ids = [
            ObjectId(s.fact_id) if ObjectId.is_valid(s.fact_id) else s.fact_id for s in view.sources
        ]
        if request.resolution == "reject":
            await self.repository.set_status(user_id, all_ids, "rejected")
            await self._record_correction(
                user_id, concept, None, None, request.reason or "Rejected all values"
            )
            return None
        if request.resolution == "custom":
            if request.custom_value in (None, ""):
                raise APIError(
                    "INVALID_VALUE", "custom_value is required for a custom resolution", 422
                )
            await self.add_user_fact(user_id, concept, request.custom_value)
            await self.repository.set_status(user_id, all_ids, "superseded")
        else:
            index = {"candidate_a": 0, "candidate_b": 1}.get(
                request.resolution, request.candidate_index
            )
            if index is None or index >= len(view.candidates):
                raise APIError("INVALID_CANDIDATE", "Choose one of the listed candidates", 422)
            chosen = view.candidates[index]
            chosen_ids = [
                ObjectId(s.fact_id) for s in chosen.sources if ObjectId.is_valid(s.fact_id)
            ]
            await self.repository.collection.update_many(
                {"user_id": user_id, "_id": {"$in": chosen_ids}},
                {"$set": {"is_user_confirmed": True, "updated_at": datetime.now(UTC)}},
            )
            await self.repository.set_status(
                user_id, [i for i in all_ids if i not in chosen_ids], "superseded"
            )
        return (await self.resolve_view(user_id)).get(concept)

    # ------------------------------------------------------------------ helpers

    async def _get(self, user_id: str, fact_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(fact_id):
            raise APIError("RESOURCE_NOT_FOUND", "Fact not found", 404)
        record = await self.repository.get(user_id, fact_id)
        if record is None or record.get("status", "active") != "active":
            raise APIError("RESOURCE_NOT_FOUND", "Fact not found", 404)
        return record

    async def _supersede_others(
        self, user_id: str, concept: str, keep_key: str, keep_id: Any = None
    ) -> None:
        if not self.ontology.is_single_valued(concept):
            return
        data_type = self.ontology.data_type(concept)
        others = [
            record["_id"]
            for record in await self.repository.list_active(user_id, concept)
            if record["_id"] != keep_id
            and comparison_key(data_type, record.get("value")) != keep_key
        ]
        await self.repository.set_status(user_id, others, "superseded")

    async def _record_correction(
        self, user_id: str, concept: str, original: Any, corrected: Any, reason: str | None
    ) -> None:
        if self.corrections_repository is None:
            return
        await self.corrections_repository.create(
            user_id,
            Correction(
                user_id=user_id,
                concept=concept,
                original_value=original,
                corrected_value=corrected,
                reason=reason or "User correction",
                created_at=datetime.now(UTC),
            ),
        )


def fact_data(record: dict[str, Any]) -> FactData:
    document_id = str(record.get("source_document_id", ""))
    page = record.get("source_page")
    return FactData(
        fact_id=str(record["_id"]),
        concept=record["concept"],
        value=record.get("value"),
        raw_value=record.get("raw_value"),
        value_type=record.get("value_type", "string"),
        origin=record.get("origin", "extracted"),
        status=record.get("status", "active"),
        source_document_id=document_id,
        document_name=record.get("document_name"),
        source_page=page,
        evidence_text=record.get("evidence_text"),
        extraction_method=record.get("extraction_method"),
        confidence=float(record.get("confidence", 0.0)),
        provenance=record.get("provenance", {}),
        is_user_confirmed=bool(record.get("is_user_confirmed", False)),
        document_type=_document_type(record),
        needs_review=bool(record.get("needs_review", False)),
        created_at=record.get("created_at") or datetime.now(UTC),
        updated_at=record.get("updated_at") or datetime.now(UTC),
        source={"document_id": document_id, "page": page},
    )


def _document_type(record: dict[str, Any]) -> str | None:
    value = record.get("document_type") or (record.get("provenance") or {}).get("document_type")
    return str(value) if value else None


def _source(record: dict[str, Any]) -> FactSource:
    return FactSource(
        fact_id=str(record["_id"]),
        document_id=str(record.get("source_document_id", "")),
        document_name=record.get("document_name"),
        page=record.get("source_page"),
        evidence=record.get("evidence_text"),
        origin=record.get("origin", "extracted"),
        confidence=float(record.get("confidence", 0.0)),
        is_user_confirmed=bool(record.get("is_user_confirmed", False)),
        document_type=_document_type(record),
        needs_review=bool(record.get("needs_review", False)),
    )


def _official_candidate(
    concept: str, candidates: list[ConflictCandidate]
) -> ConflictCandidate | None:
    """The single candidate backed by a document type that officially states ``concept``.

    A Class 12 marksheet outranks a résumé for the Class 12 percentage; two
    marksheets that disagree stay a conflict for the user to resolve. Values a
    user confirmed are handled before this rule (they supersede the others).
    """
    if any(c.is_user_confirmed for c in candidates):
        return None
    official_types = set(get_registry().document_types_for(concept))
    if not official_types:
        return None
    backed = [
        c
        for c in candidates
        if any(s.document_type in official_types and not s.needs_review for s in c.sources)
    ]
    return backed[0] if len(backed) == 1 else None


def _merge_addresses(groups: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    """Join address groups that describe the same place (same PIN, one a subset of the other)."""
    merged: list[list[dict[str, Any]]] = []
    for group in groups:
        for target in merged:
            if same_address(target[0]["value"], group[0]["value"]):
                target.extend(group)
                break
        else:
            merged.append(list(group))
    return merged


def _candidate(records: list[dict[str, Any]]) -> ConflictCandidate:
    # user-confirmed first, then the most complete wording among equally confident values
    ordered = sorted(
        records,
        key=lambda r: (
            bool(r.get("is_user_confirmed")),
            float(r.get("confidence", 0.0)),
            len(str(r.get("value", ""))),
        ),
        reverse=True,
    )
    best = ordered[0]
    sources = [_source(record) for record in ordered]
    return ConflictCandidate(
        value=best.get("value"),
        confidence=1.0 if best.get("is_user_confirmed") else float(best.get("confidence", 0.0)),
        is_user_confirmed=any(s.is_user_confirmed for s in sources),
        document_id=sources[0].document_id,
        document_name=sources[0].document_name,
        page=sources[0].page,
        evidence=sources[0].evidence,
        sources=sources,
    )


def _best_origin(sources: list[FactSource]) -> str:
    rank = {"user_provided": 0, "extracted": 1, "normalized": 2, "derived": 3, "inferred": 4}
    return min(
        (s.origin for s in sources), key=lambda origin: rank.get(origin, 5), default="extracted"
    )
