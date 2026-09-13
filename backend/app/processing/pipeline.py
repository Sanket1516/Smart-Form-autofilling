"""Resilient document processing pipeline with stage provenance.

Two-track extraction:
  Track A (primary)  : DynamicDocumentExtractor — document-agnostic LLM entity discovery
  Track B (secondary): DocumentOntologyExtractor — existing ontology-mapped extraction
                       (kept for backward compat; also acts as cross-validation)

Both tracks run in sequence. Results from both are stored:
  - discovered_facts   (Track A)
  - structured_facts   (Track B)

Cross-document conflict detection runs after Track A storage.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import logging

from app.db.chroma_client import ChromaClient
from app.extraction.llm_extractor import DocumentOntologyExtractor
from app.extraction.dynamic_extractor import DynamicDocumentExtractor
from app.extraction.conflict_detector import ConflictDetector
from app.extraction.schemas import DynamicExtractionOutput, DiscoveredAttribute
from app.models.documents import DiscoveredFact, DiscoveredConflict, StructuredFact
from app.processing.chunking import TextChunker
from app.processing.extractor import OCRUnavailableError, PDFExtractor
from app.processing.schemas import NormalizedDocument
from app.retrieval.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

STAGES = (
    "upload",
    "validation",
    "ocr",
    "parsing",
    "normalization",
    "extraction",
    "embedding",
    "mongodb_storage",
    "chromadb_storage",
    "completed",
)


class StageWriter(Protocol):
    async def record_stage(
        self,
        user_id: str,
        document_id: str,
        stage: str,
        status: str,
        error: str | None = None,
    ) -> None: ...


class FactWriter(Protocol):
    async def create(self, user_id: str, document: StructuredFact) -> dict: ...


class DiscoveredFactWriter(Protocol):
    async def upsert_discovered_fact(self, user_id: str, fact: DiscoveredFact) -> dict: ...


class DiscoveredConflictWriter(Protocol):
    async def create(self, user_id: str, conflict: DiscoveredConflict) -> dict: ...


class PipelineRetryableError(RuntimeError):
    """A transient failure eligible for bounded queue retry."""


class DocumentPipeline:
    def __init__(
        self,
        extractor: PDFExtractor,
        stage_writer: StageWriter,
        max_retries: int = 2,
        # Track B: legacy ontology extractor (optional, backward compat)
        fact_extractor: DocumentOntologyExtractor | None = None,
        fact_writer: FactWriter | None = None,
        # Track A: new dynamic entity discovery (primary)
        dynamic_extractor: DynamicDocumentExtractor | None = None,
        discovered_fact_writer: DiscoveredFactWriter | None = None,
        discovered_conflict_writer: DiscoveredConflictWriter | None = None,
        # Embedding / ChromaDB (shared)
        chunker: TextChunker | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        chroma_client: ChromaClient | None = None,
    ) -> None:
        self.extractor = extractor
        self.stage_writer = stage_writer
        self.max_retries = max_retries
        # Track B
        self.fact_extractor = fact_extractor
        self.fact_writer = fact_writer
        # Track A
        self.dynamic_extractor = dynamic_extractor
        self.discovered_fact_writer = discovered_fact_writer
        self.discovered_conflict_writer = discovered_conflict_writer
        # Shared
        self.chunker = chunker or TextChunker()
        self.embedding_provider = embedding_provider
        self.chroma_client = chroma_client
        self.conflict_detector = ConflictDetector()

    async def run(
        self,
        user_id: str,
        document_id: str,
        storage_reference: str,
        on_update: Callable[[dict[str, object]], Awaitable[None]],
        document_name: str = "document.pdf",
    ) -> NormalizedDocument:
        await self.stage_writer.record_stage(user_id, document_id, "upload", "completed")
        await self._stage(user_id, document_id, "validation", "started", on_update)
        path = Path(storage_reference)
        await self._stage(user_id, document_id, "validation", "completed", on_update)
        try:
            await self._stage(user_id, document_id, "parsing", "started", on_update)
            result = self.extractor.extract(str(path), document_name=document_name)
            direct_present = any(
                span.source_method == "direct-parse" for page in result.pages for span in page.spans
            )
            ocr_present = any(
                span.source_method == "ocr" for page in result.pages for span in page.spans
            )
            await self._stage(
                user_id, document_id, "parsing",
                "completed" if direct_present else "skipped", on_update,
            )
            await self._stage(
                user_id, document_id, "ocr",
                "completed" if ocr_present else "skipped", on_update,
            )
            await self._stage(user_id, document_id, "normalization", "completed", on_update)
            await self._stage(user_id, document_id, "extraction", "started", on_update)

            now = datetime.now(UTC)

            # ----------------------------------------------------------------
            # TRACK A: Document-agnostic dynamic entity discovery (primary)
            # ----------------------------------------------------------------
            if self.dynamic_extractor is not None:
                await self._run_dynamic_extraction(user_id, document_id, result, now)

            # ----------------------------------------------------------------
            # TRACK B: Ontology-mapped extraction (secondary / validation)
            # ----------------------------------------------------------------
            if self.fact_extractor is not None and self.fact_writer is not None:
                await self._run_ontology_extraction(user_id, document_id, result, now)

            await self._stage(user_id, document_id, "extraction", "completed", on_update)

            # ----------------------------------------------------------------
            # EMBEDDING + CHROMADB
            # ----------------------------------------------------------------
            await self._stage(user_id, document_id, "embedding", "started", on_update)
            chunks = []
            embeddings = []
            if self.chunker is not None:
                chunks = self.chunker.chunk_document(result, user_id, document_id, document_name)
            if chunks and self.embedding_provider is not None:
                texts = [c.text for c in chunks]
                embeddings = self.embedding_provider.embed_texts(texts)
            await self._stage(user_id, document_id, "embedding", "completed", on_update)

            await self._stage(user_id, document_id, "mongodb_storage", "completed", on_update)

            await self._stage(user_id, document_id, "chromadb_storage", "started", on_update)
            if chunks and embeddings and self.chroma_client is not None:
                await self.chroma_client.add_chunks(chunks, embeddings)
            await self._stage(
                user_id, document_id, "chromadb_storage",
                "completed" if chunks else "skipped", on_update,
            )

            await self._stage(user_id, document_id, "completed", "completed", on_update)
            return result

        except OCRUnavailableError:
            await self.stage_writer.record_stage(
                user_id, document_id, "ocr", "failed", "OCR service unavailable"
            )
            raise
        except Exception as error:
            await self.stage_writer.record_stage(
                user_id, document_id, "completed", "failed", str(error)
            )
            raise

    # ------------------------------------------------------------------
    # Track A: Dynamic extraction
    # ------------------------------------------------------------------

    async def _run_dynamic_extraction(
        self,
        user_id: str,
        document_id: str,
        result: NormalizedDocument,
        now: datetime,
    ) -> None:
        try:
            dyn_output: DynamicExtractionOutput = self.dynamic_extractor.extract(result, document_id)
            if dyn_output.document_status == "FAILED":
                logger.warning("dynamic_extraction_failed document_id=%s", document_id)
                return

            # Collect all attributes from entities + top-level discovered_fields
            all_attrs: list[DiscoveredAttribute] = list(dyn_output.discovered_fields)
            for entity in dyn_output.entities:
                for attr in entity.attributes:
                    if not attr.entity_id:
                        attr.entity_id = entity.entity_id
                all_attrs.extend(entity.attributes)

            # Detect intra-document conflicts BEFORE storing
            intra_conflicts = self.conflict_detector.find_intra_document_conflicts(
                all_attrs, document_id
            )

            if self.discovered_fact_writer is not None:
                for attr in all_attrs:
                    conflict_status = "CONFLICT" if attr.semantic_type in intra_conflicts else "OK"
                    entity_type = None
                    for entity in dyn_output.entities:
                        if entity.entity_id == attr.entity_id:
                            entity_type = entity.entity_type
                            break

                    fact = DiscoveredFact(
                        user_id=user_id,
                        source_document_id=document_id,
                        source_page=attr.evidence.page,
                        entity_id=attr.entity_id,
                        entity_type=entity_type,
                        field=attr.field,
                        semantic_type=attr.semantic_type,
                        value=attr.value,
                        data_type=attr.data_type,
                        confidence=attr.confidence,
                        evidence_text=attr.evidence.text,
                        ontology=attr.ontology,
                        ontology_confidence=attr.ontology_confidence,
                        unit=attr.unit,
                        currency=attr.currency,
                        date_format=attr.date_format,
                        normalization=attr.normalization,
                        conflict_status=conflict_status,
                        document_type=dyn_output.document_type,
                        created_at=now,
                        updated_at=now,
                    )
                    try:
                        await self.discovered_fact_writer.upsert_discovered_fact(user_id, fact)
                    except Exception as exc:
                        logger.error("discovered_fact_write_error field=%s err=%s", attr.field, exc)

            # Store intra-document conflicts
            if intra_conflicts and self.discovered_conflict_writer is not None:
                for semantic_type, conflicting_attrs in intra_conflicts.items():
                    candidates = [
                        {
                            "value": a.value,
                            "document_id": document_id,
                            "page": a.evidence.page,
                            "confidence": a.confidence,
                            "evidence": a.evidence.text,
                        }
                        for a in conflicting_attrs
                    ]
                    conflict_doc = DiscoveredConflict(
                        user_id=user_id,
                        field=conflicting_attrs[0].field,
                        semantic_type=semantic_type,
                        ontology=conflicting_attrs[0].ontology,
                        conflict_type="INTRA_DOCUMENT",
                        candidates=candidates,
                        created_at=now,
                        updated_at=now,
                    )
                    try:
                        await self.discovered_conflict_writer.create(user_id, conflict_doc)
                    except Exception as exc:
                        logger.error("intra_conflict_write_error: %s", exc)

            # Detect cross-document conflicts
            if self.discovered_fact_writer is not None and self.discovered_conflict_writer is not None:
                cross_conflicts = await self.conflict_detector.find_cross_document_conflicts(
                    all_attrs, user_id, document_id, self.discovered_fact_writer
                )
                for conflict_dict in cross_conflicts:
                    try:
                        c_now = conflict_dict.pop("created_at", now)
                        u_now = conflict_dict.pop("updated_at", now)
                        conflict_doc = DiscoveredConflict(
                            created_at=c_now,
                            updated_at=u_now,
                            **conflict_dict,
                        )
                        await self.discovered_conflict_writer.create(user_id, conflict_doc)
                    except Exception as exc:
                        logger.error("cross_conflict_write_error: %s", exc)

        except Exception as exc:
            logger.error("dynamic_extraction_error document_id=%s: %s", document_id, exc)

    # ------------------------------------------------------------------
    # Track B: Ontology-mapped extraction (legacy, secondary validation)
    # ------------------------------------------------------------------

    async def _run_ontology_extraction(
        self,
        user_id: str,
        document_id: str,
        result: NormalizedDocument,
        now: datetime,
    ) -> None:
        try:
            llm_output = self.fact_extractor.extract(result, document_id)
            if llm_output.document_status not in ("PROCESSED", "PARTIAL"):
                return

            for fact in llm_output.facts:
                structured = StructuredFact(
                    user_id=user_id,
                    concept=fact.ontology,
                    value=fact.value,
                    value_type=fact.data_type,
                    source_document_id=fact.evidence.document_id,
                    source_page=fact.evidence.page,
                    confidence=fact.confidence,
                    provenance={"extracted_text": fact.evidence.text, "extraction_method": "llm"},
                    status="EXTRACTED",
                    is_user_confirmed=False,
                    created_at=now,
                    updated_at=now,
                )
                if hasattr(self.fact_writer, "upsert_fact"):
                    await self.fact_writer.upsert_fact(user_id, structured)
                else:
                    await self.fact_writer.create(user_id, structured)

            for conflict in llm_output.conflicts:
                candidates = [
                    {
                        "value": c.value,
                        "confidence": c.confidence,
                        "provenance": {
                            "extracted_text": c.evidence.text,
                            "document_id": c.evidence.document_id,
                            "page": c.evidence.page,
                        },
                    }
                    for c in conflict.candidates
                ]
                structured_conflict = StructuredFact(
                    user_id=user_id,
                    concept=conflict.ontology or "unknown",
                    value=None,
                    value_type="unknown",
                    source_document_id=document_id,
                    confidence=0.5,
                    status="CONFLICT",
                    candidates=candidates,
                    is_user_confirmed=False,
                    created_at=now,
                    updated_at=now,
                )
                if hasattr(self.fact_writer, "upsert_fact"):
                    await self.fact_writer.upsert_fact(user_id, structured_conflict)
                else:
                    await self.fact_writer.create(user_id, structured_conflict)

        except Exception as exc:
            logger.error("ontology_extraction_error document_id=%s: %s", document_id, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _stage(
        self,
        user_id: str,
        document_id: str,
        stage: str,
        status: str,
        on_update: Callable[[dict[str, object]], Awaitable[None]],
    ) -> None:
        await self.stage_writer.record_stage(user_id, document_id, stage, status)
        await on_update({"current_stage": stage, "progress": _progress(stage)})


def _progress(stage: str) -> int:
    try:
        return min(99, max(0, int((STAGES.index(stage) + 1) * 100 / len(STAGES))))
    except ValueError:
        return 0
