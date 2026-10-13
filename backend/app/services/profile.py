"""The user profile: a read model computed from structured facts.

MongoDB ``structured_facts`` is the single source of truth. ``GET /profile``
groups the resolved value of every concept by namespace; ``PUT /profile`` turns
each supplied value into a user-provided, confirmed fact.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.api_errors import APIError
from app.ontology.loader import FieldOntology
from app.schemas.profile import ProfileData, ProfileField, ProfileUpdateRequest
from app.services.facts import FactService

# Section/key pairs accepted by the legacy PUT /profile body.
_LEGACY_KEYS = {
    ("personal", "full_name"): "personal.full_name",
    ("personal", "first_name"): "personal.first_name",
    ("personal", "last_name"): "personal.last_name",
    ("personal", "date_of_birth"): "personal.date_of_birth",
    ("personal", "gender"): "identity.gender",
    ("personal", "nationality"): "identity.nationality",
    ("contact", "email"): "personal.email",
    ("contact", "phone"): "personal.phone",
    ("address", "current"): "address.full_address",
    ("address", "full_address"): "address.full_address",
    ("address", "street"): "address.street",
    ("address", "city"): "address.city",
    ("address", "state"): "address.state",
    ("address", "postal_code"): "address.zipcode",
    ("address", "country"): "address.country",
}


class ProfileService:
    def __init__(self, fact_service: FactService, ontology: FieldOntology) -> None:
        self.facts = fact_service
        self.ontology = ontology

    async def get(self, user_id: str) -> ProfileData:
        views = await self.facts.resolve_view(user_id)
        sections: dict[str, dict[str, Any]] = {}
        fields: list[ProfileField] = []
        for concept in sorted(views):
            view = views[concept]
            namespace, key = concept.split(".", 1)
            if view.status == "resolved":
                sections.setdefault(namespace, {})[key] = view.value
            elif view.status == "multiple":
                sections.setdefault(namespace, {})[key] = view.values
            fields.append(
                ProfileField(
                    concept=concept,
                    label=view.label,
                    status=view.status,
                    value=view.value,
                    values=view.values,
                    confidence=view.confidence,
                    is_user_confirmed=view.is_user_confirmed,
                    origin=view.origin,
                    sources=view.sources,
                    sensitive=self.ontology.is_sensitive(concept),
                )
            )
        personal = dict(sections.get("personal", {}))
        contact = {
            key: personal.pop(key)
            for key in ("email", "phone", "linkedin", "github")
            if key in personal
        } | sections.get("contact", {})
        return ProfileData(
            user_id=user_id,
            personal=personal,
            contact=contact,
            address=sections.get("address", {}),
            education=_entries(sections.get("education", {})),
            employment=_entries(sections.get("experience", {})),
            sections=sections,
            fields=fields,
            updated_at=datetime.now(UTC),
        )

    async def update(self, user_id: str, request: ProfileUpdateRequest) -> dict[str, Any]:
        updates: dict[str, Any] = dict(request.fields or {})
        for section in ("personal", "contact", "address"):
            for key, value in (getattr(request, section) or {}).items():
                concept = _LEGACY_KEYS.get((section, key))
                if concept is None:
                    raise APIError(
                        "UNKNOWN_FIELD", f"Unsupported profile field: {section}.{key}", 422
                    )
                updates[concept] = value
        saved = 0
        for concept, value in updates.items():
            if value in (None, ""):
                continue
            await self.facts.add_user_fact(user_id, concept, value)
            saved += 1
        return {"updated": True, "saved": saved}


def _entries(section: dict[str, Any]) -> list[dict[str, Any]]:
    return [section] if section else []
