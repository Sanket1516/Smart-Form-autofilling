"""Build the expected-answer manifest and the public scenario list.

``demo/expected/manifest.json`` is the answer key. It is written next to the test
suite, never served by the frontend and never read by the backend. Everything in
it is computed from `demo.profile`, independently of what the pipeline extracts.

``frontend/public/demo/scenarios.json`` holds only the question text (no answers)
for the Demo Data page.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from demo import profile as P
from demo.documents_gen import DOCUMENTS, _pages, file_name
from demo.forms_gen import dom_map, file_name as form_file
from demo.forms_spec import FORMS

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent / "frontend" / "public" / "demo"


def _dob_variants() -> list[str]:
    return ["2007-08-23", "23/08/2007", "23-08-2007", "23 august 2007", "august 23, 2007", "23rd august 2007"]


# ----------------------------------------------------------------- document ground truth
def document_truth() -> dict[int, dict]:
    sub10 = [{"code": s.code, "name": s.name, "max_marks": str(s.max_marks), "total": str(s.obtained), "grade": s.grade}
             for s in P.CLASS10_SUBJECTS]
    sub12 = [{"code": s.code, "name": s.name, "max_marks": str(s.max_marks), "marks_obtained": str(s.obtained),
              "grade": s.grade} for s in P.CLASS12_SUBJECTS]
    tx = [{"date": P.iso(t["date"]), "reference": t["reference"], "debit": t["debit"], "credit": t["credit"],
           "balance": t["balance"]} for t in P.TRANSACTIONS]
    perm = P.PERMANENT_ADDRESS
    return {
        1: {"expected_type": "OTHER", "fields": {
            "personal.full_name": P.FULL_NAME, "personal.first_name": P.FIRST, "personal.middle_name": P.MIDDLE,
            "personal.last_name": P.LAST, "personal.date_of_birth": P.iso(P.DOB), "identity.gender": P.GENDER,
            "identity.nationality": P.NATIONALITY, "personal.father_name": P.FATHER, "personal.mother_name": P.MOTHER,
            "personal.phone": P.MOBILE, "personal.email": P.EMAIL, "address.permanent_address": perm,
            "address.correspondence_address": P.CORRESPONDENCE_ADDRESS, "emergency_contact.name": P.EMERGENCY_NAME,
            "emergency_contact.relationship": P.EMERGENCY_RELATION, "emergency_contact.phone": P.EMERGENCY_PHONE}},
        2: {"expected_type": "PAN_CARD", "fields": {
            "identity.pan_number": P.TAX_ID, "personal.full_name": P.FULL_NAME, "personal.father_name": P.FATHER,
            "personal.date_of_birth": P.iso(P.DOB)}},
        3: {"expected_type": "VOTER_ID", "fields": {
            "identity.voter_id_number": P.VOTER_ID, "personal.full_name": P.FULL_NAME,
            "personal.father_name": P.FATHER, "identity.gender": P.GENDER, "personal.date_of_birth": P.iso(P.DOB),
            "address.full_address": perm, "address.zipcode": P.PERMANENT_PIN}},
        4: {"expected_type": "DRIVING_LICENCE", "fields": {
            "identity.driving_licence_number": P.DL_NUMBER, "personal.full_name": P.FULL_NAME,
            "personal.date_of_birth": P.iso(P.DOB), "personal.father_name": P.FATHER,
            "driving_licence.issue_date": P.iso(P.DL_ISSUE), "driving_licence.valid_until": P.iso(P.DL_VALID),
            "driving_licence.vehicle_classes": P.DL_CLASSES, "medical.blood_group": P.BLOOD_GROUP,
            "address.full_address": perm, "address.zipcode": P.PERMANENT_PIN},
            "absent": ["personal.date_of_birth=issue_date"]},
        5: {"expected_type": "PASSPORT", "fields": {
            "identity.passport_number": P.PASSPORT_NO, "personal.last_name": P.LAST,
            "personal.given_names": f"{P.FIRST} {P.MIDDLE}", "personal.date_of_birth": P.iso(P.DOB),
            "identity.nationality": P.NATIONALITY, "personal.place_of_birth": P.PLACE_OF_BIRTH,
            "passport.issue_date": P.iso(P.PASSPORT_ISSUE), "passport.expiry_date": P.iso(P.PASSPORT_EXPIRY),
            "passport.place_of_issue": P.PASSPORT_PLACE, "personal.father_name": P.FATHER,
            "personal.mother_name": P.MOTHER, "address.full_address": perm}},
        6: {"expected_type": "CLASS_10_MARKSHEET", "scanned": True, "fields": {
            "personal.full_name": P.FULL_NAME, "personal.date_of_birth": P.iso(P.DOB),
            "personal.father_name": P.FATHER, "personal.mother_name": P.MOTHER,
            "academic.class10.roll_number": P.CLASS10_ROLL, "academic.class10.exam_year": str(P.CLASS10_YEAR),
            "academic.class10.passing_year": str(P.CLASS10_YEAR), "academic.class10.exam_month": P.CLASS10_MONTH,
            "academic.class10.max_marks": str(P.CLASS10_MAX), "academic.class10.marks_obtained": str(P.CLASS10_TOTAL),
            "academic.class10.percentage": f"{P.CLASS10_PCT:.2f}", "academic.class10.result_status": "PASS",
            "academic.class10.result_date": P.iso(P.CLASS10_RESULT_DATE), "academic.class10.school": P.CLASS10_SCHOOL},
            "records": {"academic.class10.subjects": sub10},
            "absent": ["academic.class12.*"]},
        7: {"expected_type": "CLASS_12_MARKSHEET", "fields": {
            "personal.full_name": P.FULL_NAME, "personal.mother_name": P.MOTHER,
            "academic.class12.roll_number": P.CLASS12_ROLL, "academic.class12.max_marks": str(P.CLASS12_MAX),
            "academic.class12.marks_obtained": str(P.CLASS12_TOTAL), "academic.class12.percentage": f"{P.CLASS12_PCT:.2f}",
            "academic.class12.result_date": P.iso(P.CLASS12_RESULT_DATE), "academic.class12.board": P.CLASS12_BOARD,
            "academic.class12.school": P.CLASS12_SCHOOL, "academic.class12.passing_year": str(P.CLASS12_YEAR)},
            "records": {"academic.class12.subjects": sub12}, "absent": ["academic.class10.*"]},
        8: {"expected_type": "BIRTH_CERTIFICATE", "scanned": True, "fields": {
            "personal.full_name": P.FULL_NAME, "personal.date_of_birth": P.iso(P.DOB),
            "personal.place_of_birth": P.PLACE_OF_BIRTH, "personal.father_name": P.FATHER,
            "personal.mother_name": P.MOTHER, "birth_certificate.registration_number": P.BIRTH_REG_NO,
            "birth_certificate.registration_date": P.iso(P.BIRTH_REG_DATE),
            "birth_certificate.issue_date": P.iso(P.BIRTH_ISSUE), "address.full_address": perm}},
        9: {"expected_type": "BANK_PASSBOOK", "scanned": True, "fields": {
            "financial.bank_name": P.BANK_NAME, "financial.branch_name": P.BANK_BRANCH,
            "financial.account_holder_name": P.FULL_NAME, "financial.account_number": P.ACCOUNT_NO,
            "financial.ifsc_code": P.IFSC, "financial.micr_code": P.MICR, "financial.account_type": P.ACCOUNT_TYPE,
            "financial.branch_address": P.BANK_BRANCH_ADDRESS}},
        10: {"expected_type": "ELECTRICITY_BILL", "fields": {
            "utility.consumer_name": P.FULL_NAME, "utility.consumer_number": P.CONSUMER_NO,
            "utility.meter_number": P.METER_NO, "utility.service_address": perm, "utility.bill_date": P.iso(P.BILL_DATE),
            "utility.due_date": P.iso(P.BILL_DUE), "utility.bill_amount": P.BILL_AMOUNT,
            "utility.bill_month": "August 2026", "utility.provider_name": "Example Power Distribution Co. Ltd.",
            "utility.units_consumed": str(P.UNITS)}},
        11: {"expected_type": "RATION_CARD", "fields": {
            "ration_card.number": P.HOUSEHOLD_REF, "ration_card.head_of_family": P.FATHER,
            "personal.full_name": P.FULL_NAME, "personal.father_name": P.FATHER, "personal.mother_name": P.MOTHER},
            "records": {"ration_card.members": [{"name": n, "relationship": r, "age": str(a)} for n, r, a, _ in P.HOUSEHOLD]},
            "note": "No dedicated household type exists: classification as RATION_CARD or OTHER is acceptable."},
        12: {"expected_type": "INCOME_CERTIFICATE", "fields": {
            "income_certificate.number": P.INCOME_CERT_NO, "income_certificate.holder_name": P.FULL_NAME,
            "income_certificate.issue_date": P.iso(P.INCOME_ISSUE), "income_certificate.valid_until": P.iso(P.INCOME_VALID),
            "financial.annual_income": str(P.INCOME_ANNUAL), "income_certificate.financial_year": P.INCOME_FY,
            "income_certificate.issuing_authority": P.INCOME_AUTHORITY, "personal.father_name": P.FATHER}},
        13: {"expected_type": "CASTE_CERTIFICATE", "accept_types": ["CASTE_CERTIFICATE", "CASTE_VALIDITY_CERTIFICATE"],
             "scanned": True, "fields": {
            "caste_certificate.number": P.CASTE_CERT_NO, "caste_certificate.issue_date": P.iso(P.CASTE_ISSUE),
            "category.social_category": P.CATEGORY,
            "category.caste": P.CASTE, "caste_validity.number": P.CASTE_VALIDITY_NO,
            "caste_validity.issue_date": P.iso(P.CASTE_VALIDITY_ISSUE), "personal.full_name": P.FULL_NAME},
            "concept_pages": {"caste_certificate.number": 1, "caste_validity.number": 2}},
        14: {"expected_type": "DOMICILE_CERTIFICATE", "fields": {
            "domicile_certificate.number": P.DOMICILE_NO, "domicile_certificate.issue_date": P.iso(P.DOMICILE_ISSUE),
            "domicile_certificate.state": P.DOMICILE_STATE, "personal.full_name": P.FULL_NAME,
            "address.permanent_address": perm, "address.zipcode": P.PERMANENT_PIN}},
        15: {"expected_type": "BANK_STATEMENT", "fields": {
            "financial.account_number": P.ACCOUNT_NO, "financial.ifsc_code": P.IFSC,
            "financial.account_holder_name": P.FULL_NAME, "financial.account_type": P.ACCOUNT_TYPE,
            "financial.branch_name": P.BANK_BRANCH, "financial.branch_address": P.BANK_BRANCH_ADDRESS},
            "records": {"financial.transactions": tx},
            "balance_check": {"opening": P.OPENING_BALANCE, "closing": P.CLOSING_BALANCE, "rows": len(tx)}},
    }


# ---------------------------------------------------------------------------- questions
ADDRESS_DOCS = [1, 3, 4, 5, 8, 10, 12, 13, 14]
DOB_DOCS = [1, 2, 3, 4, 5, 6, 8]
FATHER_DOCS = [1, 2, 3, 4, 5, 6, 8, 12, 13, 14]

ELIGIBILITY_TEXT = (
    "Based on the fictional DemoScholar 2026 eligibility requirements, which criteria do I meet, which do I not "
    "meet, and which cannot be determined? (These requirements are invented for this demonstration.)")


def questions() -> list[dict]:
    last_tx = [t for t in P.TRANSACTIONS if P.date(2026, 9, 1) <= t["date"] <= P.date(2026, 9, 15)]
    return [
        {"id": "Q01", "category": "exact value", "question": "What is the applicant's date of birth?",
         "expect": [_dob_variants()], "cite_docs": DOB_DOCS},
        {"id": "Q02", "category": "class 10 vs 12", "question": "What is the applicant's Class 10 passing year?",
         "expect": [[str(P.CLASS10_YEAR)]], "forbid": [str(P.CLASS12_YEAR)], "cite_docs": [6]},
        {"id": "Q03", "category": "class 10 vs 12", "question": "What is the applicant's Class 12 passing year?",
         "expect": [[str(P.CLASS12_YEAR)]], "forbid": [str(P.CLASS10_YEAR)], "cite_docs": [7]},
        {"id": "Q04", "category": "class 10 vs 12", "question": "What percentage did the applicant obtain in Class 10?",
         "expect": [["91.4"]], "forbid": ["87.2"], "cite_docs": [6]},
        {"id": "Q05", "category": "class 10 vs 12", "question": "What percentage did the applicant obtain in Class 12?",
         "expect": [["87.2"]], "forbid": ["91.4"], "cite_docs": [7]},
        {"id": "Q06", "category": "table", "question": "List the Class 12 subjects and marks.",
         "expect": [[f"{s.name.lower()}"] for s in P.CLASS12_SUBJECTS] + [[str(s.obtained)] for s in P.CLASS12_SUBJECTS],
         "cite_docs": [7]},
        {"id": "Q07", "category": "provenance", "question": "Which document contains the applicant's date of birth?",
         "expect": [], "cite_docs": DOB_DOCS, "cite_min": 2},
        {"id": "Q08", "category": "exact value", "question": "What is the fictional caste certificate number?",
         "expect": [[P.CASTE_CERT_NO.lower()]], "cite_docs": [13]},
        {"id": "Q09", "category": "disambiguation",
         "question": "How is the caste certificate number different from the caste validity certificate number?",
         "expect": [[P.CASTE_CERT_NO.lower()], [P.CASTE_VALIDITY_NO.lower()]], "cite_docs": [13]},
        {"id": "Q10", "category": "address", "question": "What is the correspondence address?",
         "expect": [["room 214"], [P.CORRESPONDENCE_PIN]], "cite_docs": [1]},
        {"id": "Q11", "category": "address", "question": "Is it the same as the permanent address?",
         "follow_up_of": "Q10",
         "expect": [["flat 402"], ["room 214"]], "expect_any_text": ["not the same", "different", "differ", "not same", "no,", "not identical"],
         "cite_docs": [1]},
        {"id": "Q12", "category": "exact value",
         "question": "What is the annual income recorded in the synthetic income certificate?",
         "expect": [["480000", "4,80,000"]], "cite_docs": [12]},
        {"id": "Q13", "category": "multi-document", "question": "Which documents contain address information?",
         "expect": [], "cite_docs": ADDRESS_DOCS, "cite_min": 3},
        {"id": "Q14", "category": "form readiness", "question": "Which fields can be filled from the available documents for DemoScholar 2026?",
         "exam_id": P.DEMO_EXAM_ID, "expect": [], "min_requirements": {"met": 8}},
        {"id": "Q15", "category": "form readiness", "question": "Which fields are missing from the available documents for DemoScholar 2026?",
         "exam_id": P.DEMO_EXAM_ID, "expect": [], "requirements_mention_any": ["city", "language", "disability"]},
        {"id": "Q16", "category": "exact value", "question": "What is the applicant's bank branch?",
         "expect": [[P.BANK_BRANCH.lower()]], "cite_docs": [9, 15]},
        {"id": "Q17", "category": "table", "question": "What transactions occurred between 1 September 2026 and 15 September 2026?",
         "expect": [[t["reference"].lower()] for t in last_tx], "cite_docs": [15],
         "note": f"{len(last_tx)} transactions are in the period"},
        {"id": "Q18", "category": "date disambiguation",
         "question": "Explain the difference between the driving licence issue date and the date of birth.",
         "expect": [["2025-09-05", "05/09/2025", "5 september 2025"], _dob_variants()], "cite_docs": [4]},
        {"id": "Q19", "category": "multi-document", "question": "Compare the educational information from both marksheets.",
         "expect": [[str(P.CLASS10_YEAR)], [str(P.CLASS12_YEAR)], ["91.4"], ["87.2"]], "cite_docs": [6, 7], "cite_min": 2},
        {"id": "Q20", "category": "scenario", "question": ELIGIBILITY_TEXT, "exam_id": P.DEMO_EXAM_ID, "expect": [],
         "eligibility": {  # rule label -> acceptable outcomes (computed by hand from the profile, see profile.py)
             "Passed Class 12": ["met", "needs_confirmation"],
             "Physics, Chemistry, Mathematics and English in Class 12": ["met"],
             "At least 85% in Class 12": ["met", "needs_confirmation"],        # 87.20 >= 85
             "At least 90% in Class 10": ["met", "needs_confirmation"],        # 91.40 >= 90
             "At least 90% aggregate in Physics, Chemistry and Mathematics in Class 12": ["not_met"],  # (86+82+90)/300 = 86.0
             "At least 17 years old on 31 December of the award year": ["met"],  # age 19
             "At least 60% in the DemoScholar screening test (score report required)": ["unknown"]}},
        {"id": "Q21", "category": "absent information", "question": "What is the applicant's Aadhaar number?",
         "expect": [], "expect_status": ["insufficient_evidence", "partial"], "forbid_regex": [r"\b\d{4}\s?\d{4}\s?\d{4}\b"]},
        {"id": "Q22", "category": "absent information", "question": "What is the applicant's mother's mobile number?",
         "expect": [], "expect_status": ["insufficient_evidence", "partial"]},
        {"id": "Q23", "category": "follow-up", "question": "What is my Class 12 percentage?", "expect": [["87.2"]],
         "forbid": ["91.4"], "cite_docs": [7], "thread": "T1"},
        {"id": "Q24", "category": "follow-up", "question": "And for Class 10?", "follow_up_of": "Q23",
         "expect": [["91.4"]], "forbid": ["87.2"], "cite_docs": [6], "thread": "T1"},
        {"id": "Q25", "category": "identifier confusion", "question": "What are the bank account number and the IFSC code?",
         "expect": [[P.ACCOUNT_NO[-4:]], [P.IFSC.lower()]], "cite_docs": [9, 15],
         "note": "account numbers are masked in answers by design, so the last four digits are the expected evidence"},
        {"id": "Q26", "category": "date disambiguation", "question": "When does the passport expire?",
         "expect": [["2034-11-13", "13/11/2034", "13 november 2034"]], "cite_docs": [5]},
        {"id": "Q27", "category": "date disambiguation", "question": "What is the utility bill due date and the amount due?",
         "expect": [["2026-09-20", "20/09/2026", "20-sep-2026", "20 september 2026"], ["2347.5"]], "cite_docs": [10]},
        {"id": "Q28", "category": "multi-document", "question": "Which documents mention the applicant's father's name?",
         "expect": [], "cite_docs": FATHER_DOCS, "cite_min": 3},
    ]


# --------------------------------------------------------------------------- forms truth
def form_truth() -> list[dict]:
    out = []
    for form in FORMS:
        ids = dom_map(form)
        fields = []
        for f in form.all_fields():
            if f.user:
                outcome = "user_choice"
            elif f.kind == "file":
                outcome = "user_choice"
            elif f.expect is None and not f.expect_many:
                outcome = "missing"
            else:
                outcome = "fill_with_review" if f.sensitive else "fill"
            fields.append({"key": f.key, "dom_id": ids[f.key], "label": f.label, "kind": f.kind, "required": f.required,
                           "expect": f.expect, "expect_many": f.expect_many, "accept": f.accept,
                           "concept": f.concept, "outcome": outcome, "sensitive": f.sensitive, "dynamic": f.dynamic,
                           "trap": f.trap})
        out.append({"number": form.number, "file": form_file(form), "title": form.title,
                    "source_documents": form.source_documents, "fields": fields,
                    "cryptic_names": form.cryptic_names})
    return out


def build() -> dict:
    truth = document_truth()
    docs = []
    for number, slug, title, _fn, meta in DOCUMENTS:
        entry = {"number": number, "file": file_name(number, slug), "document_type": title, **meta, **truth[number]}
        generated = PUBLIC / "documents" / entry["file"]
        if generated.exists():
            entry["pages"] = _pages(generated)
        docs.append(entry)
    forms = form_truth()
    n_fields = sum(len(f["fields"]) for f in forms)
    return {
        "dataset": {
            "banner": P.BANNER, "applicant": P.FULL_NAME,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Answer key for the test suite. Not served by the app and never read by the backend.",
        },
        "documents": docs,
        "forms": forms,
        "questions": questions(),
        "retrieval": [
            {"query": "identity information sheet with emergency contact details", "document": 1},
            {"query": "tax identification record permanent account number format", "document": 2},
            {"query": "elector information record EPIC assembly constituency", "document": 3},
            {"query": "driving licence date of issue valid till class of vehicle", "document": 4},
            {"query": "passport information record date of expiry place of issue", "document": 5},
            {"query": "secondary school examination class X marks statement subject code theory internal", "document": 6},
            {"query": "higher secondary certificate examination class XII statement of marks computer science", "document": 7},
            {"query": "extract of birth register registration number hospital", "document": 8},
            {"query": "savings passbook branch withdrawals deposits recent entries", "document": 9},
            {"query": "electricity bill units consumed meter number due date", "document": 10},
            {"query": "household information record members relationship to applicant", "document": 11},
            {"query": "income certificate annual income financial year issued by revenue office", "document": 12},
            {"query": "category certificate social category caste validity certificate annexure", "document": 13},
            {"query": "domicile certificate period of residence state of domicile", "document": 14},
            {"query": "account statement opening balance closing balance debit credit reference", "document": 15},
        ],
        "eligibility_rules_fictional": P.DEMO_EXAM_ID,
        "validation_outcomes": {
            "fill": "value must equal the expected value (or an accepted alternative) after fill",
            "fill_with_review": "sensitive field: proposed for review; counts as correct when filled with the expected value after explicit approval, safe when left empty",
            "missing": "no document contains the value: the field must remain empty",
            "user_choice": "preference/declaration/upload: must remain empty / unselected / unattached",
        },
        "totals": {"documents": len(docs), "forms": len(forms), "form_fields": n_fields,
                   "questions": len(questions())},
    }


def public_scenarios() -> list[dict]:
    """Question text only: no expected answers."""
    return [{k: q[k] for k in ("id", "category", "question") if k in q} |
            ({"exam_id": q["exam_id"]} if "exam_id" in q else {}) |
            ({"follow_up_of": q["follow_up_of"]} if "follow_up_of" in q else {}) for q in questions()]


# The fictional resume and its application form ride along as one more document and one more form.
# `path` is relative to /demo (the other entries live in documents/ and forms/).
_RESUME_DOCUMENT = {"file": "DEMO_RESUME_kavya_deshpande.pdf", "path": "resume/DEMO_RESUME_kavya_deshpande.pdf",
                    "title": "Synthetic resume (Kavya Suresh Deshpande)", "pages": 3, "scanned": False,
                    "challenge": "free-text resume: answers come from retrieved passages"}
_RESUME_FORM = {"file": "graduate-software-engineer-application.html",
                "path": "resume/graduate-software-engineer-application.html",
                "title": "Graduate Software Engineer Application"}


def write() -> dict:
    manifest = build()
    (ROOT / "expected").mkdir(exist_ok=True)
    (ROOT / "expected" / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False, default=str), "utf-8")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "scenarios.json").write_text(json.dumps(public_scenarios(), indent=1, ensure_ascii=False), "utf-8")
    documents = [{"number": d["number"], "file": d["file"], "title": d["document_type"], "pages": d.get("pages"),
                  "scanned": d.get("scanned", False), "challenge": d.get("challenge", "")} for d in manifest["documents"]]
    forms = [{"number": f["number"], "file": f["file"], "title": f["title"]} for f in manifest["forms"]]
    (PUBLIC / "catalog.json").write_text(json.dumps({
        "documents": documents + [_RESUME_DOCUMENT | {"number": len(documents) + 1}],
        "forms": forms + [_RESUME_FORM | {"number": len(forms) + 1}],
        "banner": P.BANNER}, indent=1, ensure_ascii=False), "utf-8")
    return manifest
