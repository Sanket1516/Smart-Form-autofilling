"""OCR page reading: selective preprocessing, orientation, deskew and layout.

An OCR engine returns separate text boxes ("01", "ENGLISH", "100", "082"), not
lines. The extractors need lines in reading order ("Seat No: F123456") and,
for marksheets and statements, rows whose cells stay in their columns. This
module:

1. upscales small images and raises contrast only when the image is small or
   washed out (no blind binarisation: the detector works best on the original);
2. reads the page and, when the boxes look sideways or the read is poor, tries
   the 90/180/270 degree orientations and keeps the best-scoring one;
3. estimates skew from the detected text boxes (not from every dark pixel) and
   re-reads a deskewed copy only when that improves the result;
4. groups boxes into lines (one space between neighbouring words, a wide gap
   between distant cells so "Label: value    Label: value" stays separable)
   and turns runs of multi-cell lines into ``|``-separated table spans, with
   each cell assigned to the header column it sits under.

Low-confidence boxes are kept out of the text; the page records which steps
ran so a reviewer can see how the text was obtained.
"""

from __future__ import annotations

import logging
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.processing.schemas import ExtractedSpan, LayoutBox

logger = logging.getLogger(__name__)

MIN_BOX_CONFIDENCE = 0.5
_TARGET_LONG_SIDE = 1600
_MIN_LONG_SIDE = 1100
_MAX_LONG_SIDE = 3200
_WIDE_GAP = "    "  # >= 3 spaces: the extractors' "separate pairs" marker


@dataclass
class OCRBox:
    text: str
    score: float
    x0: float
    y0: float
    x1: float
    y1: float
    angle: float = 0.0  # degrees of the box's top edge

    @property
    def height(self) -> float:
        return max(1.0, self.y1 - self.y0)

    @property
    def width(self) -> float:
        return max(1.0, self.x1 - self.x0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


class OCREngine(Protocol):
    name: str

    def read(self, image: Any) -> list[OCRBox]:
        """Detect and recognise text in an RGB numpy image."""
        ...


@dataclass
class PageReading:
    boxes: list[OCRBox]
    steps: list[str] = field(default_factory=list)
    rotation: int = 0
    skew: float = 0.0

    @property
    def mean_confidence(self) -> float:
        return statistics.fmean(b.score for b in self.boxes) if self.boxes else 0.0


# ---------------------------------------------------------------------- image helpers


def to_rgb_array(image: Any) -> Any:
    import numpy as np

    if hasattr(image, "convert"):
        return np.array(image.convert("RGB"))
    array = np.asarray(image)
    if array.ndim == 2:
        return np.stack([array] * 3, axis=-1)
    return array[..., :3]


def rescale(array: Any) -> tuple[Any, str | None]:
    """Upscale small images (resolution improvement) and cap very large ones."""
    import cv2

    height, width = array.shape[:2]
    long_side = max(height, width)
    if long_side < _MIN_LONG_SIDE:
        factor = _TARGET_LONG_SIDE / long_side
        resized = cv2.resize(array, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
        return resized, f"upscale_x{factor:.1f}"
    if long_side > _MAX_LONG_SIDE:
        factor = _MAX_LONG_SIDE / long_side
        resized = cv2.resize(array, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
        return resized, f"downscale_x{factor:.2f}"
    return array, None


def is_low_contrast(array: Any) -> bool:
    """True when ink and paper are close in brightness (washed-out photo or faint print).

    Measured between the Otsu foreground and background means, so a mostly white
    page with sharp black text is not mistaken for a low-contrast one.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    threshold, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink, paper = gray[mask == 0], gray[mask > 0]
    if ink.size == 0 or paper.size == 0:
        return False
    return float(np.median(paper)) - float(np.median(ink)) < 110


def enhance_contrast(array: Any) -> Any:
    """Locally adaptive binarisation for washed-out or unevenly lit photos.

    Measured on the rendered benchmark: on blurred, low-contrast photos the text
    detector merges neighbouring table cells ("100" + "082" -> "100082") unless
    ink and paper are separated; a light blur first keeps noise from becoming ink.
    """
    import cv2

    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    block = max(15, (min(gray.shape[:2]) // 40) | 1)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 12
    )
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)


def rotate(array: Any, degrees: float) -> Any:
    """Rotate counter-clockwise by ``degrees`` (multiples of 90 are lossless)."""
    import cv2
    import numpy as np

    quarter = {
        90: cv2.ROTATE_90_COUNTERCLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_CLOCKWISE,
    }
    if int(degrees) % 360 in quarter and float(degrees).is_integer():
        return cv2.rotate(array, quarter[int(degrees) % 360])
    height, width = array.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_w, new_h = int(height * sin + width * cos), int(height * cos + width * sin)
    matrix[0, 2] += new_w / 2 - width / 2
    matrix[1, 2] += new_h / 2 - height / 2
    border = tuple(int(v) for v in np.median(array.reshape(-1, 3), axis=0))
    return cv2.warpAffine(array, matrix, (new_w, new_h), flags=cv2.INTER_CUBIC, borderValue=border)


# ---------------------------------------------------------------------- reading


def _is_tall(box: OCRBox) -> bool:
    return len(box.text) >= 3 and box.height > 1.5 * box.width


def _score(boxes: list[OCRBox]) -> float:
    """Recognised characters weighted by confidence, from upright boxes only.

    PaddleOCR turns tall crops sideways before recognition, so a sideways page
    can still be "read"; counting only upright boxes makes the upright
    orientation win, which is what line grouping needs.
    """
    return sum(
        b.score * len(b.text) for b in boxes if b.score >= MIN_BOX_CONFIDENCE and not _is_tall(b)
    )


def _sideways_ratio(boxes: list[OCRBox]) -> float:
    wordy = [b for b in boxes if len(b.text) >= 4]
    if not wordy:
        return 0.0
    return sum(1 for b in wordy if b.height > 1.5 * b.width) / len(wordy)


def estimate_skew(boxes: list[OCRBox]) -> float:
    """Median angle of long text boxes, in degrees (positive = counter-clockwise text)."""
    angles = [b.angle for b in boxes if b.width > 4 * b.height and len(b.text) >= 6]
    if len(angles) < 3:
        return 0.0
    return float(statistics.median(angles))


def read_page(engine: OCREngine, image: Any, preprocess: str = "auto") -> PageReading:
    """Read one page image with selective preprocessing (``auto``) or none (``none``)."""
    array = to_rgb_array(image)
    steps: list[str] = []
    if preprocess != "none":
        array, step = rescale(array)
        if step:
            steps.append(step)
        if is_low_contrast(array):
            array = enhance_contrast(array)
            steps.append("contrast")
    boxes = engine.read(array)
    best = PageReading(boxes=boxes, steps=list(steps))
    if preprocess == "none":
        return best

    sideways = _sideways_ratio(boxes) > 0.5
    poor = not boxes or best.mean_confidence < 0.8
    if sideways or poor:
        baseline = _score(best.boxes)
        chosen = 0
        for degrees in (90, 270, 180):
            candidate = engine.read(rotate(array, degrees))
            if _score(candidate) > max(baseline * 1.15, _score(best.boxes)):
                best = PageReading(candidate, [*steps, f"rotate_{degrees}"], rotation=degrees)
                chosen = degrees
        if chosen:
            array = rotate(array, chosen)

    skew = estimate_skew(best.boxes)
    if 0.7 <= abs(skew) <= 20:
        straightened = engine.read(rotate(array, -skew))
        if _score(straightened) >= _score(best.boxes):
            best = PageReading(
                straightened,
                [*best.steps, f"deskew_{skew:.1f}"],
                rotation=best.rotation,
                skew=skew,
            )
    return best


# ---------------------------------------------------------------------- layout


def group_lines(boxes: list[OCRBox]) -> list[list[OCRBox]]:
    """Group boxes into text lines, top to bottom, each sorted left to right.

    Vertical positions are corrected for the page skew measured from the boxes,
    so words of one slanted line stay together and neighbouring lines do not merge.
    """
    import math

    kept = [b for b in boxes if b.score >= MIN_BOX_CONFIDENCE]
    if not kept:
        return []
    skew = estimate_skew(kept)
    slope = math.tan(math.radians(skew)) if abs(skew) > 0.3 else 0.0

    def centre(box: OCRBox) -> float:
        return box.cy + ((box.x0 + box.x1) / 2) * slope

    def text_height(box: OCRBox) -> float:
        return max(box.height - box.width * abs(slope), box.height * 0.35)

    lines: list[list[OCRBox]] = []
    centres: list[list[float]] = []
    for box in sorted(kept, key=centre):
        c, h = centre(box), text_height(box)
        target = None
        for index in range(len(lines) - 1, max(-1, len(lines) - 4), -1):
            line_centre = statistics.fmean(centres[index])
            line_height = statistics.median(text_height(b) for b in lines[index])
            if abs(c - line_centre) < 0.5 * max(h, line_height):
                target = index
                break
        if target is None:
            lines.append([box])
            centres.append([c])
        else:
            lines[target].append(box)
            centres[target].append(c)
    order = sorted(range(len(lines)), key=lambda i: statistics.fmean(centres[i]))
    result = []
    for index in order:
        result.append(sorted(lines[index], key=lambda b: b.x0))
    return result


def split_cells(line: list[OCRBox]) -> list[list[OCRBox]]:
    """Split a line into cells wherever the gap is wider than about one text height.

    A normal word space is ~0.3 of the height; a column or "Label: value" gap is wider.
    """
    height = statistics.median(b.height for b in line)
    cells: list[list[OCRBox]] = [[line[0]]]
    for previous, box in zip(line, line[1:], strict=False):
        if box.x0 - previous.x1 > 0.9 * height:
            cells.append([box])
        else:
            cells[-1].append(box)
    return cells


def _cell_text(cell: list[OCRBox]) -> str:
    return " ".join(b.text for b in cell)


def line_text(line: list[OCRBox]) -> str:
    return _WIDE_GAP.join(_cell_text(cell) for cell in split_cells(line))


_HEADER_WORDS = re.compile(
    r"\b(subject|code|marks?|max|obtained|grade|total|date|particulars|description|narration|"
    r"debit|credit|withdrawal|deposit|balance|name|relation|age|cheque|ref)\b",
    re.I,
)


def _table_blocks(lines: list[list[OCRBox]]) -> list[tuple[int, int]]:
    """Runs of >= 3 consecutive lines with >= 3 cells each (start, end exclusive).

    The line just above a run is included when it reads like a column header
    (header cells are often close together, so it may split into fewer cells).
    """
    blocks = []
    start = None
    for index, line in enumerate([*lines, []]):
        many = bool(line) and len(split_cells(line)) >= 3
        if many and start is None:
            start = index
        elif not many and start is not None:
            if index - start >= 3:
                if start > 0 and len(_HEADER_WORDS.findall(line_text(lines[start - 1]))) >= 2:
                    start -= 1
                blocks.append((start, index))
            start = None
    return blocks


def _table_text(lines: list[list[OCRBox]]) -> str:
    """Rows of ``|``-separated cells aligned to the columns of the widest row.

    Each box goes to the column it overlaps most, so header words and cells that
    the engine read close together still land under the right column.
    """
    cell_rows = [split_cells(line) for line in lines]
    anchor = max(cell_rows, key=len)
    columns = [(min(b.x0 for b in c), max(b.x1 for b in c)) for c in anchor]
    out = []
    for line in lines:
        cells = [""] * len(columns)
        for box in line:
            centre = (box.x0 + box.x1) / 2
            best = min(
                range(len(columns)),
                key=lambda i: (
                    -max(0.0, min(box.x1, columns[i][1]) - max(box.x0, columns[i][0])),
                    abs(centre - (columns[i][0] + columns[i][1]) / 2),
                ),
            )
            cells[best] = f"{cells[best]} {box.text}".strip()
        out.append(" | ".join(cells))
    return "\n".join(out)


def spans_from_boxes(boxes: list[OCRBox], page_number: int) -> list[ExtractedSpan]:
    """Line spans in reading order, plus a table span for each detected grid."""
    lines = group_lines(boxes)
    spans = [
        ExtractedSpan(
            page_number=page_number,
            text=line_text(line),
            source_method="ocr",
            bbox=LayoutBox(
                x0=min(b.x0 for b in line),
                top=min(b.y0 for b in line),
                x1=max(b.x1 for b in line),
                bottom=max(b.y1 for b in line),
            ),
        )
        for line in lines
    ]
    for start, end in _table_blocks(lines):
        block = lines[start:end]
        spans.append(
            ExtractedSpan(
                page_number=page_number,
                text=_table_text(block),
                source_method="ocr",
                is_table=True,
                bbox=LayoutBox(
                    x0=min(b.x0 for line in block for b in line),
                    top=min(b.y0 for line in block for b in line),
                    x1=max(b.x1 for line in block for b in line),
                    bottom=max(b.y1 for line in block for b in line),
                ),
            )
        )
    return spans


# ---------------------------------------------------------------------- engines


def boxes_from_paddle(result: Any) -> list[OCRBox]:
    """Convert PaddleOCR 2.x output (``[[ [quad, (text, score)], ... ]]``)."""
    import math

    boxes: list[OCRBox] = []
    for page in result or []:
        for line in page or []:
            if not line or len(line) < 2:
                continue
            quad, (text, score) = line[0], line[1]
            text = str(text).strip()
            if not text:
                continue
            xs = [float(p[0]) for p in quad]
            ys = [float(p[1]) for p in quad]
            (tlx, tly), (trx, try_) = quad[0], quad[1]
            angle = -math.degrees(math.atan2(float(try_) - float(tly), float(trx) - float(tlx)))
            boxes.append(OCRBox(text, float(score), min(xs), min(ys), max(xs), max(ys), angle))
    return boxes
