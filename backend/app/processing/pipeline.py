"""Resilient document processing pipeline with stage provenance."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from app.db.chroma_client import ChromaClient
from app.extraction.llm_extractor import DocumentOntologyExtractor
from app.models.documents import StructuredFact
from app.processing.chunking import TextChunker
from app.processing.extractor import OCRUnavailableError, PDFExtractor
from app.processing.schemas import NormalizedDocument
from app.retrieval.embeddings import EmbeddingProvider

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


class PipelineRetryableError(RuntimeError):
    """A transient failure eligible for bounded queue retry."""


class PipelineResult(Protocol):
    page_count: int


class DocumentPipeline:
    def __init__(
        self,
        extractor: PDFExtractor,
        stage_writer: StageWriter,
        max_retries: int = 2,
        fact_extractor: DocumentOntologyExtractor | None = None,
        fact_writer: FactWriter | None = None,
        chunker: TextChunker | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        chroma_client: ChromaClient | None = None,
    ) -> None:
        self.extractor = extractor
        self.stage_writer = stage_writer
        self.max_retries = max_retries
        self.fact_extractor = fact_extractor
        self.fact_writer = fact_writer
        self.chunker = chunker or TextChunker()
        self.embedding_provider = embedding_provider
        self.chroma_client = chroma_client

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
                user_id,
                document_id,
                "parsing",
                "completed" if direct_present else "skipped",
                on_update,
            )
            await self._stage(
                user_id,
                document_id,
                "ocr",
                "completed" if ocr_present else "skipped",
                on_update,
            )
            await self._stage(user_id, document_id, "normalization", "completed", on_update)
            await self._stage(user_id, document_id, "extraction", "started", on_update)
            if self.fact_extractor is not None and self.fact_writer is not None:
                from datetime import datetime, UTC
                now = datetime.now(UTC)
                llm_output = self.fact_extractor.extract(result, document_id)
                if llm_output.document_status == "PROCESSED" or llm_output.document_status == "PARTIAL":
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
                            updated_at=now
                        )
                        if hasattr(self.fact_writer, "upsert_fact"):
                            await self.fact_writer.upsert_fact(user_id, structured)
                        else:
                            await self.fact_writer.create(user_id, structured)
                    for conflict in llm_output.conflicts:
                        candidates = []
                        for c in conflict.candidates:
                            candidates.append({
                                "value": c.value,
                                "confidence": c.confidence,
                                "provenance": {"extracted_text": c.evidence.text, "document_id": c.evidence.document_id, "page": c.evidence.page}
                            })
                        structured_conflict = StructuredFact(
                            user_id=user_id,
                            concept=conflict.ontology,
                            value=None,
                            value_type="unknown",
                            source_document_id=document_id,
                            confidence=0.5,
                            status="CONFLICT",
                            candidates=candidates,
                            is_user_confirmed=False,
                            created_at=now,
                            updated_at=now
                        )
                        if hasattr(self.fact_writer, "upsert_fact"):
                            await self.fact_writer.upsert_fact(user_id, structured_conflict)
                        else:
                            await self.fact_writer.create(user_id, structured_conflict)
            await self._stage(user_id, document_id, "extraction", "completed", on_update)

            await self._stage(user_id, document_id, "embedding", "started", on_update)
            chunks = []
            embeddings = []
            if self.chunker is not None:
                chunks = self.chunker.chunk_document(
                    result, user_id, document_id, document_name
                )
            if chunks and self.embedding_provider is not None:
                texts = [c.text for c in chunks]
                embeddings = self.embedding_provider.embed_texts(texts)
            await self._stage(user_id, document_id, "embedding", "completed", on_update)

            await self._stage(user_id, document_id, "mongodb_storage", "completed", on_update)

            await self._stage(user_id, document_id, "chromadb_storage", "started", on_update)
            if chunks and embeddings and self.chroma_client is not None:
                await self.chroma_client.add_chunks(chunks, embeddings)
            await self._stage(
                user_id,
                document_id,
                "chromadb_storage",
                "completed" if chunks else "skipped",
                on_update,
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
