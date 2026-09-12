# TEST PLAN
## Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms

**Project Type:** Capstone Project  
**Academic Year:** 2026–27  
**Department:** Computer Science  
**Institution:** MPSTME, Shirpur Campus  
**Team:** Ashmit Patil (E246), Sanket Mali (E265), Pinak Salunke (E247)  
**Guide:** Dr. Nitin Choubey  

---

## 1. Document Purpose

This Test Plan defines the testing strategy, scope, test levels, test scenarios, test cases, evaluation metrics, acceptance criteria, and validation procedures for the Smart Form Auto-Filling System.

The system combines:

- React.js frontend
- Chrome Extension using Manifest V3
- FastAPI backend
- LangGraph/LangChain orchestration
- Semantic Classification Agent
- Routing Node
- Structured Retrieval Node
- RAG Retrieval Node
- Final Response Node
- MongoDB
- ChromaDB
- PaddleOCR
- pdfplumber
- LLM-based reasoning
- Context-aware dynamic web-form understanding
- Human-in-the-loop review
- Browser-based autofill and verification

The objective of testing is to verify that the system is functionally correct, reliable, secure, explainable, and sufficiently accurate for context-aware form assistance.

---

## 2. Testing Objectives

The primary objectives are:

1. Verify every functional requirement defined in the SRS.
2. Verify correct document ingestion, OCR, parsing, extraction, and normalization.
3. Verify correct storage and retrieval using MongoDB and ChromaDB.
4. Verify semantic classification of dynamic form fields.
5. Verify routing according to the information/retrieval requirement of a field.
6. Verify structured retrieval and RAG retrieval independently and together.
7. Verify LangGraph workflow orchestration and state transitions.
8. Verify conflict detection and human-in-the-loop handling.
9. Verify recommendation generation and provenance.
10. Verify safe browser autofill and post-fill verification.
11. Verify error handling and recovery from component failures.
12. Evaluate semantic and end-to-end system performance.
13. Verify privacy, security, prompt-injection resistance, and sensitive-field handling.
14. Identify usability issues and manual correction requirements.

---

## 3. Testing Scope

### 3.1 In Scope

- User registration and authentication
- Document upload and management
- PDF parsing
- OCR processing
- Entity/fact extraction
- Data normalization
- MongoDB persistence
- ChromaDB embeddings and metadata
- Profile and fact management
- Dynamic form detection
- DOM-based field perception
- Accessibility information where available
- Screenshot/image-based perception where applicable
- Semantic field classification
- Confidence estimation
- LangGraph orchestration
- Retrieval routing
- Structured retrieval
- RAG retrieval
- LLM reasoning
- Multi-source conflict detection
- Human-in-the-loop review
- Recommendation generation
- Browser autofill
- Autofill verification
- User corrections
- Feedback capture
- Logging and auditability
- API behavior
- Chrome extension behavior
- Security and privacy controls
- Performance and reliability
- Usability evaluation

### 3.2 Out of Scope

The following are not treated as mandatory production guarantees unless separately implemented:

- Universal compatibility with every website on the internet
- Perfect OCR for every document type
- Perfect semantic classification for previously unseen concepts
- Autonomous submission of high-risk forms without user confirmation
- Claims of experimental performance not yet measured
- Full production-scale load testing beyond the project's available infrastructure

---

## 4. Testing Strategy

Testing will follow a layered strategy:

```text
Unit Testing
    ↓
Component Testing
    ↓
API / Integration Testing
    ↓
Agent Workflow Testing
    ↓
End-to-End Testing
    ↓
Security & Reliability Testing
    ↓
Performance Evaluation
    ↓
User Acceptance / Usability Testing
```

Testing will use both deterministic test cases and representative real-world form/document scenarios.

---

## 5. Test Levels

### 5.1 Unit Testing

Tests individual functions or modules independently.

Examples:

- Input validation
- Data normalization
- OCR output processing
- Field-label preprocessing
- Ontology mapping
- Confidence calculation
- Retrieval filtering
- Conflict scoring
- API schema validation

### 5.2 Component Testing

Tests individual system components with their immediate dependencies.

Components include:

- Authentication service
- Document processor
- OCR service
- Fact extraction module
- MongoDB repository
- ChromaDB repository
- Semantic Classification Agent
- Routing Node
- Structured Retrieval Node
- RAG Retrieval Node
- Final Response Node
- HITL service
- Autofill service
- Verification service

### 5.3 Integration Testing

Tests interactions between components.

Important integrations:

- React ↔ FastAPI
- Chrome Extension ↔ FastAPI
- FastAPI ↔ MongoDB
- FastAPI ↔ ChromaDB
- FastAPI ↔ OCR/parser pipeline
- FastAPI ↔ LLM provider
- LangGraph ↔ retrieval nodes
- Retrieval nodes ↔ MongoDB/ChromaDB
- Recommendation ↔ autofill
- Autofill ↔ verification

### 5.4 End-to-End Testing

Tests the complete user journey:

```text
Login
  ↓
Upload Documents
  ↓
OCR / Parsing
  ↓
Extraction & Normalization
  ↓
MongoDB + ChromaDB
  ↓
Open Dynamic Web Form
  ↓
Detect Fields
  ↓
Semantic Classification
  ↓
Routing
  ↓
Retrieval
  ↓
Reasoning / Conflict Resolution
  ↓
Human Review if Required
  ↓
Recommendation
  ↓
Autofill
  ↓
Verification
  ↓
User Correction / Feedback
```

---

# 6. Test Environment

## 6.1 Software Environment

| Component | Test Environment |
|---|---|
| OS | Windows 11 / Ubuntu Linux |
| Frontend | React.js |
| Backend | FastAPI |
| Browser | Chromium-based browser supporting Manifest V3 |
| Database | MongoDB |
| Vector Database | ChromaDB |
| OCR | PaddleOCR |
| PDF Parser | pdfplumber |
| Agent Framework | LangGraph / LangChain |
| LLM | Configurable GPT-class / Llama / Qwen provider |
| Embedding | BGE-M3 or project-selected embedding model |
| Containerization | Docker |
| IDE | VS Code |
| Version Control | Git/GitHub |

## 6.2 Test Data

Test data should include:

- Clean digital PDFs
- Scanned PDFs
- Low-quality scans
- Multi-page documents
- Documents containing tables
- Documents with multiple addresses
- Documents containing dates and identifiers
- Multiple documents describing the same person
- Documents containing conflicting values
- Documents with missing information
- Sensitive personal information
- Dynamic forms with different labels and layouts
- Forms containing semantically equivalent fields with different wording
- Forms with dropdowns, radio buttons, checkboxes, text fields, date fields, and file inputs
- Ambiguous fields requiring user confirmation

Real personal documents should not be used for development testing unless appropriate consent, privacy controls, and data protection measures are in place.

---

# 7. Test Data Categories

| ID | Category | Purpose |
|---|---|---|
| TD-01 | Clean digital PDF | Baseline extraction |
| TD-02 | Scanned PDF | OCR validation |
| TD-03 | Low-quality scan | OCR robustness |
| TD-04 | Multi-page PDF | Page-level processing |
| TD-05 | Structured profile document | Structured fact extraction |
| TD-06 | Narrative document | RAG retrieval |
| TD-07 | Conflicting documents | Conflict resolution |
| TD-08 | Missing-field document | Missing information handling |
| TD-09 | Sensitive information | Security testing |
| TD-10 | Simple static form | Basic autofill |
| TD-11 | Dynamic JavaScript form | Dynamic field detection |
| TD-12 | Ambiguous form | HITL testing |
| TD-13 | Adversarial webpage | Prompt-injection/security testing |

---

# 8. Functional Test Cases

## 8.1 Authentication

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-AUTH-01 | Register with valid details | Account is created |
| TC-AUTH-02 | Register with duplicate email | Registration is rejected |
| TC-AUTH-03 | Register with invalid input | Validation error is returned |
| TC-AUTH-04 | Login with valid credentials | Authentication succeeds |
| TC-AUTH-05 | Login with invalid credentials | Authentication fails safely |
| TC-AUTH-06 | Access protected API without token | Request is rejected |
| TC-AUTH-07 | Logout | Session/token is invalidated as designed |
| TC-AUTH-08 | Access another user's data | Authorization prevents access |

---

## 8.2 Document Management

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-DOC-01 | Upload valid PDF | Document is accepted |
| TC-DOC-02 | Upload unsupported file | File is rejected |
| TC-DOC-03 | Upload oversized file | File-size validation is triggered |
| TC-DOC-04 | Upload duplicate document | Duplicate handling follows defined policy |
| TC-DOC-05 | Retrieve document list | Only authorized documents are returned |
| TC-DOC-06 | Delete document | Document and dependent data are handled according to deletion policy |
| TC-DOC-07 | Processing fails | Failure status is recorded and user receives meaningful feedback |

---

## 8.3 OCR and Parsing

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-OCR-01 | Process digital PDF | Text is extracted correctly |
| TC-OCR-02 | Process scanned PDF | OCR extracts readable content |
| TC-OCR-03 | Process multi-page PDF | Pages are processed without loss |
| TC-OCR-04 | Process poor-quality scan | System returns best available extraction and records uncertainty/errors |
| TC-OCR-05 | PDF contains tables | Relevant table content is preserved where supported |
| TC-OCR-06 | OCR service unavailable | Processing enters controlled failure/retry state |

---

## 8.4 Extraction and Normalization

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-EXT-01 | Extract name | Name is normalized and stored |
| TC-EXT-02 | Extract date | Date is normalized to project format |
| TC-EXT-03 | Extract address | Address components are represented correctly |
| TC-EXT-04 | Extract identifier | Identifier is associated with correct concept |
| TC-EXT-05 | Duplicate facts appear | Duplicate handling follows fact model |
| TC-EXT-06 | Low-confidence fact | Confidence/provenance is preserved |

---

## 8.5 MongoDB and ChromaDB

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-DB-01 | Store user | User record is persisted |
| TC-DB-02 | Store document metadata | Correct document record is created |
| TC-DB-03 | Store extracted fact | Fact is linked to correct user/document |
| TC-DB-04 | Store embedding | ChromaDB record is created with required metadata |
| TC-DB-05 | Retrieve structured fact | Correct MongoDB fact is returned |
| TC-DB-06 | Semantic search | Relevant ChromaDB chunks are returned |
| TC-DB-07 | Delete document | Associated vector/fact data follows deletion policy |
| TC-DB-08 | Unauthorized database access | Access is prevented |

---

## 8.6 Semantic Classification

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-SEM-01 | Field has exact known label | Correct semantic concept is classified |
| TC-SEM-02 | Field uses synonym | Equivalent concept is classified |
| TC-SEM-03 | Field has contextual label | Page/section context improves classification |
| TC-SEM-04 | Field is ambiguous | Confidence decreases or HITL is triggered |
| TC-SEM-05 | Previously unseen wording | System attempts ontology mapping and handles uncertainty safely |

Examples:

```text
"Full Name" → NAME
"Applicant Name" → NAME
"Name of Candidate" → NAME
"Residential Address" → ADDRESS
"Date of Birth" → DATE_OF_BIRTH
"DOB" → DATE_OF_BIRTH
```

---

## 8.7 Routing

Routing must be based on the **information/retrieval requirement of the field**, not on whether the source document is simply labeled structured or unstructured.

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-ROUTE-01 | Field requires exact known fact | Structured Retrieval Node is selected |
| TC-ROUTE-02 | Field requires contextual evidence | RAG Retrieval Node is selected |
| TC-ROUTE-03 | Field needs mixed evidence | Appropriate combined workflow is selected |
| TC-ROUTE-04 | Routing confidence is low | Safe fallback/HITL behavior occurs |

---

## 8.8 Structured Retrieval

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-SR-01 | Query exact profile fact | Correct fact is returned |
| TC-SR-02 | Query multiple candidate facts | Relevant candidates are ranked |
| TC-SR-03 | No structured fact exists | Controlled no-result state is returned |

---

## 8.9 RAG Retrieval

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-RAG-01 | Query semantically relevant content | Relevant chunks are retrieved |
| TC-RAG-02 | Query uses different wording | Semantic retrieval identifies related content |
| TC-RAG-03 | Query has no evidence | System does not fabricate supporting evidence |
| TC-RAG-04 | Multiple documents contain evidence | Sources and provenance are preserved |

---

## 8.10 Conflict Resolution

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-CON-01 | Two documents contain same value | No unnecessary conflict is raised |
| TC-CON-02 | Two documents contain different values | Conflict is detected |
| TC-CON-03 | One source is more recent | Resolution considers configured provenance/recency rules |
| TC-CON-04 | Conflict confidence is low | HITL review is triggered |
| TC-CON-05 | User selects preferred value | Selected value is recorded with audit information |

---

## 8.11 Human-in-the-Loop

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-HITL-01 | High-confidence field | No unnecessary review |
| TC-HITL-02 | Ambiguous field | Review request is created |
| TC-HITL-03 | Conflicting values | Review request shows relevant evidence |
| TC-HITL-04 | User approves value | Approved value becomes eligible for autofill |
| TC-HITL-05 | User rejects value | Value is not autofilled |
| TC-HITL-06 | User modifies value | Modified value is stored as correction/decision where appropriate |

---

## 8.12 Autofill

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-AUTO-01 | Fill text field | Correct approved value is inserted |
| TC-AUTO-02 | Fill date field | Correct value is inserted in compatible format |
| TC-AUTO-03 | Fill dropdown | Correct option is selected when mapping exists |
| TC-AUTO-04 | Fill checkbox/radio | Correct control is selected where supported |
| TC-AUTO-05 | Field is sensitive/high-risk | Additional confirmation is required where policy demands it |
| TC-AUTO-06 | No reliable value exists | Field remains unfilled rather than receiving fabricated data |
| TC-AUTO-07 | Website changes DOM dynamically | Extension re-evaluates or reports failure safely |

---

## 8.13 Verification and Feedback

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-VER-01 | Verify successful autofill | Filled values match approved recommendations |
| TC-VER-02 | Value changed by website | Verification detects discrepancy |
| TC-VER-03 | User corrects value | Correction is captured |
| TC-FB-01 | User submits feedback | Feedback is stored |
| TC-FB-02 | Repeated correction occurs | System records correction for future improvement |

---

# 9. API Testing

Every API endpoint defined in `API_SPECIFICATION.md` should be tested for:

1. Valid request.
2. Invalid request.
3. Missing required fields.
4. Invalid authentication.
5. Unauthorized resource access.
6. Correct HTTP status code.
7. Correct response schema.
8. Correct error schema.
9. Duplicate/idempotent requests where applicable.
10. Timeout/failure behavior.

### API Test Categories

```text
Authentication APIs
Document APIs
Profile APIs
Form Session APIs
Classification APIs
Recommendation APIs
Retrieval APIs
Agent APIs
HITL APIs
Correction APIs
Feedback APIs
Verification APIs
Health APIs
```

---

# 10. Agent Workflow Testing

The LangGraph workflow must be tested as a stateful process.

Expected conceptual flow:

```text
Field Input
    ↓
Semantic Classification Agent
    ↓
Routing Node
    ├──→ Structured Retrieval Node
    │
    └──→ RAG Retrieval Node
              ↓
        Evidence / Candidates
              ↓
          LLM Reasoning
              ↓
       Conflict / Confidence
          ↓          ↓
       Approved     HITL
          ↓          ↓
          └──────┬───┘
                 ↓
       Final Response Node
                 ↓
             Autofill
                 ↓
            Verification
```

### Agent Test Cases

| Test ID | Scenario | Expected Result |
|---|---|---|
| TC-AGENT-01 | Valid field enters graph | Correct initial state |
| TC-AGENT-02 | Classification succeeds | Routing receives classification |
| TC-AGENT-03 | Structured route selected | Structured node executes |
| TC-AGENT-04 | RAG route selected | RAG node executes |
| TC-AGENT-05 | Retrieval returns no evidence | Controlled fallback |
| TC-AGENT-06 | LLM service fails | Error/retry/fallback state |
| TC-AGENT-07 | Conflict detected | HITL branch is activated when required |
| TC-AGENT-08 | Final response generated | Recommendation contains evidence/provenance |
| TC-AGENT-09 | Workflow completes | Session status becomes completed |

---

# 11. Non-Functional Testing

## 11.1 Performance Testing

Measure:

- API response latency
- Document-processing latency
- OCR latency
- Semantic-classification latency
- Structured retrieval latency
- RAG retrieval latency
- End-to-end form processing latency
- Browser autofill latency

Performance should be measured under representative project workloads rather than arbitrary production-scale assumptions.

## 11.2 Reliability Testing

Test:

- Database unavailable
- OCR unavailable
- LLM unavailable
- ChromaDB unavailable
- Network interruption
- Browser extension failure
- Invalid document
- Corrupted document
- Partial processing
- Duplicate request
- Service restart

Expected behavior:

- Failure is detected.
- User receives meaningful status.
- No incorrect value is silently autofilled.
- Recoverable operations can retry where implemented.
- Processing state is preserved where appropriate.

## 11.3 Usability Testing

Evaluate:

- Ease of document upload
- Ease of profile review
- Clarity of recommendations
- Understandability of confidence indicators
- Clarity of HITL prompts
- Ease of correcting values
- Ease of reviewing provenance
- Overall autofill experience

The System Usability Scale (SUS) may be used for the user-centric evaluation.

---

# 12. Security Testing

Security testing is particularly important because the system processes personal documents and may operate on untrusted webpages.

### Security Scenarios

| Test ID | Security Scenario | Expected Result |
|---|---|---|
| TC-SEC-01 | Access another user's document | Denied |
| TC-SEC-02 | Access another user's facts | Denied |
| TC-SEC-03 | Malicious webpage content attempts prompt injection | Webpage content is treated as untrusted |
| TC-SEC-04 | Sensitive field detected | Appropriate protection/confirmation is applied |
| TC-SEC-05 | Malicious uploaded file | File validation prevents unsafe processing |
| TC-SEC-06 | Invalid/expired authentication token | Request is rejected |
| TC-SEC-07 | Unauthorized API operation | Authorization prevents operation |
| TC-SEC-08 | Database credentials exposed to client | Credentials are not exposed |
| TC-SEC-09 | Audit information checked | Sensitive information is not unnecessarily logged |
| TC-SEC-10 | Delete user data | Associated data follows deletion policy |

### Prompt-Injection Principle

Webpage text, labels, hidden content, and other browser-derived content must be treated as **untrusted input**.

A webpage must not be allowed to directly override system instructions, retrieval policy, security rules, or user-approved data.

---

# 13. Privacy Testing

Test that:

- User data is isolated.
- Documents are linked to the correct user.
- Sensitive values are not unnecessarily exposed.
- API responses contain only authorized data.
- Logs avoid unnecessary sensitive information.
- Deletion removes data according to the documented lifecycle.
- Provenance can be maintained without exposing unrelated private content.
- Test datasets are anonymized where appropriate.

---

# 14. Semantic Evaluation

The semantic field-classification component should be evaluated using labeled test data.

### Metrics

**Accuracy**

```text
Accuracy = Correct Predictions / Total Predictions
```

**Precision**

```text
Precision = TP / (TP + FP)
```

**Recall**

```text
Recall = TP / (TP + FN)
```

**Macro-F1**

```text
F1 = 2 × Precision × Recall / (Precision + Recall)
```

Calculate F1 for each semantic class and report macro-average.

### Ranking Metrics

Where multiple candidate concepts are produced:

- Top-1 Accuracy
- Top-3 Accuracy

---

# 15. End-to-End Evaluation

The following metrics should be measured:

### 15.1 Autofill Accuracy

```text
Autofill Accuracy =
Correctly Filled Fields / Total Eligible Fields
```

### 15.2 Task Completion Rate

```text
Task Completion Rate =
Successfully Completed Tasks / Total Tasks
```

### 15.3 Average Processing Latency

Measure elapsed time from field-analysis initiation to recommendation generation and/or completed autofill, with the exact measurement boundary documented.

### 15.4 Completion Time

Compare time required to complete representative forms:

```text
Manual Completion Time
vs.
System-Assisted Completion Time
```

### 15.5 Calibration Error

Evaluate whether confidence scores correspond to actual correctness.

### 15.6 Conflict Resolution Accuracy

Measure the percentage of conflict cases where the selected/approved value matches the intended ground truth under the evaluation protocol.

---

# 16. Baseline Comparison

The project may compare the proposed system against appropriate baselines.

Suggested baselines:

1. Manual form filling.
2. Simple label/value matching.
3. DOM-only semantic understanding.
4. DOM + screenshot approach.
5. DOM + screenshot + accessibility information.
6. Full proposed multimodal agentic system.

The comparison must use the same evaluation dataset and clearly defined metrics.

---

# 17. Ablation Testing

Ablation studies should evaluate the contribution of major system components.

### Multimodal Ablations

| Configuration | Components |
|---|---|
| A1 | DOM only |
| A2 | Screenshot only |
| A3 | DOM + Screenshot |
| A4 | DOM + Screenshot + Accessibility |
| A5 | Full proposed system |

### System Component Ablations

| Configuration | Removed Component |
|---|---|
| B1 | Ontology |
| B2 | Persistent memory |
| B3 | Retrieval |
| B4 | Conflict resolution |
| B5 | Multimodal perception |
| B6 | Agent orchestration |

The purpose is to determine which components materially contribute to system performance.

---

# 18. User Study

A planned user study may involve:

- **20–30 participants**
- **5–10 representative personal documents per participant**

These are planned study targets, not experimental results.

Participants may perform representative form-filling tasks using:

1. Manual completion.
2. Proposed system-assisted completion.

Collect:

- Task completion
- Completion time
- Manual corrections
- User feedback
- SUS score
- Perceived usefulness
- Confidence in recommendations

Appropriate statistical tests may include:

- Paired t-test
- Wilcoxon signed-rank test
- McNemar's test
- Repeated-measures ANOVA where applicable

Use:

- α = 0.05
- 95% confidence intervals
- Effect sizes

The selected statistical test must depend on the final data distribution and experimental design.

---

# 19. Regression Testing

Regression tests must be executed after changes to:

- Semantic ontology
- Prompt templates
- LLM provider/model
- Retrieval configuration
- Embedding model
- MongoDB schema
- ChromaDB metadata
- LangGraph state transitions
- Chrome Extension content scripts
- Autofill logic
- API contracts
- Authentication/authorization
- Conflict-resolution rules

Critical regression suite:

```text
Authentication
Document Processing
Fact Extraction
Semantic Classification
Routing
Structured Retrieval
RAG Retrieval
Conflict Resolution
HITL
Recommendation
Autofill
Verification
Security
```

---

# 20. Error and Exception Test Matrix

| Failure | Expected Handling |
|---|---|
| Invalid PDF | Reject or report parsing failure |
| OCR failure | Report controlled processing failure |
| Extraction failure | Preserve error state and avoid fabricated facts |
| MongoDB unavailable | Controlled service error |
| ChromaDB unavailable | Controlled retrieval error |
| LLM unavailable | Retry/fallback/error according to implementation |
| No matching fact | Do not fabricate a value |
| Ambiguous field | Lower confidence / HITL |
| Conflicting facts | Conflict resolution/HITL |
| Dynamic DOM change | Re-detect or fail safely |
| Autofill mismatch | Verification detects mismatch |
| Unauthorized request | Return authorization error |
| Prompt injection | Ignore malicious webpage instructions |
| Network interruption | Retry/recover where implemented |

---

# 21. Traceability Matrix

| Requirement Area | Main Test Coverage |
|---|---|
| Authentication | TC-AUTH-* |
| Document Management | TC-DOC-* |
| OCR | TC-OCR-* |
| Extraction | TC-EXT-* |
| Database | TC-DB-* |
| Semantic Classification | TC-SEM-* |
| Routing | TC-ROUTE-* |
| Structured Retrieval | TC-SR-* |
| RAG | TC-RAG-* |
| Conflict Resolution | TC-CON-* |
| HITL | TC-HITL-* |
| Autofill | TC-AUTO-* |
| Verification | TC-VER-* |
| Feedback | TC-FB-* |
| Agent Workflow | TC-AGENT-* |
| Security | TC-SEC-* |

The final implementation should map each SRS functional requirement to at least one executable test case.

---

# 22. Entry Criteria

Testing begins when:

- Build is deployable.
- Required services are available.
- Core API contracts are implemented.
- Test database is configured.
- Test documents are prepared.
- Test forms are available.
- Authentication works sufficiently for protected testing.
- Logging and error reporting are enabled.

---

# 23. Exit Criteria

Testing may be considered complete for a project milestone when:

1. All critical functional test cases pass.
2. No unresolved critical security defect remains.
3. No unresolved defect can silently cause unsafe autofill.
4. Core database operations pass.
5. Semantic classification evaluation is completed.
6. Retrieval tests are completed.
7. Agent workflow tests pass for supported scenarios.
8. End-to-end workflows pass.
9. Regression suite passes for the final release candidate.
10. Evaluation metrics are calculated and documented.
11. Known limitations are documented.
12. User-study results, if conducted, are reported separately from planned targets.

---

# 24. Defect Classification

| Severity | Description |
|---|---|
| Critical | Security breach, data leakage, destructive data loss, or unsafe autonomous autofill |
| High | Major functionality unavailable or incorrect values can frequently be produced |
| Medium | Important functionality has a workaround |
| Low | Minor UI, documentation, or non-critical behavior issue |

### Defect Lifecycle

```text
New
 ↓
Triaged
 ↓
Assigned
 ↓
In Progress
 ↓
Fixed
 ↓
Retested
 ↓
Verified
 ↓
Closed
```

If the fix fails testing:

```text
Retested → Reopened → In Progress
```

---

# 25. Test Reporting

Each test execution should record:

- Test ID
- Date
- Build/version
- Environment
- Input data
- Expected result
- Actual result
- Pass/Fail
- Defect ID if failed
- Evidence/screenshot where useful
- Tester

A test summary should report:

- Total test cases
- Passed
- Failed
- Blocked
- Not executed
- Defects by severity
- Semantic evaluation metrics
- End-to-end metrics
- Security findings
- Usability findings

---

# 26. Acceptance Criteria

The system is acceptable for the defined capstone scope when it demonstrates:

- Correct user authentication and authorization.
- Reliable document ingestion for supported document types.
- Correct storage of document metadata and structured facts in MongoDB.
- Correct vector storage and metadata in ChromaDB.
- Functional semantic classification for the evaluated ontology.
- Correct retrieval routing based on information need.
- Functional structured and RAG retrieval.
- Traceable recommendations with supporting evidence/provenance.
- Safe handling of conflicts and ambiguous fields.
- Human review for cases requiring intervention.
- Correct autofill for supported form controls.
- Verification of autofilled values.
- Safe handling of missing information.
- Protection against unauthorized data access.
- Basic resistance to webpage prompt-injection attempts.
- Meaningful error handling.
- Documented limitations and evaluation results.

---

# 27. Test Execution Priority

### Priority 1 — Critical

- Authentication
- Authorization
- Data isolation
- Document processing
- MongoDB persistence
- ChromaDB retrieval
- Semantic classification
- Retrieval routing
- Conflict handling
- Safe autofill
- Verification
- Prompt-injection protection

### Priority 2 — High

- OCR robustness
- RAG retrieval
- HITL
- API integration
- Dynamic form handling
- Error recovery
- Feedback

### Priority 3 — Medium

- UI refinements
- Extended browser compatibility
- Advanced analytics
- Non-critical usability improvements

---

# 28. Recommended Test Execution Sequence

```text
1. Unit Tests
2. Database Tests
3. OCR / Parsing Tests
4. Extraction Tests
5. API Tests
6. Semantic Classification Tests
7. Retrieval Tests
8. LangGraph Agent Tests
9. HITL Tests
10. Chrome Extension Tests
11. Autofill Tests
12. Verification Tests
13. Security Tests
14. End-to-End Tests
15. Performance Tests
16. User Study
17. Regression Tests
18. Final Acceptance
```

---

# 29. Testing Principles

The project should follow these principles:

1. **Correctness before automation** — the system must not fill a field merely because a value is available.
2. **Evidence before inference** — recommendations should be grounded in retrieved user information.
3. **No fabrication** — missing evidence must not be converted into invented personal data.
4. **Human control** — ambiguous or high-risk cases should require user involvement where appropriate.
5. **Traceability** — important recommendations should retain provenance.
6. **Security by design** — webpage content is untrusted.
7. **Privacy by design** — personal documents and facts must remain isolated and protected.
8. **Failure safety** — system failures should fail safely rather than silently produce incorrect autofill.
9. **Reproducibility** — evaluation datasets, configurations, prompts/model versions, and test conditions should be recorded.
10. **Separation of planned and measured results** — planned participant counts and target metrics must never be presented as achieved experimental results.

---

# 30. Final Test Plan Summary

The testing strategy validates the Smart Form Auto-Filling System from individual components through the complete browser-assisted workflow.

The most important validation chain is:

```text
Document
   ↓
OCR / Parsing
   ↓
Extraction
   ↓
Normalization
   ↓
MongoDB + ChromaDB
   ↓
Dynamic Form Perception
   ↓
Semantic Classification
   ↓
Information-Need Routing
   ↓
Structured / RAG Retrieval
   ↓
Agentic Reasoning
   ↓
Conflict Resolution
   ↓
HITL when required
   ↓
Final Recommendation
   ↓
Autofill
   ↓
Verification
   ↓
Correction / Feedback
```

The final evaluation should combine functional correctness, semantic classification metrics, retrieval quality, end-to-end autofill performance, security testing, usability assessment, and ablation studies. No experimental result should be reported until the corresponding test has actually been executed and measured.
