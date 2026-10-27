"""Fictional resume used by the resume-and-form demo. Single source of truth for the PDF.

Every value here is invented. The backend never reads this module: the resume is uploaded as a PDF
and goes through the normal extraction, chunking and vector indexing like any user document.
"""

from __future__ import annotations

BANNER = "DEMO DATA — fictional profile. Not a real person; not verified employment or education history."

NAME = "Aarav Sharma"
EMAIL = "aarav.sharma.demo@example.com"
PHONE = "+91-9000001234"
LOCATION = "Pune, Maharashtra, India"

HEADLINE = "B.Tech in Computer Science and Engineering · Example Institute of Technology"

CAREER_OBJECTIVE = (
    "To begin my career as a software engineer, contribute to practical software development projects, "
    "and strengthen my skills in backend engineering, AI applications, and system design."
)

EDUCATION = [
    ("Degree", "B.Tech in Computer Science and Engineering"),
    ("University", "Example Institute of Technology"),
    ("Graduation Year", "2027"),
    ("CGPA", "8.6/10"),
]

SKILLS = [
    ("Programming Languages", "Python, C++, JavaScript, SQL"),
    ("Frontend", "React.js, HTML5, CSS3, Tailwind CSS"),
    ("Backend", "Node.js, Express.js, FastAPI"),
    ("Databases", "MongoDB, PostgreSQL, MySQL"),
    ("AI and Machine Learning", "Large Language Models, Retrieval-Augmented Generation (RAG), Semantic Search, "
                                "Document Processing, Natural Language Processing"),
    ("Tools", "Git, GitHub, Docker, Postman"),
]

EXPERIENCE = {
    "position": "Software Development Intern",
    "organization": "DemoTech Solutions (fictional)",
    "duration": "May 2026 – July 2026",
    "note": "Fictional internship entry for demonstration; not verified employment history.",
    "responsibilities": [
        "Developed REST API endpoints for an internal project management application.",
        "Implemented database operations for storing and retrieving project information.",
        "Assisted with frontend integration and API testing.",
        "Collaborated with team members to identify and resolve application bugs.",
    ],
    "achievements": [
        "Implemented automated API tests for selected endpoints.",
        "Improved the reliability of the demo application's data validation workflow.",
    ],
}

PROJECTS = [
    ("AI-Powered Resume Assistant",
     "Developed a prototype that extracts information from resumes and retrieves relevant details to answer "
     "questions about a candidate's qualifications.",
     "Python, FastAPI, RAG, vector database."),
    ("Smart Campus Monitoring System",
     "Developed a prototype for monitoring campus entry and exit events, managing student records, and "
     "generating attendance reports.",
     "React, Node.js, Express.js, MongoDB."),
    ("Task Management Web Application",
     "Built a web application for creating, updating, assigning, and tracking tasks.",
     "React.js, Express.js, PostgreSQL."),
]

STRENGTHS = [
    "Analytical problem-solving.",
    "Quick learning and adaptability.",
    "Ability to break complex problems into smaller tasks.",
    "Team collaboration.",
    "Willingness to learn new technologies.",
]

WEAKNESSES = (
    "I sometimes spend extra time refining technical solutions because I want them to be reliable. "
    "I am improving my ability to prioritize tasks, define time limits, and balance code quality with "
    "delivery deadlines."
)

ACHIEVEMENTS = [
    "Completed an academic project involving REST APIs and database integration.",
    "Built multiple academic software prototypes.",
    "Practiced programming and problem-solving through technical exercises.",
]

ADDITIONAL = [
    ("Availability", "Immediate"),
    ("Preferred Role", "Software Development Engineer"),
    ("Preferred Work Mode", "Hybrid"),
    ("Notice Period", "Not applicable to the fictional student profile."),
]

# What the demo form should and should not be able to fill from this resume. Used by tests only.
EXPECTED_STRUCTURED = {
    "full_name": "Aarav Sharma",
    "email": EMAIL,
    "graduation_year": "2027",
    "university": "Example Institute of Technology",
    "job_role": "Software Development Engineer",
    "work_mode": "Hybrid",
    "availability": "Immediate",
}
NOT_IN_RESUME = ("cloud computing", "AWS", "Azure", "Kubernetes")
