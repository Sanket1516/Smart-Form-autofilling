# Crops screenshots to their content (removes the dashboard sidebar/top bar and empty margins). Originals are kept.
import os
from PIL import Image, ImageChops, ImageOps
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "screens")
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "screens_c")
os.makedirs(DST, exist_ok=True)

def trim(im, margin=36, tol=12):
    bg = Image.new("RGB", im.size, im.getpixel((im.width - 3, im.height - 3)))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > tol else 0)
    box = diff.getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(0, l - margin), max(0, t - margin), min(im.width, r + margin), min(im.height, b + margin)))

for fn in sorted(os.listdir(SRC)):
    im = Image.open(os.path.join(SRC, fn)).convert("RGB")
    if fn in ("fig5_1_login.png", "fig5_6_ext_scan.png", "fig5_7_ext_review.png"):
        out = trim(im)
    else:
        out = trim(im.crop((500, 128, im.width, im.height)))
    out = ImageOps.expand(out, border=2, fill="#B8BFCC")
    out.save(os.path.join(DST, fn))
    print(fn, im.size, "->", out.size)
