"""Profile service handling profile read/update and best structured facts aggregation."""

from datetime import UTC, datetime
from typing import Any

from app.models.documents import ProfileDocument
from app.repositories.collections import ProfilesRepository, StructuredFactsRepository
from app.schemas.profile import ProfileData, ProfileUpdateRequest


class ProfileService:
    def __init__(
        self,
        profiles_repository: ProfilesRepository,
        structured_facts_repository: StructuredFactsRepository,
    ) -> None:
        self.profiles_repository = profiles_repository
        self.structured_facts_repository = structured_facts_repository

    async def get(self, user_id: str) -> ProfileData:
        # 1. Fetch stored profile document
        profile_doc = await self.profiles_repository.get_for_user(user_id)
        if not profile_doc:
            now = datetime.now(UTC)
            profile_doc = {
                "user_id": user_id,
                "personal": {},
                "contact": {},
                "address": {},
                "education": [],
                "employment": [],
                "updated_at": now,
            }

        # 2. Fetch all structured facts for user
        facts = await self.structured_facts_repository.list(user_id)

        # 3. Aggregate best facts per concept
        best_facts: dict[str, dict[str, Any]] = {}
        for fact in facts:
            concept = fact.get("concept")
            if not concept:
                continue
            
            current_best = best_facts.get(concept)
            if current_best is None:
                best_facts[concept] = fact
            else:
                # Prefer confirmed > higher confidence > latest updated_at
                cur_confirmed = current_best.get("is_user_confirmed", False)
                new_confirmed = fact.get("is_user_confirmed", False)
                if new_confirmed and not cur_confirmed:
                    best_facts[concept] = fact
                elif new_confirmed == cur_confirmed:
                    cur_conf = current_best.get("confidence", 0.0)
                    new_conf = fact.get("confidence", 0.0)
                    if new_conf > cur_conf:
                        best_facts[concept] = fact

        # Build aggregated view from facts
        aggregated_personal: dict[str, Any] = {}
        aggregated_contact: dict[str, Any] = {}
        aggregated_address: dict[str, Any] = {}
        aggregated_education: list[dict[str, Any]] = []
        aggregated_employment: list[dict[str, Any]] = []

        concept_to_personal_field = {
            "full_name": "full_name",
            "person_name": "full_name",
            "name": "full_name",
            "first_name": "first_name",
            "last_name": "last_name",
            "date_of_birth": "date_of_birth",
            "gender": "gender",
            "nationality": "nationality",
        }

        concept_to_contact_field = {
            "email": "email",
            "email_address": "email",
            "phone": "phone",
            "phone_number": "phone",
            "linkedin": "linkedin",
            "github": "github",
        }

        for concept, fact in best_facts.items():
            val = fact.get("value")
            if val is None:
                continue

            if concept in concept_to_personal_field:
                aggregated_personal[concept_to_personal_field[concept]] = val
            elif concept in concept_to_contact_field:
                aggregated_contact[concept_to_contact_field[concept]] = val
            elif concept in ("current_address", "address"):
                aggregated_address["current"] = val
            elif concept == "permanent_address":
                aggregated_address["permanent"] = val
            elif concept == "city":
                aggregated_address["city"] = val
            elif concept == "state":
                aggregated_address["state"] = val
            elif concept == "country":
                aggregated_address["country"] = val
            elif concept == "postal_code":
                aggregated_address["postal_code"] = val
            elif concept == "education":
                if isinstance(val, list):
                    aggregated_education.extend(val)
                elif isinstance(val, dict):
                    aggregated_education.append(val)
            elif concept in ("employment", "organization"):
                if isinstance(val, list):
                    aggregated_employment.extend(val)
                elif isinstance(val, dict):
                    aggregated_employment.append(val)

        # 4. Merge: profile_doc explicit fields override/overlay aggregated facts
        merged_personal = {**aggregated_personal, **profile_doc.get("personal", {})}
        merged_contact = {**aggregated_contact, **profile_doc.get("contact", {})}
        merged_address = {**aggregated_address, **profile_doc.get("address", {})}
        merged_education = profile_doc.get("education") or aggregated_education
        merged_employment = profile_doc.get("employment") or aggregated_employment

        updated_at = profile_doc.get("updated_at")
        if not isinstance(updated_at, datetime):
            updated_at = datetime.now(UTC)

        return ProfileData(
            user_id=user_id,
            personal=merged_personal,
            contact=merged_contact,
            address=merged_address,
            education=merged_education,
            employment=merged_employment,
            updated_at=updated_at,
        )

    async def update(self, user_id: str, request: ProfileUpdateRequest) -> dict[str, Any]:
        existing = await self.profiles_repository.get_for_user(user_id)
        now = datetime.now(UTC)

        personal = dict(existing.get("personal", {})) if existing else {}
        contact = dict(existing.get("contact", {})) if existing else {}
        address = dict(existing.get("address", {})) if existing else {}
        education = list(existing.get("education", [])) if existing else []
        employment = list(existing.get("employment", [])) if existing else []

        if request.personal is not None:
            personal.update(request.personal)
        if request.contact is not None:
            contact.update(request.contact)
        if request.address is not None:
            address.update(request.address)
        if request.education is not None:
            education = request.education
        if request.employment is not None:
            employment = request.employment

        profile_doc = ProfileDocument(
            user_id=user_id,
            personal=personal,
            contact=contact,
            address=address,
            education=education,
            employment=employment,
            updated_at=now,
        )

        if existing and "_id" in existing:
            updates = profile_doc.model_dump(exclude_none=True)
            updates.pop("user_id", None)
            await self.profiles_repository.update(
                user_id,
                str(existing["_id"]),
                updates,
            )
        else:
            await self.profiles_repository.create(user_id, profile_doc)

        return {"updated": True}
