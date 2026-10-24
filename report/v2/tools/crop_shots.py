# -*- coding: utf-8 -*-
"""Crops the raw screenshots (figures/screens, captured by capture.cjs) into the figures used in Chapter 5.
Boxes are in CSS pixels; the screenshots were taken at device scale factor 2.5."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "figures", "screens")
OUT = os.path.join(HERE, "..", "figures", "shots")
SCALE = 2.5
BOXES = {
    "dashboard": (222, 15, 978, 470),
    "document_details": (222, 10, 978, 607),
    "profile": (222, 15, 978, 476),
    "conflicts": (222, 15, 978, 626),
    "ask": (275, 0, 975, 590),
}


def crop(name, box, src=None):
    im = Image.open(os.path.join(SRC, (src or name) + ".png")).convert("RGB")
    l, t, r, b = (int(v * SCALE) for v in box)
    im.crop((l, t, r, b)).save(os.path.join(OUT, name + ".png"), optimize=True)


def border(im, w=2):
    out = Image.new("RGB", (im.width + 2 * w, im.height + 2 * w), (120, 120, 120))
    out.paste(im, (w, w))
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for k, box in BOXES.items():
        crop(k, box)
    crop("form_marks", (15, 750, 745, 1310), "form_filled")
    a = border(Image.open(os.path.join(SRC, "ext_review.png")).convert("RGB"))
    b = border(Image.open(os.path.join(SRC, "ext_done.png")).convert("RGB"))
    gap = 40
    pair = Image.new("RGB", (a.width + b.width + gap, max(a.height, b.height)), "white")
    pair.paste(a, (0, 0))
    pair.paste(b, (a.width + gap, 0))
    pair.save(os.path.join(OUT, "ext_pair.png"), optimize=True)
    print("cropped figures written to", OUT)
