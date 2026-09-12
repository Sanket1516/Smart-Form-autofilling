"""Direct PDF parsing and PaddleOCR fallback adapters."""

from typing import Any, Protocol

from app.processing.preprocessing import preprocess_for_ocr
from app.processing.schemas import ExtractedSpan, LayoutBox, NormalizedDocument, NormalizedPage


class OCRUnavailableError(RuntimeError):
    """Raised when OCR dependencies or the OCR engine are unavailable."""


class OCRAdapter(Protocol):
    def extract(self, image: Any, page_number: int) -> list[ExtractedSpan]: ...


class PaddleOCRAdapter:
    """Lazy PaddleOCR adapter to keep API startup independent from OCR loading."""

    def __init__(self, language: str = "en") -> None:
        self.language = language
        self._engine: Any | None = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as error:
                raise OCRUnavailableError("PaddleOCR is not installed") from error
            self._engine = PaddleOCR(lang=self.language, use_doc_orientation_classify=False)
        return self._engine

    def extract(self, image: Any, page_number: int) -> list[ExtractedSpan]:
        processed = preprocess_for_ocr(image)
        result = self._get_engine().predict(processed)
        spans: list[ExtractedSpan] = []
        for page_result in result:
            data = page_result.json if hasattr(page_result, "json") else page_result
            spans.extend(_spans_from_paddle(data, page_number))
        return spans


def _spans_from_paddle(data: Any, page_number: int) -> list[ExtractedSpan]:
    if isinstance(data, dict) and "res" in data:
        data = data["res"]
    if not isinstance(data, dict):
        return []
    texts = data.get("rec_texts", [])
    boxes = data.get("rec_boxes", [])
    scores = data.get("rec_scores", [])
    spans: list[ExtractedSpan] = []
    for index, text in enumerate(texts):
        if not text or (scores and float(scores[index]) < 0.35):
            continue
        box = boxes[index] if index < len(boxes) else None
        bbox = None
        if box is not None and len(box) >= 4:
            values = [float(value) for value in box]
            bbox = LayoutBox(x0=values[0], top=values[1], x1=values[2], bottom=values[3])
        spans.append(
            ExtractedSpan(page_number=page_number, text=str(text), source_method="ocr", bbox=bbox)
        )
    return spans


class PDFExtractor:
    def __init__(self, ocr: OCRAdapter | None = None, resolution: int = 150) -> None:
        self.ocr = ocr or PaddleOCRAdapter()
        self.resolution = resolution

    def extract(self, path: str) -> NormalizedDocument:
        try:
            import pdfplumber
        except ImportError as error:
            raise RuntimeError("pdfplumber is not installed") from error

        pages: list[NormalizedPage] = []
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                spans = self._direct_spans(page, page_number)
                if not any(span.text.strip() for span in spans):
                    spans = self._ocr_page(page, page_number)
                pages.append(
                    NormalizedPage(
                        page_number=page_number,
                        width=page.width,
                        height=page.height,
                        spans=spans,
                    )
                )
        return NormalizedDocument(pages=pages)

    @staticmethod
    def _direct_spans(page: Any, page_number: int) -> list[ExtractedSpan]:
        spans: list[ExtractedSpan] = []
        text = page.extract_text() or ""
        for line in text.splitlines():
            if line.strip():
                spans.append(
                    ExtractedSpan(
                        page_number=page_number,
                        text=line.strip(),
                        source_method="direct-parse",
                    )
                )
        for table in page.extract_tables() or []:
            rows = [" | ".join(str(cell or "").strip() for cell in row) for row in table]
            table_text = "\n".join(row for row in rows if row.strip())
            if table_text:
                spans.append(
                    ExtractedSpan(
                        page_number=page_number,
                        text=table_text,
                        source_method="direct-parse",
                        is_table=True,
                    )
                )
        return spans

    def _ocr_page(self, page: Any, page_number: int) -> list[ExtractedSpan]:
        try:
            image = page.to_image(resolution=self.resolution).original
        except Exception as error:
            raise OCRUnavailableError("Unable to render PDF page for OCR") from error
        return self.ocr.extract(image, page_number)
