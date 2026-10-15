# Document extraction schemas

Generated from `backend/app/extraction/document_types.yaml` and the test fixtures
(`backend/tests/indian_fixtures.py`, `backend/tests/heldout_fixtures.py`). Every field
listed under *Tested fields* is asserted by `tests/test_indian_documents.py` or the
evaluation in `tests/eval/run_eval.py`. Documents may yield more: any other labelled
value is kept as a generic key-value with its original label.

Every stored value carries: original label, concept, original (`raw_value`) and
normalised value, data type, source document, page, evidence text, confidence,
origin (`extracted`/`normalized`/`derived`/`inferred`/`user_provided`) and, in
`provenance`, the document type, validation result and any derivation note.

## Aadhaar card (`AADHAAR_CARD`)

- Validated identifiers: `identity.aadhaar_number` (aadhaar)
- Classified by: "unique identification authority of india", "uidai", "आधार", "aadhaar", "enrolment no"
- Layout rules: gender_line, name_before_dob, relation_prefix
- Tested fields: `address.full_address`, `address.zipcode`, `identity.aadhaar_number`, `identity.gender`, `personal.date_of_birth`, `personal.father_name`, `personal.full_name`
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `personal.date_of_birth`, `personal.email`
- Fixtures: aadhaar_front_bilingual (multilingual), aadhaar_back_ocr (ocr), ho_aadhaar_yob (ocr)

## PAN card (`PAN_CARD`)

- Validated identifiers: `identity.pan_number` (pan)
- Classified by: "permanent account number", "income tax department", "आयकर विभाग", "govt of india"
- Tested fields: `identity.pan_number`, `personal.date_of_birth`, `personal.father_name`, `personal.full_name`
- Fixtures: pan_card_bilingual (multilingual), ho_pan_old_format (ocr)

## Voter ID card (`VOTER_ID`)

- Validated identifiers: `identity.voter_id_number` (epic)
- Classified by: "election commission of india", "electors photo identity card", "epic", "elector"
- Tested fields: `address.full_address`, `address.zipcode`, `identity.gender`, `identity.voter_id_number`, `personal.date_of_birth`, `personal.father_name`, `personal.full_name`
- Fixtures: voter_id_clean (clean), ho_voter_id (clean)

## Driving licence (`DRIVING_LICENCE`)

- Context scope: `driving_licence` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Validated identifiers: `identity.driving_licence_number` (driving_licence)
- Classified by: "driving license", "driving licence", "class of vehicle", "transport department", "motor"
- Tested fields: `address.full_address`, `address.zipcode`, `driving_licence.issue_date`, `driving_licence.issuing_authority`, `driving_licence.valid_until`, `driving_licence.vehicle_classes`, `identity.driving_licence_number`, `medical.blood_group`, `personal.date_of_birth`, `personal.full_name`
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `personal.father_name`
- Fixtures: driving_licence_clean (clean)

## Passport (`PASSPORT`)

- Context scope: `passport` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Validated identifiers: `identity.passport_number` (passport)
- Classified by: "p<ind", "republic of india", "passport", "place of issue", "file no"
- Tested fields: `identity.gender`, `identity.nationality`, `identity.passport_number`, `passport.expiry_date`, `passport.issue_date`, `passport.place_of_issue`, `personal.date_of_birth`, `personal.given_names`, `personal.last_name`, `personal.place_of_birth`
- Fixtures: passport_clean (clean)

## Class 10 marksheet (`CLASS_10_MARKSHEET`)

- Context scope: `class_10` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "secondary school examination", "secondary school certificate", "matriculation", "class x", "statement of marks"
- Distinguished from look-alikes by: "higher secondary", "senior school certificate", "class xii"
- Layout rules: exam_session, certify-that holder, header line, sentence phrases
- Record tables: marks
- Tested fields: `academic.class10.board`, `academic.class10.exam_year`, `academic.class10.passing_year`, `academic.class10.result_date`, `academic.class10.result_status`, `academic.class10.roll_number`, `academic.class10.school`, `personal.date_of_birth`, `personal.father_name`, `personal.full_name`, `personal.mother_name`
- Tested records `academic.class10.subjects`: columns code, grade, marks_obtained, name, practical_or_internal, theory, total
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `academic.class10.percentage`, `education.percentage`
- Fixtures: class10_cbse_table (table), ho_icse_class10 (ocr)

## Class 12 marksheet (`CLASS_12_MARKSHEET`)

- Context scope: `class_12` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "senior school certificate", "higher secondary certificate", "senior secondary", "intermediate examination", "higher secondary"
- Layout rules: exam_session, certify-that holder, header line, sentence phrases
- Record tables: marks
- Tested fields: `academic.class12.board`, `academic.class12.exam_month`, `academic.class12.exam_year`, `academic.class12.marks_obtained`, `academic.class12.max_marks`, `academic.class12.passing_year`, `academic.class12.percentage`, `academic.class12.result_date`, `academic.class12.result_status`, `academic.class12.roll_number`, `academic.class12.school`, `academic.class12.stream`, `personal.father_name`, `personal.full_name`, `personal.mother_name`
- Tested records `academic.class12.subjects`: columns code, grade, marks_obtained, max_marks, name, theory, total
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `academic.class10.roll_number`, `academic.class12.percentage`
- Fixtures: class12_hsc_table (table), class12_hsc_scanned (ocr), ho_cbse_class12 (table)

## Birth certificate (`BIRTH_CERTIFICATE`)

- Context scope: `birth_certificate` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "birth certificate", "registrar of births", "registration of births", "place of birth"
- Tested fields: `birth_certificate.issue_date`, `birth_certificate.registration_date`, `birth_certificate.registration_number`, `identity.gender`, `personal.date_of_birth`, `personal.father_name`, `personal.full_name`, `personal.mother_name`, `personal.place_of_birth`
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `address.full_address`
- Fixtures: birth_certificate_clean (clean)

## Bank passbook (`BANK_PASSBOOK`)

- Validated identifiers: `financial.ifsc_code` (ifsc)
- Classified by: "passbook", "pass book", "ifsc", "branch", "bank"
- Distinguished from look-alikes by: "statement of account"
- Layout rules: header line
- Record tables: transactions
- Tested fields: `financial.account_holder_name`, `financial.account_number`, `financial.account_type`, `financial.bank_name`, `financial.branch_address`, `financial.branch_name`, `financial.cif_number`, `financial.ifsc_code`, `financial.micr_code`
- Tested records `financial.transactions`: columns balance, credit, date, debit, description, reference
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `personal.full_name`
- Fixtures: bank_passbook_table (table)

## Bank statement (`BANK_STATEMENT`)

- Validated identifiers: `financial.ifsc_code` (ifsc)
- Classified by: "statement of account", "bank statement", "account statement", "statement period", "opening balance"
- Distinguished from look-alikes by: "passbook"
- Layout rules: header line
- Record tables: transactions
- Tested fields: `financial.account_holder_name`, `financial.account_number`, `financial.bank_name`, `financial.branch_name`, `financial.cif_number`, `financial.ifsc_code`, `financial.micr_code`
- Tested records `financial.transactions`: columns balance, credit, date, debit, description, reference
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `identity.aadhaar_number`, `personal.full_name`
- Fixtures: bank_statement_table (table), bank_statement_ocr (ocr), ho_bank_statement (table)

## Electricity bill (`ELECTRICITY_BILL`)

- Classified by: "electricity bill", "units consumed", "energy bill", "consumer no", "electricity"
- Layout rules: header line
- Tested fields: `utility.bill_amount`, `utility.bill_date`, `utility.bill_month`, `utility.billing_unit`, `utility.consumer_name`, `utility.consumer_number`, `utility.due_date`, `utility.meter_number`, `utility.provider_name`, `utility.service_address`, `utility.units_consumed`
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `address.full_address`, `personal.full_name`
- Fixtures: electricity_bill_clean (clean), ho_electricity_bill (clean)

## Ration card (`RATION_CARD`)

- Classified by: "ration card", "civil supplies", "public distribution", "head of family", "fair price shop"
- Record tables: members
- Tested fields: `ration_card.address`, `ration_card.card_type`, `ration_card.head_of_family`, `ration_card.number`
- Tested records `ration_card.members`: columns age, gender, name, relation
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `address.full_address`, `personal.full_name`
- Fixtures: ration_card_table (table)

## Income certificate (`INCOME_CERTIFICATE`)

- Context scope: `income_certificate` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "income certificate", "annual income", "annual family income", "tahsildar"
- Layout rules: certify-that holder
- Tested fields: `financial.annual_income`, `income_certificate.application_number`, `income_certificate.financial_year`, `income_certificate.holder_name`, `income_certificate.issue_date`, `income_certificate.issuing_authority`, `income_certificate.number`, `income_certificate.valid_until`
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `personal.full_name`
- Fixtures: income_certificate_clean (clean), ho_income_certificate (clean)

## Caste certificate (`CASTE_CERTIFICATE`)

- Context scope: `caste_certificate` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "caste certificate", "scheduled caste", "belongs to the", "backward class"
- Distinguished from look-alikes by: "validity", "scrutiny committee", "creamy layer"
- Layout rules: certify-that holder
- Tested fields: `caste_certificate.application_number`, `caste_certificate.holder_name`, `caste_certificate.issue_date`, `caste_certificate.issuing_authority`, `caste_certificate.number`, `category.caste`, `category.social_category`
- Asserted absent where the document does not state it (e.g. a year-of-birth-only Aadhaar has no date of birth): `caste_validity.number`
- Fixtures: caste_certificate_clean (clean), ho_caste_certificate_sc (multilingual)

## Caste validity certificate (`CASTE_VALIDITY_CERTIFICATE`)

- Context scope: `caste_validity` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "caste validity", "validity certificate", "scrutiny committee"
- Tested fields: `caste_certificate.number`, `caste_validity.issue_date`, `caste_validity.issuing_authority`, `caste_validity.number`, `category.caste`, `category.social_category`, `personal.full_name`
- Fixtures: caste_validity_clean (clean)

## Non-creamy layer certificate (`NON_CREAMY_LAYER_CERTIFICATE`)

- Context scope: `ncl_certificate` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "non-creamy layer", "non creamy layer", "creamy layer"
- Tested fields: `ncl_certificate.issue_date`, `ncl_certificate.issuing_authority`, `ncl_certificate.number`, `ncl_certificate.valid_until`
- Fixtures: ncl_certificate_clean (clean)

## Domicile certificate (`DOMICILE_CERTIFICATE`)

- Context scope: `domicile_certificate` (generic labels such as *Certificate No*, *Seat No*, *Date of Issue* resolve to this document's own fields)
- Classified by: "domicile certificate", "domiciled", "domicile"
- Layout rules: certify-that holder, sentence phrases
- Tested fields: `domicile_certificate.issue_date`, `domicile_certificate.issuing_authority`, `domicile_certificate.number`, `domicile_certificate.state`, `identity.nationality`, `personal.full_name`
- Fixtures: domicile_certificate_marathi (multilingual), ho_domicile_certificate (clean)
