"""Form sessions: analysis, review decisions, approved values and fill verification."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.graph import FormFillGraph
from app.agents.value_formatting import format_for_field
from app.core.api_errors import APIError
from app.db.repositories.form_sessions import FormSessionsRepository
from app.db.repositories.recommendations import FILLABLE_STATUSES, RecommendationsRepository
from app.ontology.loader import FieldOntology
from app.schemas.form_sessions import (
    ApprovedValueData,
    FieldDecision,
    FieldObject,
    FillResult,
    FormSessionResponseData,
    RecommendationOutput,
    SelectedOption,
)
from app.services.facts import FactService
from app.services.user_memories import UserMemoryService

logger = logging.getLogger(__name__)

_DECIDABLE = {
    "ready",
    "needs_review",
    "missing_information",
    "approved",
    "edited",
    "rejected",
    "skipped",
    "error",
}


class FormFillService:
    def __init__(
        self,
        *,
        sessions: FormSessionsRepository,
        recommendations: RecommendationsRepository,
        graph: FormFillGraph,
        facts: FactService,
        memories: UserMemoryService,
        ontology: FieldOntology,
    ) -> None:
        self.sessions = sessions
        self.recommendations = recommendations
        self.graph = graph
        self.facts = facts
        self.memories = memories
        self.ontology = ontology

    async def require_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        session = await self.sessions.get_session(user_id, session_id)
        if session is None:
            raise APIError("RESOURCE_NOT_FOUND", "Form session not found", 404)
        return session

    async def session_data(self, user_id: str, session: dict[str, Any]) -> FormSessionResponseData:
        counts = await self.recommendations.count_by_status(user_id, session["_id"])
        return FormSessionResponseData(
            session_id=session["_id"],
            website_origin=session.get("website_origin", ""),
            page_url=session.get("page_url", ""),
            form_id=session.get("form_id", ""),
            status=session.get("status", "started"),
            started_at=session.get("started_at"),
            total_fields=session.get("total_fields", 0),
            filled_fields=session.get("filled_fields", 0),
            reviewed_fields=session.get("reviewed_fields", 0),
            failed_fields=session.get("failed_fields", 0),
            error=session.get("error"),
            counts=counts,
        )

    # ------------------------------------------------------------------ analysis

    async def analyze(self, user_id: str, session_id: str, fields: list[FieldObject]) -> None:
        try:
            await self.graph.run(user_id, session_id, fields, persist=True)
        except Exception:
            logger.exception("form_analysis_failed", extra={"session_id": session_id})
            await self.sessions.update_session(
                user_id,
                session_id,
                {"status": "failed", "error": "Form analysis failed. Try again."},
            )
            return
        await self.refresh_status(user_id, session_id)

    async def refresh_status(self, user_id: str, session_id: str) -> str:
        counts = await self.recommendations.count_by_status(user_id, session_id)
        if counts.get("missing_required"):
            status = "information_required"
        elif counts.get("needs_review"):
            status = "review_required"
        else:
            status = "ready"
        reviewed = counts.get("approved", 0) + counts.get("edited", 0) + counts.get("rejected", 0)
        await self.sessions.update_session(
            user_id, session_id, {"status": status, "reviewed_fields": reviewed, "error": None}
        )
        return status

    async def recommendations_for(
        self, user_id: str, session_id: str
    ) -> list[RecommendationOutput]:
        return [
            to_output(doc)
            for doc in await self.recommendations.list_for_session(user_id, session_id)
        ]

    # ------------------------------------------------------------------ decisions

    async def apply_decisions(
        self, user_id: str, session_id: str, decisions: list[FieldDecision]
    ) -> tuple[str, int]:
        await self.require_session(user_id, session_id)
        seen: set[str] = set()
        records = []
        for decision in decisions:
            if decision.field_id in seen:
                raise APIError("DUPLICATE_FIELD", "Each field may appear only once", 422)
            seen.add(decision.field_id)
            record = await self.recommendations.get_for_field(
                user_id, session_id, decision.field_id
            )
            if record is None or record["status"] not in _DECIDABLE:
                raise APIError(
                    "UNKNOWN_FIELD",
                    f"No reviewable recommendation for field {decision.field_id}",
                    409,
                )
            records.append((decision, record))
        saved = 0
        for decision, record in records:
            saved += await self.apply_decision(user_id, record, decision)
        return await self.refresh_status(user_id, session_id), saved

    async def apply_decision(
        self, user_id: str, record: dict[str, Any], decision: FieldDecision
    ) -> int:
        """Apply one decision. Returns 1 when a value was saved for future forms."""
        updates: dict[str, Any] = {}
        value: Any = None
        if decision.decision == "approve":
            if record.get("recommended_value") in (None, ""):
                raise APIError(
                    "NO_VALUE",
                    f"Field {decision.field_id} has no value to approve; edit it instead",
                    422,
                )
            updates["status"] = "approved"
            value = record["recommended_value"]
        elif decision.decision == "edit":
            if not (decision.value or "").strip():
                raise APIError("NO_VALUE", "A value is required to edit a field", 422)
            formatted, selected = self._format(record, decision.value or "")
            updates.update(
                status="edited",
                recommended_value=formatted,
                selected_option=selected,
                origin="user_provided",
                confidence=1.0,
                reason="Entered or corrected by you.",
            )
            value = decision.value
        elif decision.decision == "reject":
            updates["status"] = "rejected"
        else:
            updates["status"] = "skipped"
        await self.recommendations.update_fields(user_id, record["_id"], updates)
        if (
            decision.save_for_future
            and value not in (None, "")
            and decision.decision in ("approve", "edit")
        ):
            concept = record.get("concept")
            if concept and self.ontology.is_known(concept) and self.ontology.is_fillable(concept):
                await self.facts.add_user_fact(user_id, concept, value)
            else:
                await self.memories.save(
                    user_id,
                    record.get("field_label") or decision.field_id,
                    concept or "free_text",
                    str(value),
                )
            return 1
        return 0

    def _format(self, record: dict[str, Any], value: str) -> tuple[str, dict[str, str] | None]:
        field_data = record.get("field")
        if not field_data:
            return value.strip(), None
        field_obj = FieldObject.model_validate(field_data)
        concept = record.get("concept")
        data_type = self.ontology.data_type(concept) if concept else "string"
        formatted = format_for_field(field_obj, data_type, value)
        if formatted.value is None:
            raise APIError(
                "INVALID_VALUE", formatted.problem or "Value does not fit this field", 422
            )
        return formatted.value, formatted.selected_option

    # ------------------------------------------------------------------ filling

    async def approved_values(self, user_id: str, session_id: str) -> list[ApprovedValueData]:
        await self.require_session(user_id, session_id)
        values = []
        for doc in await self.recommendations.list_for_session(user_id, session_id):
            if doc["status"] not in FILLABLE_STATUSES or doc.get("recommended_value") in (None, ""):
                continue
            if doc["status"] == "ready" and doc.get("requires_confirmation"):
                continue
            selected = doc.get("selected_option")
            values.append(
                ApprovedValueData(
                    recommendation_id=str(doc["_id"]),
                    field_id=doc["field_id"],
                    concept=doc.get("concept"),
                    value=str(doc["recommended_value"]),
                    input_type=doc.get("input_type", "text"),
                    field_label=doc.get("field_label", ""),
                    selected_option=SelectedOption(**selected) if selected else None,
                    status=doc["status"],
                )
            )
        return values

    async def record_fill_results(
        self, user_id: str, session_id: str, results: list[FillResult]
    ) -> dict[str, int]:
        await self.require_session(user_id, session_id)
        for result in results:
            record = await self.recommendations.get_for_field(user_id, session_id, result.field_id)
            if record:
                await self.recommendations.update_fields(
                    user_id, record["_id"], {"fill_result": result.model_dump()}
                )
        return await self.sessions.record_fill_results(
            user_id, session_id, [r.model_dump() for r in results]
        )


def to_output(doc: dict[str, Any]) -> RecommendationOutput:
    source = doc.get("source") or None
    provenance = (
        [{"document_id": source["document_id"], "page": source.get("page")}]
        if source and source.get("document_id") and source.get("type") in ("profile", "document")
        else []
    )
    return RecommendationOutput(
        recommendation_id=str(doc["_id"]),
        field_id=doc["field_id"],
        field_label=doc.get("field_label", ""),
        input_type=doc.get("input_type", "text"),
        required=bool(doc.get("required", False)),
        concept=doc.get("concept"),
        recommended_value=doc.get("recommended_value"),
        confidence=float(doc.get("confidence", 0.0)),
        status=doc["status"],
        reason=doc.get("reason", ""),
        requires_confirmation=bool(doc.get("requires_confirmation", False)),
        origin=doc.get("origin"),
        retrieval_type=doc.get("retrieval_type", "none"),
        source=source,
        candidates=doc.get("candidates", []),
        options=doc.get("options", []),
        selected_option=doc.get("selected_option"),
        provenance=provenance,
        fill_result=doc.get("fill_result"),
    )
