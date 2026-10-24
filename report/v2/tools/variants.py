import copy, sys
from docx import Document
from docx.oxml.ns import qn
SRC = "Smart_Form_Black_Book_2026-27_v2.docx"
def save(name, fn):
    d = Document(SRC); fn(d); d.save(f"tools/v_{name}.docx")
def noimg(d):
    for el in list(d.element.body.iter(qn("w:drawing"))): el.getparent().remove(el)
def nohdr(d):
    for s in d.sections:
        for part in (s.header, s.footer, s.first_page_header, s.first_page_footer):
            for p in part.paragraphs:
                for c in list(p._p): 
                    if c.tag != qn("w:pPr"): p._p.remove(c)
def nofields(d):
    body = d.element.body
    for tag in ("w:fldChar", "w:instrText"):
        for el in list(body.iter(qn(tag))): el.getparent().remove(el)
def notables(d):
    for t in list(d.element.body.iter(qn("w:tbl"))): t.getparent().remove(t)
for n, f in [("noimg", noimg), ("nohdr", nohdr), ("nofields", nofields), ("notables", notables)]:
    save(n, f)
print("ok")
