"""Single source of truth for the synthetic demo applicant.

Every document, form expectation and test answer is derived from this module.
Nothing here is a real person, identifier, certificate or account. Identifiers
only follow the *shape* a form validator expects so the extraction pipeline can
be exercised; none is valid, issued or traceable.

SYNTHETIC DEMO DATA - NOT A VALID GOVERNMENT DOCUMENT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

BANNER = "SYNTHETIC DEMO DATA — NOT A VALID GOVERNMENT DOCUMENT"

# --------------------------------------------------------------------------- person
FIRST, MIDDLE, LAST = "Kavya", "Suresh", "Deshpande"
FULL_NAME = f"{FIRST} {MIDDLE} {LAST}"
FATHER = "Suresh Ramesh Deshpande"
MOTHER = "Sunita Suresh Deshpande"
DOB = date(2007, 8, 23)
GENDER = "Female"
NATIONALITY = "Indian"
PLACE_OF_BIRTH = "Nashik, Maharashtra"
BIRTH_HOSPITAL = "Demo City Hospital"
BLOOD_GROUP = "O+"
MOBILE = "9000054321"
EMAIL = "kavya.deshpande.demo@example.com"

PERMANENT_ADDRESS = "Flat 402, Sunrise Heights, Demo Nagar, Nashik, Maharashtra 422099"
PERMANENT_PIN = "422099"
CORRESPONDENCE_ADDRESS = "Room 214, Block C, Demo Institute Hostel, University Road, Pune, Maharashtra 411099"
CORRESPONDENCE_PIN = "411099"
CITY, STATE = "Nashik", "Maharashtra"

EMERGENCY_NAME = "Rahul Ramesh Deshpande"
EMERGENCY_RELATION = "Uncle"
EMERGENCY_PHONE = "9000067890"

# --------------------------------------------------------------------- identifiers
TAX_ID = "DEMPD4821Z"                  # PAN-shaped, not issued
VOTER_ID = "DMO4821937"                # EPIC-shaped, not issued
DL_NUMBER = "MH15 20250054321"
DL_ISSUE, DL_VALID = date(2025, 9, 5), date(2045, 9, 4)
DL_CLASSES, DL_AUTHORITY = "MCWG, LMV", "RTO Nashik (Fictional)"
PASSPORT_NO = "Z9012345"
PASSPORT_ISSUE, PASSPORT_EXPIRY = date(2024, 11, 14), date(2034, 11, 13)
PASSPORT_PLACE = "Pune"
BIRTH_REG_NO = "B-2007-NSK-004519"
BIRTH_REG_DATE, BIRTH_ISSUE = date(2007, 9, 4), date(2007, 9, 12)

# ---------------------------------------------------------------------------- bank
BANK_NAME = "Example Sahakari Bank (Fictional)"
BANK_BRANCH = "Demo Nagar Branch"
BANK_BRANCH_ADDRESS = "Shop 6, Demo Plaza, Demo Nagar, Nashik, Maharashtra 422099"
ACCOUNT_NO = "910000456789"
IFSC = "DEMO0000417"                   # four letters + 0 + six characters, deliberately DEMO
MICR = "422999017"
ACCOUNT_TYPE = "Savings Account"

# ----------------------------------------------------------------------- utility
UTILITY_PROVIDER = "Example Power Distribution Co. Ltd. (Fictional)"
CONSUMER_NO = "EL-4010-0508-1"
METER_NO = "MT-77-0I58"                # letter I next to digits on purpose
BILL_PERIOD = (date(2026, 8, 1), date(2026, 8, 31))
BILL_DATE, BILL_DUE = date(2026, 9, 5), date(2026, 9, 20)
UNITS, BILL_AMOUNT = 312, "2347.50"

# ---------------------------------------------------------------------- household
HOUSEHOLD_REF = "HH-NSK-2024-00417"
HOUSEHOLD = [  # name, relationship to applicant, age, occupation
    ("Suresh Ramesh Deshpande", "Father", 49, "Self-employed"),
    ("Sunita Suresh Deshpande", "Mother", 46, "Homemaker"),
    (FULL_NAME, "Self (Applicant)", 19, "Student"),
    ("Aditya Suresh Deshpande", "Brother", 14, "Student"),
    ("Ramesh Vithal Deshpande", "Grandfather", 76, "Retired"),
]

# ------------------------------------------------------------------ certificates
INCOME_ANNUAL = 480000
INCOME_CERT_NO = "INC/2026/NSK/008812"
INCOME_ISSUE, INCOME_VALID = date(2026, 4, 18), date(2027, 3, 31)
INCOME_AUTHORITY = "Demo Tehsil Revenue Office, Nashik (Fictional)"
INCOME_FY = "2025-26"

CATEGORY = "OBC"
CASTE = "Demo Community A (Fictional)"
CASTE_CERT_NO = "CC/2025/NSK/004512"
CASTE_ISSUE, CASTE_AUTHORITY = date(2025, 7, 9), "Sub-Divisional Office, Nashik (Fictional)"
CASTE_VALIDITY_NO = "CVC/2025/NSK/007731"
CASTE_VALIDITY_ISSUE = date(2025, 11, 20)
CASTE_VALIDITY_AUTHORITY = "Demo Caste Scrutiny Committee, Nashik (Fictional)"

DOMICILE_STATE = "Maharashtra"
DOMICILE_NO = "DOM/2026/NSK/003377"
DOMICILE_ISSUE = date(2026, 2, 11)
DOMICILE_AUTHORITY = "Demo Tehsil Revenue Office, Nashik (Fictional)"
DOMICILE_YEARS = 19  # resident since birth

# --------------------------------------------------------------------- education


@dataclass(frozen=True)
class Subject:
    code: str
    name: str
    max_marks: int
    obtained: int
    grade: str
    theory: int | None = None
    internal: int | None = None


CLASS10_BOARD = "Example Board of Secondary Education (Fictional)"
CLASS10_SCHOOL = "Demo Vidya Mandir High School, Nashik"
CLASS10_ROLL = "204518"
CLASS10_MONTH, CLASS10_YEAR = "March", 2023
CLASS10_RESULT_DATE = date(2023, 5, 14)
CLASS10_SUBJECTS = [
    Subject("EN-101", "English", 100, 91, "A1", 73, 18),
    Subject("MR-102", "Marathi", 100, 88, "A2", 70, 18),
    Subject("MA-103", "Mathematics", 100, 96, "A1", 77, 19),
    Subject("SC-104", "Science", 100, 92, "A1", 73, 19),
    Subject("SS-105", "Social Science", 100, 90, "A2", 72, 18),
]

CLASS12_BOARD = "Example State Board of Higher Secondary Education (Fictional)"
CLASS12_SCHOOL = "Demo Junior College of Science, Nashik"
CLASS12_ROLL = "S317442"
CLASS12_STREAM = "Science"
CLASS12_MONTH, CLASS12_YEAR = "March", 2025
CLASS12_RESULT_DATE = date(2025, 5, 12)
CLASS12_SUBJECTS = [
    Subject("01", "English", 100, 84, "A"),
    Subject("54", "Physics", 100, 86, "A"),
    Subject("55", "Chemistry", 100, 82, "A"),
    Subject("40", "Mathematics", 100, 90, "A+"),
    Subject("61", "Computer Science", 100, 94, "A+"),
]


def totals(subjects: list[Subject]) -> tuple[int, int, float]:
    got = sum(s.obtained for s in subjects)
    out_of = sum(s.max_marks for s in subjects)
    return got, out_of, round(got / out_of * 100, 2)


CLASS10_TOTAL, CLASS10_MAX, CLASS10_PCT = totals(CLASS10_SUBJECTS)    # 457 / 500 / 91.40
CLASS12_TOTAL, CLASS12_MAX, CLASS12_PCT = totals(CLASS12_SUBJECTS)    # 436 / 500 / 87.20

# --------------------------------------------------------------- bank statement
STATEMENT_PERIOD = (date(2026, 7, 1), date(2026, 9, 30))
OPENING_BALANCE = 24350.00
# (date, description, reference, debit, credit)
_RAW_TRANSACTIONS = [
    (date(2026, 7, 2), "UPI/Campus Canteen", "UPI6112340011", 185.00, None),
    (date(2026, 7, 4), "NEFT CR Suresh R Deshpande", "NEFT26070401277", None, 8000.00),
    (date(2026, 7, 6), "UPI/Demo Book Store", "UPI6112340187", 1240.00, None),
    (date(2026, 7, 9), "ATM WDL Univ Road Pune", "ATM260709004", 2000.00, None),
    (date(2026, 7, 12), "UPI/City Bus Pass", "UPI6112340455", 450.00, None),
    (date(2026, 7, 15), "UPI/Mess Fees July", "UPI6112340602", 3200.00, None),
    (date(2026, 7, 21), "INT CR Quarterly Interest", "INT260721", None, 212.40),
    (date(2026, 7, 27), "UPI/Stationery Mart", "UPI6112340933", 365.00, None),
    (date(2026, 8, 3), "NEFT CR Suresh R Deshpande", "NEFT26080301544", None, 8000.00),
    (date(2026, 8, 5), "UPI/Demo Mobile Recharge", "UPI6112341020", 299.00, None),
    (date(2026, 8, 8), "UPI/Mess Fees August", "UPI6112341118", 3200.00, None),
    (date(2026, 8, 11), "UPI/Lab Fee Demo Institute", "UPI6112341205", 1500.00, None),
    (date(2026, 8, 14), "IMPS CR Merit Scholarship Demo", "IMPS26081408812", None, 12000.00),
    (date(2026, 8, 17), "UPI/Online Course Demo", "UPI6112341399", 899.00, None),
    (date(2026, 8, 23), "UPI/Birthday Gift Shop", "UPI6112341476", 780.00, None),
    (date(2026, 8, 29), "ATM WDL Univ Road Pune", "ATM260829011", 1500.00, None),
    (date(2026, 9, 1), "UPI/Mess Fees September", "UPI6112341590", 3200.00, None),
    (date(2026, 9, 3), "NEFT CR Suresh R Deshpande", "NEFT26090301791", None, 8000.00),
    (date(2026, 9, 5), "UPI/Demo Books Online", "UPI6112341702", 2150.00, None),
    (date(2026, 9, 9), "UPI/Campus Canteen", "UPI6112341811", 220.00, None),
    (date(2026, 9, 12), "UPI/Demo Cab Ride", "UPI6112341934", 340.00, None),
    (date(2026, 9, 15), "UPI/Exam Application Fee Demo", "UPI6112342077", 1800.00, None),
    (date(2026, 9, 18), "UPI/Pharmacy Demo", "UPI6112342155", 410.00, None),
    (date(2026, 9, 24), "ATM WDL Univ Road Pune", "ATM260924017", 2000.00, None),
    (date(2026, 9, 28), "UPI/Campus Canteen", "UPI6112342290", 175.00, None),
]


def transactions() -> list[dict]:
    """Rows with a consistent running balance (computed once, never typed)."""
    balance = OPENING_BALANCE
    rows = []
    for when, desc, ref, debit, credit in _RAW_TRANSACTIONS:
        balance = round(balance - (debit or 0) + (credit or 0), 2)
        rows.append({"date": when, "description": desc, "reference": ref,
                     "debit": debit, "credit": credit, "balance": balance})
    return rows


TRANSACTIONS = transactions()
CLOSING_BALANCE = TRANSACTIONS[-1]["balance"]

# ----------------------------------------------------- fictional scholarship rules
DEMO_EXAM_ID = "DEMOSCHOLAR_2026"
DEMO_EXAM_NAME = "Demo Merit Scholarship 2026 (fictional)"


def iso(d: date) -> str:
    return d.isoformat()


def dmy(d: date, sep: str = "/") -> str:
    return d.strftime(f"%d{sep}%m{sep}%Y")


def long_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


def mon_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def inr(amount: float) -> str:
    """Indian digit grouping, e.g. 480000 -> 4,80,000.00"""
    whole, frac = f"{amount:.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join([*groups, tail]) + "." + frac


def age_on(day: date) -> int:
    return day.year - DOB.year - ((day.month, day.day) < (DOB.month, DOB.day))
