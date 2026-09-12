"""Semantic Classification Agent for form field semantic understanding (SRS §13)."""

import logging
from typing import Any

from app.ontology.loader import FieldOntology
from app.schemas.forms import AlternativeConcept, ClassificationOutput, FieldObject

logger = logging.getLogger(__name__)


class SemanticClassifier:
    """Agent that classifies form fields into canonical ontology concepts."""

    def __init__(
        self,
        ontology: FieldOntology | None = None,
        min_confidence: float = 0.50,
    ) -> None:
        self.ontology = ontology or FieldOntology()
        self.min_confidence = min_confidence

    def classify_field(self, field: FieldObject) -> ClassificationOutput:
        """Classifies a single FieldObject into an ontology concept.
        
        Guarantees zero personal value fabrication — returns semantic concept classification only.
        """
        context_used: list[str] = []
        candidates: dict[str, float] = {}

        # 1. Autocomplete attribute check (high priority standard tokens)
        if field.autocomplete and field.autocomplete.strip():
            auto_token = field.autocomplete.strip().lower()
            context_used.append("autocomplete")
            mapped_concept = self._map_autocomplete(auto_token)
            if mapped_concept:
                candidates[mapped_concept] = max(candidates.get(mapped_concept, 0.0), 0.99)

        # 2. Visible Label evaluation
        if field.label and field.label.strip():
            context_used.append("label")
            matches = self.ontology.find_matches(field.label)
            for concept, conf in matches:
                candidates[concept] = max(candidates.get(concept, 0.0), conf)

        # 3. Placeholder evaluation
        if field.placeholder and field.placeholder.strip():
            context_used.append("placeholder")
            matches = self.ontology.find_matches(field.placeholder)
            for concept, conf in matches:
                candidates[concept] = max(candidates.get(concept, 0.0), conf * 0.90)

        # 4. Name & ID attributes evaluation
        for attr_name, attr_val in [("name", field.name), ("id", field.id)]:
            if attr_val and attr_val.strip():
                context_used.append(attr_name)
                # Clean camelCase/snake_case into space-separated string
                cleaned_attr = self._clean_identifier(attr_val)
                matches = self.ontology.find_matches(cleaned_attr)
                for concept, conf in matches:
                    candidates[concept] = max(candidates.get(concept, 0.0), conf * 0.85)

        # 5. Accessibility attributes evaluation
        if field.aria_label and field.aria_label.strip():
            context_used.append("aria_label")
            matches = self.ontology.find_matches(field.aria_label)
            for concept, conf in matches:
                candidates[concept] = max(candidates.get(concept, 0.0), conf * 0.90)

        # 6. Surrounding / nearby text evaluation
        if field.nearby_text and field.nearby_text.strip():
            context_used.append("nearby_text")
            matches = self.ontology.find_matches(field.nearby_text)
            for concept, conf in matches:
                candidates[concept] = max(candidates.get(concept, 0.0), conf * 0.75)

        # 7. Section context boosting & contextual refinement (TC-SEM-03)
        if field.section_context and field.section_context.strip():
            context_used.append("section_context")
            section_lower = field.section_context.strip().lower()

            # Refine address concept if section is "Permanent" or "Current"
            if "permanent" in section_lower or "home" in section_lower or "native" in section_lower:
                if "address" in candidates:
                    candidates["permanent_address"] = max(candidates.get("permanent_address", 0.0), 0.95)
                    del candidates["address"]
            elif "current" in section_lower or "present" in section_lower or "local" in section_lower:
                if "address" in candidates:
                    candidates["current_address"] = max(candidates.get("current_address", 0.0), 0.95)
                    del candidates["address"]

        # Deduplicate context_used list preserving order
        unique_context_used = list(dict.fromkeys(context_used))

        if not candidates:
            # Unknown / unsupported concept fallback (SRS §12.4)
            return ClassificationOutput(
                field_id=field.field_id,
                concept="unknown",
                confidence=0.0,
                alternatives=[],
                context_used=unique_context_used,
                status="unknown",
            )

        # Sort candidates by confidence descending
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        best_concept, best_confidence = sorted_candidates[0]

        # Check against minimum confidence threshold
        if best_confidence < self.min_confidence:
            alternatives = [
                AlternativeConcept(concept=c, confidence=conf)
                for c, conf in sorted_candidates
            ]
            return ClassificationOutput(
                field_id=field.field_id,
                concept="unknown",
                confidence=best_confidence,
                alternatives=alternatives,
                context_used=unique_context_used,
                status="unknown",
            )

        alternatives = [
            AlternativeConcept(concept=c, confidence=conf)
            for c, conf in sorted_candidates[1:4]
        ]

        return ClassificationOutput(
            field_id=field.field_id,
            concept=best_concept,
            confidence=best_confidence,
            alternatives=alternatives,
            context_used=unique_context_used,
            status="classified",
        )

    def classify_fields(self, fields: list[FieldObject]) -> list[ClassificationOutput]:
        """Batch classifies a list of FieldObjects."""
        return [self.classify_field(field) for field in fields]

    @staticmethod
    def _map_autocomplete(token: str) -> str | None:
        mapping = {
            "name": "full_name",
            "given-name": "first_name",
            "family-name": "last_name",
            "email": "email_address",
            "tel": "phone_number",
            "tel-national": "phone_number",
            "bday": "date_of_birth",
            "street-address": "address",
            "address-line1": "address",
            "address-level2": "city",
            "address-level1": "state",
            "country": "country",
            "postal-code": "postal_code",
            "organization": "organization",
        }
        return mapping.get(token)

    @staticmethod
    def _clean_identifier(ident: str) -> str:
        """Converts camelCase or snake_case identifiers to space-separated words."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1 \2", ident)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1 \2", s1)
        return s2.replace("_", " ").replace("-", " ")
