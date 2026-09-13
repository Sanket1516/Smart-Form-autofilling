#!/usr/bin/env python3
"""
Create a realistic multi-page test resume PDF for end-to-end pipeline testing.
Run: python test-data/create_test_resume.py
Requires: pip install reportlab
"""
from pathlib import Path

OUTPUT = Path(__file__).parent / "sample_resume.pdf"


def create_resume():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib import colors
    except ImportError:
        print("reportlab not installed. Install with: pip install reportlab")
        _create_minimal_pdf()
        return

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    heading1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=20, spaceAfter=4)
    heading2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#2563eb"))
    normal = styles["Normal"]
    normal.fontSize = 10
    normal.leading = 15

    story = []

    # ─── PAGE 1: PERSONAL + CONTACT + EDUCATION ───────────────────────────
    story.append(Paragraph("Sanket Anil Desai", heading1))
    story.append(Paragraph("Software Engineer", normal))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Email: sanket.desai@example.com", normal))
    story.append(Paragraph("Phone: +91 98765 43210", normal))
    story.append(Paragraph("LinkedIn: https://linkedin.com/in/sanketdesai", normal))
    story.append(Paragraph("GitHub: https://github.com/sanketdesai", normal))
    story.append(Paragraph("Date of Birth: 15/08/1998", normal))
    story.append(Paragraph("Gender: Male", normal))
    story.append(Paragraph("Nationality: Indian", normal))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Current Address: 42, MG Road, Koregaon Park, Pune, Maharashtra 411001", normal))
    story.append(Paragraph("Permanent Address: 12, Shivaji Nagar, Kolhapur, Maharashtra 416001", normal))
    story.append(Paragraph("City: Pune", normal))
    story.append(Paragraph("State: Maharashtra", normal))
    story.append(Paragraph("Country: India", normal))
    story.append(Paragraph("Postal Code: 411001", normal))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("SUMMARY", heading2))
    story.append(Paragraph(
        "Summary: Results-driven Software Engineer with 4+ years of experience building "
        "scalable backend systems and data pipelines. Proficient in Python, FastAPI, and "
        "distributed systems. Passionate about clean architecture and developer tooling.",
        normal,
    ))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("EDUCATION", heading2))
    story.append(Paragraph("University: Savitribai Phule Pune University", normal))
    story.append(Paragraph("Degree: Bachelor of Engineering", normal))
    story.append(Paragraph("Specialization: Computer Engineering", normal))
    story.append(Paragraph("Graduation Year: 2020", normal))
    story.append(Paragraph("CGPA: 8.7 / 10", normal))
    story.append(Spacer(1, 8))

    story.append(Paragraph("College: MIT College of Engineering, Pune", normal))
    story.append(Paragraph("Degree: Bachelor of Engineering", normal))
    story.append(Paragraph("Branch: Computer Science", normal))
    story.append(Paragraph("Passing Year: 2020", normal))
    story.append(Paragraph("Percentage: 85.4%", normal))

    # ─── PAGE 2: EXPERIENCE + SKILLS ──────────────────────────────────────
    from reportlab.platypus import PageBreak
    story.append(PageBreak())

    story.append(Paragraph("WORK EXPERIENCE", heading2))

    story.append(Paragraph("<b>Software Engineer</b>", normal))
    story.append(Paragraph("Company: Infosys Limited", normal))
    story.append(Paragraph("Job Title: Software Engineer II", normal))
    story.append(Paragraph("Designation: Senior Software Engineer", normal))
    story.append(Paragraph("Duration: August 2022 - Present", normal))
    story.append(Paragraph(
        "• Designed and maintained REST APIs using FastAPI and PostgreSQL serving 2M+ daily requests.<br/>"
        "• Led migration from monolith to microservices, reducing deployment time by 60%.<br/>"
        "• Implemented ML model serving layer using ONNX Runtime and Redis caching.",
        normal,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Junior Developer</b>", normal))
    story.append(Paragraph("Organization: TechMahindra", normal))
    story.append(Paragraph("Role: Backend Developer", normal))
    story.append(Paragraph("Duration: July 2020 - July 2022", normal))
    story.append(Paragraph(
        "• Built ETL pipelines processing 50GB+ of daily log data using Apache Spark.<br/>"
        "• Created automated testing framework reducing QA cycle by 40%.",
        normal,
    ))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("SKILLS", heading2))
    story.append(Paragraph(
        "Technical Skills: Python, FastAPI, Django, PostgreSQL, MongoDB, Redis, "
        "Docker, Kubernetes, Apache Kafka, Apache Spark, React, TypeScript, "
        "REST APIs, GraphQL, AWS, GCP, Git, CI/CD",
        normal,
    ))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("CERTIFICATIONS", heading2))
    story.append(Paragraph("Certifications: AWS Certified Solutions Architect – Associate (2023)", normal))
    story.append(Paragraph("Certificate: Google Cloud Professional Data Engineer (2022)", normal))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("LANGUAGES", heading2))
    story.append(Paragraph("Languages: English (Fluent), Hindi (Native), Marathi (Native)", normal))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("ACHIEVEMENTS", heading2))
    story.append(Paragraph(
        "Achievements: Winner, Smart India Hackathon 2019 (National Level). "
        "Published research paper on distributed tracing in IEEE conference 2021. "
        "Top performer award at Infosys for Q3 2023.",
        normal,
    ))

    # ─── PAGE 3: PROJECTS + IDENTIFIERS ───────────────────────────────────
    story.append(PageBreak())

    story.append(Paragraph("PROJECTS", heading2))
    story.append(Paragraph(
        "<b>Smart Form Auto-Filling System</b> (2024)<br/>"
        "• Full-stack application leveraging LLMs and RAG to auto-fill web forms from uploaded documents.<br/>"
        "• Stack: Python, FastAPI, React, ChromaDB, MongoDB, Celery, BAAI/bge-m3.",
        normal,
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Real-Time Fraud Detection Pipeline</b> (2023)<br/>"
        "• Kafka-based streaming pipeline processing 100K events/sec with sub-50ms latency.<br/>"
        "• Used XGBoost model with online learning capabilities.",
        normal,
    ))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("IDENTIFICATION (FOR VERIFICATION)", heading2))
    story.append(Paragraph("PAN: ABCDE1234F", normal))
    story.append(Paragraph("Passport Number: A1234567", normal))
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph("REFERENCES", heading2))
    story.append(Paragraph("Available on request.", normal))

    doc.build(story)
    print(f"Created: {OUTPUT}")


def _create_minimal_pdf():
    """Minimal PDF without reportlab (uses raw PDF bytes)."""
    content = b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R 4 0 R 5 0 R] /Count 3>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]
/Contents 6 0 R /Resources <</Font <</F1 7 0 R>>>>>>endobj
4 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]
/Contents 8 0 R /Resources <</Font <</F1 7 0 R>>>>>>endobj
5 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]
/Contents 9 0 R /Resources <</Font <</F1 7 0 R>>>>>>endobj
6 0 obj<</Length 820>>
stream
BT /F1 16 Tf 72 780 Td (Sanket Anil Desai) Tj ET
BT /F1 11 Tf 72 755 Td (Software Engineer) Tj ET
BT /F1 10 Tf 72 720 Td (Email: sanket.desai@example.com) Tj ET
BT /F1 10 Tf 72 705 Td (Phone: +91 98765 43210) Tj ET
BT /F1 10 Tf 72 690 Td (LinkedIn: https://linkedin.com/in/sanketdesai) Tj ET
BT /F1 10 Tf 72 675 Td (GitHub: https://github.com/sanketdesai) Tj ET
BT /F1 10 Tf 72 660 Td (Date of Birth: 15/08/1998) Tj ET
BT /F1 10 Tf 72 645 Td (Gender: Male) Tj ET
BT /F1 10 Tf 72 630 Td (Nationality: Indian) Tj ET
BT /F1 10 Tf 72 615 Td (Current Address: 42 MG Road Pune Maharashtra 411001) Tj ET
BT /F1 10 Tf 72 600 Td (City: Pune) Tj ET
BT /F1 10 Tf 72 585 Td (State: Maharashtra) Tj ET
BT /F1 10 Tf 72 570 Td (Country: India) Tj ET
BT /F1 10 Tf 72 555 Td (Postal Code: 411001) Tj ET
BT /F1 10 Tf 72 530 Td (EDUCATION) Tj ET
BT /F1 10 Tf 72 515 Td (University: Savitribai Phule Pune University) Tj ET
BT /F1 10 Tf 72 500 Td (Degree: Bachelor of Engineering) Tj ET
BT /F1 10 Tf 72 485 Td (Specialization: Computer Engineering) Tj ET
BT /F1 10 Tf 72 470 Td (Graduation Year: 2020) Tj ET
BT /F1 10 Tf 72 455 Td (CGPA: 8.7 / 10) Tj ET
BT /F1 10 Tf 72 440 Td (Percentage: 85.4%) Tj ET
endstream
endobj
7 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
8 0 obj<</Length 480>>
stream
BT /F1 14 Tf 72 780 Td (WORK EXPERIENCE) Tj ET
BT /F1 10 Tf 72 755 Td (Company: Infosys Limited) Tj ET
BT /F1 10 Tf 72 740 Td (Job Title: Software Engineer II) Tj ET
BT /F1 10 Tf 72 725 Td (Duration: August 2022 - Present) Tj ET
BT /F1 10 Tf 72 700 Td (Organization: TechMahindra) Tj ET
BT /F1 10 Tf 72 685 Td (Role: Backend Developer) Tj ET
BT /F1 10 Tf 72 670 Td (Duration: July 2020 - July 2022) Tj ET
BT /F1 14 Tf 72 640 Td (SKILLS) Tj ET
BT /F1 10 Tf 72 620 Td (Technical Skills: Python FastAPI Django PostgreSQL MongoDB Redis Docker) Tj ET
BT /F1 14 Tf 72 590 Td (CERTIFICATIONS) Tj ET
BT /F1 10 Tf 72 570 Td (Certifications: AWS Certified Solutions Architect 2023) Tj ET
BT /F1 14 Tf 72 540 Td (LANGUAGES) Tj ET
BT /F1 10 Tf 72 520 Td (Languages: English Hindi Marathi) Tj ET
endstream
endobj
9 0 obj<</Length 260>>
stream
BT /F1 14 Tf 72 780 Td (PROJECTS) Tj ET
BT /F1 10 Tf 72 755 Td (Smart Form Auto-Filling System 2024) Tj ET
BT /F1 10 Tf 72 730 Td (Real-Time Fraud Detection Pipeline 2023) Tj ET
BT /F1 14 Tf 72 700 Td (IDENTIFICATION) Tj ET
BT /F1 10 Tf 72 680 Td (PAN: ABCDE1234F) Tj ET
BT /F1 10 Tf 72 660 Td (Passport Number: A1234567) Tj ET
endstream
endobj
xref
0 10
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000433 00000 n
0000000593 00000 n
0000001461 00000 n
0000001540 00000 n
0000002068 00000 n
trailer<</Size 10 /Root 1 0 R>>
startxref
2376
%%EOF
"""
    OUTPUT.write_bytes(content)
    print(f"Created minimal PDF (no reportlab): {OUTPUT}")


if __name__ == "__main__":
    create_resume()
