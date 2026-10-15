"""Document processing pipeline.

    parse text (+OCR) -> deterministic extraction -> LLM extraction -> merge
    -> replace this document's facts in MongoDB -> chunk, embed, index in ChromaDB

Facts are written per document: re-processing first removes the document's
previous facts and chunks, so nothing is duplicated and nothing stale remains.
An indexing failure does not lose the extracted facts; it is recorded on the
document (``index_status=failed``) so the user can see that RAG is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.db.chroma_client import ChromaClient, VectorStoreError
from app.extraction.deterministic import DeterministicExtractor
from app.extraction.llm_extraction import LLMFactExtractor
from app.extraction.schemas import CandidateFact
from app.extraction.service import DocumentExtractionService
from app.models.documents import DiscoveredFact, StructuredFact
from app.ontology.loader import FieldOntology
from app.processing.chunking import TextChunker
from app.processing.extractor import DocumentReadError, UniversalDocumentExtractor
from app.processing.schemas import NormalizedDocument
from app.repositories.collections import (
    DiscoveredFactsRepository,
    ProcessingRecordsRepository,
    StructuredFactsRepository,
)
from app.retrieval.embeddings import EmbeddingProvider, EmbeddingUnavailableError

logger = logging.getLogger(__name__)

STAGES = ("validation", "parsing", "extraction", "storage", "indexing", "completed")
_PROGRESS = {
    "validation": 10,
    "parsing": 30,
    "extraction": 55,
    "storage": 75,
    "indexing": 90,
    "completed": 100,
}

OnUpdate = Callable[[dict[str, object]], Awaitable[None]]


@dataclass
class PipelineResult:
    normalized: NormalizedDocument
    document_type: str = "UNKNOWN"
    document_type_confidence: float | None = None
    fact_count: int = 0
    discovered_count: int = 0
    warnings: list[str] = field(default_factory=list)
    index_status: str = "pending"
    chunk_count: int = 0
    index_error: str | None = None


class DocumentPipeline:
    def __init__(
        self,
        *,
        extractor: UniversalDocumentExtractor,
        ontology: FieldOntology,
        deterministic: DeterministicExtractor,
        llm_extractor: LLMFactExtractor | None,
        facts: StructuredFactsRepository,
        discovered: DiscoveredFactsRepository,
        stages: ProcessingRecordsRepository,
        chunker: TextChunker,
        embeddings: EmbeddingProvider,
        vector_store: ChromaClient,
    ) -> None:
        self.extractor = extractor
        self.ontology = ontology
        self.deterministic = deterministic
        self.llm_extractor = llm_extractor
        self.facts = facts
        self.discovered = discovered
        self.stages = stages
        self.chunker = chunker
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.extraction = DocumentExtractionService(ontology, llm_extractor, deterministic)

    async def run(
        self,
        user_id: str,
        document_id: str,
        local_path: str,
        document_name: str,
        on_update: OnUpdate,
    ) -> PipelineResult:
        await self._stage(user_id, document_id, "parsing", on_update)
        normalized = await asyncio.to_thread(self.extractor.extract, local_path, document_name)
        if not normalized.text.strip():
            raise DocumentReadError("No readable text was found in the document.")
        result = PipelineResult(normalized=normalized, warnings=list(normalized.warnings))

        await self._stage(user_id, document_id, "extraction", on_update)
        extraction = await self.extraction.extract(normalized, document_name)
        result.warnings.extend(extraction.warnings)
        result.document_type = extraction.document_type
        if extraction.classification.document_type != "UNKNOWN":
            result.document_type_confidence = extraction.classification.confidence
        merged = extraction.candidates

        await self._stage(user_id, document_id, "storage", on_update)
        now = datetime.now(UTC)
        await self.facts.delete_for_document(user_id, document_id)
        await self.discovered.delete_for_document(user_id, document_id)
        structured = [
            self._structured(
                user_id, document_id, document_name, candidate, now, result.document_type
            )
            for candidate in merged
            if candidate.concept and self.ontology.is_fillable(candidate.concept)
        ]
        discovered = [
            self._discovered(user_id, document_id, result.document_type, candidate, now)
            for candidate in merged
        ]
        result.fact_count = await self.facts.insert_many(user_id, structured)
        result.discovered_count = await self.discovered.insert_many(user_id, discovered)

        await self._stage(user_id, document_id, "indexing", on_update)
        await self._index(user_id, document_id, document_name, result)
        await self.stages.record_stage(user_id, document_id, "completed", "completed")
        return result

    async def _index(
        self, user_id: str, document_id: str, document_name: str, result: PipelineResult
    ) -> None:
        chunks = self.chunker.chunk_document(
            result.normalized, user_id, document_id, document_name, result.document_type
        )
        try:
            await self.vector_store.delete_document_chunks(user_id, document_id)
            if not chunks:
                result.index_status = "empty"
                return
            vectors = await self.embeddings.embed_texts([chunk.embed_text for chunk in chunks])
            await self.vector_store.upsert_chunks(chunks, vectors)
        except (EmbeddingUnavailableError, VectorStoreError) as error:
            logger.warning(
                "document_indexing_failed", extra={"document_id": document_id, "error": str(error)}
            )
            result.index_status = "failed"
            result.index_error = str(error)
            await self.stages.record_stage(user_id, document_id, "indexing", "failed", str(error))
            return
        result.index_status = "indexed"
        result.chunk_count = len(chunks)

    async def _stage(self, user_id: str, document_id: str, stage: str, on_update: OnUpdate) -> None:
        await self.stages.record_stage(user_id, document_id, stage, "started")
        await on_update({"current_stage": stage, "progress": _PROGRESS[stage]})

    @staticmethod
    def _structured(
        user_id: str,
        document_id: str,
        document_name: str,
        candidate: CandidateFact,
        now: datetime,
        document_type: str = "UNKNOWN",
    ) -> StructuredFact:
        validation = str(candidate.extra.get("validation") or "")
        return StructuredFact(
            user_id=user_id,
            concept=candidate.concept or "",
            value=candidate.value,
            raw_value=candidate.raw_value,
            value_type=candidate.data_type,
            origin=candidate.origin,  # type: ignore[arg-type]
            source_document_id=document_id,
            document_name=document_name,
            source_page=candidate.page,
            evidence_text=candidate.evidence_text or None,
            extraction_method=candidate.method,
            confidence=candidate.confidence,
            provenance=_provenance(candidate),
            document_type=document_type if document_type != "UNKNOWN" else None,
            needs_review=(
                candidate.confidence < 0.7
                or candidate.origin == "inferred"
                or "repair" in validation.lower()
            ),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _discovered(
        user_id: str, document_id: str, document_type: str, candidate: CandidateFact, now: datetime
    ) -> DiscoveredFact:
        return DiscoveredFact(
            user_id=user_id,
            source_document_id=document_id,
            source_page=candidate.page,
            entity_type=candidate.entity_type,
            field=candidate.field or "value",
            semantic_type=candidate.semantic_type or "UNKNOWN",
            value=candidate.value,
            raw_value=candidate.raw_value,
            original_label=str(candidate.extra.get("original_label") or "") or None,
            data_type=candidate.data_type,
            confidence=candidate.confidence,
            evidence_text=candidate.evidence_text,
            ontology=candidate.concept,
            origin=candidate.origin,  # type: ignore[arg-type]
            extraction_method=candidate.method,
            document_type=document_type,
            created_at=now,
            updated_at=now,
        )


def _provenance(candidate: CandidateFact) -> dict[str, object]:
    """Where a value came from and how it was checked (no document text beyond the evidence)."""
    keep = ("document_type", "original_label", "validation", "derivation")
    return {key: str(candidate.extra[key]) for key in keep if candidate.extra.get(key)}
