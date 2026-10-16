"""Specifications of the 15 demo forms.

One spec drives two independent outputs:

* the HTML pages (`forms_gen.py`), which contain NO values and no canonical keys, and
* the expected-answer manifest (`manifest_gen.py`), used only by the test suite.

`expect` is the value the profile says belongs in the field. ``None`` means no
document holds it, so the field must stay empty. ``user=True`` marks a choice or
declaration that only the person may make (must stay empty after autofill).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from demo import profile as P

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
STATES = ["Andhra Pradesh", "Gujarat", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Rajasthan",
          "Tamil Nadu", "Telangana", "Uttar Pradesh"]
CATEGORIES = ["General (Unreserved)", "EWS", "OBC", "SC", "ST"]
YEARS = [str(y) for y in range(2016, 2027)]


@dataclass
class Fld:
    key: str                      # stable spec key (not shown in the HTML)
    label: str
    kind: str = "text"            # text email tel date number textarea select radio checkbox checks file
    expect: str | None = None
    concept: str = ""             # canonical profile concept the field should map to (manifest only)
    required: bool = False
    options: list[str] = field(default_factory=list)
    hint: str = ""
    placeholder: str = ""
    pattern: str = ""
    sensitive: bool = False       # the extension asks for an explicit tick before filling these
    user: bool = False            # choice / declaration reserved for the person
    dynamic: bool = False         # rendered by demo-forms.js after load
    expect_many: list[str] = field(default_factory=list)   # checkbox groups: values that should be checked
    accept: list[str] = field(default_factory=list)        # other defensible values
    trap: str = ""                # what this field is meant to catch


@dataclass
class Section:
    title: str
    fields: list[Fld]
    note: str = ""
    reveal: dict | None = None    # {"when": field_key, "values": [...]} section appears after a choice


@dataclass
class FormSpec:
    number: int
    slug: str
    title: str
    intro: str
    sections: list[Section]
    cryptic_names: bool = False
    accent: str = "#1f4e79"
    source_documents: list[int] = field(default_factory=list)
    subject_tables: list[dict] = field(default_factory=list)   # dynamic subject rows (see below)

    def all_fields(self) -> list[Fld]:
        return [f for s in self.sections for f in s.fields]


def d_iso(d) -> str:
    return P.iso(d)


def subject_fields(prefix: str, label: str, subjects: list[P.Subject], extra_blank: str | None = None) -> list[Fld]:
    """Rows rendered dynamically: max marks and marks obtained per subject."""
    out: list[Fld] = []
    scope = "academic.class10" if prefix == "c10" else "academic.class12"
    for s in subjects:
        slug = s.name.lower().replace(" ", "_")
        out.append(Fld(f"{prefix}_{slug}_max", f"{s.name} — maximum marks", "number", str(s.max_marks),
                       f"{scope}.subjects[{s.name}].max_marks", dynamic=True,
                       trap=f"{label} subject marks"))
        out.append(Fld(f"{prefix}_{slug}_obt", f"{s.name} — marks obtained", "number", str(s.obtained),
                       f"{scope}.subjects[{s.name}].marks_obtained", dynamic=True,
                       trap=f"{label} subject marks"))
    if extra_blank:
        slug = extra_blank.lower().replace(" ", "_")
        out.append(Fld(f"{prefix}_{slug}_max", f"{extra_blank} — maximum marks", "number", None, "", dynamic=True))
        out.append(Fld(f"{prefix}_{slug}_obt", f"{extra_blank} — marks obtained", "number", None, "", dynamic=True))
    return out


def subject_table(prefix: str, subjects: list[P.Subject], extra_blank: str | None = None) -> dict:
    names = [s.name for s in subjects] + ([extra_blank] if extra_blank else [])
    return {"prefix": prefix, "subjects": names}


def f_name(label="Full name", key="full_name", **kw) -> Fld:
    return Fld(key, label, "text", P.FULL_NAME, "personal.full_name", required=True, **kw)


def f_dob(label="Date of birth", key="dob", **kw) -> Fld:
    return Fld(key, label, "date", d_iso(P.DOB), "personal.date_of_birth", required=True, **kw)


def f_gender(**kw) -> Fld:
    return Fld("gender", "Gender", "radio", P.GENDER, "identity.gender", required=True,
               options=["Male", "Female", "Other", "Prefer not to say"], **kw)


FORMS: list[FormSpec] = []

# ------------------------------------------------------------------------------ 1
FORMS.append(FormSpec(
    1, "general-applicant-registration", "General Applicant Registration",
    "Create an applicant record for the demo portal. Nothing is submitted anywhere.",
    [Section("Personal details", [
        f_name(), f_dob(), f_gender(),
        Fld("nationality", "Nationality", "select", P.NATIONALITY, "identity.nationality", required=True,
            options=["Indian", "Other"]),
        Fld("occupation", "Current occupation", "text", None, "", hint="Not stated in any document."),
    ]), Section("Contact", [
        Fld("email", "Email address", "email", P.EMAIL, "personal.email", required=True),
        Fld("mobile", "Mobile number", "tel", P.MOBILE, "personal.phone", required=True, pattern="[0-9]{10}",
            hint="10 digits"),
        Fld("alt_mobile", "Alternate mobile number", "tel", None, "", pattern="[0-9]{10}",
            trap="alternate vs primary mobile (emergency contact phone is a different number)"),
        Fld("permanent_address", "Permanent address", "textarea", P.PERMANENT_ADDRESS,
            "address.permanent_address", required=True),
    ])], source_documents=[1],
))

# ------------------------------------------------------------------------------ 2
FORMS.append(FormSpec(
    2, "tax-identification-application", "Tax Identification Application",
    "Request or update a tax identification record. The identifier is optional (\"if you already have one\").",
    [Section("Applicant", [
        f_name("Applicant name", "applicant_name"), f_dob(),
        Fld("father_name", "Father / parent name", "text", P.FATHER, "personal.father_name", required=True,
            trap="applicant name vs parent name"),
        Fld("mother_name", "Mother's name", "text", P.MOTHER, "personal.mother_name"),
        Fld("existing_tax_id", "Existing tax identifier (if available)", "text", P.TAX_ID, "identity.pan_number",
            sensitive=True, pattern="[A-Z]{5}[0-9]{4}[A-Z]", hint="Ten characters: 5 letters, 4 digits, 1 letter"),
        Fld("aadhaar_link", "Aadhaar number (if available)", "text", None, "", sensitive=True,
            hint="No document in the demo set contains one."),
    ]), Section("Correspondence", [
        Fld("corr_address", "Correspondence address", "textarea", P.CORRESPONDENCE_ADDRESS,
            "address.correspondence_address", required=True, trap="permanent vs correspondence address"),
        Fld("corr_pin", "Correspondence PIN code", "text", P.CORRESPONDENCE_PIN, "address.correspondence_zipcode",
            pattern="[0-9]{6}", trap="permanent vs correspondence PIN"),
        Fld("mobile", "Mobile number", "tel", P.MOBILE, "personal.phone", pattern="[0-9]{10}"),
        Fld("income_source", "Principal source of income", "select", None, "", user=True,
            options=["Salary", "Business", "Scholarship / stipend", "Other"]),
    ])], source_documents=[1, 2],
))

# ------------------------------------------------------------------------------ 3
FORMS.append(FormSpec(
    3, "voter-information-application", "Voter Information Application",
    "Apply to add or correct your entry in the electoral roll (fictional demo process).",
    [Section("Applicant", [
        f_name("Applicant name", "applicant_name"), f_dob(),
        Fld("relative_name", "Name of father / mother / husband", "text", P.FATHER, "personal.father_name",
            required=True, trap="applicant name vs relative name"),
        Fld("relation_type", "Relationship to the person named above", "select", None, "", user=True,
            options=["Father", "Mother", "Husband", "Guardian"]),
    ]), Section("Residence", [
        Fld("address", "Address of ordinary residence", "textarea", P.PERMANENT_ADDRESS, "address.permanent_address",
            required=True),
        Fld("pin", "PIN code", "text", P.PERMANENT_PIN, "address.zipcode", required=True, pattern="[0-9]{6}"),
        Fld("reference_no", "Existing electoral reference number (if any)", "text", P.VOTER_ID,
            "identity.voter_id_number", pattern="[A-Z]{3}[0-9]{7}", trap="reference number vs other identifiers"),
        Fld("previous_ref", "Application reference of an earlier request", "text", None, "",
            trap="reference number vs application number"),
    ])], cryptic_names=True, accent="#2e7d32", source_documents=[3],
))

# ------------------------------------------------------------------------------ 4
FORMS.append(FormSpec(
    4, "driving-licence-application", "Driving Licence Application",
    "Renew or duplicate a driving licence. Three different dates appear on this form: read each label.",
    [Section("Applicant", [
        f_name("Applicant name", "applicant_name"), f_dob(),
        Fld("guardian", "Son / wife / daughter of", "text", P.FATHER, "personal.father_name", required=True),
        Fld("blood_group", "Blood group", "select", P.BLOOD_GROUP, "medical.blood_group",
            options=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]),
        Fld("address", "Address", "textarea", P.PERMANENT_ADDRESS, "address.permanent_address", required=True),
        Fld("pin", "PIN code", "text", P.PERMANENT_PIN, "address.zipcode", pattern="[0-9]{6}"),
    ]), Section("Existing licence", [
        Fld("licence_no", "Existing licence number (if available)", "text", P.DL_NUMBER,
            "identity.driving_licence_number"),
        Fld("issue_date", "Date of issue of existing licence", "text", P.dmy(P.DL_ISSUE), "driving_licence.issue_date",
            placeholder="DD/MM/YYYY", trap="date of birth vs issue date vs validity date"),
        Fld("valid_till", "Valid until", "text", P.dmy(P.DL_VALID), "driving_licence.valid_until",
            placeholder="DD/MM/YYYY", trap="issue date vs validity date"),
        Fld("vehicle_classes", "Classes of vehicle held", "checks", None, "driving_licence.vehicle_classes",
            options=["MCWG", "LMV", "HMV", "TRANS"], expect_many=["MCWG", "LMV"]),
        Fld("learner_no", "Learner licence number", "text", None, "", trap="learner vs permanent licence number"),
    ])], accent="#c28a00", source_documents=[4],
))

# ------------------------------------------------------------------------------ 5
FORMS.append(FormSpec(
    5, "passport-information-application", "Passport Information Application",
    "Collect the details printed on an existing travel document (fictional demo workflow).",
    [Section("Applicant", [
        Fld("given_names", "Given name(s)", "text", f"{P.FIRST} {P.MIDDLE}", "personal.given_names", required=True),
        Fld("surname", "Surname", "text", P.LAST, "personal.last_name", required=True),
        f_dob(), f_gender(),
        Fld("place_of_birth", "Place of birth", "text", P.PLACE_OF_BIRTH, "personal.place_of_birth", required=True),
        Fld("nationality", "Nationality", "select", P.NATIONALITY, "identity.nationality", required=True,
            options=["Indian", "Other"]),
        Fld("marital_status", "Marital status", "select", None, "", user=True,
            options=["Single", "Married", "Divorced", "Widowed"]),
    ]), Section("Parents and address", [
        Fld("father_name", "Father's name", "text", P.FATHER, "personal.father_name", required=True,
            trap="applicant name vs parent name"),
        Fld("mother_name", "Mother's name", "text", P.MOTHER, "personal.mother_name", required=True),
        Fld("address", "Present address", "textarea", P.PERMANENT_ADDRESS, "address.permanent_address",
            required=True),
        Fld("pin", "PIN code", "text", P.PERMANENT_PIN, "address.zipcode", pattern="[0-9]{6}"),
    ]), Section("Existing travel document (if available)", [
        Fld("passport_no", "Passport number", "text", P.PASSPORT_NO, "identity.passport_number", sensitive=True,
            pattern="[A-Z][0-9]{7}"),
        Fld("passport_issue", "Date of issue", "date", d_iso(P.PASSPORT_ISSUE), "passport.issue_date",
            trap="date of birth vs issue date"),
        Fld("passport_expiry", "Date of expiry", "date", d_iso(P.PASSPORT_EXPIRY), "passport.expiry_date",
            trap="issue date vs expiry date"),
        Fld("place_of_issue", "Place of issue", "text", P.PASSPORT_PLACE, "passport.place_of_issue"),
        Fld("emergency_name", "Emergency contact name", "text", P.EMERGENCY_NAME, "emergency_contact.name",
            trap="applicant name vs emergency contact"),
        Fld("emergency_phone", "Emergency contact phone", "tel", P.EMERGENCY_PHONE, "emergency_contact.phone",
            pattern="[0-9]{10}", trap="applicant mobile vs emergency phone"),
    ])], accent="#5b3a8a", source_documents=[1, 5],
))

# ------------------------------------------------------------------------------ 6
c10_rows = subject_fields("c10", "Class 10", P.CLASS10_SUBJECTS)
FORMS.append(FormSpec(
    6, "class-10-educational-record", "Class 10 Educational Record",
    "Enter your Class 10 (secondary school) examination details. Subject rows are generated by the page.",
    [Section("Examination", [
        Fld("board", "Board / council", "text", P.CLASS10_BOARD, "academic.class10.board", required=True),
        Fld("school", "School name", "text", P.CLASS10_SCHOOL, "academic.class10.school"),
        Fld("roll", "Roll number", "text", P.CLASS10_ROLL, "academic.class10.roll_number", required=True),
        Fld("pass_month", "Passing month", "select", P.CLASS10_MONTH, "academic.class10.exam_month",
            options=MONTHS, required=True),
        Fld("pass_year", "Passing year", "select", str(P.CLASS10_YEAR), "academic.class10.passing_year",
            options=YEARS, required=True),
        Fld("result", "Result", "select", "Pass", "academic.class10.result_status", options=["Pass", "Fail", "Compartment"]),
    ]), Section("Subject-wise marks", c10_rows, note="Rows are rendered by the page after it loads."),
        Section("Totals", [
            Fld("total_max", "Total maximum marks", "number", str(P.CLASS10_MAX), "academic.class10.max_marks",
                required=True),
            Fld("total_obt", "Total marks obtained", "number", str(P.CLASS10_TOTAL), "academic.class10.marks_obtained",
                required=True),
            Fld("percentage", "Percentage", "number", f"{P.CLASS10_PCT:.2f}", "academic.class10.percentage",
                required=True, hint="Two decimals, e.g. 85.50"),
            Fld("grade_point", "CGPA (if the board awards one)", "number", None, ""),
        ])], subject_tables=[subject_table("c10", P.CLASS10_SUBJECTS)], accent="#444444", source_documents=[6],
))

# ------------------------------------------------------------------------------ 7
c12_rows = subject_fields("c12", "Class 12", P.CLASS12_SUBJECTS, extra_blank="Elective language")
FORMS.append(FormSpec(
    7, "class-12-educational-record", "Class 12 Educational Record",
    "Enter your Class 12 (higher secondary) details. A short reference block repeats Class 10 values so a "
    "mix-up between the two examinations is easy to spot.",
    [Section("Class 12 examination", [
        Fld("board", "Class 12 board / council", "text", P.CLASS12_BOARD, "academic.class12.board", required=True),
        Fld("college", "Junior college name", "text", P.CLASS12_SCHOOL, "academic.class12.school"),
        Fld("roll", "Class 12 seat / roll number", "text", P.CLASS12_ROLL, "academic.class12.roll_number",
            required=True, trap="class 12 vs class 10 roll number"),
        Fld("stream", "Stream", "select", P.CLASS12_STREAM, "academic.class12.stream",
            options=["Science", "Commerce", "Arts"]),
        Fld("pass_month", "Class 12 passing month", "select", P.CLASS12_MONTH, "academic.class12.exam_month",
            options=MONTHS, required=True),
        Fld("pass_year", "Class 12 passing year", "select", str(P.CLASS12_YEAR), "academic.class12.passing_year",
            options=YEARS, required=True, trap="class 12 vs class 10 passing year"),
        Fld("result", "Class 12 result", "select", "Pass", "academic.class12.result_status",
            options=["Pass", "Fail", "Compartment"]),
    ]), Section("Class 12 subject-wise marks", c12_rows),
        Section("Class 12 totals", [
            Fld("total_max", "Class 12 total maximum marks", "number", str(P.CLASS12_MAX),
                "academic.class12.max_marks", required=True),
            Fld("total_obt", "Class 12 total marks obtained", "number", str(P.CLASS12_TOTAL),
                "academic.class12.marks_obtained", required=True),
            Fld("percentage", "Class 12 percentage", "number", f"{P.CLASS12_PCT:.2f}", "academic.class12.percentage",
                required=True, trap="class 12 vs class 10 percentage"),
        ]),
        Section("Reference: Class 10 (do not confuse with Class 12)", [
            Fld("c10_year", "Class 10 passing year", "select", str(P.CLASS10_YEAR), "academic.class10.passing_year",
                options=YEARS, trap="class 10 value must not be replaced by class 12"),
            Fld("c10_percentage", "Class 10 percentage", "number", f"{P.CLASS10_PCT:.2f}", "academic.class10.percentage",
                trap="class 10 value must not be replaced by class 12"),
            Fld("c10_roll", "Class 10 roll number", "text", P.CLASS10_ROLL, "academic.class10.roll_number"),
        ])],
    subject_tables=[subject_table("c12", P.CLASS12_SUBJECTS, "Elective language")], accent="#1f4e79",
    source_documents=[6, 7],
))

# ------------------------------------------------------------------------------ 8
FORMS.append(FormSpec(
    8, "birth-information-application", "Birth Information Application",
    "Request an extract of a birth record (fictional demo registry).",
    [Section("Person born", [
        f_name("Full name of the person", "full_name"), f_dob("Date of birth"), f_gender(),
        Fld("place_of_birth", "Place of birth", "text", P.PLACE_OF_BIRTH, "personal.place_of_birth", required=True),
        Fld("time_of_birth", "Time of birth", "text", None, "", placeholder="HH:MM"),
    ]), Section("Parents and registration", [
        Fld("father", "Father's full name", "text", P.FATHER, "personal.father_name", required=True),
        Fld("mother", "Mother's full name", "text", P.MOTHER, "personal.mother_name", required=True),
        Fld("reg_ref", "Birth registration reference", "text", P.BIRTH_REG_NO, "birth_certificate.registration_number",
            required=True, trap="registration reference vs other reference numbers"),
        Fld("reg_date", "Date of registration", "date", d_iso(P.BIRTH_REG_DATE), "birth_certificate.registration_date",
            trap="date of birth vs registration date"),
        Fld("issue_date", "Date of issue of the extract", "date", d_iso(P.BIRTH_ISSUE), "birth_certificate.issue_date"),
    ])], cryptic_names=True, accent="#a1442b", source_documents=[8],
))

# ------------------------------------------------------------------------------ 9
FORMS.append(FormSpec(
    9, "bank-account-information", "Bank Account Information Form",
    "Provide account details for a payout. Account number and IFSC-style code are different fields.",
    [Section("Account holder", [
        Fld("holder", "Account holder name", "text", P.FULL_NAME, "financial.account_holder_name", required=True),
        Fld("bank", "Bank name", "text", P.BANK_NAME, "financial.bank_name", required=True,
            accept=["Example Sahakari Bank"]),
        Fld("branch", "Branch", "text", P.BANK_BRANCH, "financial.branch_name", required=True),
        Fld("branch_address", "Branch address", "textarea", P.BANK_BRANCH_ADDRESS, "financial.branch_address"),
    ]), Section("Account", [
        Fld("account_no", "Account number", "text", P.ACCOUNT_NO, "financial.account_number", required=True,
            sensitive=True, pattern="[0-9]{9,18}", trap="account number vs IFSC"),
        Fld("account_no2", "Re-enter account number", "text", P.ACCOUNT_NO, "financial.account_number",
            sensitive=True, pattern="[0-9]{9,18}"),
        Fld("ifsc", "IFSC code", "text", P.IFSC, "financial.ifsc_code", required=True, sensitive=True,
            pattern="[A-Z]{4}0[A-Z0-9]{6}", trap="account number vs IFSC"),
        Fld("micr", "MICR code (optional)", "text", P.MICR, "financial.micr_code", pattern="[0-9]{9}",
            trap="IFSC vs MICR"),
        Fld("account_type", "Account type", "select", "Savings", "financial.account_type",
            options=["Savings", "Current", "Salary", "Fixed deposit"], required=True),
        Fld("upi", "UPI ID", "text", None, ""),
    ])], accent="#0b6b5d", source_documents=[9, 15],
))

# ----------------------------------------------------------------------------- 10
FORMS.append(FormSpec(
    10, "utility-service-application", "Utility Service Application",
    "Apply for a change on an electricity connection (fictional distribution company).",
    [Section("Customer", [
        Fld("customer", "Customer name", "text", P.FULL_NAME, "utility.consumer_name", required=True),
        Fld("consumer_no", "Consumer number", "text", P.CONSUMER_NO, "utility.consumer_number", required=True,
            trap="consumer number vs meter number"),
        Fld("meter_no", "Meter number", "text", P.METER_NO, "utility.meter_number"),
        Fld("service_address", "Service address", "textarea", P.PERMANENT_ADDRESS, "utility.service_address",
            required=True),
        Fld("billing_address", "Billing address", "textarea", P.PERMANENT_ADDRESS, "address.billing_address",
            accept=[P.CORRESPONDENCE_ADDRESS],
            trap="the profile holds two addresses; either is defensible, a wrong value is not"),
    ]), Section("Contact", [
        Fld("contact_mobile", "Contact mobile number", "tel", P.MOBILE, "personal.phone", required=True,
            pattern="[0-9]{10}"),
        Fld("contact_email", "Contact email", "email", P.EMAIL, "personal.email"),
        Fld("bill_month", "Latest bill month", "text", "August 2026", "utility.bill_month"),
        Fld("bill_date", "Bill date", "date", d_iso(P.BILL_DATE), "utility.bill_date", trap="bill date vs due date"),
        Fld("due_date", "Due date", "date", d_iso(P.BILL_DUE), "utility.due_date", trap="bill date vs due date"),
        Fld("load_kw", "Requested sanctioned load (kW)", "number", None, "", user=True),
    ])], accent="#b34700", source_documents=[10],
))

# ----------------------------------------------------------------------------- 11
member_rows = []
for i, (name, rel, age, _occ) in enumerate(P.HOUSEHOLD[:3], start=1):
    member_rows += [
        Fld(f"m{i}_name", f"Member {i} — name", "text", name, "ration_card.members", dynamic=True),
        Fld(f"m{i}_rel", f"Member {i} — relationship to applicant", "text", rel.replace(" (Applicant)", ""),
            "ration_card.members", dynamic=True),
        Fld(f"m{i}_age", f"Member {i} — age", "number", str(age), "ration_card.members", dynamic=True),
    ]
FORMS.append(FormSpec(
    11, "household-information", "Household Information Form",
    "List the people in your household. Use the button to add more rows.",
    [Section("Applicant", [
        f_name("Applicant name", "applicant_name"),
        Fld("father_name", "Father's name", "text", P.FATHER, "personal.father_name", required=True),
        Fld("mother_name", "Mother's name", "text", P.MOTHER, "personal.mother_name", required=True),
        Fld("household_ref", "Household reference", "text", P.HOUSEHOLD_REF, "ration_card.number", required=True),
        Fld("head", "Head of household", "text", P.FATHER, "ration_card.head_of_family",
            trap="applicant name vs head of household"),
    ]), Section("Household members", member_rows,
                note="Rows are rendered by the page; add another with the button below the table.")],
    accent="#3b6b4f", source_documents=[11],
))

# ----------------------------------------------------------------------------- 12
FORMS.append(FormSpec(
    12, "income-information", "Income Information Form",
    "Declare the income stated on an income certificate. The certificate date and the validity date differ.",
    [Section("Declaration", [
        f_name("Applicant name", "applicant_name"),
        Fld("annual_income", "Annual family income (INR)", "number", str(P.INCOME_ANNUAL), "financial.annual_income",
            required=True, sensitive=True),
        Fld("currency", "Currency", "select", "INR", "", options=["INR", "USD", "EUR"]),
        Fld("fin_year", "Financial year", "text", P.INCOME_FY, "income_certificate.financial_year"),
    ]), Section("Certificate", [
        Fld("cert_ref", "Income certificate number", "text", P.INCOME_CERT_NO, "income_certificate.number",
            required=True, trap="certificate number vs application reference"),
        Fld("app_ref", "Application reference number (if any)", "text", None, "",
            trap="certificate number vs application reference"),
        Fld("issue_date", "Certificate issue date", "date", d_iso(P.INCOME_ISSUE), "income_certificate.issue_date",
            required=True, trap="issue date vs validity date"),
        Fld("valid_until", "Valid until", "date", d_iso(P.INCOME_VALID), "income_certificate.valid_until",
            trap="issue date vs validity date"),
        Fld("authority", "Issuing authority", "text", P.INCOME_AUTHORITY, "income_certificate.issuing_authority"),
    ])], accent="#7a6a1a", source_documents=[12],
))

# ----------------------------------------------------------------------------- 13
FORMS.append(FormSpec(
    13, "category-certificate-information", "Category Certificate Information Form",
    "Record the category certificate and its separate caste validity certificate.",
    [Section("Applicant", [
        f_name("Applicant name", "applicant_name"),
        Fld("category", "Category", "select", P.CATEGORY, "category.social_category", required=True, sensitive=True,
            options=CATEGORIES),
        Fld("caste", "Caste / community", "text", P.CASTE, "category.caste", sensitive=True),
    ]), Section("Certificates", [
        Fld("cert_no", "Category certificate number", "text", P.CASTE_CERT_NO, "caste_certificate.number",
            required=True, sensitive=True, trap="certificate number vs validity certificate number"),
        Fld("cert_issue", "Category certificate issue date", "date", d_iso(P.CASTE_ISSUE),
            "caste_certificate.issue_date"),
        Fld("cert_authority", "Category certificate issuing authority", "text", P.CASTE_AUTHORITY,
            "caste_certificate.issuing_authority"),
        Fld("validity_no", "Caste validity certificate number", "text", P.CASTE_VALIDITY_NO, "caste_validity.number",
            sensitive=True, trap="certificate number vs validity certificate number"),
        Fld("validity_issue", "Caste validity certificate issue date", "date", d_iso(P.CASTE_VALIDITY_ISSUE),
            "caste_validity.issue_date"),
        Fld("doc_status", "Supporting document status", "radio", None, "", user=True,
            options=["Original available", "Applied, awaiting issue", "Not available"]),
    ])], accent="#5a4a8a", source_documents=[13],
))

# ----------------------------------------------------------------------------- 14
FORMS.append(FormSpec(
    14, "domicile-information", "Domicile Information Form",
    "Record domicile details from a domicile certificate (fictional demo workflow).",
    [Section("Applicant", [
        f_name("Applicant name", "applicant_name"),
        Fld("domicile_state", "State of domicile", "select", P.DOMICILE_STATE, "domicile_certificate.state",
            required=True, sensitive=True, options=STATES),
        Fld("domicile_details", "Domicile details (period of residence)", "text", f"{P.DOMICILE_YEARS} years", "",
            hint="e.g. \"15 years\""),
        Fld("permanent_address", "Permanent address", "textarea", P.PERMANENT_ADDRESS, "address.permanent_address",
            required=True),
        Fld("pin", "PIN code", "text", P.PERMANENT_PIN, "address.zipcode", pattern="[0-9]{6}"),
    ]), Section("Certificate", [
        Fld("cert_ref", "Domicile certificate reference", "text", P.DOMICILE_NO, "domicile_certificate.number",
            required=True),
        Fld("issue_date", "Issue date", "date", d_iso(P.DOMICILE_ISSUE), "domicile_certificate.issue_date",
            required=True),
        Fld("authority", "Issuing authority", "text", P.DOMICILE_AUTHORITY, "domicile_certificate.issuing_authority"),
        Fld("ration_no", "Ration card number", "text", None, "", sensitive=False,
            hint="Not in the documents (the household reference is a different identifier)."),
    ])], accent="#1d6f85", source_documents=[14],
))

# ----------------------------------------------------------------------------- 15
c10_f = subject_fields("c10", "Class 10", P.CLASS10_SUBJECTS)
c12_f = subject_fields("c12", "Class 12", P.CLASS12_SUBJECTS)
FORMS.append(FormSpec(
    15, "combined-entrance-application", "Demo Entrance Examination Application",
    "A long, multi-section application for the fictional DemoScholar 2026 entrance process. Exam preferences, "
    "declarations and uploads must be completed by the candidate.",
    [Section("A. Candidate", [
        Fld("cand_name", "Candidate's name", "text", P.FULL_NAME, "personal.full_name", required=True),
        Fld("cand_dob", "Date of birth", "date", d_iso(P.DOB), "personal.date_of_birth", required=True),
        Fld("cand_gender", "Gender", "radio", P.GENDER, "identity.gender", required=True,
            options=["Male", "Female", "Transgender"]),
        Fld("cand_nationality", "Nationality", "select", P.NATIONALITY, "identity.nationality", required=True,
            options=["Indian", "Other"]),
        Fld("cand_birthplace", "Place of birth", "text", P.PLACE_OF_BIRTH, "personal.place_of_birth"),
    ]), Section("B. Parents / guardian", [
        Fld("father", "Father's name", "text", P.FATHER, "personal.father_name", required=True,
            trap="candidate vs father vs guardian"),
        Fld("mother", "Mother's name", "text", P.MOTHER, "personal.mother_name", required=True),
        Fld("guardian", "Guardian's name (if different)", "text", None, ""),
        Fld("father_occupation", "Father's occupation", "text", None, ""),
    ]), Section("C. Contact", [
        Fld("email", "Email address", "email", P.EMAIL, "personal.email", required=True),
        Fld("mobile", "Candidate mobile number", "tel", P.MOBILE, "personal.phone", required=True,
            pattern="[0-9]{10}"),
        Fld("parent_mobile", "Parent / guardian mobile number", "tel", None, "", pattern="[0-9]{10}",
            trap="candidate mobile vs parent mobile vs emergency contact"),
        Fld("emergency_name", "Emergency contact name", "text", P.EMERGENCY_NAME, "emergency_contact.name"),
        Fld("emergency_phone", "Emergency contact phone", "tel", P.EMERGENCY_PHONE, "emergency_contact.phone",
            pattern="[0-9]{10}"),
    ]), Section("D. Addresses", [
        Fld("perm_address", "Permanent address", "textarea", P.PERMANENT_ADDRESS, "address.permanent_address",
            required=True, trap="permanent vs correspondence address"),
        Fld("perm_pin", "Permanent address PIN code", "text", P.PERMANENT_PIN, "address.zipcode",
            pattern="[0-9]{6}", required=True),
        Fld("corr_address", "Address for correspondence", "textarea", P.CORRESPONDENCE_ADDRESS,
            "address.correspondence_address", required=True, trap="permanent vs correspondence address"),
        Fld("corr_pin", "Correspondence PIN code", "text", P.CORRESPONDENCE_PIN, "address.correspondence_zipcode",
            pattern="[0-9]{6}"),
        Fld("same_address", "My correspondence address is the same as my permanent address", "checkbox", None, "",
            user=True),
    ]), Section("E. Class 10 examination", [
        Fld("c10_board", "Class 10 board", "text", P.CLASS10_BOARD, "academic.class10.board", required=True),
        Fld("c10_roll", "Class 10 roll number", "text", P.CLASS10_ROLL, "academic.class10.roll_number", required=True,
            trap="class 10 vs class 12 roll number"),
        Fld("c10_month", "Class 10 passing month", "select", P.CLASS10_MONTH, "academic.class10.exam_month",
            options=MONTHS),
        Fld("c10_year", "Class 10 passing year", "select", str(P.CLASS10_YEAR), "academic.class10.passing_year",
            options=YEARS, required=True, trap="class 10 vs class 12 passing year"),
        Fld("c10_percentage", "Class 10 percentage", "number", f"{P.CLASS10_PCT:.2f}", "academic.class10.percentage",
            required=True, trap="class 10 vs class 12 percentage"),
        *c10_f,
    ]), Section("F. Class 12 examination", [
        Fld("c12_board", "Class 12 board", "text", P.CLASS12_BOARD, "academic.class12.board", required=True),
        Fld("c12_roll", "Class 12 roll number", "text", P.CLASS12_ROLL, "academic.class12.roll_number", required=True,
            trap="class 10 vs class 12 roll number"),
        Fld("c12_month", "Class 12 passing month", "select", P.CLASS12_MONTH, "academic.class12.exam_month",
            options=MONTHS),
        Fld("c12_year", "Class 12 passing year", "select", str(P.CLASS12_YEAR), "academic.class12.passing_year",
            options=YEARS, required=True, trap="class 10 vs class 12 passing year"),
        Fld("c12_percentage", "Class 12 percentage", "number", f"{P.CLASS12_PCT:.2f}", "academic.class12.percentage",
            required=True, trap="class 10 vs class 12 percentage"),
        *c12_f,
    ]), Section("G. Category", [
        Fld("category", "Category", "select", P.CATEGORY, "category.social_category", sensitive=True,
            options=CATEGORIES, required=True),
        Fld("pwbd", "Person with benchmark disability", "radio", None, "", user=True, options=["Yes", "No"]),
    ]), Section("Category certificate details", [
        Fld("cat_cert_no", "Category certificate number", "text", P.CASTE_CERT_NO, "caste_certificate.number",
            sensitive=True, trap="certificate number vs validity certificate number"),
        Fld("cat_validity_no", "Caste validity certificate number", "text", P.CASTE_VALIDITY_NO,
            "caste_validity.number", sensitive=True),
        Fld("cat_issue", "Category certificate issue date", "date", d_iso(P.CASTE_ISSUE), "caste_certificate.issue_date"),
    ], note="Shown after a reserved category is chosen.",
        reveal={"when": "category", "values": ["EWS", "OBC", "SC", "ST"]}),
    Section("H. Documents available with me", [
        Fld("docs_available", "Documents I can upload", "checks", None, "", user=True,
            options=["Class 10 marksheet", "Class 12 marksheet", "Category certificate", "Income certificate",
                     "Domicile certificate", "Birth certificate"]),
    ]), Section("I. Examination preferences (choose yourself)", [
        Fld("city1", "Examination city — first preference", "select", None, "", user=True, required=True,
            options=["Nashik", "Pune", "Mumbai", "Nagpur", "Aurangabad"]),
        Fld("city2", "Examination city — second preference", "select", None, "", user=True,
            options=["Nashik", "Pune", "Mumbai", "Nagpur", "Aurangabad"]),
        Fld("medium", "Medium of question paper", "radio", None, "", user=True, required=True,
            options=["English", "Marathi", "Hindi"]),
        Fld("slot", "Preferred examination slot", "radio", None, "", user=True, options=["Morning", "Afternoon"]),
    ]), Section("J. Uploads", [
        Fld("photo", "Passport-size photograph", "file", None, "", required=True, hint="JPG/PNG, 10–300 KB"),
        Fld("signature", "Signature", "file", None, "", required=True, hint="JPG/PNG, 4–100 KB"),
    ]), Section("K. Declaration", [
        Fld("declaration", "I declare that the information given is true and correct", "checkbox", None, "",
            user=True, required=True),
    ])],
    subject_tables=[subject_table("c10", P.CLASS10_SUBJECTS), subject_table("c12", P.CLASS12_SUBJECTS)],
    accent="#7b2d8e", source_documents=[1, 6, 7, 12, 13],
))


def by_number(n: int) -> FormSpec:
    return next(f for f in FORMS if f.number == n)
