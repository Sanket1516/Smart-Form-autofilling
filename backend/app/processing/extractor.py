"""Text extraction from PDF, DOCX, TXT and image documents.

Failures are explicit:

* ``DocumentReadError``: the file cannot be parsed (corrupt, encrypted, wrong
  content). The document is marked ``failed`` with the message.
* ``OCRUnavailableError``: the document needs OCR but no OCR engine is
  installed. The document is marked ``requires_review``.

The extractor never falls back to reading raw bytes as text.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from app.processing.preprocessing import preprocess_for_ocr
from app.processing.schemas import ExtractedSpan, LayoutBox, NormalizedDocument, NormalizedPage

logger = logging.getLogger(__name__)

_MIN_WORDS_PER_PAGE = 10


class DocumentReadError(RuntimeError):
    """The document could not be parsed. The message is safe to show to the user."""


class OCRUnavailableError(RuntimeError):
    """The document needs OCR but no OCR engine is available."""


class OCRAdapter(Protocol):
    def extract(self, image: Any, page_number: int) -> list[ExtractedSpan]: ...


class PaddleOCRAdapter:
    """Lazily loaded PaddleOCR 2.x engine (optional dependency)."""

    def __init__(self, language: str = "en") -> None:
        self.language = language
        self._engine: Any | None = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR  # type: ignore[import-not-found]
            except ImportError as error:
                raise OCRUnavailableError(
                    "This document needs OCR, but the OCR engine is not installed "
                    "(see backend/requirements-ocr.txt)."
                ) from error
            self._engine = PaddleOCR(lang=self.language, use_angle_cls=False, show_log=False)
        return self._engine

    def extract(self, image: Any, page_number: int) -> list[ExtractedSpan]:
        import numpy as np

        engine = self._get_engine()
        array = preprocess_for_ocr(
            np.array(image.convert("RGB")) if hasattr(image, "convert") else image
        )
        array = np.asarray(array)
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)
        result = engine.ocr(array, cls=False) or []
        spans: list[ExtractedSpan] = []
        for page in result:
            for line in page or []:
                if not line or len(line) < 2:
                    continue
                box, text_info = line[0], line[1]
                text, score = str(text_info[0]).strip(), float(text_info[1])
                if not text or score < 0.5:
                    continue
                xs = [float(point[0]) for point in box]
                ys = [float(point[1]) for point in box]
                spans.append(
                    ExtractedSpan(
                        page_number=page_number,
                        text=text,
                        source_method="ocr",
                        bbox=LayoutBox(x0=min(xs), top=min(ys), x1=max(xs), bottom=max(ys)),
                    )
                )
        return spans


class UniversalDocumentExtractor:
    """Dispatches on file extension: .pdf, .docx, .txt, .png, .jpg, .jpeg."""

    def __init__(self, ocr: OCRAdapter | None = None, resolution: int = 150) -> None:
        self.ocr = ocr or PaddleOCRAdapter()
        self.resolution = resolution

    def extract(self, path: str, document_name: str = "") -> NormalizedDocument:
        suffix = Path(document_name or path).suffix.lower() or Path(path).suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix == ".docx":
            return self._extract_docx(path)
        if suffix == ".txt":
            return self._extract_txt(path)
        if suffix in (".png", ".jpg", ".jpeg"):
            return self._extract_image(path)
        raise DocumentReadError(f"Unsupported document type: {suffix or 'unknown'}")

    # ------------------------------------------------------------------ PDF

    def _extract_pdf(self, path: str) -> NormalizedDocument:
        try:
            import pdfplumber
        except ImportError as error:  # pragma: no cover - dependency is required
            raise RuntimeError("pdfplumber is not installed") from error
        pages: list[NormalizedPage] = []
        warnings: list[str] = []
        ocr_missing = False
        try:
            with pdfplumber.open(path) as pdf:
                if not pdf.pages:
                    raise DocumentReadError("The PDF has no pages.")
                for number, page in enumerate(pdf.pages, start=1):
                    spans = _direct_spans(page, number)
                    if _word_count(spans) < _MIN_WORDS_PER_PAGE:
                        try:
                            image = page.to_image(resolution=self.resolution).original
                            ocr_spans = self.ocr.extract(image, number)
                        except OCRUnavailableError:
                            ocr_missing = True
                            ocr_spans = []
                        if _word_count(ocr_spans) > _word_count(spans):
                            spans = ocr_spans
                    pages.append(
                        NormalizedPage(
                            page_number=number, width=page.width, height=page.height, spans=spans
                        )
                    )
        except DocumentReadError:
            raise
        except Exception as error:
            logger.info("pdf_parse_failed", extra={"error_type": type(error).__name__})
            raise DocumentReadError(
                "The PDF could not be read. It may be corrupted or password-protected."
            ) from error
        document = NormalizedDocument(pages=pages)
        if ocr_missing:
            if not document.text.strip():
                raise OCRUnavailableError(
                    "This PDF is scanned and needs OCR, but the OCR engine is not installed."
                )
            warnings.append(
                "Some pages look scanned and were skipped because OCR is not installed."
            )
        document.warnings = warnings
        return document

    # ------------------------------------------------------------------ DOCX

    def _extract_docx(self, path: str) -> NormalizedDocument:
        try:
            import docx  # python-docx
        except ImportError as error:  # pragma: no cover - dependency is required
            raise RuntimeError("python-docx is not installed") from error
        try:
            word = docx.Document(path)
        except Exception as error:
            raise DocumentReadError("The Word document could not be read.") from error
        spans = [
            ExtractedSpan(page_number=1, text=paragraph.text.strip(), source_method="direct-parse")
            for paragraph in word.paragraphs
            if paragraph.text.strip()
        ]
        for table in word.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                line = " | ".join(cell for cell in cells if cell)
                if line:
                    spans.append(
                        ExtractedSpan(
                            page_number=1, text=line, source_method="direct-parse", is_table=True
                        )
                    )
        return NormalizedDocument(pages=[NormalizedPage(page_number=1, spans=spans)])

    # ------------------------------------------------------------------ TXT

    def _extract_txt(self, path: str) -> NormalizedDocument:
        try:
            content = Path(path).read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentReadError("The text file is not valid UTF-8.") from error
        spans = [
            ExtractedSpan(page_number=1, text=line.strip(), source_method="direct-parse")
            for line in content.splitlines()
            if line.strip()
        ]
        return NormalizedDocument(pages=[NormalizedPage(page_number=1, spans=spans)])

    # ------------------------------------------------------------------ images

    def _extract_image(self, path: str) -> NormalizedDocument:
        from PIL import Image, UnidentifiedImageError

        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                spans = self.ocr.extract(image.convert("RGB"), page_number=1)
        except UnidentifiedImageError as error:
            raise DocumentReadError("The image could not be read.") from error
        return NormalizedDocument(
            pages=[
                NormalizedPage(page_number=1, width=float(width), height=float(height), spans=spans)
            ]
        )


def _direct_spans(page: Any, page_number: int) -> list[ExtractedSpan]:
    spans = [
        ExtractedSpan(page_number=page_number, text=line.strip(), source_method="direct-parse")
        for line in (page.extract_text() or "").splitlines()
        if line.strip()
    ]
    for table in page.extract_tables() or []:
        rows = [" | ".join(str(cell or "").strip() for cell in row) for row in table]
        text = "\n".join(row for row in rows if row.strip(" |"))
        if text:
            spans.append(
                ExtractedSpan(
                    page_number=page_number, text=text, source_method="direct-parse", is_table=True
                )
            )
    return spans


def _word_count(spans: list[ExtractedSpan]) -> int:
    return sum(1 for span in spans for word in span.text.split() if any(c.isalnum() for c in word))
