"""Resilient document processing pipeline with stage provenance."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from app.extraction.facts import CandidateFactExtractor, with_user_id
from app.models.documents import StructuredFact
from app.processing.extractor import OCRUnavailableError, PDFExtractor
from app.processing.schemas import NormalizedDocument

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
        fact_extractor: CandidateFactExtractor | None = None,
        fact_writer: FactWriter | None = None,
    ) -> None:
        self.extractor = extractor
        self.stage_writer = stage_writer
        self.max_retries = max_retries
        self.fact_extractor = fact_extractor
        self.fact_writer = fact_writer

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
        if path.suffix.lower() != ".pdf":
            await self._stage(user_id, document_id, "validation", "completed", on_update)
            raise ValueError("processing currently requires a PDF document")
        await self._stage(user_id, document_id, "validation", "completed", on_update)
        try:
            await self._stage(user_id, document_id, "parsing", "started", on_update)
            result = self.extractor.extract(str(path))
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
                for fact in self.fact_extractor.extract(result, document_id, document_name):
                    await self.fact_writer.create(user_id, with_user_id(fact, user_id))
            await self._stage(user_id, document_id, "extraction", "completed", on_update)
            await self._stage(user_id, document_id, "embedding", "skipped", on_update)
            await self._stage(user_id, document_id, "mongodb_storage", "completed", on_update)
            await self._stage(user_id, document_id, "chromadb_storage", "skipped", on_update)
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
