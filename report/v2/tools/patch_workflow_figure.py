"""Corrects the user's workflow diagram: OCR engine, document-type examples, form arrow and review label."""
import sys
from PIL import Image, ImageDraw, ImageFont
src, out, fonts = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(src).convert("RGB")
dr = ImageDraw.Draw(im)
REG, BOLD = fonts + "/Lato-Regular.ttf", fonts + "/Lato-Bold.ttf"

def fit(path, text, width):
    """Font size whose rendering of `text` matches an original line's width."""
    s = 10
    while ImageFont.truetype(path, s + 1).getlength(text) <= width:
        s += 1
    return ImageFont.truetype(path, s)

def erase(x0, y0, x1, y1):
    """Fill with the background, interpolated per row between the colours just outside the box."""
    for y in range(y0, y1 + 1):
        l, r = im.getpixel((x0 - 3, y)), im.getpixel((x1 + 3, y))
        for x in range(x0, x1 + 1):
            t = (x - x0) / max(1, x1 - x0)
            im.putpixel((x, y), tuple(round(l[i] + (r[i] - l[i]) * t) for i in range(3)))

def darkest(box):
    x0, y0, x1, y1 = box
    return min((im.getpixel((x, y)) for y in range(y0, y1) for x in range(x0, x1)), key=sum)

def text_at(x, top, s, font, fill):
    """Draw text so that its ink starts at x and its ascender top at `top`."""
    bb = font.getbbox("Ag")
    dr.text((x, top - bb[1]), s, font=font, fill=fill)

# 1. Step 2: Tesseract -> RapidOCR (the code uses RapidOCR with PP-OCR models)
body = fit(REG, "OCR for scanned files", 446 - 262)  # width of the line above
col = darkest((262, 361, 353, 378))
erase(258, 357, 400, 382)
text_at(262, 361, "(RapidOCR, PP-OCR models)", body, col)

# 2. Step 3: real document types instead of generic categories
col3 = darkest((262, 491, 499, 508))
erase(258, 487, 520, 535)
f3 = fit(REG, "e.g. ID Proof, Address Proof,", 499 - 262)
text_at(262, 491, "e.g. PAN card, Passport,", f3, col3)
text_at(262, 515, "Class 12 mark sheet, etc.", f3, col3)

# 2b. Step 4: the LLM call during fact extraction is optional
col4 = darkest((262, 659, 395, 673))
erase(258, 655, 520, 677)
text_at(263, 659, "Rules + optional LLM for", fit(REG, "structured information", 452 - 262), col4)

# 3. Arrow between Phase B and the web form: fields are read from the form and approved values written back
blue = darkest((1067, 462, 1120, 482))
green_line = im.getpixel((1066, 520))
# Rebuild the background by interpolating each column between the rows just above and below the old label and arrow.
for x in range(1046, 1124):
    a, b = im.getpixel((x, 406)), im.getpixel((x, 494))
    for y in range(407, 494):
        t = (y - 406) / 88
        im.putpixel((x, y), tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))
for y in range(407, 494):
    for x in (1065, 1066, 1067):
        im.putpixel((x, y), green_line)
fb, fr = ImageFont.truetype(BOLD, 15), ImageFont.truetype(BOLD, 13)
for s, f, top in (("Read fields", fb, 414), ("& fill values", fr, 436)):
    w = f.getlength(s)
    x = round(1086 - w / 2)
    bb = f.getbbox(s)
    dr.rectangle((x - 2, top - 2, x + w + 2, top + bb[3] - bb[1] + 2), fill=im.getpixel((1090, 400)))
    text_at(x, top, s, f, blue)
y = 472
dr.rectangle((1078, y - 2, 1110, y + 2), fill=blue)
dr.polygon([(1068, y), (1080, y - 8), (1080, y + 8)], fill=blue)
dr.polygon([(1121, y), (1109, y - 8), (1109, y + 8)], fill=blue)

# 4. Review happens in the extension popup, not on the web page
g = darkest((1130, 727, 1254, 771))
lab = ImageFont.truetype(BOLD, 19)
fit_w = lab.getlength("in extension popup")
erase(1124, 724, 1306, 776)
for s, top in (("Review & approve", 727), ("in extension popup", 752)):
    w = lab.getlength(s)
    text_at(round(1212 - w / 2), top, s, lab, g)
im.save(out)
print("saved", out, "body font", body.size, "step3 font", f3.size, "label width", fit_w)
