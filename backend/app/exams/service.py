"""Entrance-exam readiness: what the profile can supply for an exam and what is missing.

For each requirement of an exam profile (``requirements.yaml``) the status is one of

* ``available``           documents (or the user) supply one consistent value
* ``needs_confirmation``  a value exists but must be confirmed (eligibility claims,
                          sensitive data, values copied from another field)
* ``conflict``            documents disagree
* ``missing``             nothing yet; ``evidence`` lists documents that would supply it
* ``needs_user_input``    a preference, declaration or official code only the user can give

Uploads are evaluated the same way: whether each is required for this candidate,
and (stateless) whether a given file meets the configured format and size.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.agents.graph import match_subject
from app.core.api_errors import APIError
from app.extraction.registry import get_registry
from app.extraction.validators import mask
from app.ontology.loader import FieldOntology
from app.schemas.facts import ConceptView
from app.services.facts import FactService

REQUIREMENTS_PATH = Path(__file__).parent / "requirements.yaml"
_CONFIRMED_THRESHOLD = 0.85
_IMAGE_FORMATS = {"jpg", "jpeg", "png"}


DEMO_REQUIREMENTS_PATH = Path(__file__).parent / "demo_requirements.yaml"


@lru_cache
def load_exam_profiles(path: Path = REQUIREMENTS_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        profiles = yaml.safe_load(handle)["exams"]
    # The fictional demo profile (clearly labelled, invented rules) never ships to production.
    if path == REQUIREMENTS_PATH and os.environ.get("APP_ENV", "development").lower() != "production":
        with open(DEMO_REQUIREMENTS_PATH, encoding="utf-8") as handle:
            profiles = {**profiles, **yaml.safe_load(handle)["exams"]}
    return profiles


class ExamService:
    def __init__(self, facts: FactService, ontology: FieldOntology) -> None:
        self.facts = facts
        self.ontology = ontology
        self.profiles = load_exam_profiles()

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "exam_id": exam_id,
                "name": profile["name"],
                "conducting_body": profile.get("conducting_body"),
                "official_site": profile.get("official_site"),
                "last_reviewed": profile.get("last_reviewed"),
                "verified_against_official_bulletin": bool(
                    profile.get("verified_against_official_bulletin")
                ),
                "note": profile.get("note"),
            }
            for exam_id, profile in self.profiles.items()
        ]

    def _profile(self, exam_id: str) -> dict[str, Any]:
        profile = self.profiles.get(exam_id.upper())
        if profile is None:
            raise APIError("RESOURCE_NOT_FOUND", f"Unknown exam: {exam_id}", 404)
        return profile

    async def readiness(self, user_id: str, exam_id: str) -> dict[str, Any]:
        profile = self._profile(exam_id)
        views = await self.facts.resolve_view(user_id)
        registry = get_registry()
        sections = []
        counts: dict[str, int] = {}
        for section in profile["sections"]:
            items = []
            for requirement in section["requirements"]:
                item = self._requirement(requirement, views)
                item["evidence"] = [
                    {
                        "document_type": t,
                        "label": registry.types[t].label if t in registry.types else t,
                    }
                    for t in requirement.get("evidence", [])
                ]
                counts[item["status"]] = counts.get(item["status"], 0) + 1
                items.append(item)
            sections.append({"title": section["title"], "requirements": items})
        return {
            "exam_id": exam_id.upper(),
            "name": profile["name"],
            "last_reviewed": profile.get("last_reviewed"),
            "verified_against_official_bulletin": bool(
                profile.get("verified_against_official_bulletin")
            ),
            "note": profile.get("note"),
            "summary": counts,
            "sections": sections,
            "uploads": [self._upload_requirement(u, views) for u in profile.get("uploads", [])],
        }

    def _requirement(
        self, requirement: dict[str, Any], views: dict[str, ConceptView]
    ) -> dict[str, Any]:
        concept = requirement["concept"]
        sensitive = self.ontology.is_sensitive(concept)
        item: dict[str, Any] = {
            "concept": concept,
            "label": self.ontology.description(concept),
            "required": bool(requirement.get("required", False)),
            "sensitive": sensitive,
            "value": None,
            "sources": [],
        }
        view = views.get(concept)
        if requirement.get("subjects"):
            return item | self._subjects(requirement["subjects"], view)
        if requirement.get("source") == "user" or self.ontology.is_user_only(concept):
            confirmed = [c for c in (view.candidates if view else []) if c.is_user_confirmed]
            if confirmed:
                return item | {
                    "status": "available",
                    "value": confirmed[0].value,
                    "sources": ["Entered by you"],
                }
            return item | {
                "status": "needs_user_input",
                "reason": "Only you can provide this (a choice, declaration or official code).",
            }
        fallback = self.ontology.fallback(concept)
        if (
            view is None
            and fallback
            and views.get(fallback)
            and views[fallback].status == "resolved"
        ):
            base = views[fallback]
            return item | {
                "status": "needs_confirmation",
                "value": base.value,
                "sources": _names(base),
                "reason": f"Taken from your {self.ontology.description(fallback).lower()}; confirm it applies.",
            }
        if view is None:
            return item | {
                "status": "missing",
                "reason": "Not found in your documents or profile yet.",
            }
        if view.status == "conflict":
            return item | {
                "status": "conflict",
                "candidates": [_display(c.value, sensitive) for c in view.candidates],
                "sources": _names(view),
                "reason": "Your documents disagree; choose the correct value.",
            }
        if view.status == "multiple":
            return item | {
                "status": "needs_confirmation",
                "candidates": [_display(v, sensitive) for v in view.values],
                "sources": _names(view),
                "reason": "Several values are stored; choose one.",
            }
        needs_confirmation = not view.is_user_confirmed and (
            requirement.get("confirm")
            or sensitive
            or view.origin in ("inferred", "derived")
            or view.confidence < _CONFIRMED_THRESHOLD
        )
        return item | {
            "status": "needs_confirmation" if needs_confirmation else "available",
            "value": _display(view.value, sensitive),
            "sources": _names(view),
            "reason": (
                "A document states this, but eligibility or sensitive data must be confirmed by you."
                if needs_confirmation
                else "Found in your documents."
            ),
        }

    def _subjects(self, subjects: list[str], view: ConceptView | None) -> dict[str, Any]:
        rows = [
            (c, c.value) for c in (view.candidates if view else []) if isinstance(c.value, dict)
        ]
        found, missing = [], []
        for subject in subjects:
            matches = match_subject(subject, rows)
            if matches:
                row = matches[0][1]
                found.append(
                    {
                        "subject": subject,
                        "name": row.get("name"),
                        "marks_obtained": row.get("marks_obtained") or row.get("total"),
                        "max_marks": row.get("max_marks"),
                        "grade": row.get("grade"),
                    }
                )
            else:
                missing.append(subject)
        if not rows:
            return {
                "status": "missing",
                "reason": "No subject-wise marks are stored yet; upload the marksheet.",
            }
        return {
            "status": "available" if not missing else "missing",
            "value": found,
            "sources": _names(view) if view else [],
            "missing_subjects": missing,
            "reason": (
                "All required subjects found."
                if not missing
                else f"Not on your marksheet: {', '.join(missing)}."
            ),
        }

    def _upload_requirement(
        self, upload: dict[str, Any], views: dict[str, ConceptView]
    ) -> dict[str, Any]:
        required: bool | None = bool(upload.get("required", False))
        reason = None
        condition = upload.get("required_if")
        if condition:
            concept, values = next(iter(condition.items()))
            view = views.get(concept)
            current = view.value if view and view.status == "resolved" else None
            if current is None:
                required, reason = (
                    None,
                    f"Depends on your {self.ontology.description(concept).lower()}.",
                )
            else:
                required = any(
                    str(current).casefold().startswith(str(v).casefold()) for v in values
                )
        return {
            "id": upload["id"],
            "label": upload["label"],
            "required": required,
            "reason": reason,
            "formats": upload.get("formats", []),
            "min_kb": upload.get("min_kb"),
            "max_kb": upload.get("max_kb"),
            "verified": bool(upload.get("verified", False)),
            "note": (
                "Never taken from a marksheet or ID card; upload a separate file."
                if upload["id"]
                in ("photograph", "postcard_photograph", "signature", "thumb_impressions")
                else None
            ),
        }

    def check_upload(
        self, exam_id: str, upload_id: str, file_name: str, content: bytes
    ) -> dict[str, Any]:
        profile = self._profile(exam_id)
        spec = next((u for u in profile.get("uploads", []) if u["id"] == upload_id), None)
        if spec is None:
            raise APIError("RESOURCE_NOT_FOUND", f"Unknown upload: {upload_id}", 404)
        problems: list[str] = []
        extension = Path(file_name).suffix.lower().lstrip(".")
        formats = spec.get("formats") or []
        if formats and extension not in formats:
            problems.append(f"Format .{extension or '?'} is not one of: {', '.join(formats)}.")
        size_kb = round(len(content) / 1024, 1)
        if spec.get("min_kb") and size_kb < spec["min_kb"]:
            problems.append(f"File is {size_kb} KB; the minimum is {spec['min_kb']} KB.")
        if spec.get("max_kb") and size_kb > spec["max_kb"]:
            problems.append(f"File is {size_kb} KB; the maximum is {spec['max_kb']} KB.")
        dimensions = None
        if extension in _IMAGE_FORMATS:
            dimensions = _image_size(content)
            if dimensions is None:
                problems.append("The file is not a readable image.")
        verified = bool(spec.get("verified", False))
        return {
            "upload_id": upload_id,
            "file_name": file_name,
            "size_kb": size_kb,
            "dimensions": {"width": dimensions[0], "height": dimensions[1]} if dimensions else None,
            "ok": not problems,
            "problems": problems,
            "verified_rules": verified,
            "note": (
                None
                if verified
                else (
                    "These limits are not yet verified against the official bulletin; check them there."
                )
            ),
        }


def _image_size(content: bytes) -> tuple[int, int] | None:
    import io

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(content)) as image:
            return image.size
    except (UnidentifiedImageError, OSError):
        return None


def _names(view: ConceptView) -> list[str]:
    return sorted({s.document_name or "document" for s in view.sources})


def _display(value: Any, sensitive: bool) -> Any:
    return mask(str(value)) if sensitive and isinstance(value, str) else value
