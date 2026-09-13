"""Semantic Classification Agent for form field semantic understanding (Pipeline C)."""

import json
import logging
from typing import Any

from app.ontology.loader import FieldOntology
from app.schemas.forms import AlternativeConcept, ClassificationOutput, FieldObject
from app.agents.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Universal Form Field Ontology Mapping Agent.
Your job is to receive a form field's metadata and map it to exactly one canonical ontology concept from the provided Universal Ontology.

RULES:
1. Output ONLY a valid JSON object matching the requested schema.
2. If the field perfectly maps to an ontology concept, output its canonical_name as the "ontology".
3. If the field is ambiguous or does not map to any known concept in the ontology, output "MISSING".
4. Determine the "field_type":
   - "STRUCTURED": For short, discrete facts (e.g. personal.full_name, identity.passport_number, education.institution)
   - "CONTEXTUAL": For long-form text or semantic descriptions (e.g. project.description, experience.description, medical.history_description)
   - "MISSING": If ontology is "MISSING".
5. Do NOT hallucinate concepts that do not exist in the provided ontology list.
6. Provide a "confidence" float between 0.0 and 1.0.

JSON SCHEMA:
{
  "ontology": "canonical.concept.name",
  "field_type": "STRUCTURED",
  "confidence": 0.95
}
"""

class SemanticClassifier:
    """Agent that classifies form fields into canonical ontology concepts using an LLM."""

    def __init__(
        self,
        ontology: FieldOntology | None = None,
        llm_provider: LLMProvider | None = None,
        min_confidence: float = 0.50,
    ) -> None:
        self.ontology = ontology or FieldOntology()
        self.llm_provider = llm_provider
        self.min_confidence = min_confidence
        
        # Build the ontology context string once during initialization
        self.ontology_context = self._build_ontology_context()

    def _build_ontology_context(self) -> str:
        lines = ["=== UNIVERSAL ONTOLOGY ==="]
        for concept_name, meta in self.ontology.concepts.items():
            desc = meta.get("description", "")
            lines.append(f"- {concept_name}: {desc}")
        return "\n".join(lines)

    def classify_field(self, field: FieldObject) -> ClassificationOutput:
        """Classifies a single FieldObject into an ontology concept using the LLM."""
        if not self.llm_provider:
            # Fallback to unknown if no LLM provider is available
            return ClassificationOutput(
                field_id=field.field_id,
                ontology="unknown",
                field_type="MISSING",
                confidence=0.0,
                status="unknown"
            )

        field_data = {
            "label": field.label,
            "placeholder": field.placeholder,
            "name": field.name,
            "id": field.id,
            "autocomplete": field.autocomplete,
            "input_type": field.type,
            "section": field.section_context,
            "nearby_text": field.nearby_text,
            "aria_label": field.aria_label
        }
        # Remove empty fields
        field_data = {k: v for k, v in field_data.items() if v}

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"{self.ontology_context}\n\n"
            f"=== FIELD METADATA ===\n"
            f"{json.dumps(field_data, indent=2)}\n\n"
            f"Respond with the JSON object:"
        )

        try:
            response = self.llm_provider.complete(prompt)
            # Find JSON block if wrapped in markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(response)
            
            ontology = parsed.get("ontology", "unknown")
            field_type = parsed.get("field_type", "MISSING")
            confidence = float(parsed.get("confidence", 0.0))
            
            # Revert to missing if confidence is too low or not in ontology
            if confidence < self.min_confidence or ontology == "MISSING" or (ontology != "unknown" and not self.ontology.get_concept(ontology)):
                ontology = "unknown"
                field_type = "MISSING"
                confidence = 0.0

            return ClassificationOutput(
                field_id=field.field_id,
                ontology=ontology,
                field_type=field_type,
                confidence=confidence,
                status="classified" if ontology != "unknown" else "unknown"
            )
            
        except Exception as e:
            logger.error(f"LLM Classification failed for field {field.field_id}: {e}")
            return ClassificationOutput(
                field_id=field.field_id,
                ontology="unknown",
                field_type="MISSING",
                confidence=0.0,
                status="error"
            )

    def classify_fields(self, fields: list[FieldObject]) -> list[ClassificationOutput]:
        """Batch classifies a list of FieldObjects."""
        # For a production system, this could be batched into a single LLM prompt
        # but for simplicity, we classify them sequentially.
        return [self.classify_field(field) for field in fields]
