"""Generate the 15 synthetic demo documents (PDF) from `demo.profile`.

    python -m demo.cli generate

Digital documents are text PDFs built with reportlab. "Scanned" documents are
rendered to an image, lightly rotated / blurred / noised and wrapped back into a
PDF, so they go through the real OCR path. All content is fictional and every
page carries the synthetic-data banner. No emblem, seal, QR code or exact
government layout is reproduced.
"""

from __future__ import annotations

import io
import random
from pathlib import Path
from typing import Any

import pymupdf as fitz  # PyMuPDF: used only to rasterise pages for the scanned-style documents
import numpy as np
from PIL import Image, ImageFilter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)

from demo import profile as P

PREFIX = "DEMO_"
SS = getSampleStyleSheet()


def _style(name: str, **kw: Any) -> ParagraphStyle:
    return ParagraphStyle(name, parent=SS["Normal"], **kw)


BODY = _style("body", fontName="Helvetica", fontSize=10, leading=13)
SMALL = _style("small", fontName="Helvetica", fontSize=7.5, leading=9, textColor=colors.HexColor("#444444"))
H1 = _style("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, alignment=TA_CENTER)
H2 = _style("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=3)
CENTER = _style("center", fontName="Helvetica", fontSize=10, leading=13, alignment=TA_CENTER)
SERIF = _style("serif", fontName="Times-Roman", fontSize=11.5, leading=16)
SERIF_C = _style("serifc", fontName="Times-Bold", fontSize=15, leading=19, alignment=TA_CENTER)
LABEL = _style("label", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.HexColor("#222222"))
VALUE = _style("value", fontName="Helvetica", fontSize=10, leading=12.5)
MONO = _style("mono", fontName="Courier", fontSize=9.5, leading=12)


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


# ------------------------------------------------------------------------ plumbing
def _frame(doc_no: int, title: str, accent: str):
    def draw(canvas, doc):  # noqa: ANN001
        w, h = doc.pagesize
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#b00020"))
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString(w / 2, h - 9 * mm, P.BANNER)
        canvas.setStrokeColor(colors.HexColor(accent))
        canvas.setLineWidth(1.2)
        canvas.line(15 * mm, h - 11 * mm, w - 15 * mm, h - 11 * mm)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(15 * mm, 8 * mm, f"Demo document {doc_no:02d} of 15 · {title} · page {doc.page}")
        canvas.drawRightString(w - 15 * mm, 8 * mm, "Fictional data for software demonstration only")
        canvas.restoreState()
    return draw


def build_pdf(path: Path, doc_no: int, title: str, story: list, accent: str = "#1f4e79",
              pagesize=A4, margins=(18, 16, 18, 16)) -> int:
    left, top, right, bottom = (m * mm for m in margins)
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, leftMargin=left, rightMargin=right,
                            topMargin=top + 6 * mm, bottomMargin=bottom + 4 * mm,
                            title=f"{title} (synthetic demo)", author="Smart Form demo dataset")
    frame = _frame(doc_no, title, accent)
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    with fitz.open(path) as d:
        return len(d)


def kv(rows: list[tuple[str, str]], widths=(55 * mm, 115 * mm), accent="#e8eef5", size=10) -> Table:
    data = [[p(f"<b>{a}</b>", _style("l", fontName="Helvetica", fontSize=size - 0.5, leading=size + 3)),
             p(b, _style("v", fontName="Helvetica", fontSize=size, leading=size + 3))] for a, b in rows]
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(accent)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def grid(header: list[str], rows: list[list[str]], widths: list[float], size=9, head_bg="#1f4e79",
         zebra=True, align_right: tuple[int, ...] = ()) -> Table:
    t = Table([header, *rows], colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(head_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), size),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8896a5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if zebra:
        style += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f4f8")])]
    for col in align_right:
        style.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def disclaimer(extra: str = "") -> Paragraph:
    return p(f"<font color='#b00020'><b>{P.BANNER}</b></font><br/>{extra}", SMALL)


# ---------------------------------------------------------------- scanned-style pass
def scanify(pdf_path: Path, *, rotate: float, noise: float = 6.0, blur: float = 0.5, dpi: int = 170,
            contrast: float = 0.96, seed: int = 7) -> None:
    """Rasterise `pdf_path`, add scan artefacts and replace it with an image-only PDF."""
    rng = np.random.default_rng(seed)
    src = fitz.open(pdf_path)
    out = fitz.open()
    for index, page in enumerate(src):
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        angle = rotate if index % 2 == 0 else -rotate * 0.6
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(250, 250, 248))
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        arr = np.asarray(img).astype(np.float32)
        arr = 128 + (arr - 128) * contrast
        arr += rng.normal(0, noise, arr.shape[:2])[..., None]
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, "JPEG", quality=82)
        new = out.new_page(width=page.rect.width, height=page.rect.height)
        new.insert_image(new.rect, stream=buf.getvalue())
    src.close()
    tmp = pdf_path.with_suffix('.scan.tmp')
    out.save(tmp, garbage=3, deflate=True)
    out.close()
    tmp.replace(pdf_path)


# ============================================================================ documents
def doc01(path: Path) -> None:
    s = [p("IDENTITY INFORMATION SHEET", H1), p("Applicant identity summary · issued for demonstration", CENTER),
         Spacer(1, 6 * mm),
         kv([("Full Name", P.FULL_NAME), ("First / Middle / Last Name", f"{P.FIRST} / {P.MIDDLE} / {P.LAST}"),
             ("Date of Birth", P.long_date(P.DOB)), ("Gender", P.GENDER), ("Nationality", P.NATIONALITY),
             ("Father's Name", P.FATHER), ("Mother's Name", P.MOTHER), ("Mobile Number", P.MOBILE),
             ("Email", P.EMAIL)]),
         Spacer(1, 4 * mm), p("Addresses", H2),
         kv([("Permanent Address", P.PERMANENT_ADDRESS),
             ("Correspondence Address", P.CORRESPONDENCE_ADDRESS)]),
         Spacer(1, 4 * mm), p("Emergency Contact", H2),
         kv([("Emergency Contact Name", P.EMERGENCY_NAME), ("Emergency Contact Relationship", P.EMERGENCY_RELATION), ("Emergency Contact Phone", P.EMERGENCY_PHONE)]),
         Spacer(1, 8 * mm), disclaimer("This sheet summarises fictional applicant details. It is not an identity document.")]
    build_pdf(path, 1, "Identity Information Sheet", s)


def doc02(path: Path) -> None:
    s = [p("TAX IDENTIFICATION RECORD", H1), p("Permanent Account Number (PAN-format) · demonstration record", CENTER),
         Spacer(1, 8 * mm),
         kv([("Permanent Account Number", f"<font name='Courier-Bold' size=13>{P.TAX_ID}</font>"),
             ("Name", P.FULL_NAME.upper()), ("Father's Name", P.FATHER.upper()),
             ("Date of Birth", P.dmy(P.DOB)), ("Taxpayer Type", "Individual")], widths=(60 * mm, 110 * mm),
            accent="#f3ecd9"),
         Spacer(1, 6 * mm),
         p("The identifier above is a fictional value that only follows the 10-character PAN <i>shape</i> "
           "(five letters, four digits, one letter). It is not issued by any authority and cannot be used "
           "for any tax or financial purpose.", BODY),
         Spacer(1, 6 * mm), p("Note: letters O/0, I/1, Z/2 and S/5 look alike. Read the value exactly as printed.", SMALL),
         Spacer(1, 10 * mm), disclaimer()]
    build_pdf(path, 2, "Tax Identification Record", s, accent="#8a6d1d")


def doc03(path: Path) -> None:
    s = [p("ELECTOR INFORMATION RECORD", H1), p("Voter information abstract · demonstration", CENTER), Spacer(1, 6 * mm)]
    left = [("EPIC No", P.VOTER_ID), ("Elector's Name", P.FULL_NAME), ("Father's Name", P.FATHER),
            ("Gender", P.GENDER), ("Date of Birth", P.dmy(P.DOB))]
    right = [("Assembly Constituency", "215 - Demo Nagar (Fictional)"), ("Part No. and Name", "45 - Demo Primary School"),
             ("Serial No. in Part", "318")]
    s += [kv(left, widths=(45 * mm, 125 * mm), accent="#e6f2e6"), Spacer(1, 3 * mm),
          kv([("Address", P.PERMANENT_ADDRESS)], widths=(45 * mm, 125 * mm), accent="#e6f2e6"), Spacer(1, 3 * mm),
          kv(right, widths=(45 * mm, 125 * mm), accent="#e6f2e6"), Spacer(1, 10 * mm), disclaimer()]
    build_pdf(path, 3, "Voter Information Record", s, accent="#2e7d32")
    scanify(path, rotate=1.2, noise=5.0, blur=0.45, seed=3)


def doc04(path: Path) -> None:
    box = Table([[p("<b>MOTOR DRIVING LICENCE RECORD</b><br/><font size=8>Fictional state transport department (demo)</font>", CENTER)]],
                colWidths=[174 * mm])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3d6")),
                             ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#c28a00")),
                             ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    s = [box, Spacer(1, 5 * mm),
         kv([("DL No", P.DL_NUMBER), ("Name", P.FULL_NAME), ("S/W/D of", P.FATHER), ("DOB", P.dmy(P.DOB)),
             ("Blood Group", P.BLOOD_GROUP), ("Address", P.PERMANENT_ADDRESS)], widths=(42 * mm, 132 * mm), accent="#fdf0cc"),
         Spacer(1, 4 * mm),
         grid(["Date of Issue", "Valid Till (NT)", "Class of Vehicle", "Issuing Authority"],
              [[P.dmy(P.DL_ISSUE), P.dmy(P.DL_VALID), P.DL_CLASSES, P.DL_AUTHORITY]],
              [34 * mm, 38 * mm, 46 * mm, 56 * mm], head_bg="#c28a00", zebra=False),
         Spacer(1, 4 * mm),
         p("The licence was issued after the holder's 18th birthday. <b>Date of birth</b>, <b>date of issue</b> and "
           "<b>validity date</b> are three different dates.", SMALL),
         Spacer(1, 10 * mm), disclaimer()]
    build_pdf(path, 4, "Driving Licence Record", s, accent="#c28a00")


def doc05(path: Path) -> None:
    d = lambda x: x.strftime("%d %b %Y").upper()  # noqa: E731
    surname, given = P.LAST.upper(), f"{P.FIRST} {P.MIDDLE}".upper()
    s = [p("PASSPORT INFORMATION RECORD", H1), p("Travel-document data page abstract · demonstration", CENTER), Spacer(1, 5 * mm),
         grid(["Type", "Country Code", "Passport No."], [["P", "IND", f"<b>{P.PASSPORT_NO}</b>"]], [30 * mm, 40 * mm, 104 * mm],
              head_bg="#5b3a8a", zebra=False),
         Spacer(1, 3 * mm),
         kv([("Surname", surname), ("Given Name(s)", given), ("Nationality", P.NATIONALITY.upper()), ("Sex", "F"),
             ("Date of Birth", d(P.DOB)), ("Place of Birth", P.PLACE_OF_BIRTH.upper()),
             ("Place of Issue", P.PASSPORT_PLACE.upper()), ("Date of Issue", d(P.PASSPORT_ISSUE)),
             ("Date of Expiry", d(P.PASSPORT_EXPIRY)), ("Father's Name", P.FATHER.upper()),
             ("Mother's Name", P.MOTHER.upper()), ("Address", P.PERMANENT_ADDRESS)],
            widths=(48 * mm, 126 * mm), accent="#ece5f6"),
         Spacer(1, 4 * mm),
         p("No machine-readable zone is reproduced. Issue and expiry dates are ten years apart and neither is the date of birth.", SMALL),
         Spacer(1, 8 * mm), disclaimer()]
    build_pdf(path, 5, "Passport Information Record", s, accent="#5b3a8a")


def doc06(path: Path) -> None:
    s = [p(P.CLASS10_BOARD.upper(), _style("b", fontName="Times-Bold", fontSize=13, leading=16, alignment=TA_CENTER)),
         p("SECONDARY SCHOOL EXAMINATION (CLASS X) — MARCH 2023", SERIF_C),
         p("MARKS STATEMENT CUM CERTIFICATE", _style("m", fontName="Times-Bold", fontSize=12, leading=15, alignment=TA_CENTER)),
         Spacer(1, 4 * mm),
         p(f"This is to certify that <b>{P.FULL_NAME.upper()}</b>", SERIF),
         p(f"Roll No. <b>{P.CLASS10_ROLL}</b>", SERIF),
         p(f"Mother's Name <b>{P.MOTHER.upper()}</b>", SERIF),
         p(f"Father's / Guardian's Name <b>{P.FATHER.upper()}</b>", SERIF),
         p(f"Date of Birth <b>{P.dmy(P.DOB, '-')}</b>", SERIF),
         p(f"School <b>{P.CLASS10_SCHOOL.upper()}</b>", SERIF),
         Spacer(1, 4 * mm)]
    rows = [[x.code, x.name.upper(), str(x.max_marks), f"{x.theory:03d}", f"{x.internal:03d}", f"{x.obtained:03d}", x.grade]
            for x in P.CLASS10_SUBJECTS]
    s.append(grid(["SUB CODE", "SUBJECT", "MAX", "THEORY", "INTERNAL", "TOTAL", "GRADE"], rows,
                  [24 * mm, 56 * mm, 16 * mm, 20 * mm, 22 * mm, 18 * mm, 18 * mm], size=9.5, head_bg="#444444"))
    s += [Spacer(1, 3 * mm),
          kv([("Total Maximum Marks", str(P.CLASS10_MAX)), ("Total Marks Obtained", str(P.CLASS10_TOTAL)),
              ("Percentage", f"{P.CLASS10_PCT:.2f}%"), ("Result", "PASS")], widths=(60 * mm, 60 * mm), accent="#eeeeee", size=9.5),
          Spacer(1, 2 * mm),
          p("Percentage = Total Marks Obtained ÷ Total Maximum Marks × 100. Grade scale: A1 91–100, A2 81–90.", SMALL),
          p(f"Month and Year of Passing: <b>{P.CLASS10_MONTH} {P.CLASS10_YEAR}</b> · Result declared on "
            f"{P.dmy(P.CLASS10_RESULT_DATE, '-')} · Place: Nashik", SERIF),
          Spacer(1, 6 * mm), disclaimer()]
    build_pdf(path, 6, "Class 10 Marksheet", s, accent="#444444")
    scanify(path, rotate=0.7, noise=5.5, blur=0.5, seed=6)


def doc07(path: Path) -> None:
    s = [p(P.CLASS12_BOARD.upper(), _style("b", fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=TA_CENTER)),
         p("HIGHER SECONDARY CERTIFICATE EXAMINATION (CLASS XII) — MARCH 2025", H1),
         p("STATEMENT OF MARKS", CENTER), Spacer(1, 4 * mm),
         kv([("Name of Candidate", P.FULL_NAME.upper()), ("Seat / Roll No.", P.CLASS12_ROLL),
             ("Stream", P.CLASS12_STREAM.upper()), ("College", P.CLASS12_SCHOOL.upper()),
             ("Mother's Name", P.MOTHER.upper()), ("Examination", f"{P.CLASS12_MONTH.upper()} {P.CLASS12_YEAR}")],
            widths=(48 * mm, 126 * mm), accent="#e4eef7"),
         Spacer(1, 4 * mm)]
    rows = [[x.code, x.name.upper(), str(x.max_marks), str(x.obtained), x.grade] for x in P.CLASS12_SUBJECTS]
    s.append(grid(["CODE", "SUBJECT", "MAX MARKS", "MARKS OBTAINED", "GRADE"], rows,
                  [22 * mm, 64 * mm, 28 * mm, 36 * mm, 24 * mm], size=10, head_bg="#1f4e79", align_right=(2, 3)))
    s += [Spacer(1, 3 * mm),
          kv([("Total Maximum Marks", str(P.CLASS12_MAX)), ("Total Marks Obtained", str(P.CLASS12_TOTAL)),
              ("Percentage", f"{P.CLASS12_PCT:.2f}%"), ("Result", "PASS"),
              ("Month and Year of Passing", f"{P.CLASS12_MONTH} {P.CLASS12_YEAR}"),
              ("Result Date", P.long_date(P.CLASS12_RESULT_DATE))], widths=(70 * mm, 70 * mm), accent="#e4eef7"),
          Spacer(1, 2 * mm),
          p("Percentage = Total Marks Obtained ÷ Total Maximum Marks × 100 (five subjects of 100 marks each).", SMALL),
          Spacer(1, 8 * mm), disclaimer("This statement belongs to the Class XII examination only and carries no Class X data.")]
    build_pdf(path, 7, "Class 12 Marksheet", s)


def doc08(path: Path) -> None:
    s = [p("EXAMPLE MUNICIPAL REGISTRY (FICTIONAL)", _style("b", fontName="Times-Bold", fontSize=12, leading=15, alignment=TA_CENTER)),
         p("EXTRACT OF BIRTH REGISTER", SERIF_C), Spacer(1, 5 * mm),
         p(f"Registration Number: <b>{P.BIRTH_REG_NO}</b>", SERIF),
         p(f"Date of Registration: {P.long_date(P.BIRTH_REG_DATE)}", SERIF),
         Spacer(1, 3 * mm),
         p(f"It is certified that the birth of <b>{P.FULL_NAME}</b>, {P.GENDER.lower()}, took place on "
           f"<b>{P.long_date(P.DOB)}</b> ({P.dmy(P.DOB, '-')}) at {P.BIRTH_HOSPITAL}.", SERIF),
         Spacer(1, 3 * mm),
         kv([("Place of Birth", P.PLACE_OF_BIRTH), ("Father's Name", P.FATHER), ("Mother's Name", P.MOTHER),
             ("Address of Parents", P.PERMANENT_ADDRESS), ("Date of Issue", P.long_date(P.BIRTH_ISSUE))],
            widths=(50 * mm, 124 * mm), accent="#f6e9e4"),
         Spacer(1, 10 * mm), disclaimer()]
    build_pdf(path, 8, "Birth Certificate Record", s, accent="#a1442b")
    scanify(path, rotate=-1.4, noise=6.5, blur=0.55, seed=8)


def doc09(path: Path) -> None:
    head = Table([[p(f"<b>{P.BANK_NAME.upper()}</b><br/>{P.BANK_BRANCH} · {P.BANK_BRANCH_ADDRESS}", _style("bh", fontName="Helvetica", fontSize=9.5, leading=12, textColor=colors.white)),
                   p("<b>SAVINGS PASSBOOK</b>", _style("bp", fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER, textColor=colors.white))]],
                 colWidths=[122 * mm, 52 * mm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0b6b5d")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    rows = [[P.dmy(t["date"]), t["description"], f"{t['debit']:,.2f}" if t["debit"] else "",
             f"{t['credit']:,.2f}" if t["credit"] else "", f"{t['balance']:,.2f}"] for t in P.TRANSACTIONS[-6:]]
    s = [head, Spacer(1, 4 * mm),
         kv([("Account Holder", P.FULL_NAME), ("Account Number", f"<font name='Courier-Bold'>{P.ACCOUNT_NO}</font>"),
             ("IFSC", f"<font name='Courier-Bold'>{P.IFSC}</font>  (test value)"), ("MICR", P.MICR),
             ("Account Type", P.ACCOUNT_TYPE), ("Branch", P.BANK_BRANCH), ("Branch Address", P.BANK_BRANCH_ADDRESS)],
            widths=(45 * mm, 129 * mm), accent="#dff1ee"),
         Spacer(1, 4 * mm), p("Recent entries", H2),
         grid(["Date", "Particulars", "Withdrawals", "Deposits", "Balance"], rows,
              [24 * mm, 66 * mm, 28 * mm, 26 * mm, 30 * mm], size=8.5, head_bg="#0b6b5d", align_right=(2, 3, 4)),
         Spacer(1, 4 * mm),
         p("The account number and the IFSC-style code are different identifiers: the first has twelve digits, "
           "the second begins with four letters. Both are fictional and cannot be used for any transaction.", SMALL),
         Spacer(1, 8 * mm), disclaimer()]
    build_pdf(path, 9, "Bank Passbook", s, accent="#0b6b5d")
    scanify(path, rotate=0.3, noise=4.0, blur=0.4, seed=9)


def doc10(path: Path) -> None:
    a, b = P.BILL_PERIOD
    top = Table([[p(f"<b>{P.UTILITY_PROVIDER}</b><br/>Electricity bill · consumer copy", _style("u", fontName="Helvetica", fontSize=11, leading=14, textColor=colors.white)),
                  p(f"<b>AMOUNT DUE</b><br/><font size=15>INR {float(P.BILL_AMOUNT):,.2f}</font>", _style("ua", fontName="Helvetica", fontSize=9, leading=16, textColor=colors.white, alignment=TA_CENTER))]],
                colWidths=[118 * mm, 56 * mm])
    top.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#b34700")), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    cols = Table([[kv([("Consumer Name", P.FULL_NAME), ("Consumer No.", P.CONSUMER_NO), ("Meter No.", P.METER_NO),
                       ("Service Address", P.PERMANENT_ADDRESS)], widths=(30 * mm, 60 * mm), accent="#fbe9dc", size=8.5),
                  kv([("Billing Period", f"{P.mon_date(a)} to {P.mon_date(b)}"), ("Bill Date", P.mon_date(P.BILL_DATE)),
                      ("Due Date", P.mon_date(P.BILL_DUE)), ("Units Consumed", f"{P.UNITS} kWh"),
                      ("Bill Month", "August 2026")], widths=(28 * mm, 52 * mm), accent="#fbe9dc", size=8.5)]],
                colWidths=[93 * mm, 83 * mm])
    cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    s = [top, Spacer(1, 5 * mm), cols, Spacer(1, 5 * mm),
         grid(["Charge", "Units / basis", "Amount (INR)"],
              [["Energy charge", "312 kWh", "1,872.00"], ["Fixed charge", "per month", "210.00"],
               ["Electricity duty", "", "187.50"], ["Fuel adjustment", "", "78.00"], ["<b>Total payable</b>", "", f"<b>{float(P.BILL_AMOUNT):,.2f}</b>"]],
              [86 * mm, 46 * mm, 42 * mm], head_bg="#b34700", align_right=(2,)),
         Spacer(1, 4 * mm),
         p(f"Pay by {P.mon_date(P.BILL_DUE)} to avoid a late fee. The bill date ({P.mon_date(P.BILL_DATE)}) is not the due date.", SMALL),
         Spacer(1, 8 * mm), disclaimer()]
    build_pdf(path, 10, "Utility Bill", s, accent="#b34700")


def doc11(path: Path) -> None:
    rows = [[str(i + 1), n, rel, str(age), occ] for i, (n, rel, age, occ) in enumerate(P.HOUSEHOLD)]
    s = [p("HOUSEHOLD INFORMATION RECORD", H1), p("Family card abstract · demonstration", CENTER), Spacer(1, 5 * mm),
         kv([("Household Reference", P.HOUSEHOLD_REF), ("Head of Household", P.FATHER), ("Address", P.PERMANENT_ADDRESS),
             ("Applicant", P.FULL_NAME), ("Members Listed", str(len(P.HOUSEHOLD)))], widths=(48 * mm, 126 * mm), accent="#e3efe8"),
         Spacer(1, 5 * mm), p("Household members", H2),
         grid(["#", "Name", "Relationship to Applicant", "Age", "Occupation"], rows,
              [10 * mm, 66 * mm, 44 * mm, 14 * mm, 40 * mm], head_bg="#3b6b4f"),
         Spacer(1, 4 * mm),
         p("Relationships are stated from the applicant's point of view. The applicant appears as a member of the household.", SMALL),
         Spacer(1, 8 * mm), disclaimer()]
    build_pdf(path, 11, "Household Information Record", s, accent="#3b6b4f")


def doc12(path: Path) -> None:
    s = [p("INCOME CERTIFICATE", _style("c", fontName="Times-Bold", fontSize=22, leading=26, alignment=TA_CENTER)),
         p(f"Issued by: {P.INCOME_AUTHORITY}", CENTER), Spacer(1, 6 * mm),
         p(f"Certificate No.: <b>{P.INCOME_CERT_NO}</b>", SERIF),
         p(f"Date of Issue: <b>{P.long_date(P.INCOME_ISSUE)}</b>", SERIF),
         p(f"Valid Until: <b>{P.long_date(P.INCOME_VALID)}</b>", SERIF), Spacer(1, 4 * mm),
         p(f"This is to certify that <b>{P.FULL_NAME}</b>, daughter of {P.FATHER}, resident of {P.PERMANENT_ADDRESS}, "
           f"belongs to a family whose total annual income from all sources for the financial year "
           f"<b>{P.INCOME_FY}</b> is declared as <b>INR {P.inr(P.INCOME_ANNUAL)}</b> "
           f"(Rupees Four Lakh Eighty Thousand only).", SERIF),
         Spacer(1, 4 * mm),
         kv([("Applicant Name", P.FULL_NAME), ("Annual Income", f"INR {P.inr(P.INCOME_ANNUAL)}"), ("Currency", "Indian Rupee (INR)"),
             ("Source of Declaration", "Employer / self-declaration with supporting returns"),
             ("Financial Year", P.INCOME_FY)], widths=(55 * mm, 119 * mm), accent="#f2efe0"),
         Spacer(1, 4 * mm),
         p("Supporting details: income declared on self-employment records of the father, verified against "
           "a fictional revenue inspector report. The certificate date and the validity date are different.", BODY),
         Spacer(1, 14 * mm), disclaimer("Issuing authority and signature are fictional placeholders.")]
    build_pdf(path, 12, "Income Certificate", s, accent="#7a6a1a", margins=(22, 18, 22, 18))


def doc13(path: Path) -> None:
    s = [p("CATEGORY CERTIFICATE", _style("c", fontName="Times-Bold", fontSize=20, leading=24, alignment=TA_CENTER)),
         p(f"Issued by: {P.CASTE_AUTHORITY}", CENTER), Spacer(1, 5 * mm),
         p(f"Certificate No.: <b>{P.CASTE_CERT_NO}</b> &nbsp;&nbsp; Date of Issue: <b>{P.dmy(P.CASTE_ISSUE)}</b>", SERIF),
         Spacer(1, 3 * mm),
         p(f"This is to certify that <b>{P.FULL_NAME}</b>, daughter of {P.FATHER}, resident of {P.PERMANENT_ADDRESS}, "
           f"belongs to the <b>{P.CASTE}</b> community, which is recognised in the fictional demonstration schedule "
           f"under the social category <b>{P.CATEGORY}</b>.", SERIF),
         Spacer(1, 3 * mm),
         kv([("Applicant Name", P.FULL_NAME), ("Social Category", P.CATEGORY), ("Caste / Community", P.CASTE),
             ("Certificate Number", P.CASTE_CERT_NO), ("Date of Issue", P.dmy(P.CASTE_ISSUE)), ("Issuing Authority", P.CASTE_AUTHORITY)],
            widths=(50 * mm, 124 * mm), accent="#e9e4f4"),
         Spacer(1, 6 * mm),
         p("This certificate establishes the category only. It is separate from the caste <i>validity</i> certificate "
           "attached on the next page, which has its own number and issuing committee.", SMALL),
         PageBreak(),
         p("CASTE VALIDITY CERTIFICATE (ANNEXURE)", _style("c2", fontName="Times-Bold", fontSize=18, leading=22, alignment=TA_CENTER)),
         p(f"Issued by: {P.CASTE_VALIDITY_AUTHORITY}", CENTER), Spacer(1, 5 * mm),
         p(f"Validity Certificate No.: <b>{P.CASTE_VALIDITY_NO}</b> &nbsp;&nbsp; Date of Issue: <b>{P.dmy(P.CASTE_VALIDITY_ISSUE)}</b>", SERIF),
         Spacer(1, 3 * mm),
         p(f"The claim of <b>{P.FULL_NAME}</b> to the <b>{P.CASTE}</b> community has been scrutinised and the "
           f"caste claim is declared <b>VALID</b>. Caste certificate reference: {P.CASTE_CERT_NO}.", SERIF),
         Spacer(1, 10 * mm), disclaimer()]
    build_pdf(path, 13, "Category Certificate", s, accent="#5a4a8a", margins=(22, 18, 22, 18))
    scanify(path, rotate=0.5, noise=5.0, blur=0.5, seed=13)


def doc14(path: Path) -> None:
    s = [p("DOMICILE CERTIFICATE", _style("c", fontName="Times-Bold", fontSize=22, leading=26, alignment=TA_CENTER)),
         p(f"Issued by: {P.DOMICILE_AUTHORITY}", CENTER), Spacer(1, 6 * mm),
         p(f"Certificate No.: <b>{P.DOMICILE_NO}</b>", SERIF),
         p(f"Date of Issue: <b>{P.long_date(P.DOMICILE_ISSUE)}</b>", SERIF), Spacer(1, 4 * mm),
         p(f"This is to certify that <b>{P.FULL_NAME}</b>, daughter of {P.FATHER}, is a domicile of the State of "
           f"<b>{P.DOMICILE_STATE}</b>, having resided at the address below continuously for {P.DOMICILE_YEARS} years "
           f"since birth.", SERIF),
         Spacer(1, 4 * mm),
         kv([("Applicant Name", P.FULL_NAME), ("Domicile State", P.DOMICILE_STATE),
             ("Permanent Address", P.PERMANENT_ADDRESS), ("Period of Residence", f"{P.DOMICILE_YEARS} years (since birth)"),
             ("Certificate Reference", P.DOMICILE_NO)], widths=(55 * mm, 119 * mm), accent="#e1eef2"),
         Spacer(1, 12 * mm), disclaimer("Issuing authority and signature are fictional placeholders.")]
    build_pdf(path, 14, "Domicile Certificate", s, accent="#1d6f85", margins=(22, 18, 22, 18))


def doc15(path: Path) -> dict[str, Any]:
    a, b = P.STATEMENT_PERIOD
    small = _style("st", fontName="Helvetica", fontSize=8, leading=10)
    s = [p(f"<b>{P.BANK_NAME.upper()}</b> — ACCOUNT STATEMENT", _style("sh", fontName="Helvetica-Bold", fontSize=13, leading=16)),
         Spacer(1, 2 * mm),
         kv([("Account Holder", P.FULL_NAME), ("Account Number", P.ACCOUNT_NO), ("IFSC (test value)", P.IFSC),
             ("Branch", P.BANK_BRANCH), ("Branch Address", P.BANK_BRANCH_ADDRESS), ("Account Type", P.ACCOUNT_TYPE),
             ("Statement Period", f"{P.dmy(a)} to {P.dmy(b)}"), ("Opening Balance", f"INR {P.OPENING_BALANCE:,.2f}"),
             ("Closing Balance", f"INR {P.CLOSING_BALANCE:,.2f}")], widths=(40 * mm, 134 * mm), accent="#e8e8e8", size=8.5),
         Spacer(1, 3 * mm)]
    rows = [[P.dmy(t["date"]), t["description"], t["reference"], f"{t['debit']:,.2f}" if t["debit"] else "",
             f"{t['credit']:,.2f}" if t["credit"] else "", f"{t['balance']:,.2f}"] for t in P.TRANSACTIONS]
    s.append(grid(["Date", "Description", "Reference", "Debit", "Credit", "Balance"], rows,
                  [22 * mm, 56 * mm, 32 * mm, 20 * mm, 20 * mm, 24 * mm], size=7.5, head_bg="#333333", align_right=(3, 4, 5)))
    s += [Spacer(1, 3 * mm), p(f"Opening balance + total credits − total debits = closing balance. Total debits "
          f"INR {sum(t['debit'] or 0 for t in P.TRANSACTIONS):,.2f}; total credits INR "
          f"{sum(t['credit'] or 0 for t in P.TRANSACTIONS):,.2f}.", small), Spacer(1, 4 * mm), disclaimer()]
    pages = build_pdf(path, 15, "Bank Statement", s, accent="#333333", margins=(14, 12, 14, 12))
    return {"pages": pages}


DOCUMENTS: list[tuple[int, str, str, Any, dict[str, Any]]] = [
    (1, "identity_information_sheet", "Synthetic identity profile", doc01, {"scanned": False}),
    (2, "tax_identification_record", "Synthetic tax identification record", doc02, {"scanned": False}),
    (3, "voter_information_record", "Synthetic voter information record", doc03, {"scanned": True, "rotation_deg": 1.2}),
    (4, "driving_licence_record", "Synthetic driving licence record", doc04, {"scanned": False}),
    (5, "passport_information_record", "Synthetic passport information record", doc05, {"scanned": False}),
    (6, "class10_marksheet", "Class 10 marksheet", doc06, {"scanned": True, "rotation_deg": 0.7, "challenge": "dense table + rotation"}),
    (7, "class12_marksheet", "Class 12 marksheet", doc07, {"scanned": False}),
    (8, "birth_certificate_record", "Synthetic birth certificate record", doc08, {"scanned": True, "rotation_deg": -1.4}),
    (9, "bank_passbook", "Synthetic bank passbook", doc09, {"scanned": True, "rotation_deg": 0.3, "challenge": "account number vs IFSC"}),
    (10, "utility_bill", "Synthetic utility bill", doc10, {"scanned": False, "challenge": "multiple dates"}),
    (11, "household_information_record", "Synthetic household information record", doc11, {"scanned": False}),
    (12, "income_certificate", "Synthetic income certificate", doc12, {"scanned": False}),
    (13, "category_certificate", "Synthetic caste/category certificate (+ validity annexure)", doc13, {"scanned": True, "rotation_deg": 0.5}),
    (14, "domicile_certificate", "Synthetic domicile certificate", doc14, {"scanned": False}),
    (15, "bank_statement", "Synthetic bank statement", doc15, {"scanned": False, "challenge": "dense 25-row transaction table"}),
]


def _pages(path: Path) -> int:
    with fitz.open(path) as d:
        return len(d)


def file_name(number: int, slug: str) -> str:
    return f"{PREFIX}{number:02d}_{slug}.pdf"


def generate(out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    produced = []
    for number, slug, title, fn, meta in DOCUMENTS:
        path = out_dir / file_name(number, slug)
        extra = fn(path) or {}
        produced.append({"number": number, "slug": slug, "title": title, "file": path.name,
                         "pages": _pages(path), "bytes": path.stat().st_size, **meta, **extra})
    return produced
