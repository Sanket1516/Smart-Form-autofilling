# Demo evaluation report

Generated 2026-10-16T22:15:51 against `http://localhost:8000`. All figures come from live calls to the real pipeline; the answer key is `demo/expected/manifest.json`.

LLM provider: **configured** · model `gemini-3.5-flash-lite` · embedding `all-MiniLM-L6-v2`

## Extraction (OCR → structured facts)

| Metric | Result |
|---|---|
| Document-type accuracy | 100.0% |
| Exact-field accuracy | 97.0% (128/132) |
| …with no conflicting extra value | 92.4% |
| Subject-wise table accuracy | 100.0% |
| All record rows (subjects, transactions, members) | 40/40 |
| Scanned-document fields | 97.8% |
| Digital-PDF fields | 96.6% |

### Per document

| # | File | Type found | Fields | Records |
|---|---|---|---|---|
| 1 | DEMO_01_identity_information_sheet.pdf | OTHER ✓ | 16/16 | – |
| 2 | DEMO_02_tax_identification_record.pdf | PAN_CARD ✓ | 4/4 | – |
| 3 | DEMO_03_voter_information_record.pdf | VOTER_ID ✓ | 7/7 | – |
| 4 | DEMO_04_driving_licence_record.pdf | DRIVING_LICENCE ✓ | 10/10 | – |
| 5 | DEMO_05_passport_information_record.pdf | PASSPORT ✓ | 12/12 | – |
| 6 | DEMO_06_class10_marksheet.pdf | CLASS_10_MARKSHEET ✓ | 14/14 | subjects 5/5 |
| 7 | DEMO_07_class12_marksheet.pdf | CLASS_12_MARKSHEET ✓ | 10/10 | subjects 5/5 |
| 8 | DEMO_08_birth_certificate_record.pdf | BIRTH_CERTIFICATE ✓ | 9/9 | – |
| 9 | DEMO_09_bank_passbook.pdf | BANK_PASSBOOK ✓ | 8/8 | – |
| 10 | DEMO_10_utility_bill.pdf | ELECTRICITY_BILL ✓ | 9/10 | – |
| 11 | DEMO_11_household_information_record.pdf | RATION_CARD ✓ | 3/5 | members 5/5 |
| 12 | DEMO_12_income_certificate.pdf | INCOME_CERTIFICATE ✓ | 8/8 | – |
| 13 | DEMO_13_category_certificate.pdf | CASTE_VALIDITY_CERTIFICATE ✓ | 6/7 | – |
| 14 | DEMO_14_domicile_certificate.pdf | DOMICILE_CERTIFICATE ✓ | 6/6 | – |
| 15 | DEMO_15_bank_statement.pdf | BANK_STATEMENT ✓ | 6/6 | transactions 25/25 |

### Fields not extracted correctly

| File | Concept | Expected | Found |
|---|---|---|---|
| DEMO_10_utility_bill.pdf | utility.provider_name | Example Power Distribution Co. Ltd. | — |
| DEMO_11_household_information_record.pdf | personal.father_name | Suresh Ramesh Deshpande | — |
| DEMO_11_household_information_record.pdf | personal.mother_name | Sunita Suresh Deshpande | — |
| DEMO_13_category_certificate.pdf | caste_certificate.issue_date | 2025-07-09 | — |

## Storage, indexing and retrieval

* structured facts stored (MongoDB): 15/15
* vector-indexed (ChromaDB): 15/15
* retrieval top-1 93.3%, top-4 100.0% over 15 queries

## Ask Documents

* questions: 28 · fully passing: 28 · answer correctness: 100.0%
* source attribution: 100.0% over 23 questions with expected sources
* infrastructure errors: 0 · evidence-only answers (LLM unavailable): 0 · forbidden-value hits: 0 · median latency 0.08 s

| ID | Category | Outcome | Status | Failed checks |
|---|---|---|---|---|
| Q01 | exact value | pass | answered |  |
| Q02 | class 10 vs 12 | pass | answered |  |
| Q03 | class 10 vs 12 | pass | answered |  |
| Q04 | class 10 vs 12 | pass | answered |  |
| Q05 | class 10 vs 12 | pass | answered |  |
| Q06 | table | pass | answered |  |
| Q07 | provenance | pass | answered |  |
| Q08 | exact value | pass | answered |  |
| Q09 | disambiguation | pass | partial |  |
| Q10 | address | pass | answered |  |
| Q11 | address | pass | answered |  |
| Q12 | exact value | pass | answered |  |
| Q13 | multi-document | pass | answered |  |
| Q14 | form readiness | pass | answered |  |
| Q15 | form readiness | pass | answered |  |
| Q16 | exact value | pass | answered |  |
| Q17 | table | pass | answered |  |
| Q18 | date disambiguation | pass | answered |  |
| Q19 | multi-document | pass | partial |  |
| Q20 | scenario | pass | answered |  |
| Q21 | absent information | pass | insufficient_evidence |  |
| Q22 | absent information | pass | partial |  |
| Q23 | follow-up | pass | answered |  |
| Q24 | follow-up | pass | answered |  |
| Q25 | identifier confusion | pass | answered |  |
| Q26 | date disambiguation | pass | answered |  |
| Q27 | date disambiguation | pass | answered |  |
| Q28 | multi-document | pass | answered |  |

## Browser autofill (real extension, real backend)

Mode: **default** · forms analysed 15/15 · extension build `dist build of this repo`

| Measure | Count |
|---|---|
| Fields correctly filled | 112 |
| Fields incorrectly filled | 9 |
| Missing-in-documents fields left empty | 12/15 |
| Expected values held for review (not filled) | 84 |
| Expected values missed (empty, not flagged) | 0 |
| User-only fields touched | 0 |
| Forms submitted | 0 |
| Files attached | 0 |

| Form | Fill-expected | Correct | Incorrect | Held | Missed | Missing-safe | User-safe |
|---|---|---|---|---|---|---|---|
| 1 General Applicant Registration | 7 | 6 | 1 | 1 | 0 | 1/2 | 0/0 |
| 2 Tax Identification Application | 8 | 4 | 1 | 3 | 0 | 1/1 | 1/1 |
| 3 Voter Information Application | 6 | 4 | 0 | 2 | 0 | 1/1 | 1/1 |
| 4 Driving Licence Application | 10 | 5 | 0 | 4 | 0 | 1/1 | 0/0 |
| 5 Passport Information Application | 16 | 11 | 1 | 4 | 0 | 0/0 | 1/1 |
| 6 Class 10 Educational Record | 19 | 4 | 0 | 15 | 0 | 1/1 | 0/0 |
| 7 Class 12 Educational Record | 23 | 21 | 2 | 2 | 0 | 0/2 | 0/0 |
| 8 Birth Information Application | 9 | 5 | 0 | 4 | 0 | 1/1 | 0/0 |
| 9 Bank Account Information Form | 9 | 0 | 0 | 9 | 0 | 1/1 | 0/0 |
| 10 Utility Service Application | 10 | 7 | 0 | 3 | 0 | 0/0 | 1/1 |
| 11 Household Information Form | 14 | 2 | 3 | 9 | 0 | 0/0 | 0/0 |
| 12 Income Information Form | 8 | 0 | 0 | 8 | 0 | 1/1 | 0/0 |
| 13 Category Certificate Information Form | 8 | 0 | 0 | 8 | 0 | 0/0 | 1/1 |
| 14 Domicile Information Form | 8 | 2 | 0 | 6 | 0 | 1/1 | 0/0 |
| 15 Demo Entrance Examination Application | 49 | 41 | 1 | 6 | 0 | 3/3 | 10/10 |
