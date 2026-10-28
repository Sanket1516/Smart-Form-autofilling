"""Fictional resume used by the resume-and-form demo. Single source of truth for the PDF.

Every value here is invented. The backend never reads this module: the resume is uploaded as a PDF
and goes through the normal extraction, chunking and vector indexing like any user document.
"""

from __future__ import annotations

BANNER = "DEMO DATA — fictional profile. Not a real person; not verified employment or education history."

NAME = "Kavya Suresh Deshpande"
EMAIL = "kavya.deshpande.demo@example.com"
PHONE = "+91-9000054321"
LOCATION = "Pune, Maharashtra, India"

HEADLINE = "B.Tech in Computer Science and Engineering · Demo Institute of Technology"

CAREER_OBJECTIVE = (
    "To begin my career as a software engineer, contribute to practical software development projects, "
    "and strengthen my skills in backend engineering, AI applications, and system design."
)

EDUCATION = [
    ("Degree", "B.Tech in Computer Science and Engineering"),
    ("University", "Demo Institute of Technology"),
    ("Graduation Year", "2029"),
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

ACHIEVEMENTS_INTRO = (
    "Achievements I am most proud of: I completed an academic project involving REST APIs and database integration, "
    "built several working software prototypes during my first year, and implemented automated API tests during my "
    "internship that made the team's releases more reliable."
)
ACHIEVEMENTS = [
    "Completed an academic project involving REST APIs and database integration.",
    "Built multiple academic software prototypes.",
    "Practiced programming and problem-solving through technical exercises.",
]

ADDITIONAL_NOTE = (
    "Additional information: I am open to relocating, comfortable working in a hybrid setup, available to join "
    "immediately, and happy to complete a technical assessment or interview at the company's convenience. "
    "I have no other commitments that affect my availability."
)

ADDITIONAL = [
    ("Availability", "Immediate"),
    ("Preferred Role", "Software Development Engineer"),
    ("Preferred Work Mode", "Hybrid"),
    ("Notice Period", "Not applicable to the fictional student profile."),
]

PROJECT_CONTRIBUTION = (
    "My contribution to the AI-Powered Resume Assistant project: I designed the document ingestion flow, wrote the FastAPI endpoints that accept resume uploads and answer questions about a candidate, and built the retrieval step that selects the most relevant passages. I also wrote the automated tests for the upload and question-answering endpoints and documented how to run the project."
)

TECHNICAL_CHALLENGE = (
    "A technical challenge I solved: in the AI-Powered Resume Assistant, answers sometimes quoted unrelated sections because long resumes were split into chunks that were too large. I solved it by splitting text into smaller overlapping chunks, comparing the retrieved passages against a set of sample questions, and tuning the chunk size until the correct section was returned consistently."
)

CLOUD_EXPERIENCE = (
    "Cloud computing experience: deployed the AI-Powered Resume Assistant to a cloud virtual machine on AWS EC2, "
    "packaged the FastAPI service with Docker, and stored its data on a managed MongoDB Atlas cluster. "
    "I configured environment variables, security groups and a simple health check for the deployment. "
    "(Fictional demo experience.)"
)

WHY_HIRE = (
    "Why you should hire me: I bring a solid foundation in Python and JavaScript, hands-on experience building REST APIs and AI-based document tools, and a habit of testing my work before I share it. I learn new technologies quickly, communicate clearly with teammates, and take ownership of problems until they are resolved. I am ready to start immediately and contribute from the first week."
)

WHY_ROLE = (
    "I am applying for the Software Development Engineer role because it combines backend engineering with "
    "practical AI applications, which is where my projects and internship have been focused. I want to build "
    "reliable software used by real people and keep growing under experienced engineers."
)

PROBLEM_APPROACH = (
    "My approach to solving difficult problems: I first reproduce the problem and read the error messages and logs to understand what is actually failing. Then I break it into smaller parts, test each assumption, fix the smallest cause, and add a test so the problem does not return. If I am stuck for too long, I ask a teammate for help and share what I have already tried."
)

TEAMWORK = (
    "How I work in a team: during my internship I worked with two other interns and a mentor, taking part in daily check-ins, code reviews and bug triage. In the AI-Powered Resume Assistant project I coordinated a team of four, divided the work by module, reviewed pull requests before merging, and kept everyone updated with short written progress notes."
)

IMPROVEMENT_AREAS = (
    "Areas I am currently trying to improve: I want to improve my system design skills for larger applications, learn more about cloud deployment and monitoring, and become faster at estimating how long tasks will take. I am working on these by reading engineering blogs, building small deployment exercises and asking my mentor for feedback on my plans."
)

CAREER_GOALS = (
    "In the next few years I want to become a dependable backend engineer, gain experience designing scalable "
    "services and AI-powered features, and eventually mentor new engineers while growing into a technical lead."
)

RESPONSES = [
    ("Project contribution", PROJECT_CONTRIBUTION),
    ("Technical challenge solved", TECHNICAL_CHALLENGE),
    ("Achievements I am most proud of", ACHIEVEMENTS_INTRO),
    ("Why you should hire me", WHY_HIRE),
    ("Why this role", WHY_ROLE),
    ("Approach to solving difficult problems", PROBLEM_APPROACH),
    ("How I work in a team", TEAMWORK),
    ("Areas I am improving", IMPROVEMENT_AREAS),
    ("Additional information", ADDITIONAL_NOTE),
]

# What the demo form should and should not be able to fill from this resume. Used by tests only.
EXPECTED_STRUCTURED = {
    "full_name": "Kavya Suresh Deshpande",
    "email": EMAIL,
    "graduation_year": "2029",
    "university": "Demo Institute of Technology",
    "job_role": "Software Development Engineer",
    "work_mode": "Hybrid",
    "availability": "Immediate",
}
NOT_IN_RESUME = ("Kubernetes", "Azure")
