"""Held-out evaluation set: written after development, never used for tuning.

A different (fictitious) candidate, boards, banks, layouts and form wording than
``indian_fixtures.py``. Expected values are what a careful human reading the
document would record. Scores on this set are the honest generalisation estimate.
"""

from __future__ import annotations

from tests.indian_fixtures import DocFixture, FormFieldCase, _options, table

AADHAAR = DocFixture(
    "ho_aadhaar_yob",
    "AADHAAR_CARD",
    "ocr",
    [
        [
            "Government of India",
            "Priya Example Deshmukh",
            "Year of Birth : 2006",
            "FEMALE",
            "9876 5432 1012",
            "Aadhaar - Aam Admi ka Adhikar",
        ]
    ],
    expected={
        "personal.full_name": "Priya Example Deshmukh",
        "identity.gender": "Female",
        "identity.aadhaar_number": "987654321012",
    },
    absent=("personal.date_of_birth",),
)

PAN_OLD = DocFixture(
    "ho_pan_old_format",
    "PAN_CARD",
    "ocr",
    [
        [
            "INCOME TAX DEPARTMENT",
            "GOVT. OF INDIA",
            "PRIYA EXAMPLE DESHMUKH",
            "RAMESH EXAMPLE DESHMUKH",
            "09/11/2006",
            "Permanent Account Number",
            "BCDPD5678K",
            "Signature",
        ]
    ],
    expected={"identity.pan_number": "BCDPD5678K"},
)

CBSE_12 = DocFixture(
    "ho_cbse_class12",
    "CLASS_12_MARKSHEET",
    "table",
    [
        [
            "CENTRAL BOARD OF SECONDARY EDUCATION",
            "SENIOR SCHOOL CERTIFICATE EXAMINATION 2024",
            "STATEMENT OF MARKS",
            "This is to certify that PRIYA EXAMPLE DESHMUKH",
            "Roll No. 21456789",
            "Mother's Name SUNITA EXAMPLE DESHMUKH",
            "Father's / Guardian's Name RAMESH EXAMPLE DESHMUKH",
            "School 55443 EXAMPLE VIDYALAYA NAGPUR",
            *table(
                "SUB CODE | SUB NAME | THEORY | PRAC./IA | TOTAL | POSITIONAL GRADE",
                "301 | ENGLISH CORE | 072 | 020 | 092 | A1",
                "042 | PHYSICS | 058 | 030 | 088 | A2",
                "043 | CHEMISTRY | 061 | 030 | 091 | A1",
                "044 | BIOLOGY | 064 | 030 | 094 | A1",
                "041 | MATHEMATICS | 070 | 020 | 090 | A1",
            ),
            "Result: PASS",
        ]
    ],
    expected={
        "personal.full_name": "Priya Example Deshmukh",
        "personal.mother_name": "Sunita Example Deshmukh",
        "personal.father_name": "Ramesh Example Deshmukh",
        "academic.class12.roll_number": "21456789",
        "academic.class12.board": "CENTRAL BOARD OF SECONDARY EDUCATION",
        "academic.class12.exam_year": "2024",
        "academic.class12.passing_year": "2024",
        "academic.class12.result_status": "PASS",
        "academic.class12.school": "55443 EXAMPLE VIDYALAYA NAGPUR",
    },
    absent=("academic.class12.percentage", "academic.class10.roll_number"),
    records={
        "academic.class12.subjects": [
            {"code": "301", "name": "ENGLISH CORE", "theory": "72", "total": "92", "grade": "A1"},
            {"code": "042", "name": "PHYSICS", "theory": "58", "total": "88", "grade": "A2"},
            {"code": "043", "name": "CHEMISTRY", "theory": "61", "total": "91", "grade": "A1"},
            {"code": "044", "name": "BIOLOGY", "theory": "64", "total": "94", "grade": "A1"},
            {"code": "041", "name": "MATHEMATICS", "theory": "70", "total": "90", "grade": "A1"},
        ]
    },
)

ICSE_10 = DocFixture(
    "ho_icse_class10",
    "CLASS_10_MARKSHEET",
    "ocr",
    [
        [
            "COUNCIL FOR THE INDIAN SCHOOL CERTIFICATE EXAMINATIONS",
            "INDIAN CERTIFICATE OF SECONDARY EDUCATION (CLASS X) EXAMINATION 2022",
            "Name: PRIYA EXAMPLE DESHMUKH",
            "Unique ID: 7654321",
            "Index No: T/1234/056",
            "Date of Birth: 09/11/2006",
            "School: EXAMPLE CONVENT HIGH SCHOOL, NAGPUR",
            "SUBJECT MARKS OBTAINED",
            "ENGLISH 91",
            "HISTORY CIVICS & GEOGRAPHY 88",
            "MATHEMATICS 95",
            "SCIENCE 93",
            "Result: Pass Certificate Awarded",
        ]
    ],
    expected={
        "personal.full_name": "Priya Example Deshmukh",
        "personal.date_of_birth": "2006-11-09",
        "academic.class10.board": "COUNCIL FOR THE INDIAN SCHOOL CERTIFICATE EXAMINATIONS",
        "academic.class10.school": "EXAMPLE CONVENT HIGH SCHOOL, NAGPUR",
        "academic.class10.exam_year": "2022",
    },
    records={
        "academic.class10.subjects": [
            {"name": "ENGLISH", "marks_obtained": "91"},
            {"name": "MATHEMATICS", "marks_obtained": "95"},
            {"name": "SCIENCE", "marks_obtained": "93"},
        ]
    },
    preserved_labels=("Unique ID", "Index No"),
)

BANK = DocFixture(
    "ho_bank_statement",
    "BANK_STATEMENT",
    "table",
    [
        [
            "EXAMPLE STATE BANK",
            "ACCOUNT STATEMENT",
            "Account Holder: PRIYA EXAMPLE DESHMUKH",
            "A/c No.: 30012345678",
            "IFS Code: EXSB0004567",
            "Branch Name: Civil Lines, Nagpur",
            "MICR: 440002011",
            *table(
                "Txn Date | Value Dt | Narration | Chq./Ref.No. | Withdrawal Amt. | Deposit Amt. | Closing Balance",
                "02/01/2025 | 02/01/2025 | NEFT CR-SCHOLARSHIP | 0000123 | | 12,000.00 | 15,500.00",
                "09/01/2025 | 09/01/2025 | UPI-BOOKSTORE | 509876543210 | 1,250.00 | | 14,250.00",
            ),
        ]
    ],
    expected={
        "financial.account_holder_name": "Priya Example Deshmukh",
        "financial.account_number": "30012345678",
        "financial.ifsc_code": "EXSB0004567",
        "financial.branch_name": "Civil Lines, Nagpur",
        "financial.micr_code": "440002011",
        "financial.bank_name": "EXAMPLE STATE BANK",
    },
    records={
        "financial.transactions": [
            {
                "date": "2025-01-02",
                "description": "NEFT CR-SCHOLARSHIP",
                "reference": "0000123",
                "credit": "12000.00",
                "balance": "15500.00",
            },
            {
                "date": "2025-01-09",
                "description": "UPI-BOOKSTORE",
                "reference": "509876543210",
                "debit": "1250.00",
                "balance": "14250.00",
            },
        ]
    },
)

CASTE_SC = DocFixture(
    "ho_caste_certificate_sc",
    "CASTE_CERTIFICATE",
    "multilingual",
    [
        [
            "महाराष्ट्र शासन",
            "जात प्रमाणपत्र / CASTE CERTIFICATE",
            "Certificate No. : SC/2023/NGP/000777",
            "This is to certify that Kumari PRIYA EXAMPLE DESHMUKH daughter of RAMESH EXAMPLE DESHMUKH of Nagpur belongs to the Examplejati caste which is recognised as a Scheduled Caste.",
            "Category : SC",
            "Date of Issue : 03/03/2023",
            "Issued by : Sub Divisional Officer, Nagpur",
        ]
    ],
    expected={
        "caste_certificate.number": "SC/2023/NGP/000777",
        "caste_certificate.holder_name": "Priya Example Deshmukh",
        "category.social_category": "SC",
        "caste_certificate.issue_date": "2023-03-03",
        "caste_certificate.issuing_authority": "Sub Divisional Officer, Nagpur",
    },
    absent=("caste_validity.number",),
)

INCOME = DocFixture(
    "ho_income_certificate",
    "INCOME_CERTIFICATE",
    "clean",
    [
        [
            "OFFICE OF THE TAHSILDAR, NAGPUR (URBAN)",
            "INCOME CERTIFICATE",
            "Sr. No. INC/NGP/2025/1188",
            "Name of Applicant: Ramesh Example Deshmukh",
            "Annual Family Income: Rs. 7.2 Lakh",
            "Year: 2024-2025",
            "Valid Upto: 31/03/2026",
        ]
    ],
    expected={
        "financial.annual_income": "720000",
        "income_certificate.valid_until": "2026-03-31",
    },
    absent=("personal.full_name",),
)

ELECTRICITY = DocFixture(
    "ho_electricity_bill",
    "ELECTRICITY_BILL",
    "clean",
    [
        [
            "EXAMPLE POWER DISTRIBUTION LIMITED",
            "Electricity Bill for the month of AUG-2025",
            "Consumer Number: 410012398765",
            "Name: RAMESH EXAMPLE DESHMUKH",
            "Units Consumed: 210",
            "Amount Payable: Rs. 2,145.00",
            "Due Date: 20/09/2025",
        ]
    ],
    expected={
        "utility.consumer_number": "410012398765",
        "utility.consumer_name": "Ramesh Example Deshmukh",
        "utility.units_consumed": "210",
        "utility.due_date": "2025-09-20",
    },
    absent=("personal.full_name",),
)

VOTER = DocFixture(
    "ho_voter_id",
    "VOTER_ID",
    "clean",
    [
        [
            "ELECTION COMMISSION OF INDIA",
            "IDENTITY CARD",
            "ABC7654321",
            "Name: Priya Example Deshmukh",
            "Father's Name: Ramesh Example Deshmukh",
            "Sex: Female",
            "Date of Birth: 09/11/2006",
        ]
    ],
    expected={
        "identity.voter_id_number": "ABC7654321",
        "personal.full_name": "Priya Example Deshmukh",
        "personal.father_name": "Ramesh Example Deshmukh",
        "identity.gender": "Female",
        "personal.date_of_birth": "2006-11-09",
    },
)

DOMICILE = DocFixture(
    "ho_domicile_certificate",
    "DOMICILE_CERTIFICATE",
    "clean",
    [
        [
            "GOVERNMENT OF MAHARASHTRA",
            "DOMICILE CERTIFICATE",
            "No. DOM/NGP/2024/5555",
            "This is to certify that PRIYA EXAMPLE DESHMUKH daughter of RAMESH EXAMPLE DESHMUKH has been residing in the State of Maharashtra and is domiciled in the State of Maharashtra.",
            "Date: 11/06/2024",
        ]
    ],
    expected={
        "personal.full_name": "Priya Example Deshmukh",
        "domicile_certificate.state": "Maharashtra",
    },
)

HELDOUT_DOCUMENTS = [
    AADHAAR,
    PAN_OLD,
    CBSE_12,
    ICSE_10,
    BANK,
    CASTE_SC,
    INCOME,
    ELECTRICITY,
    VOTER,
    DOMICILE,
]
HELDOUT_PROFILE_DOCUMENTS = HELDOUT_DOCUMENTS
HELDOUT_USER_FACTS = {"personal.email": "priya.example@example.com", "personal.phone": "9876500002"}

_CASES: list[FormFieldCase] = []


def _f(form: str, concept: str | None, outcome: str, value: str | None = None, **kwargs) -> None:
    kwargs.setdefault("input_type", "text")
    kwargs.setdefault("label", "")
    kwargs["field_id"] = f"{form}:{len(_CASES)}"
    _CASES.append(FormFieldCase(form, kwargs, concept, outcome, value))


F = "heldout_form"
_f(F, "personal.full_name", "fill", "Priya Example Deshmukh", label="Applicant Name")
_f(F, "personal.father_name", "fill", "Ramesh Example Deshmukh", label="Father/Guardian Name")
_f(F, "personal.mother_name", "fill", "Sunita Example Deshmukh", label="Mother Name")
_f(F, "personal.date_of_birth", "fill", "09/11/2006", label="DOB", placeholder="DD/MM/YYYY")
_f(
    F,
    "identity.gender",
    "fill",
    "Female",
    label="Sex",
    input_type="radio",
    options=_options("Male", "Female", "Other"),
)
_f(F, "academic.class12.board", "fill", "CENTRAL BOARD OF SECONDARY EDUCATION", label="12th Board")
_f(F, "academic.class12.roll_number", "fill", "21456789", label="12th Roll No")
_f(F, "academic.class12.subject_marks", "fill", "88", label="Marks in Physics", section="Class XII")
_f(F, "academic.class12.subject_marks", "fill", "94", label="Biology marks", section="Class XII")
_f(F, "academic.class12.percentage", "abstain", None, label="Percentage", section="Class XII")
_f(
    F,
    "academic.class10.school",
    "fill",
    "EXAMPLE CONVENT HIGH SCHOOL, NAGPUR",
    label="Name of School",
    section="Class X details",
)
_f(
    F,
    "academic.class10.subject_marks",
    "fill",
    "95",
    label="Mathematics marks",
    section="Class X details",
)
_f(
    F,
    "category.social_category",
    "review",
    "SC",
    label="Social Category",
    input_type="select",
    options=_options("GEN", "EWS", "OBC-NCL", "SC", "ST"),
)
_f(
    F,
    "financial.annual_income",
    "review",
    "6 to 8 Lakh",
    label="Income Group",
    input_type="select",
    options=_options("Below 2.5 Lakh", "2.5 to 6 Lakh", "6 to 8 Lakh", "Above 8 Lakh"),
)
_f(
    F,
    "financial.account_number",
    "review",
    "30012345678",
    label="Account No.",
    section="Bank details",
)
_f(F, "financial.ifsc_code", "fill", "EXSB0004567", label="IFS Code", section="Bank details")
_f(
    F,
    "financial.branch_name",
    "fill",
    "Civil Lines, Nagpur",
    label="Bank Branch",
    section="Bank details",
)
_f(F, "identity.voter_id_number", "review", "ABC7654321", label="Voter ID Number")
_f(
    F,
    "exam.city_preference",
    "abstain",
    None,
    label="Preferred Exam City",
    input_type="select",
    options=_options("Nagpur", "Pune"),
)
_f(F, None, "abstain", None, label="Enter Captcha")

HELDOUT_FORM_CASES = list(_CASES)
