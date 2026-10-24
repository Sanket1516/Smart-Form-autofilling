# Renders contact sheets (8 pages per sheet) of the exported PDF for visual inspection.
import sys, pymupdf
pdf, out, per = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8
d = pymupdf.open(pdf)
cols = 4; W, H = 420, 594
for s in range(0, len(d), per):
    pages = list(range(s, min(len(d), s + per)))
    rows = (len(pages) + cols - 1) // cols
    doc = pymupdf.open(); pg = doc.new_page(width=cols * W, height=rows * H)
    for k, i in enumerate(pages):
        x, y = (k % cols) * W, (k // cols) * H
        r = pymupdf.Rect(x + 3, y + 3, x + W - 3, y + H - 3)
        pg.show_pdf_page(r, d, i)
        pg.draw_rect(r, color=(1, 0, 0), width=0.8)
        pg.insert_text((x + 8, y + 16), f"p{i+1}", color=(1, 0, 0), fontsize=12)
    pg.get_pixmap(dpi=110).save(f"{out}_{s//per+1}.png")
print("sheets:", (len(d) + per - 1) // per)
