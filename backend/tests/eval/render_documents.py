"""Render the synthetic document fixtures as real files for OCR and end-to-end tests.

    cd backend
    python -m tests.eval.render_documents --out ../test-data/rendered

For every fixture in ``tests.indian_fixtures.DOCUMENTS`` (and the held-out set)
this writes:

* ``<id>.digital.pdf``   text PDF (pdfplumber reads it without OCR)
* ``<id>.clean.png``     scan-quality image (OCR)
* ``<id>.skew.png``      rotated by a few degrees
* ``<id>.rot90.png``     rotated by 90 degrees (phone photo taken sideways)
* ``<id>.photo.png``     low contrast, blur and noise (phone photo)
* ``<id>.scanned.pdf``   the clean image wrapped in a PDF (scanned PDF path)

plus ``manifest.json`` with the ground truth (expected fields and records).
Tables are drawn as real grids, one cell per column, so the OCR has to rebuild
rows from separate text boxes exactly as it must on a real marksheet.

All content is synthetic (see the fixture modules). Needs Pillow and reportlab.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from tests.heldout_fixtures import HELDOUT_DOCUMENTS
from tests.indian_fixtures import DOCUMENTS, DocFixture, T

WIDTH = 1700
MARGIN = 80
LINE_GAP = 18
FONT_CANDIDATES = (
    os.environ.get("RENDER_FONT", ""),
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
)
DEVANAGARI_FONTS = (
    os.environ.get("RENDER_FONT_DEVANAGARI", ""),
    "C:/Windows/Fonts/Nirmala.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
)


def _font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("No TrueType font found; set RENDER_FONT to a .ttf file")


def _has_devanagari(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def _items(page: list[object]) -> list[tuple[str, str]]:
    """[(kind, text)] with kind 'line' or 'table'."""
    out: list[tuple[str, str]] = []
    table_next = False
    for item in page:
        if item == T:
            table_next = True
            continue
        out.append(("table" if table_next else "line", str(item)))
        table_next = False
    return out


def render_page(page: list[object], font_size: int = 30) -> Image.Image:
    latin = _font(FONT_CANDIDATES, font_size)
    deva = _font(DEVANAGARI_FONTS, font_size)
    items = _items(page)
    # Text lines that duplicate a following table are part of the fixture's
    # "what pdfplumber saw" model; a real page shows the table once, as a grid.
    has_table = any(kind == "table" for kind, _ in items)
    table_rows = {
        " ".join(cell.strip() for cell in row.split("|") if cell.strip()).casefold()
        for kind, text in items
        if kind == "table"
        for row in text.split("\n")
    }
    lines: list[tuple[str, str]] = []
    for kind, text in items:
        if kind == "line" and has_table and " ".join(text.split()).casefold() in table_rows:
            continue
        if kind == "line" and has_table and _looks_like_unpiped_row(text, table_rows):
            continue
        lines.append((kind, text))
    height = MARGIN * 2
    for kind, text in lines:
        rows = text.split("\n") if kind == "table" else [text]
        height += len(rows) * (font_size + LINE_GAP + (14 if kind == "table" else 0))
    image = Image.new("RGB", (WIDTH, max(height, 600)), "white")
    draw = ImageDraw.Draw(image)
    y = MARGIN
    for kind, text in lines:
        if kind == "line":
            font = deva if _has_devanagari(text) else latin
            draw.text((MARGIN, y), text, fill="black", font=font)
            y += font_size + LINE_GAP
            continue
        rows = [[cell.strip() for cell in row.split("|")] for row in text.split("\n")]
        columns = max(len(row) for row in rows)
        widths = [0] * columns
        for row in rows:
            for index, cell in enumerate(row):
                widths[index] = max(widths[index], int(draw.textlength(cell, font=latin)) + 40)
        scale = min(1.0, (WIDTH - 2 * MARGIN) / max(1, sum(widths)))
        widths = [int(w * scale) for w in widths]
        row_height = font_size + LINE_GAP + 14
        for row in rows:
            x = MARGIN
            for index in range(columns):
                cell = row[index] if index < len(row) else ""
                draw.rectangle([x, y, x + widths[index], y + row_height], outline="black", width=2)
                draw.text((x + 12, y + 8), cell, fill="black", font=latin)
                x += widths[index]
            y += row_height
        y += LINE_GAP
    return image


def _looks_like_unpiped_row(text: str, table_rows: set[str]) -> bool:
    normalized = " ".join(text.split()).casefold()
    return any(normalized.replace(" ", "") == row.replace(" ", "") for row in table_rows if row)


def degrade(image: Image.Image, variant: str, seed: int) -> Image.Image:
    rng = random.Random(seed)
    if variant == "clean":
        return image
    if variant == "skew":
        return image.rotate(rng.choice((-4, -3, 3, 4)), expand=True, fillcolor="white")
    if variant == "rot90":
        return image.rotate(90, expand=True, fillcolor="white")
    if variant == "photo":
        import numpy as np

        img = image.convert("L").filter(ImageFilter.GaussianBlur(1.2))
        array = np.asarray(img, dtype=np.float32)
        array = 70 + array * 0.55  # washed out, low contrast
        gradient = np.linspace(0, 40, array.shape[1], dtype=np.float32)[None, :]
        array = array - gradient  # uneven lighting
        array += np.random.default_rng(seed).normal(0, 9, array.shape)
        img = Image.fromarray(np.clip(array, 0, 255).astype("uint8")).convert("RGB")
        img = img.rotate(rng.choice((-1.5, 1.5)), expand=True, fillcolor=(150, 150, 150))
        return img.resize((int(img.width * 0.75), int(img.height * 0.75)))
    raise ValueError(variant)


def write_digital_pdf(fixture: DocFixture, path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    font_name = "Helvetica"
    for candidate in FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            pdfmetrics.registerFont(TTFont("RenderSans", candidate))
            font_name = "RenderSans"
            break
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    for page in fixture.pages:
        y = height - 50
        for kind, text in _items(page):
            if kind == "table":
                continue  # the fixture repeats table rows as plain lines
            if _has_devanagari(text):
                text = "".join(ch for ch in text if not "\u0900" <= ch <= "\u097f").strip(" /")
                if not text:
                    continue
            size = 9
            pdf.setFont(font_name, size)
            pdf.drawString(40, y, text[:140])
            y -= 14
            if y < 40:
                pdf.showPage()
                y = height - 50
        pdf.showPage()
    pdf.save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../test-data/rendered")
    parser.add_argument("--variants", default="clean,skew,rot90,photo")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    fixtures = [*DOCUMENTS, *HELDOUT_DOCUMENTS]
    for seed, fixture in enumerate(fixtures):
        files: dict[str, str] = {}
        pages = [render_page(page) for page in fixture.pages]
        for variant in args.variants.split(","):
            if len(pages) != 1:
                break  # multi-page fixtures are covered by the PDF outputs
            name = f"{fixture.fixture_id}.{variant}.png"
            degrade(pages[0], variant, seed).save(out / name)
            files[variant] = name
        scanned = f"{fixture.fixture_id}.scanned.pdf"
        pages[0].save(out / scanned, "PDF", resolution=200, save_all=True, append_images=pages[1:])
        files["scanned_pdf"] = scanned
        digital = f"{fixture.fixture_id}.digital.pdf"
        write_digital_pdf(fixture, out / digital)
        files["digital_pdf"] = digital
        manifest.append(
            {
                "fixture": fixture.fixture_id,
                "document_type": fixture.document_type,
                "variant": fixture.variant,
                "files": files,
                "expected": fixture.expected,
                "absent": list(fixture.absent),
                "records": fixture.records,
                "lines": [text for page in fixture.pages for kind, text in _items(page)],
            }
        )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), "utf-8")
    print(f"rendered {len(manifest)} fixtures into {out}")


if __name__ == "__main__":
    main()
