"""Semantic Classification Agent for form field semantic understanding (Pipeline C).

Extended to emit:
  - semantic_type: a dynamic label (SCREAMING_SNAKE_CASE) even when the field
    is not in the formal ontology. Used to query discovered_facts.
  - retrieval_strategy: MONGODB | CHROMADB | BOTH | MISSING
"""

import json
import logging
from typing import Any

from app.ontology.loader import FieldOntology
from app.schemas.forms import AlternativeConcept, ClassificationOutput, FieldObject
from app.agents.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Universal Form Field Semantic Classifier.
Your job is to receive a form field's metadata and:
  1. Map it to an ontology concept (if one exists in the provided list)
  2. ALWAYS produce a semantic_type label (even if not in the ontology)
  3. Determine the best retrieval strategy

RULES:
1. Output ONLY a valid JSON object matching the requested schema.
2. If the field perfectly maps to an ontology concept, output its canonical_name as the "ontology".
3. If the field is ambiguous or does not map to any known concept, output "MISSING" for ontology.
4. ALWAYS output a "semantic_type" in SCREAMING_SNAKE_CASE (e.g. "BANK_ACCOUNT_NUMBER",
   "ACADEMIC_SCORE", "INVOICE_NUMBER", "EMPLOYEE_ID", "UNKNOWN").
   This is mandatory even when ontology is "MISSING".
5. Determine the "field_type":
   - "STRUCTURED": short, discrete facts (personal.full_name, bank_account, cgpa)
   - "CONTEXTUAL": long-form text or semantic descriptions (project description, summary)
   - "MISSING": cannot be determined at all
6. Determine "retrieval_strategy":
   - "MONGODB": structured/discovered fact lookup by semantic_type or ontology concept
   - "CHROMADB": semantic similarity search in embedded chunks (for contextual/long-form)
   - "BOTH": use both sources
   - "MISSING": no retrieval possible
7. Do NOT hallucinate concepts not in the ontology list.
8. Provide a "confidence" float between 0.0 and 1.0.

JSON SCHEMA:
{
  "ontology": "canonical.concept.name or MISSING",
  "semantic_type": "SCREAMING_SNAKE_CASE_TYPE",
  "field_type": "STRUCTURED",
  "retrieval_strategy": "MONGODB",
  "confidence": 0.95
}
"""


class SemanticClassifier:
    """Agent that classifies form fields into canonical ontology concepts using an LLM.

    Now also emits semantic_type and retrieval_strategy for document-agnostic retrieval.
    """

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
            return ClassificationOutput(
                field_id=field.field_id,
                ontology="unknown",
                semantic_type="UNKNOWN",
                field_type="MISSING",
                retrieval_strategy="MISSING",
                confidence=0.0,
                status="unknown",
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
            "aria_label": field.aria_label,
            "visual_context": field.visual_context,
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

            ontology = parsed.get("ontology", "MISSING")
            semantic_type = parsed.get("semantic_type", "UNKNOWN") or "UNKNOWN"
            field_type = parsed.get("field_type", "MISSING")
            confidence = float(parsed.get("confidence", 0.0))
            retrieval_strategy = parsed.get("retrieval_strategy", "MISSING")

            # Normalize MISSING ontology to "unknown" for backward compat
            if ontology == "MISSING" or confidence < self.min_confidence:
                ontology = "unknown"
                # Still allow retrieval via semantic_type if we have one
                if semantic_type and semantic_type != "UNKNOWN":
                    field_type = field_type if field_type != "MISSING" else "STRUCTURED"
                    retrieval_strategy = "MONGODB" if retrieval_strategy == "MISSING" else retrieval_strategy
                else:
                    field_type = "MISSING"
                    retrieval_strategy = "MISSING"
            elif ontology != "unknown" and not self.ontology.get_concept(ontology):
                # LLM hallucinated an ontology concept — reject it but keep semantic_type
                ontology = "unknown"

            # Determine retrieval strategy from field_type if not explicitly set
            if retrieval_strategy == "MISSING" and field_type != "MISSING":
                retrieval_strategy = "CHROMADB" if field_type == "CONTEXTUAL" else "MONGODB"

            return ClassificationOutput(
                field_id=field.field_id,
                ontology=ontology,
                semantic_type=semantic_type,
                field_type=field_type,
                retrieval_strategy=retrieval_strategy,
                confidence=confidence,
                status="classified" if ontology != "unknown" or semantic_type != "UNKNOWN" else "unknown",
            )

        except Exception as e:
            logger.error("LLM Classification failed for field %s: %s", field.field_id, e)
            return ClassificationOutput(
                field_id=field.field_id,
                ontology="unknown",
                semantic_type="UNKNOWN",
                field_type="MISSING",
                retrieval_strategy="MISSING",
                confidence=0.0,
                status="error",
            )

    def classify_fields(self, fields: list[FieldObject]) -> list[ClassificationOutput]:
        """Batch classifies a list of FieldObjects."""
        return [self.classify_field(field) for field in fields]
