"""Document extraction: classify, extract deterministically, add LLM facts, merge.

* A document the registry classifies confidently (Aadhaar, marksheets, bank
  statements, certificates...) goes through ``DocumentAwareExtractor``.
* Anything else (résumés, letters, unknown layouts) keeps the generic
  ``DeterministicExtractor``.
* When an LLM is configured it reads the document too, with the detected type as
  a hint; its facts are checked against the document text and merged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.extraction.deterministic import DeterministicExtractor
from app.extraction.document_extractor import DocumentAwareExtractor
from app.extraction.llm_extraction import LLMFactExtractor
from app.extraction.merge import merge_candidates
from app.extraction.registry import Classification, DocumentRegistry, get_registry
from app.extraction.schemas import CandidateFact
from app.ontology.loader import FieldOntology
from app.processing.schemas import NormalizedDocument


@dataclass
class ExtractionResult:
    document_type: str = "UNKNOWN"
    classification: Classification = field(default_factory=Classification)
    candidates: list[CandidateFact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DocumentExtractionService:
    def __init__(
        self,
        ontology: FieldOntology,
        llm_extractor: LLMFactExtractor | None,
        deterministic: DeterministicExtractor | None = None,
        registry: DocumentRegistry | None = None,
    ) -> None:
        self.ontology = ontology
        self.llm_extractor = llm_extractor
        self.deterministic = deterministic or DeterministicExtractor(ontology)
        self.registry = registry or get_registry()
        self.document_extractor = DocumentAwareExtractor(ontology)

    async def extract(
        self, document: NormalizedDocument, document_name: str = ""
    ) -> ExtractionResult:
        classification = self.registry.classify(document)
        result = ExtractionResult(
            document_type=classification.document_type, classification=classification
        )
        doc_type = self.registry.get(classification.document_type)
        if doc_type is not None:
            candidates = self.document_extractor.extract(document, doc_type)
        else:
            candidates = self.deterministic.extract(document)
        if self.llm_extractor is not None:
            llm_result = await self.llm_extractor.extract(
                document,
                document_type=classification.document_type,
                scope=doc_type.scope if doc_type else None,
            )
            candidates.extend(llm_result.facts)
            result.warnings.extend(llm_result.warnings)
            if doc_type is None and llm_result.document_type != "UNKNOWN":
                # A CV or letter that mentions an ID must not become that ID document
                # (its values would then outrank the real document's).
                if not (classification.free_form and self.registry.get(llm_result.document_type)):
                    result.document_type = llm_result.document_type
        if (
            doc_type is None
            and not classification.free_form
            and classification.scores
            and max(classification.scores.values()) >= 2
        ):
            likely = max(classification.scores, key=classification.scores.__getitem__)
            if result.document_type == "UNKNOWN":
                result.warnings.append(
                    "The document type could not be identified with confidence "
                    f"(it may be a {self.registry.types[likely].label.lower()}); only clearly "
                    "labelled values were extracted."
                )
        result.candidates = merge_candidates(candidates)
        return result
