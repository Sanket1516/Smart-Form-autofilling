"""OCR benchmark on rendered synthetic documents (needs PaddleOCR installed).

    cd backend
    python -m tests.eval.render_documents --out ../test-data/rendered
    python -m tests.eval.ocr_benchmark --data ../test-data/rendered --out ../docs/eval/ocr.json

Compares OCR configurations on the same images and scores each with:

* ``word_recall``: share of ground-truth words found in the OCR text;
* ``field_recall``: share of expected fields the deterministic extractor gets
  exactly right from that text (document classification included);
* ``record_recall``: share of expected table records (subjects, transactions)
  recovered with every expected cell correct;
* seconds per page.

Configurations:

* ``legacy``: the previous adapter (always Otsu-binarise, deskew from all dark
  pixels with ``minAreaRect``, one span per OCR box);
* ``layout_none``: the new layout rebuilding without image corrections;
* ``layout_auto``: the new layout rebuilding with selective corrections.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "eval-secret-key-that-is-long-enough-123456")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from app.extraction.normalize import comparison_key  # noqa: E402
from app.extraction.service import DocumentExtractionService  # noqa: E402
from app.ontology.loader import FieldOntology  # noqa: E402
from app.processing.extractor import PaddleOCRAdapter, RapidOCRAdapter  # noqa: E402
from app.processing.ocr import boxes_from_paddle  # noqa: E402
from app.processing.schemas import (  # noqa: E402
    ExtractedSpan,
    LayoutBox,
    NormalizedDocument,
    NormalizedPage,
)


def _legacy_preprocess(image: Any) -> Any:
    """The adapter's previous preprocessing, kept verbatim for comparison."""
    import cv2
    import numpy as np

    array = np.asarray(image)
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY) if len(array.shape) == 3 else array
    threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    sample_step = max(1, math.ceil(math.sqrt(threshold.size / 1_000_000)))
    sampled = threshold[::sample_step, ::sample_step]
    coordinates = np.column_stack(np.where(sampled < 255))
    if coordinates.shape[0] >= 3:
        angle = cv2.minAreaRect(coordinates)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.5:
            height, width = threshold.shape[:2]
            matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
            threshold = cv2.warpAffine(
                threshold,
                matrix,
                (width, height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
    return threshold


class LegacyAdapter:
    def __init__(self, paddle: PaddleOCRAdapter) -> None:
        self.paddle = paddle

    def extract(self, image: Any, page_number: int) -> list[ExtractedSpan]:
        import numpy as np

        array = np.asarray(_legacy_preprocess(np.array(image.convert("RGB"))))
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)
        spans = []
        for box in boxes_from_paddle(self.paddle._get_engine().ocr(array, cls=False)):
            if box.score < 0.5:
                continue
            spans.append(
                ExtractedSpan(
                    page_number=page_number,
                    text=box.text,
                    source_method="ocr",
                    bbox=LayoutBox(x0=box.x0, top=box.y0, x1=box.x1, bottom=box.y1),
                )
            )
        return spans


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9]+", text.casefold()) if len(w) > 1]


def word_recall(truth_lines: list[str], text: str) -> float:
    truth = _words(" ".join(truth_lines))
    found = set(_words(text))
    return sum(1 for w in truth if w in found) / max(1, len(truth))


def score_fields(
    candidates: list[Any], expected: dict[str, str], ontology: FieldOntology
) -> tuple[int, int]:
    correct = 0
    for concept, value in expected.items():
        data_type = ontology.data_type(concept) if ontology.is_known(concept) else "string"
        want = comparison_key(data_type, value)
        if any(
            c.concept == concept and comparison_key(data_type, c.value) == want for c in candidates
        ):
            correct += 1
    return correct, len(expected)


def score_records(
    candidates: list[Any], records: dict[str, list[dict[str, str]]]
) -> tuple[int, int]:
    expected = [row for rows in records.values() for row in rows]
    got = [c.value for c in candidates if isinstance(c.value, dict)]

    def norm(v: Any) -> str:
        text = str(v).strip().casefold()
        return text.lstrip("0") or text

    hit = 0
    for row in expected:
        if any(all(norm(r.get(k, "")) == norm(v) for k, v in row.items()) for r in got):
            hit += 1
    return hit, len(expected)


async def run(
    data: Path, configs: list[str], variants: list[str], limit: int | None
) -> dict[str, Any]:
    from PIL import Image

    manifest = json.loads((data / "manifest.json").read_text("utf-8"))[:limit]
    ontology = FieldOntology()
    service = DocumentExtractionService(ontology, llm_extractor=None)
    paddle_auto = PaddleOCRAdapter(preprocess="auto")
    factories = {
        "legacy": lambda: LegacyAdapter(paddle_auto),
        "layout_none": lambda: PaddleOCRAdapter(preprocess="none"),
        "layout_auto": lambda: paddle_auto,
        "rapid_auto": lambda: RapidOCRAdapter(preprocess="auto"),
    }
    results: dict[str, Any] = {}
    for config in configs:
        adapter = factories[config]()
        per_variant: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        rows = []
        for entry in manifest:
            for variant in variants:
                name = entry["files"].get(variant)
                if not name:
                    continue
                with Image.open(data / name) as image:
                    started = time.perf_counter()
                    spans = adapter.extract(image.convert("RGB"), 1)
                    seconds = time.perf_counter() - started
                document = NormalizedDocument(pages=[NormalizedPage(page_number=1, spans=spans)])
                extraction = await service.extract(document, name)
                fields_ok, fields_n = score_fields(
                    extraction.candidates, entry["expected"], ontology
                )
                rec_ok, rec_n = score_records(extraction.candidates, entry["records"])
                metrics = per_variant[variant]
                metrics["word_recall"].append(word_recall(entry["lines"], document.text))
                metrics["type_correct"].append(
                    float(extraction.document_type == entry["document_type"])
                )
                metrics["fields_ok"].append(fields_ok)
                metrics["fields_n"].append(fields_n)
                metrics["records_ok"].append(rec_ok)
                metrics["records_n"].append(rec_n)
                metrics["seconds"].append(seconds)
                rows.append(
                    {
                        "file": name,
                        "type_ok": extraction.document_type == entry["document_type"],
                        "fields": f"{fields_ok}/{fields_n}",
                        "records": f"{rec_ok}/{rec_n}",
                        "steps": list(getattr(adapter, "last_steps", [])),
                    }
                )
                print(config, rows[-1], flush=True)
        summary = {}
        for variant, m in per_variant.items():
            summary[variant] = {
                "documents": len(m["seconds"]),
                "word_recall": round(statistics.fmean(m["word_recall"]), 4),
                "classification_accuracy": round(statistics.fmean(m["type_correct"]), 4),
                "field_recall": round(sum(m["fields_ok"]) / max(1, sum(m["fields_n"])), 4),
                "record_recall": round(sum(m["records_ok"]) / max(1, sum(m["records_n"])), 4),
                "seconds_per_page": round(statistics.fmean(m["seconds"]), 2),
            }
        results[config] = {"summary": summary, "documents": rows}
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="../test-data/rendered")
    parser.add_argument("--out", default="")
    parser.add_argument("--configs", default="legacy,layout_auto")
    parser.add_argument("--variants", default="clean,skew,rot90,photo")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    results = asyncio.run(
        run(Path(args.data), args.configs.split(","), args.variants.split(","), args.limit)
    )
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "engine": "PaddleOCR 2.x (en), CPU",
        "results": {k: v["summary"] for k, v in results.items()},
        "documents": {k: v["documents"] for k, v in results.items()},
    }
    print(json.dumps(report["results"], indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1), "utf-8")


if __name__ == "__main__":
    main()
