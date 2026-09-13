import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors

def create_resume():
    output_path = "test-data/sanket_mali.pdf"
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontSize = 10
    normal.leading = 12

    heading = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=12, spaceAfter=6, textColor=colors.black)

    story = []

    text = """Sanket Mali
B.Tech - Computer Science (2023–2027)
Date of Birth: 18 Sep 2005
+91 9699980709 | Email | LinkedIn | GitHub

Education
MPSTME, NMIMS University 2023 - 2027
B. Tech in Computer Science
CGPA: 8.68/10.00
R.C. Patel Junior College 2022 - 2023
HSC: 79.50
R.C. Patel English Medium Secondary School 2020 - 2021
SSC: 86.50

Projects
Smart Campus Entry Monitoring System | GitHub
• Engineered a real-time entry/exit tracking platform to eliminate manual register-based entry and reduce gate congestion at peak hours
• Built biometric + SAP ID authentication, role-based access control (RBAC), and live analytics dashboards using React.js, Node.js, Express.js, MongoDB, Socket.IO, Tailwind CSS, Chart.js
• Containerized the application using Docker with separate services for frontend, backend, and database, ensuring consistent deployment across environments
• Piloted with 60 students, reducing average entry processing time from ~5 seconds to under 1 second per student while automating visitor logging and parent SMS/email alerts currently under evaluation for full deployment across campus

Wanderlust | GitHub
• Built a scalable Airbnb-inspired booking platform using the MVC architecture with Node.js, Express.js, MongoDB, secure authentication (Passport.js), and RESTful APIs.
• Integrated Mapbox for interactive property maps, Cloudinary for image hosting, and Razorpay for payment processing
• Added wishlist management, an AI chatbot powered by the Groq API, an admin dashboard, and integrated Prometheus and Grafana for real-time monitoring of API response times, user logins, booking metrics, and system health, delivering a production-ready, modular application.

MetroMind | GitHub
• Built an AI-powered intelligent document management system to process, classify, and retrieve large volumes of multilingual documents using AI-based OCR and semantic search powered by open-source Sentence-Transformer embeddings.
• Developed an AI-driven document classification module for automatic categorization and integrated real-time notifications using WebSockets and email for enhanced user engagement.
• Secured the platform with JWT-based authentication and role-based access control (RBAC) and built an analytics dashboard to monitor document insights and system activity.
• Used GitHub Copilot and ChatGPT/Claude throughout development to accelerate coding, manually reviewing and validating all AI-generated code for correctness, security, and performance before integration.

Certifications & Publications
• Advanced Database Testing and Verification Using Automated Tools and Vulnerability Analysis – Presented at 4th IEEE DELCON 2025, Jamia Millia Islamia, New Delhi; published in IEEE Xplore.
• Providing Technical Support for AWS Workloads – AWS
• AWS Cloud Technical Essentials – AWS
• Introduction to Information Technology and AWS Cloud – AWS
• Hands-on Introduction to Linux Commands and Shell Scripting – IBM

Core Skills
Technical Skills:
Languages: C++, JavaScript, SQL
Frontend: React, HTML5, CSS3, Tailwind
Backend: Node.js, Express.js, EJS
Databases: MongoDB, MySQL
Cloud/DevOps: AWS, Docker, Prometheus, Grafana, Linux
GenAI/LLM Tools: GitHub Copilot, ChatGPT & Claude, Prompt Engineering, Groq API, Sentence-Transformers
Concepts: OOP, DBMS, OS, CN, REST APIs, Microservices, Data Structures & Algorithms
Soft Skills: Critical Thinking, Adaptability, Problem Solving, Team Collaboration, Continuous Learning

Achievements & Extracurriculars
• Team Leader, Smart India Hackathon (SIH)
• Advanced to Round 2 of the Nomura Kakushin Hackathon (Top 6 teams)
• Active CSI Member (2023–Present)
• Participated in 10+ hackathons
"""

    for line in text.split("\n"):
        if line.strip() == "":
            story.append(Spacer(1, 10))
        elif line.strip() in ["Education", "Projects", "Certifications & Publications", "Core Skills", "Achievements & Extracurriculars"]:
            story.append(Paragraph(f"<b>{line.strip()}</b>", heading))
        else:
            story.append(Paragraph(line.strip(), normal))

    doc.build(story)
    print(f"Created: {output_path}")

if __name__ == "__main__":
    create_resume()
