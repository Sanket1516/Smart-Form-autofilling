"""Corrects the generated architecture diagram (Figure 4.1).

1. The dashed file-storage arrow ran into "Merge; keep page and evidence" and pointed down into File storage; in the
   system the "Read text" step reads the uploaded file, so the arrow now goes from File storage around the Merge
   card into "Read text".
2. Ask Documents also searches ChromaDB, so a connector from ChromaDB joins the MongoDB arrow into Ask Documents.
Usage: python patch_architecture_figure.py <source.png> <output.png>
"""
import sys
from PIL import Image, ImageDraw

im = Image.open(sys.argv[1]).convert("RGB")
dr = ImageDraw.Draw(im)
DASH = (7, 83, 191)
SOLID = (0, 69, 166)


def erase_h(x0, y0, x1, y1):
    """Erase a box by interpolating each row between its left and right neighbours (keeps horizontal borders)."""
    for y in range(y0, y1 + 1):
        a, b = im.getpixel((x0 - 2, y)), im.getpixel((x1 + 2, y))
        for x in range(x0, x1 + 1):
            t = (x - x0) / max(1, x1 - x0)
            im.putpixel((x, y), tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def erase_v(x0, y0, x1, y1):
    """Erase a box by interpolating each column between the pixels above and below (keeps vertical lines)."""
    for x in range(x0, x1 + 1):
        a, b = im.getpixel((x, y0 - 2)), im.getpixel((x, y1 + 2))
        for y in range(y0, y1 + 1):
            t = (y - y0) / max(1, y1 - y0)
            im.putpixel((x, y), tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def dashed(p, q, on=7, off=5, w=2):
    (x0, y0), (x1, y1) = p, q
    n = max(abs(x1 - x0), abs(y1 - y0))
    for k in range(0, n, on + off):
        s, e = k / n, min(k + on, n) / n
        dr.line([(x0 + (x1 - x0) * s, y0 + (y1 - y0) * s), (x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)], fill=DASH, width=w)


# 1. File storage -> Read text
erase_h(527, 666, 543, 709)            # up-arrow into the bottom of Merge and its dashed stem
erase_v(462, 706, 545, 716)            # right part of the horizontal dashed run
erase_h(376, 739, 395, 752)            # arrowhead pointing down into File storage
erase_h(530, 568, 540, 583)            # stub between the new junction and the top of Merge
dashed((385, 750), (385, 740))
dashed((460, 711), (460, 567))         # up through the gap between "Extract facts" and "Merge"
dashed((460, 567), (535, 567))         # join the existing dashed arrow into "Read text"

# 2. ChromaDB -> Ask Documents (joins the MongoDB arrow below the storage panel)
dr.line([(591, 888), (917, 888)], fill=SOLID, width=3)
dr.polygon([(626, 888), (638, 881), (638, 895)], fill=SOLID)
dr.ellipse((585, 883, 595, 893), fill=SOLID)
dr.ellipse((914, 883, 924, 893), fill=SOLID)
im.save(sys.argv[2])
print("saved", sys.argv[2])
