"""Synthetic test documents. All people, numbers and addresses are fictitious."""

from __future__ import annotations

import io

RESUME_LINES = [
    "Avery Quinn Example",
    "Email: avery.example@example.com",
    "Phone: +1 555 010 4477",
    "Date of Birth: 14/02/1996",
    "Postal Code: 560001",
    "City: Springfield",
    "Education",
    "Degree: Bachelor of Technology in Computer Science",
    "University: Example Institute of Technology",
    "Experience",
    "Worked as a data analyst at Example Corp building reporting dashboards for three years.",
]

ID_CARD_LINES = [
    "SAMPLE IDENTITY CARD - NOT A REAL DOCUMENT",
    "Full Name: Avery Quinn Example",
    "Date of Birth: 15/02/1996",
    "Gender: Female",
]


def pdf_bytes(lines: list[str]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    for line in lines:
        page.drawString(60, y, line)
        y -= 20
    page.save()
    return buffer.getvalue()


def docx_bytes(lines: list[str]) -> bytes:
    import docx

    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def txt_bytes(lines: list[str]) -> bytes:
    return "\n".join(lines).encode("utf-8")
