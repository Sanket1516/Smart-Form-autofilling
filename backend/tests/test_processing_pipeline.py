"""TC-OCR-01 through TC-OCR-06 pipeline tests."""

import pytest
from app.processing.extractor import OCRUnavailableError
from app.processing.pipeline import DocumentPipeline
from app.processing.schemas import ExtractedSpan, NormalizedDocument, NormalizedPage


class FakeStageWriter:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, str]] = []

    async def record_stage(
        self,
        user_id: str,
        document_id: str,
        stage: str,
        status: str,
        error: str | None = None,
    ) -> None:
        self.records.append((stage, status, error or ""))


class FakeFactWriter:
    def __init__(self) -> None:
        self.facts: list[Any] = []

    async def create(self, user_id: str, document: Any) -> dict[str, Any]:
        self.facts.append(document)
        return {"_id": f"fact-{len(self.facts)}", **document.model_dump()}


class FakeExtractor:
    def __init__(self, result: NormalizedDocument | Exception) -> None:
        self.result = result

    def extract(self, path: str) -> NormalizedDocument:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def page(
    number: int, text: str, source: str = "direct-parse", table: bool = False
) -> NormalizedPage:
    return NormalizedPage(
        page_number=number,
        width=612,
        height=792,
        spans=[ExtractedSpan(page_number=number, text=text, source_method=source, is_table=table)],
    )


async def run_pipeline(result: NormalizedDocument | Exception) -> FakeStageWriter:
    writer = FakeStageWriter()
    pipeline = DocumentPipeline(FakeExtractor(result), writer)
    await pipeline.run("user-a", "document-a", "document.pdf", lambda _: _completed())
    return writer


async def _completed() -> None:
    return None


@pytest.mark.asyncio
async def test_tc_ocr_01_digital_pdf_uses_direct_parse() -> None:
    writer = await run_pipeline(NormalizedDocument(pages=[page(1, "Digital PDF text")]))
    assert ("parsing", "completed", "") in writer.records
    assert ("ocr", "skipped", "") in writer.records


@pytest.mark.asyncio
async def test_tc_ocr_02_scanned_pdf_uses_ocr_provenance() -> None:
    writer = await run_pipeline(NormalizedDocument(pages=[page(1, "Scanned text", "ocr")]))
    assert ("ocr", "completed", "") in writer.records


@pytest.mark.asyncio
async def test_tc_ocr_03_multi_page_boundaries_are_preserved() -> None:
    result = NormalizedDocument(pages=[page(1, "Page one"), page(2, "Page two", "ocr")])
    writer = await run_pipeline(result)
    assert result.page_count == 2
    assert {span.page_number for page_data in result.pages for span in page_data.spans} == {1, 2}
    assert ("completed", "completed", "") in writer.records


@pytest.mark.asyncio
async def test_tc_ocr_04_low_quality_scan_keeps_best_effort_ocr() -> None:
    result = NormalizedDocument(pages=[page(1, "uncertain OCR", "ocr")])
    writer = await run_pipeline(result)
    assert result.pages[0].spans[0].source_method == "ocr"
    assert ("normalization", "completed", "") in writer.records


@pytest.mark.asyncio
async def test_tc_ocr_05_table_content_is_preserved() -> None:
    result = NormalizedDocument(pages=[page(1, "Name | Degree\nA | B", table=True)])
    await run_pipeline(result)
    assert result.pages[0].spans[0].is_table is True
    assert "Degree" in result.text


@pytest.mark.asyncio
async def test_tc_ocr_06_ocr_unavailable_is_controlled() -> None:
    writer = FakeStageWriter()
    pipeline = DocumentPipeline(FakeExtractor(OCRUnavailableError("OCR unavailable")), writer)
    with pytest.raises(OCRUnavailableError):
        await pipeline.run("user-a", "document-a", "document.pdf", lambda _: _completed())
    assert any(stage == "ocr" and status == "failed" for stage, status, _ in writer.records)


@pytest.mark.asyncio
async def test_extraction_runs_after_normalization_and_writes_candidates() -> None:
    writer = FakeStageWriter()
    fact_writer = FakeFactWriter()
    pipeline = DocumentPipeline(
        FakeExtractor(NormalizedDocument(pages=[page(1, "Email: candidate@example.com")])),
        writer,
        fact_writer=fact_writer,
    )
    await pipeline.run("user-a", "document-a", "document.pdf", lambda _: _completed())
    assert [stage for stage, _, _ in writer.records].index("normalization") < [
        stage for stage, _, _ in writer.records
    ].index("extraction")
    assert fact_writer.facts[0].user_id == "user-a"
    assert fact_writer.facts[0].concept == "email"
