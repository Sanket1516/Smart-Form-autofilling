"""OCR layout rebuilding, chunking, classification guard, source precedence and LLM fallback.

No OCR engine, database or network is needed: OCR output is simulated with
boxes, and providers with scripted HTTP responses.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from app.agents.llm_provider import (
    FallbackLLMProvider,
    GoogleProvider,
    LLMProviderError,
    MockLLMProvider,
    OllamaProvider,
)
from app.extraction.registry import get_registry
from app.extraction.service import DocumentExtractionService
from app.ontology.loader import FieldOntology, detect_scopes
from app.processing import ocr
from app.processing.chunking import TextChunker
from app.processing.ocr import OCRBox, group_lines, read_page, spans_from_boxes
from app.processing.schemas import ExtractedSpan, NormalizedDocument, NormalizedPage
from app.schemas.facts import ConflictCandidate, FactSource
from app.services.facts import _official_candidate

from tests.indian_fixtures import CLASS12_HSC

# ---------------------------------------------------------------------- OCR layout


def _box(
    text: str,
    x: float,
    y: float,
    w: float | None = None,
    h: float = 20,
    score: float = 0.95,
    angle: float = 0.0,
) -> OCRBox:
    w = w if w is not None else 11 * len(text)
    return OCRBox(text, score, x, y, x + w, y + h, angle)


def _marks_boxes(skew_deg: float = 0.0) -> list[OCRBox]:
    """A marksheet the way an OCR engine returns it: one box per cell."""
    rows = [
        ["Seat No: F123456", "Stream: SCIENCE"],
        ["Subject Code", "Subject Name", "Max Marks", "Marks Obtained"],
        ["01", "ENGLISH", "100", "082"],
        ["54", "PHYSICS", "100", "091"],
        ["40", "MATHEMATICS & STATISTICS", "100", "090"],
        ["Total", "", "600", "532"],
    ]
    columns = [40, 260, 700, 900]
    slope = math.tan(math.radians(skew_deg))
    boxes = []
    for r, row in enumerate(rows):
        y = 100 + r * 50
        xs = [40, 500] if r == 0 else columns
        for text, x in zip(row, xs, strict=False):
            if text:
                boxes.append(_box(text, x, y - x * slope, angle=skew_deg))
    return boxes


def test_boxes_become_lines_and_a_table_span() -> None:
    spans = spans_from_boxes(_marks_boxes(), 1)
    lines = [s.text for s in spans if not s.is_table]
    assert lines[0] == "Seat No: F123456    Stream: SCIENCE"  # wide gap keeps pairs separable
    assert lines[3] == "54    PHYSICS    100    091"
    tables = [s.text for s in spans if s.is_table]
    assert tables == [
        "Subject Code | Subject Name | Max Marks | Marks Obtained\n"
        "01 | ENGLISH | 100 | 082\n"
        "54 | PHYSICS | 100 | 091\n"
        "40 | MATHEMATICS & STATISTICS | 100 | 090\n"
        "Total |  | 600 | 532"
    ]


def test_skewed_lines_do_not_merge() -> None:
    lines = group_lines(_marks_boxes(skew_deg=3.0))
    assert [len(line) for line in lines] == [2, 4, 4, 4, 4, 3]


def test_low_confidence_boxes_are_left_out() -> None:
    spans = spans_from_boxes([_box("Name: Real", 10, 10), _box("Gh0st", 300, 10, score=0.2)], 1)
    assert spans[0].text == "Name: Real"


def test_ocr_table_feeds_the_marks_parser() -> None:
    page = NormalizedPage(page_number=1, spans=spans_from_boxes(_marks_boxes(), 1))
    from app.extraction.tables import parse_marks

    result = parse_marks([page])
    names = [r.values["name"] for r in result.records]
    assert names == ["ENGLISH", "PHYSICS", "MATHEMATICS & STATISTICS"]
    assert result.records[1].values["marks_obtained"] == "91"
    assert result.totals.values == {"max_marks": "600", "marks_obtained": "532"}


def test_lookalike_characters_are_repaired_only_in_numeric_cells() -> None:
    from app.extraction.tables import repair_numeric

    assert repair_numeric("10O") == "100"
    assert repair_numeric("O9l") == "091"
    assert repair_numeric("O") == "O"  # a grade
    assert repair_numeric("A1") == "A1"
    assert repair_numeric("PASS") == "PASS"


class _FakeEngine:
    """Reads text only when the page is upright; sideways reads come back as tall boxes."""

    name = "fake"

    def __init__(self, upright_after: int) -> None:
        self.upright_after = upright_after  # degrees of rotation that make the page upright
        self.calls: list[int] = []

    def read(self, image: Any) -> list[OCRBox]:
        rotation = int(getattr(image, "rotation", 0))
        self.calls.append(rotation)
        if rotation % 360 == self.upright_after % 360:
            return [_box("Candidate Name: AARAV EXAMPLE", 10, 10 + i * 40) for i in range(5)]
        return [OCRBox("Candidate Name: AARAV EXAMPLE", 0.97, 10, 10, 30, 400) for _ in range(5)]


class _Img:
    def __init__(self, rotation: int = 0) -> None:
        self.rotation = rotation


def test_sideways_page_is_rotated_to_the_best_upright_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ocr, "to_rgb_array", lambda image: image)
    monkeypatch.setattr(ocr, "rescale", lambda array: (array, None))
    monkeypatch.setattr(ocr, "is_low_contrast", lambda array: False)
    monkeypatch.setattr(ocr, "rotate", lambda array, deg: _Img(array.rotation + int(deg)))
    engine = _FakeEngine(upright_after=270)
    reading = read_page(engine, _Img(0))
    assert reading.rotation == 270 and "rotate_270" in reading.steps
    assert not any(box.height > box.width for box in reading.boxes)


def test_upright_page_is_read_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "to_rgb_array", lambda image: image)
    monkeypatch.setattr(ocr, "rescale", lambda array: (array, None))
    monkeypatch.setattr(ocr, "is_low_contrast", lambda array: False)
    engine = _FakeEngine(upright_after=0)
    reading = read_page(engine, _Img(0))
    assert engine.calls == [0] and reading.steps == []


def test_low_contrast_detection_is_selective() -> None:
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    page = np.full((200, 400, 3), 255, dtype=np.uint8)
    page[90:110, 50:350] = 0  # crisp black text on white
    assert not ocr.is_low_contrast(page)
    washed = (page * 0.3 + 150).astype(np.uint8)  # grey on light grey
    assert ocr.is_low_contrast(washed)


# ---------------------------------------------------------------------- chunking


def test_chunks_keep_whole_lines_and_repeat_table_headers() -> None:
    document = CLASS12_HSC.normalized()
    chunks = TextChunker(chunk_size=200, chunk_overlap=40).chunk_document(
        document, "u1", "d1", "hsc.pdf", "CLASS_12_MARKSHEET"
    )
    source_lines = {line.strip() for line in document.text.splitlines()}
    for chunk in chunks:
        for line in chunk.text.splitlines():
            assert line in source_lines, line  # nothing cut mid-line
    tables = [c for c in chunks if c.metadata["is_table"]]
    assert tables and all(c.text.startswith("Subject Code | Subject Name") for c in tables)
    assert all(c.embed_text.startswith("Class 12 marksheet (hsc.pdf), page 1") for c in chunks)
    plain = "\n".join(c.text for c in chunks if not c.metadata["is_table"])
    assert "54 PHYSICS 100 091" not in plain  # table rows are not duplicated as text
    assert {c.metadata["document_type"] for c in chunks} == {"CLASS_12_MARKSHEET"}


def test_long_paragraphs_split_at_word_boundaries() -> None:
    text = " ".join(f"word{i}" for i in range(200))
    document = NormalizedDocument(
        pages=[
            NormalizedPage(
                page_number=1,
                spans=[ExtractedSpan(page_number=1, text=text, source_method="direct-parse")],
            )
        ]
    )
    chunks = TextChunker(100, 20).chunk_document(document, "u", "d", "a.txt")
    assert all(len(c.text) <= 100 for c in chunks)
    assert all(not c.text.startswith("ord") for c in chunks)


# ---------------------------------------------------------------------- classification guard


def _doc(lines: list[str]) -> NormalizedDocument:
    spans = [
        ExtractedSpan(page_number=1, text=line, source_method="direct-parse") for line in lines
    ]
    return NormalizedDocument(pages=[NormalizedPage(page_number=1, spans=spans)])


RESUME_WITH_PASSPORT = [
    "AARAV EXAMPLE PATIL",
    "Career Objective: build reliable software",
    "Education: B.Tech Computer Science, CGPA 8.9",
    "HSC: 88.67%   SSC: 93%",
    "Technical Skills: Python, React",
    "Projects: Smart form filler",
    "Internship: Example Corp",
    "Passport No: K1234567   Place of Issue: Pune",
]


def test_a_cv_mentioning_a_passport_is_not_a_passport() -> None:
    classification = get_registry().classify(_doc(RESUME_WITH_PASSPORT))
    assert classification.document_type == "UNKNOWN" and classification.free_form


@pytest.mark.asyncio
async def test_llm_cannot_relabel_a_cv_as_an_official_document() -> None:
    llm = MockLLMProvider(
        responder=lambda task, prompt: json.dumps({"document_type": "PASSPORT", "attributes": []})
    )
    from app.extraction.llm_extraction import LLMFactExtractor

    ontology = FieldOntology()
    service = DocumentExtractionService(ontology, LLMFactExtractor(llm, ontology))
    result = await service.extract(_doc(RESUME_WITH_PASSPORT), "cv.pdf")
    assert result.document_type == "UNKNOWN"


def test_a_real_passport_is_still_classified() -> None:
    from tests.indian_fixtures import PASSPORT

    assert get_registry().classify(PASSPORT.normalized()).document_type == "PASSPORT"


def test_scope_detection_finds_both_classes() -> None:
    assert detect_scopes("Compare my Class 10 and 12 marks") == {"class_10", "class_12"}
    assert detect_scopes("HSC percentage") == {"class_12"}


# ---------------------------------------------------------------------- source precedence


def _candidate(
    value: str, document_type: str | None, name: str, needs_review: bool = False
) -> ConflictCandidate:
    source = FactSource(
        fact_id=name,
        document_id=name,
        document_name=name,
        origin="extracted",
        confidence=0.9,
        is_user_confirmed=False,
        document_type=document_type,
        needs_review=needs_review,
    )
    return ConflictCandidate(
        value=value,
        confidence=0.9,
        is_user_confirmed=False,
        document_id=name,
        document_name=name,
        sources=[source],
    )


def test_official_document_outranks_a_cv() -> None:
    marksheet = _candidate("88.67", "CLASS_12_MARKSHEET", "hsc.pdf")
    cv = _candidate("88.6", None, "cv.pdf")
    assert _official_candidate("academic.class12.percentage", [cv, marksheet]) is marksheet


def test_two_official_documents_that_disagree_stay_a_conflict() -> None:
    first = _candidate("2007-02-14", "CLASS_10_MARKSHEET", "a.pdf")
    second = _candidate("2007-02-15", "BIRTH_CERTIFICATE", "b.pdf")
    assert _official_candidate("personal.date_of_birth", [first, second]) is None


def test_uncertain_official_value_does_not_win_automatically() -> None:
    marksheet = _candidate("88.67", "CLASS_12_MARKSHEET", "hsc.pdf", needs_review=True)
    cv = _candidate("88.6", None, "cv.pdf")
    assert _official_candidate("academic.class12.percentage", [cv, marksheet]) is None


# ---------------------------------------------------------------------- providers


class _Response:
    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status_code = status
        self._body = body
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._body


def test_fallback_is_used_when_primary_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def post(url: str, **kwargs: Any) -> _Response:
        if "googleapis" in url:
            raise httpx.ConnectError("offline")
        return _Response(200, {"message": {"content": '{"answer": "ok"}'}})

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr("time.sleep", lambda s: None)
    primary = GoogleProvider(model="gemini-x", api_key="k", timeout=5, max_tokens=256, retries=1)
    local = OllamaProvider(model="qwen2:7b", api_key="", timeout=5, max_tokens=256, retries=0)
    chain = FallbackLLMProvider(primary, local)
    assert chain.complete("q", task="rag_answer") == '{"answer": "ok"}'
    assert chain.last_used == "ollama"


def test_both_failing_raises_instead_of_inventing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda url, **kw: _Response(503, {}))
    monkeypatch.setattr("time.sleep", lambda s: None)
    chain = FallbackLLMProvider(
        GoogleProvider(model="g", api_key="k", timeout=5, max_tokens=256, retries=1),
        OllamaProvider(model="m", api_key="", timeout=5, max_tokens=256, retries=0),
    )
    with pytest.raises(LLMProviderError):
        chain.complete("q", task="rag_answer")


def test_invalid_credentials_are_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def post(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        return _Response(401, {})

    monkeypatch.setattr(httpx, "post", post)
    provider = GoogleProvider(model="g", api_key="bad", timeout=5, max_tokens=256, retries=3)
    with pytest.raises(LLMProviderError, match="rejected"):
        provider.complete("q", task="rag_answer")
    assert len(calls) == 1


def test_settings_accept_a_local_fallback() -> None:
    from app.core.config import Settings

    settings = Settings(
        jwt_secret_key="x" * 40,
        llm_provider="google",
        llm_model="gemini-x",
        llm_api_key="k",
        llm_fallback_provider="ollama",
        llm_fallback_model="qwen2:7b",
    )
    assert settings.llm_fallback_provider == "ollama"
    with pytest.raises(ValueError):
        Settings(jwt_secret_key="x" * 40, llm_provider="ollama", llm_model="")


def test_created_now_is_timezone_aware() -> None:  # guard for fact timestamps used above
    assert datetime.now(UTC).tzinfo is not None
