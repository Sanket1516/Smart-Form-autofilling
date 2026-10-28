"""Generate the fictional demo resume (PDF) from `demo.resume_profile`.

    python -m demo.cli resume generate

A plain, single-column text PDF (reportlab) so it goes through the normal digital-PDF path.
Every page carries the DEMO DATA banner.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from demo import resume_profile as R

PREFIX = "DEMO_RESUME_"
FILE_NAME = f"{PREFIX}kavya_deshpande.pdf"

_SS = getSampleStyleSheet()


def _style(name: str, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, parent=_SS["Normal"], **kw)


NAME = _style("name", fontName="Helvetica-Bold", fontSize=20, leading=24)
SUB = _style("sub", fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#444444"))
H = _style("h", fontName="Helvetica-Bold", fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=3,
           textColor=colors.HexColor("#1a5f7a"))
BODY = _style("body", fontName="Helvetica", fontSize=10, leading=13.5)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=12, bulletIndent=2)
LABEL = _style("label", fontName="Helvetica-Bold", fontSize=10, leading=13.5)
NOTE = _style("note", fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))


def _p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(escape(text), style)


def _bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(escape(item), BULLET, bulletText="•") for item in items]


def _pairs(rows: list[tuple[str, str]]) -> Table:
    table = Table([[_p(k, LABEL), _p(v)] for k, v in rows], colWidths=[48 * mm, 122 * mm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                               ("TOPPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return table


def _responses() -> Table:
    """Open-question answers as a bordered table: the chunker keeps each row whole and repeats the header,
    so every answer is retrieved together with its topic instead of being split mid-paragraph."""
    rows = [[_p("Topic", LABEL), _p("Response", LABEL)]] + [[_p(k, LABEL), _p(v)] for k, v in R.RESPONSES]
    table = Table(rows, colWidths=[40 * mm, 130 * mm], repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f6"))]))
    return table


def _banner(canvas, doc) -> None:  # noqa: ANN001
    width, height = doc.pagesize
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#fff3cd"))
    canvas.rect(0, height - 11 * mm, width, 11 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#664d03"))
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawCentredString(width / 2, height - 7 * mm, R.BANNER)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(width / 2, 8 * mm, f"Demo resume · page {doc.page}")
    canvas.restoreState()


def build_story() -> list:
    exp = R.EXPERIENCE
    story: list = [
        _p(R.NAME, NAME),
        _p(R.HEADLINE, SUB),
        _p(f"{R.EMAIL}  ·  {R.PHONE}  ·  {R.LOCATION}", SUB),
        Spacer(1, 4),
        _p("Career Objective", H), _p(R.CAREER_OBJECTIVE),
        _p("Career Goals", H), _p(R.CAREER_GOALS),
        _p("Education", H), _pairs(R.EDUCATION),
        _p("Technical Skills", H), _pairs(R.SKILLS),
        _p("Work Experience", H),
        _p(f"{exp['position']} — {exp['organization']}", LABEL),
        _p(f"Duration: {exp['duration']}"),
        _p(exp["note"], NOTE),
        _p("Responsibilities", LABEL), *_bullets(exp["responsibilities"]),
        _p("Achievements during the internship", LABEL), *_bullets(exp["achievements"]),
        _p("Projects", H),
    ]
    title, description, technologies = R.PROJECTS[0]
    story += [_p(f"Project: {title}", LABEL), _p(f"Description: {description}"),
              _p(f"Technologies: {technologies}"), Spacer(1, 4)]
    story += [
        _p("Cloud Experience", H), _p(R.CLOUD_EXPERIENCE),
        _p("Strengths", H), *_bullets(R.STRENGTHS),
        _p("Weaknesses", H), _p(R.WEAKNESSES),
        _p("Selected Responses", H), _responses(),
        _p("All achievements and experience in this document are fictional demo content.", NOTE),
        _p("Additional Information", H), _pairs(R.ADDITIONAL),
    ]
    return story


def generate(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / FILE_NAME
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=16 * mm, title="DEMO resume — Kavya Suresh Deshpande (fictional)",
                            author="Smart Form demo data", subject=R.BANNER)
    doc.build(build_story(), onFirstPage=_banner, onLaterPages=_banner)
    return path
