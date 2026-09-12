# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms

**Capstone Project — 2026–27**  
**Department of Computer Science**  
**Mukesh Patel School of Technology Management and Engineering (MPSTME), Shirpur Campus, SVKM's NMIMS**

**Team Members**
- Ashmit Patil — E246
- Sanket Mali — E265
- Pinak Salunke — E247

**Project Guide:** Dr. Nitin Choubey

**Document Type:** Software Requirements Specification  
**Version:** 1.0  
**Status:** Detailed Project Specification  
**Date:** September 2026

---

# Document Control

| Field | Value |
|---|---|
| Project | Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms |
| Document | Software Requirements Specification |
| Version | 1.0 |
| Academic Year | 2026–27 |
| Institution | MPSTME Shirpur Campus, SVKM's NMIMS |
| Department | Computer Science |
| Guide | Dr. Nitin Choubey |
| Primary Interface | React-based web application and Chrome Extension |
| Backend | Python + FastAPI |
| Agent Orchestration | LangGraph / LangChain |
| Structured Database | MongoDB |
| Vector Database | ChromaDB |
| OCR | PaddleOCR |
| PDF Parsing | pdfplumber |
| Browser Technology | Chrome Extension, Manifest V3 |
| Status | Requirements and implementation specification |

---

# Table of Contents

1. Introduction  
2. Overall Description  
3. System Scope  
4. Product Perspective and Architecture  
5. Stakeholders and User Classes  
6. Functional Requirements  
7. Detailed Module Requirements  
8. Data Requirements and Database Specification  
9. Semantic Ontology Requirements  
10. Agentic Workflow Requirements  
11. Retrieval and Reasoning Requirements  
12. Human-in-the-Loop Requirements  
13. Browser Extension Requirements  
14. User Interface Requirements  
15. API Requirements  
16. External Interface Requirements  
17. Non-Functional Requirements  
18. Security and Privacy Requirements  
19. Error Handling and Recovery Requirements  
20. Logging, Monitoring and Auditability  
21. Performance and Scalability Requirements  
22. Testing and Quality Requirements  
23. Evaluation and Research Requirements  
24. Acceptance Criteria  
25. Deployment and Environment Requirements  
26. Constraints and Assumptions  
27. Risks and Mitigation  
28. Traceability Matrix  
29. Project Delivery and Definition of Done  
30. Future Enhancements  
31. Conclusion

---

# 1. Introduction

## 1.1 Purpose

This Software Requirements Specification defines the functional, non-functional, data, interface, security, performance, testing, and deployment requirements for the capstone project titled **“Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms.”**

The system is intended to provide an intelligent browser-based assistant capable of understanding heterogeneous and dynamically generated web forms, identifying the semantic meaning of individual fields, retrieving relevant personal information from user-provided documents and stored knowledge, resolving ambiguity and conflicting information, and assisting the user in safely filling the form.

The system treats web-form completion as a **semantic reasoning problem rather than a simple label-to-value lookup problem**. A field such as “Given Name,” “Applicant Name,” “Legal Name,” or a context-dependent label may require different interpretations depending on the surrounding form, section, field constraints, and available user information.

The SRS establishes a common technical contract for implementation and testing. It is intended to be sufficiently detailed for developers, testers, project guides, reviewers, and future maintainers to understand what the system must do and what conditions must be satisfied for the implementation to be considered complete.

The requirements are based on the approved capstone direction and the project's supporting research work. The proposed framework integrates multimodal webpage perception, ontology-guided semantic classification, persistent personal knowledge, structured and vector retrieval, conflict-aware reasoning, browser interaction, and human validation. The research material explicitly treats empirical performance as something to be established through implementation and experimentation rather than as an already demonstrated result. 

## 1.2 Product Vision

The product vision is to develop a reusable intelligent form-understanding and assistance platform that can:

1. Understand web forms independent of website-specific field labels.
2. Interpret fields using structural, textual, accessibility, visual, and contextual information.
3. Map fields to standardized semantic concepts through a Universal Field Ontology.
4. Maintain reusable personal information obtained from user-provided documents.
5. Retrieve information through deterministic structured lookup or semantic vector retrieval depending on the information need.
6. Resolve conflicting candidate values using provenance, recency, source reliability, contextual relevance, and confidence.
7. Ask the user for confirmation when an automated decision is unsafe or ambiguous.
8. Fill validated information into dynamic web forms.
9. Verify that browser actions produced the intended form state.
10. Preserve traceability of important decisions and data sources.

## 1.3 Problem Statement

Conventional browser autofill systems generally depend on predefined field mappings, fixed HTML attributes, browser profiles, or manually configured templates. These approaches can become unreliable when websites use inconsistent labels, dynamic interfaces, multi-step workflows, hidden or visually rendered elements, semantically ambiguous fields, or unfamiliar terminology.

The proposed system addresses the problem of reliably interpreting such fields and selecting the appropriate user information before performing browser interaction.

## 1.4 Objectives

The system shall aim to:

- provide semantic understanding of heterogeneous web-form fields;
- create a reusable representation of user information;
- support document ingestion and extraction;
- map extracted information to standardized semantic concepts;
- provide deterministic structured retrieval for known personal facts;
- provide semantic retrieval over document chunks when direct structured information is insufficient;
- use agentic orchestration for classification, routing, retrieval, reasoning, and response generation;
- detect and handle conflicts between candidate values;
- provide human confirmation for uncertain or high-risk decisions;
- perform browser-side form assistance and autofill;
- verify completed field states;
- maintain provenance and audit information;
- collect user corrections and feedback for adaptive improvement.

## 1.5 Scope

### 1.5.1 In Scope

- User registration and authentication.
- User profile management.
- Upload of supported personal documents.
- PDF parsing.
- OCR of scanned/image-based content.
- Text extraction, normalization, chunking, and metadata generation.
- Extraction of candidate personal facts.
- Storage of canonical structured facts in MongoDB.
- Storage of searchable chunks and embeddings in ChromaDB.
- Provenance metadata.
- Dynamic web-form detection through the browser extension.
- DOM and contextual field extraction.
- Accessibility metadata extraction where available.
- Screenshot/visual information as supported by the implementation.
- Universal Field Ontology mapping.
- Semantic classification.
- Retrieval routing based on information/retrieval need.
- Structured retrieval from MongoDB.
- RAG/vector retrieval from ChromaDB.
- LLM-assisted reasoning.
- Conflict-aware candidate selection.
- Confidence estimation.
- Human-in-the-loop confirmation.
- Browser-side field filling.
- Post-fill verification.
- User corrections and feedback.
- Logging and auditability.
- Security and privacy controls.
- Evaluation of semantic and end-to-end performance.

### 1.5.2 Out of Scope for the Core Release

- Fully autonomous submission of sensitive forms without user approval.
- Guaranteed interpretation of every possible field in every language.
- Replacement of legal, financial, medical, or governmental decision-making.
- Training a foundation language model from scratch.
- Treating webpage instructions as trusted system instructions.
- Claiming experimental superiority before the planned evaluation is completed.

---

# 2. Overall Description

## 2.1 Product Perspective

The system is a distributed software product consisting of:

1. **React Web Application** — user dashboard and management interface.
2. **Chrome Extension (Manifest V3)** — in-browser form detection and assistance.
3. **FastAPI Backend** — authentication, document services, orchestration APIs, retrieval APIs, and application services.
4. **Document Processing Pipeline** — OCR, PDF parsing, extraction, normalization and chunking.
5. **MongoDB** — structured application and canonical personal information store.
6. **ChromaDB** — vector store for document chunks, embeddings, and semantic retrieval metadata.
7. **LangGraph/LangChain Agent Layer** — stateful orchestration and tool-based reasoning.
8. **LLM Provider Layer** — configurable GPT-class, Llama, Qwen, or project-selected compatible model.
9. **Embedding Layer** — project-selected embedding model such as BGE-M3 where appropriate.
10. **Browser Interaction Layer** — safe mapping of validated values to form elements.

The system is deliberately divided into deterministic and probabilistic responsibilities. Databases remain the source of stored facts. The LLM assists with interpretation, semantic reasoning, retrieval decisions, and conflict analysis; it must not fabricate personal information.

## 2.2 High-Level Workflow

```text
User
  |
  +--> Upload Documents
  |       |
  |       +--> PDF Parsing / OCR
  |       +--> Extraction
  |       +--> Normalization
  |       +--> Fact Validation
  |       |
  |       +--> MongoDB (Canonical Structured Facts)
  |       +--> ChromaDB (Chunks + Embeddings + Metadata)
  |
  +--> Open Dynamic Web Form
          |
          +--> Chrome Extension
          |
          +--> Field Detection
          |
          +--> Field Context Construction
          |
          +--> Semantic Classification Agent
          |
          +--> Routing Node
                  |
                  +--> Structured Retrieval Node
                  |
                  +--> RAG Retrieval Node
          |
          +--> Candidate Aggregation
          |
          +--> Conflict / Confidence Reasoning
          |
          +--> Final Response Node
          |
          +--> Human Confirmation if required
          |
          +--> Browser Autofill
          |
          +--> Verification
          |
          +--> Feedback / Audit
```

## 2.3 Design Principles

The implementation shall follow these principles:

- **Semantic first:** field meaning is determined before value selection.
- **Context aware:** neighboring fields, section headings, labels, placeholders, constraints, and visual information may influence interpretation.
- **Database grounded:** personal values must come from stored or explicitly supplied sources.
- **Provenance preserved:** important values must remain traceable to their source.
- **Confidence gated:** low-confidence decisions should not be silently automated.
- **Human controlled:** users retain authority over sensitive and ambiguous actions.
- **Webpage untrusted:** webpage text must never override system or user security policies.
- **Modular agents:** each reasoning responsibility is independently testable.
- **Deterministic ingestion:** the same document-processing input should produce reproducible structured outputs subject to the configured extraction model.
- **Separation of filling and submission:** filling a form is not equivalent to submitting it.

---

# 3. System Scope

## 3.1 Primary Use Case

A user uploads personal documents such as resumes, identity records, educational documents, addresses, certificates, or other supported documents. The system extracts relevant information and creates a structured personal information layer.

When the user visits an unfamiliar web form, the extension detects input fields and constructs a semantic representation using available webpage evidence. The Semantic Classification Agent maps each field to a Universal Field Ontology concept.

The Routing Node determines what retrieval capability is required. If the required value is available as a canonical structured fact, the system uses structured retrieval. If the field requires semantic evidence from document content, the system performs vector retrieval and RAG-style contextual retrieval.

Candidate values are evaluated. If there is one sufficiently confident candidate, it can be presented for autofill. If multiple candidates conflict or confidence is insufficient, the system asks the user to select or confirm a value. The selected value is then inserted into the appropriate browser field and the result is verified.

## 3.2 Supported User Categories

### 3.2.1 Standard User

Can:
- create an account;
- upload documents;
- review extracted information;
- correct personal facts;
- use browser assistance;
- approve/reject ambiguous values;
- view relevant history and provenance.

### 3.2.2 Administrator / Project Operator

Depending on the implemented deployment, an administrator may:
- monitor service health;
- inspect non-sensitive system logs;
- manage configuration;
- review evaluation datasets;
- manage system-level ontology configuration.

Administrator access must not automatically imply unrestricted access to sensitive user data.

---

# 4. Product Perspective and Architecture

## 4.1 Layered Architecture

The system shall implement the following conceptual layers.

### Layer 1 — Presentation and Browser Interaction

Responsible for:
- React dashboard;
- Chrome Extension;
- in-page assistant interface;
- user confirmations;
- field highlighting;
- status messages.

### Layer 2 — Application and API Layer

Implemented using FastAPI.

Responsible for:
- authentication;
- document upload;
- document status;
- user profile operations;
- retrieval requests;
- orchestration requests;
- feedback;
- audit queries.

### Layer 3 — Document Ingestion

Responsible for:
- file validation;
- PDF parsing;
- OCR;
- preprocessing;
- text extraction;
- chunking;
- metadata creation;
- structured fact extraction;
- normalization.

### Layer 4 — Knowledge and Memory

#### MongoDB

MongoDB shall be used for:
- user accounts;
- document records;
- canonical structured personal facts;
- normalized profile information;
- provenance references;
- processing status;
- feedback;
- audit metadata;
- system configuration where appropriate.

#### ChromaDB

ChromaDB shall be used for:
- document chunks;
- embeddings;
- semantic retrieval;
- chunk metadata;
- source-document references;
- page/section references;
- timestamps and confidence metadata where required.

### Layer 5 — Semantic Understanding

Responsible for:
- field representation;
- ontology mapping;
- semantic classification;
- confidence estimation;
- context interpretation.

### Layer 6 — Agentic Reasoning

Implemented using LangGraph/LangChain.

Required nodes:
1. Semantic Classification Agent.
2. Routing Node.
3. Structured Retrieval Node.
4. RAG Retrieval Node.
5. Final Response Node.

Additional validation/conflict states may be implemented as internal graph states where needed.

### Layer 7 — Browser Execution

Responsible for:
- mapping validated values to target elements;
- triggering appropriate browser events;
- verifying field state;
- handling dynamic page updates;
- preventing unintended submission.

## 4.2 Architectural Requirement

The architecture shall not route requests based simply on whether a document is “structured” or “unstructured.” Routing shall depend on the **information requirement of the current field and whether a suitable structured fact is available**, with semantic/vector retrieval used when document-level contextual evidence is required.

---

# 5. Stakeholders and User Classes

| Stakeholder | Interest |
|---|---|
| Student development team | Implementation, integration, testing and documentation |
| Project guide | Technical correctness and academic evaluation |
| End user | Safe and convenient form completion |
| Project evaluator | Architecture, innovation, usability and measurable performance |
| System administrator | Deployment and service monitoring |
| Future researcher | Reproducible architecture and evaluation |
| Security reviewer | Privacy, data handling and prompt-injection resistance |

---

# 6. Functional Requirements

## 6.1 Authentication Requirements

### FR-AUTH-01 — User Registration

The system shall allow a new user to create an account using the supported authentication fields.

**Input:** registration information.  
**Output:** authenticated or pending account.  
**Validation:** required fields must be validated before account creation.

### FR-AUTH-02 — User Login

The system shall authenticate registered users and create a secure session.

### FR-AUTH-03 — Logout

The system shall invalidate the user's active session or authentication token as appropriate.

### FR-AUTH-04 — Authorization

The system shall restrict protected resources to authenticated users and apply role-based access where administrator functionality exists.

### FR-AUTH-05 — Authentication Failure Handling

Invalid credentials shall result in a controlled error without exposing whether sensitive account information exists.

---

# 7. Detailed Module Requirements

## 7.1 Document Management

### FR-DOC-01 — Document Upload

The system shall allow authenticated users to upload supported documents.

Supported document categories may include:
- PDF documents;
- scanned documents;
- image-based documents;
- text-bearing documents supported by the implementation.

### FR-DOC-02 — File Validation

The system shall validate:
- file type;
- file size;
- file integrity;
- upload authorization.

### FR-DOC-03 — Document Metadata

Each document record shall include, as applicable:
- document identifier;
- owner identifier;
- original filename;
- document type;
- upload timestamp;
- processing status;
- page count;
- extraction status;
- processing error state;
- provenance information.

### FR-DOC-04 — Document Status

The system shall expose processing states such as:

```text
UPLOADED
QUEUED
PROCESSING
EXTRACTED
NORMALIZED
INDEXED
READY
FAILED
REQUIRES_REVIEW
```

### FR-DOC-05 — Document Listing

The user shall be able to view uploaded documents and their processing states.

### FR-DOC-06 — Document Deletion

The user shall be able to delete a document subject to authorization.

Deletion shall remove or invalidate associated structured and vector records according to the project's data-retention policy.

### FR-DOC-07 — Document Reprocessing

The system may allow a failed or outdated document to be reprocessed.

### FR-DOC-08 — Provenance

Every extracted fact that can influence autofill should be traceable to a source document and, where possible, page/section/chunk information.

---

# 8. OCR and Document Processing Requirements

## 8.1 OCR

### FR-OCR-01

The system shall use PaddleOCR for OCR processing of supported scanned/image-based documents.

### FR-OCR-02

The OCR subsystem shall preserve extracted text and relevant page information.

### FR-OCR-03

Where available, OCR output should preserve bounding-box or layout information.

### FR-OCR-04

OCR failures shall produce a controlled processing status.

### FR-OCR-05

The system shall distinguish OCR-derived text from directly parsed text in provenance metadata.

### FR-OCR-06

OCR shall not silently create personal facts when the source text is unreadable or ambiguous.

## 8.2 PDF Parsing

### FR-PDF-01

The system shall use pdfplumber for supported text-based PDF extraction.

### FR-PDF-02

The parser shall retain page boundaries.

### FR-PDF-03

The system shall use OCR when direct text extraction is insufficient and the document requires image-based interpretation.

## 8.3 Normalization

The processing pipeline shall normalize extracted information by:
- removing irrelevant extraction artifacts;
- standardizing whitespace;
- preserving meaningful punctuation;
- normalizing dates where safe;
- normalizing phone-number representation where possible;
- preserving source text for provenance.

---

# 9. Information Extraction Requirements

## 9.1 Candidate Fact Extraction

The system shall identify candidate personal facts from documents.

Examples include:
- person name;
- email address;
- phone number;
- address;
- date of birth;
- educational details;
- organization;
- skills;
- identifiers where explicitly supported;
- other ontology-supported concepts.

## 9.2 Fact Normalization

Extracted facts shall be converted into a normalized representation without destroying the original source value.

## 9.3 Fact Confidence

Each extracted candidate fact should contain:
- extraction confidence;
- source type;
- source document;
- source location;
- extraction timestamp.

## 9.4 User Verification

The system shall allow the user to review and correct extracted facts before they become trusted canonical profile information.

---

# 10. Personal Knowledge Requirements

## 10.1 Canonical Profile

The system shall maintain a canonical representation of verified personal information.

A canonical fact shall include, where applicable:

```text
fact_id
user_id
concept_id
value
normalized_value
source_document_ids
confidence
verified
created_at
updated_at
valid_from
valid_until
```

## 10.2 Multiple Candidate Values

The system shall permit multiple source values for the same semantic concept.

Example:

```text
ADDRESS
 ├── Address from current residence document
 ├── Address from older resume
 └── Address from application document
```

The existence of multiple candidates shall not automatically be treated as an error.

## 10.3 Provenance

The system shall preserve the relationship:

```text
User
  -> Fact
      -> Source Document
          -> Page / Section / Chunk
              -> Extraction Event
```

## 10.4 Verification

A fact shall support states such as:
- unverified;
- user-verified;
- system-derived;
- superseded;
- disputed.

---

# 11. Dynamic Web Form Understanding

## 11.1 Field Detection

The browser extension shall detect relevant interactive form elements, including supported:
- input elements;
- textarea elements;
- select controls;
- checkbox controls;
- radio controls;
- dynamically generated controls where technically accessible.

## 11.2 Field Object

For each field, the extension/backend pipeline shall construct a Field Object containing available information such as:

```text
field_id
tag
type
name
id
placeholder
label
aria_label
aria_description
autocomplete
required
pattern
input_constraints
nearby_text
section_context
position
DOM_context
accessibility_context
visual_context
```

## 11.3 Context Collection

The system shall consider:
- visible field labels;
- placeholders;
- HTML attributes;
- accessibility attributes;
- surrounding text;
- section headings;
- neighboring fields;
- field ordering;
- validation constraints;
- visual layout where available.

## 11.4 Dynamic Forms

The extension shall support forms whose fields are:
- dynamically inserted;
- modified after page load;
- displayed through JavaScript;
- present across multi-step interfaces where technically feasible.

## 11.5 Re-analysis

When relevant DOM changes occur, the extension shall be capable of re-evaluating affected fields rather than assuming that the original field representation remains valid.

---

# 12. Universal Field Ontology

## 12.1 Purpose

The Universal Field Ontology shall provide a standardized semantic vocabulary that separates field meaning from webpage-specific labels.

Examples:

```text
PERSON_NAME
FIRST_NAME
LAST_NAME
EMAIL_ADDRESS
PHONE_NUMBER
DATE_OF_BIRTH
ADDRESS
CITY
STATE
COUNTRY
POSTAL_CODE
ORGANIZATION
EDUCATION
SKILL
```

The actual ontology shall be extensible.

## 12.2 Ontology Mapping

Each classified field shall contain:
- ontology concept;
- confidence;
- alternative concepts where applicable;
- reasoning/context metadata;
- field identifier.

## 12.3 Synonym Handling

The system shall support semantically equivalent labels, such as:
- Full Name;
- Applicant Name;
- Given Name;
- Email;
- Contact Email;
- Mobile;
- Telephone Number.

The mapping shall not rely exclusively on exact string matching.

## 12.4 Unknown Concept

If a field cannot be mapped with sufficient confidence, the system shall:
- classify it as unknown/unsupported where appropriate;
- request additional context;
- avoid unsafe autofill;
- optionally record it for later ontology improvement.

---

# 13. Semantic Classification Agent

## 13.1 FR-SEM-01

The Semantic Classification Agent shall receive a Field Object and return a semantic interpretation.

## 13.2 FR-SEM-02

The agent shall use available field context rather than relying only on the field's visible label.

## 13.3 FR-SEM-03

The agent shall produce confidence information.

## 13.4 FR-SEM-04

The agent may use LLM and/or embedding-based reasoning according to the configured implementation.

## 13.5 FR-SEM-05

The agent shall not invent personal values during semantic classification.

## 13.6 Classification Output

A conceptual result shall resemble:

```json
{
  "field_id": "field_123",
  "concept": "EMAIL_ADDRESS",
  "confidence": 0.94,
  "alternatives": [
    {"concept": "CONTACT_EMAIL", "confidence": 0.05}
  ],
  "context_used": [
    "label",
    "placeholder",
    "section_heading",
    "aria_label"
  ]
}
```

The exact implementation schema may vary, but the semantic decision and confidence must be represented.

---

# 14. Retrieval Routing Requirements

## 14.1 Routing Principle

The Routing Node shall determine the retrieval path based on the **information requirement of the current semantic field**, availability of canonical structured facts, and need for contextual document evidence.

## 14.2 Structured Retrieval Route

The router shall prefer structured retrieval when:
- the ontology concept is known;
- a verified canonical fact exists;
- direct value lookup is sufficient;
- contextual document evidence is not required.

## 14.3 RAG Retrieval Route

The router shall select semantic/vector retrieval when:
- the exact structured fact is unavailable;
- webpage terminology differs significantly from stored terminology;
- contextual evidence is required;
- the required information is contained inside document text/chunks;
- multiple pieces of document evidence must be considered.

## 14.4 No-Data Route

If neither structured nor semantic retrieval produces sufficient evidence, the system shall return a missing-information state rather than fabricate a value.

---

# 15. Structured Retrieval Node

## 15.1 FR-SR-01

The Structured Retrieval Node shall query MongoDB for relevant verified or appropriately ranked facts.

## 15.2 FR-SR-02

The retrieval process shall support filtering by:
- user;
- semantic concept;
- verification state;
- validity;
- relevant context.

## 15.3 FR-SR-03

The node shall return provenance with retrieved candidates.

Example:

```text
Concept: PHONE_NUMBER
Value: +91XXXXXXXXXX
Source: User-verified profile
Status: Verified
Updated: <timestamp>
```

---

# 16. RAG Retrieval Node

## 16.1 FR-RAG-01

The RAG Retrieval Node shall query ChromaDB using semantic embeddings.

## 16.2 FR-RAG-02

Retrieved chunks shall include source metadata.

## 16.3 FR-RAG-03

Metadata filtering shall support user/document/page/section constraints where applicable.

## 16.4 FR-RAG-04

The system shall use retrieved evidence as grounding context and shall not treat the LLM's unsupported generation as a personal fact.

## 16.5 Chunk Metadata

A vector record should contain:

```text
chunk_id
user_id
document_id
page_number
section
language
content
embedding_reference
created_at
confidence
source_type
```

---

# 17. Final Response Node

## 17.1 Purpose

The Final Response Node shall aggregate semantic classification, retrieval outputs, conflict reasoning, confidence, and user decisions into a structured result.

## 17.2 Output States

Possible states include:

```text
READY_TO_FILL
REQUIRES_CONFIRMATION
MULTIPLE_CANDIDATES
MISSING_INFORMATION
UNSUPPORTED_FIELD
LOW_CONFIDENCE
SECURITY_BLOCKED
ERROR
```

## 17.3 No Fabrication

If no reliable candidate value exists, the Final Response Node shall not generate a plausible-looking personal value.

## 17.4 Explainability

Where appropriate, the response shall identify:
- selected concept;
- selected value;
- confidence;
- source;
- reason for confirmation.

---

# 18. Conflict Resolution

## 18.1 Conflict Definition

A conflict exists when multiple candidate values correspond to the same semantic concept but are not equivalent.

Example:

```text
ADDRESS
Candidate A -> older address
Candidate B -> newer address
```

## 18.2 Conflict Factors

The conflict-resolution process may consider:
- source reliability;
- verification status;
- document recency;
- semantic compatibility;
- contextual relevance;
- field constraints;
- historical user preference.

## 18.3 Confidence Gate

If the conflict-resolution confidence is below the configured threshold, the system shall request user confirmation.

## 18.4 Sensitive Fields

Sensitive fields shall have stricter confirmation requirements.

## 18.5 Conflict Outcome

The system shall produce:

```text
selected_candidate
confidence
candidate_set
provenance
decision_reason
requires_confirmation
```

---

# 19. Human-in-the-Loop Requirements

## 19.1 HITL Trigger Conditions

Human confirmation shall be available or required when:
- semantic classification is ambiguous;
- multiple candidate values conflict;
- confidence is below threshold;
- a sensitive field is involved;
- the system detects a potentially unsafe action;
- the user explicitly requests confirmation.

## 19.2 User Options

The confirmation interface shall allow the user to:
- select candidate A;
- select candidate B;
- select another candidate;
- edit the value;
- reject autofill;
- mark a value as preferred where supported.

## 19.3 User Decision Persistence

A confirmed user decision may be used to update the canonical profile or preference model according to explicit product rules.

## 19.4 Timeout / Dismissal

If the user dismisses a confirmation request, the system shall not fill the affected field automatically.

---

# 20. Browser Autofill Requirements

## 20.1 Field Mapping

The system shall map a validated semantic value to the correct browser field.

## 20.2 Event Handling

The extension shall trigger the input/change events required by common modern web applications where technically possible.

## 20.3 Dynamic UI

The system shall account for fields that become visible or enabled after user interaction.

## 20.4 Verification

After filling, the system shall verify that:
- the target element contains the intended value;
- the value has not immediately been overwritten;
- the field remains associated with the intended semantic concept.

## 20.5 Submission Separation

The system shall treat form filling and form submission as separate actions.

The default behavior shall not silently submit sensitive forms.

## 20.6 User Override

The user shall be able to manually modify an automatically inserted value before submission.

---

# 21. Feedback and Adaptive Learning

## 21.1 User Corrections

The system shall record user corrections where consent and configuration permit.

## 21.2 Feedback Types

Feedback may include:
- accepted value;
- corrected value;
- rejected value;
- corrected semantic label;
- confirmed conflict resolution;
- manual completion.

## 21.3 Adaptive Updates

Feedback may be used to improve:
- user-specific preferences;
- semantic mappings;
- confidence statistics;
- retrieval ranking.

The system shall not silently retrain or modify foundational models without an explicit implementation mechanism.

---

# 22. Data Requirements and Database Specification

## 22.1 MongoDB Responsibilities

MongoDB shall be the structured application and canonical personal-information store.

### Proposed Collections

#### users

```text
_id
email
password_hash / auth_reference
role
status
created_at
updated_at
```

#### documents

```text
_id
user_id
filename
document_type
mime_type
storage_reference
processing_status
page_count
uploaded_at
processed_at
```

#### extracted_facts

```text
_id
user_id
document_id
concept_id
raw_value
normalized_value
confidence
verification_status
page_number
source_text
created_at
updated_at
```

#### profile_facts

```text
_id
user_id
concept_id
value
normalized_value
verification_status
source_ids
valid_from
valid_until
confidence
preferred
created_at
updated_at
```

#### feedback

```text
_id
user_id
field_id
concept_id
old_value
new_value
feedback_type
created_at
```

#### audit_logs

```text
_id
user_id
event_type
resource_type
resource_id
timestamp
result
metadata
```

## 22.2 ChromaDB Responsibilities

ChromaDB shall contain semantic retrieval records.

Each vector record shall conceptually include:

```text
id
document_id
user_id
page_number
section
language
content
embedding
metadata
```

ChromaDB shall not replace MongoDB as the canonical source for structured personal profile facts.

## 22.3 Data Consistency

Document ingestion shall update MongoDB and ChromaDB through a controlled processing workflow.

If one storage operation fails:
- the processing state shall reflect partial failure;
- retry shall be possible;
- duplicate insertion shall be avoided where practical;
- provenance shall remain intact.

---

# 23. API Requirements

## 23.1 General

The backend shall expose REST-style APIs through FastAPI.

## 23.2 Authentication

Conceptual endpoints:

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

## 23.3 Documents

```text
POST   /api/documents
GET    /api/documents
GET    /api/documents/{document_id}
DELETE /api/documents/{document_id}
POST   /api/documents/{document_id}/reprocess
```

## 23.4 Profile

```text
GET    /api/profile
GET    /api/profile/facts
PATCH  /api/profile/facts/{fact_id}
DELETE /api/profile/facts/{fact_id}
```

## 23.5 Form Understanding

```text
POST /api/forms/analyze
POST /api/forms/classify
POST /api/forms/retrieve
POST /api/forms/resolve
POST /api/forms/fill-plan
```

## 23.6 Feedback

```text
POST /api/feedback
GET  /api/feedback
```

## 23.7 Audit

```text
GET /api/audit
GET /api/audit/{event_id}
```

Exact endpoint names may be finalized in the API Specification document, but the implemented API shall preserve equivalent responsibilities.

---

# 24. External Interface Requirements

## 24.1 Browser Interface

The Chrome Extension shall:
- communicate with the backend securely;
- detect supported fields;
- display assistant state;
- request semantic analysis;
- receive fill recommendations;
- display confirmation prompts;
- execute approved browser actions.

## 24.2 LLM Interface

The LLM interface shall:
- support configurable providers;
- provide structured outputs where possible;
- handle model/API failures;
- avoid exposing unnecessary personal data;
- receive only the context required for the current task.

## 24.3 Embedding Interface

The embedding subsystem shall:
- generate deterministic embeddings for the selected model/version;
- maintain model/version metadata;
- support semantic retrieval from ChromaDB.

## 24.4 OCR Interface

The OCR interface shall provide:
- extracted text;
- page references;
- layout/bounding information where available;
- processing status.

---

# 25. User Interface Requirements

## 25.1 Dashboard

The dashboard shall provide:
- login/register;
- document management;
- processing status;
- profile/facts;
- conflict review;
- history/audit views where permitted;
- system status where appropriate.

## 25.2 Extension Sidebar

The extension UI shall display:
- detected fields;
- semantic understanding status;
- recommended values;
- confidence indicators;
- source/provenance where appropriate;
- confirmation prompts;
- autofill controls;
- error states.

## 25.3 Field Highlighting

The system may highlight:
- fields ready for autofill;
- fields requiring confirmation;
- fields with missing information;
- unsupported fields.

## 25.4 Accessibility

The UI shall support:
- keyboard navigation;
- readable labels;
- adequate contrast;
- accessible status messaging;
- screen-reader-compatible controls where practical.

---

# 26. Non-Functional Requirements

## 26.1 Performance

The system shall be designed to minimize unnecessary model calls.

Structured retrieval should be preferred when a reliable canonical fact exists because it avoids unnecessary semantic generation.

## 26.2 Availability

The backend should recover gracefully from temporary:
- database failures;
- LLM API failures;
- OCR failures;
- vector database failures.

## 26.3 Reliability

The system shall prefer a safe “requires confirmation” result over an unsupported automated decision.

## 26.4 Usability

The workflow should minimize repetitive user actions while retaining user control for uncertain cases.

## 26.5 Maintainability

The system shall use modular components with clear interfaces.

The agent graph, retrieval services, browser extension, document processor, and databases shall be independently testable.

## 26.6 Portability

The backend shall be containerizable using Docker.

Target operating environments:
- Windows 11 development environment;
- Ubuntu Linux deployment environment.

## 26.7 Scalability

The architecture should support:
- multiple users;
- multiple documents per user;
- multiple simultaneous form-analysis requests;
- independent scaling of API and processing services.

## 26.8 Extensibility

The ontology shall support adding new concepts without redesigning the entire retrieval pipeline.

The LLM provider shall be configurable.

---

# 27. Security and Privacy Requirements

## 27.1 Data Minimization

Only information required for a specific task should be sent to the relevant processing component.

## 27.2 Authentication

Protected APIs shall require authentication.

## 27.3 Authorization

Users shall only access their own documents, facts, and audit records.

## 27.4 Sensitive Data

Sensitive information shall receive stricter handling and confirmation requirements.

## 27.5 Encryption

Data in transit shall use secure transport. Sensitive stored data should be protected according to the deployment environment.

## 27.6 Prompt Injection Resistance

Webpage content shall be treated as **untrusted input**.

A malicious webpage must not be able to:
- override system instructions;
- modify security policies;
- instruct the agent to reveal personal data;
- force sensitive autofill;
- bypass confirmation.

## 27.7 Data Leakage Prevention

The system shall avoid including unrelated user documents or facts in model prompts.

## 27.8 Auditability

Important actions should produce auditable events without unnecessarily duplicating sensitive raw data in logs.

## 27.9 Safe Failure

When security checks fail, the system shall block or defer the operation rather than silently continue.

---

# 28. Error Handling and Recovery

## 28.1 Document Errors

Possible states:
- unsupported file;
- corrupt file;
- OCR failure;
- parser failure;
- extraction failure;
- indexing failure.

## 28.2 Browser Errors

Possible states:
- field disappeared;
- field became disabled;
- DOM changed;
- value rejected;
- cross-origin limitation;
- extension permission limitation.

## 28.3 Retrieval Errors

Possible states:
- MongoDB unavailable;
- ChromaDB unavailable;
- no candidate;
- insufficient confidence;
- stale data.

## 28.4 LLM Errors

Possible states:
- timeout;
- provider unavailable;
- malformed output;
- rate limit;
- invalid response.

The system shall have bounded retry behavior and shall never interpret a failed model call as successful reasoning.

## 28.5 Recovery

Recoverable errors should support:
- retry;
- re-analysis;
- manual entry;
- user confirmation;
- safe cancellation.

---

# 29. Logging, Monitoring and Auditability

## 29.1 Application Logs

Logs should capture:
- service status;
- request IDs;
- processing states;
- error types;
- latency;
- agent-node execution states.

## 29.2 Agent Trace

Where technically feasible, each workflow should have a trace containing:

```text
workflow_id
user_id/reference
field_id
semantic_classification
route
retrieval_result
candidate_set
conflict_status
confidence
HITL_decision
fill_result
verification_result
```

Sensitive raw values should not be unnecessarily logged.

## 29.3 Audit Events

Auditable events include:
- document uploaded;
- document deleted;
- profile fact changed;
- value confirmed;
- value rejected;
- autofill performed;
- autofill blocked;
- conflict resolved.

---

# 30. Agentic Workflow Specification

## 30.1 LangGraph State

The graph state should conceptually contain:

```text
workflow_id
user_id
page_context
field_objects
current_field
semantic_result
retrieval_route
structured_candidates
rag_candidates
conflict_result
confidence
human_decision
final_value
execution_result
verification_result
errors
```

## 30.2 State Transition

```text
START
  |
  v
Field Detection
  |
  v
Semantic Classification Agent
  |
  v
Routing Node
  |
  +----> Structured Retrieval Node ----+
  |                                    |
  +----> RAG Retrieval Node -----------+
                                       |
                                       v
                              Candidate Aggregation
                                       |
                                       v
                              Conflict / Confidence
                                       |
                         +-------------+-------------+
                         |                           |
                    High Confidence             Low/Unsafe
                         |                           |
                         v                           v
                  Final Response              HITL Review
                         |                           |
                         +-------------+-------------+
                                       |
                                       v
                                  Browser Fill
                                       |
                                       v
                                   Verify
                                       |
                                       v
                                      END
```

## 30.3 Agent Isolation

Each node shall have:
- defined input;
- defined output;
- bounded responsibility;
- error state;
- trace information.

---

# 31. Mathematical / Decision Requirements

The system may model semantic classification as:

\[
c^* = \arg\max_{c \in O} P(c \mid F)
\]

where:

- \(F\) is the Field Object;
- \(O\) is the Universal Field Ontology;
- \(c^*\) is the selected semantic concept.

Candidate selection may be modeled as:

\[
v^* = \arg\max_{v \in V} S(v \mid c, K, C)
\]

where:

- \(V\) is the candidate-value set;
- \(c\) is the classified concept;
- \(K\) is retrieved personal knowledge;
- \(C\) is current form context.

The system shall apply a confidence gate:

\[
\text{Autofill}(v^*) =
\begin{cases}
1 & \text{if } Conf(v^*) \geq \tau \\
0 & \text{otherwise}
\end{cases}
\]

where \(\tau\) is the configured confidence threshold.

These mathematical expressions describe the intended decision behavior; they are not claims of experimentally validated performance.

---

# 32. Testing Requirements

## 32.1 Unit Testing

Unit tests shall cover:
- field parsing;
- normalization;
- ontology mapping;
- MongoDB access;
- ChromaDB retrieval;
- API validation;
- confidence logic;
- conflict resolution;
- browser field mapping.

## 32.2 Integration Testing

Integration tests shall cover:
- extension → backend;
- backend → MongoDB;
- backend → ChromaDB;
- document processor → both databases;
- agent graph → retrieval tools;
- final decision → extension.

## 32.3 End-to-End Testing

An end-to-end test shall cover:

```text
Document Upload
→ Processing
→ Knowledge Creation
→ Web Form Detection
→ Semantic Classification
→ Retrieval
→ Decision
→ Confirmation
→ Autofill
→ Verification
```

## 32.4 Security Testing

Security testing shall include:
- unauthorized API access;
- cross-user data access;
- malicious webpage instructions;
- prompt injection;
- unsafe sensitive-field requests;
- malformed files;
- oversized uploads.

## 32.5 Browser Compatibility Testing

Primary target:
- Chromium-based browsers supporting Manifest V3.

The implementation shall document tested browser versions.

---

# 33. Evaluation and Research Requirements

The research material defines evaluation as a planned empirical activity; no performance values shall be inserted into this SRS unless experiments have actually been completed.

## 33.1 Semantic Metrics

The system shall be evaluated using:
- Accuracy;
- Precision;
- Recall;
- Macro-F1;
- Top-1 semantic classification accuracy;
- Top-3 semantic classification accuracy.

## 33.2 End-to-End Metrics

Evaluation may include:
- Autofill Accuracy;
- Task Completion Rate;
- average processing latency;
- completion time;
- calibration error;
- Conflict Resolution Accuracy.

## 33.3 User-Centric Metrics

Where user evaluation is conducted:
- System Usability Scale (SUS);
- number of manual corrections;
- confirmation frequency;
- perceived usefulness.

## 33.4 Planned User Study

The supporting research material proposes approximately:
- 20–30 participants;
- 5–10 representative personal documents per participant.

These are **study targets, not experimental results**.

## 33.5 Baselines

Potential comparison systems include:
- rule-based field mapping;
- embedding-based matching;
- vanilla LLM prompting;
- conventional browser autofill;
- password-manager-style autofill.

## 33.6 Ablation Study

The planned configurations include:

| Configuration | Components |
|---|---|
| A | DOM only |
| B | Screenshot only |
| C | DOM + Screenshot |
| D | DOM + Screenshot + Accessibility |
| E | Full system |

Additional component ablations may remove:
- ontology;
- persistent memory;
- retrieval;
- conflict resolution;
- multimodal perception;
- agentic orchestration.

The purpose is to identify the contribution of individual components rather than merely increasing model complexity.

## 33.7 Statistical Analysis

Where appropriate, the research plan may use:
- paired t-test;
- Wilcoxon signed-rank test;
- McNemar's test;
- repeated-measures ANOVA.

Statistical significance is planned at:

\[
\alpha = 0.05
\]

Results should include effect sizes and 95% confidence intervals where applicable.

---

# 34. Acceptance Criteria

The system shall be considered functionally acceptable when the following conditions are satisfied.

## AC-01 Authentication

A user can securely register, log in, access protected functionality, and log out.

## AC-02 Document Ingestion

A supported document can be uploaded, processed, and assigned a final processing state.

## AC-03 OCR

A supported scanned document can be processed using PaddleOCR where direct text extraction is insufficient.

## AC-04 Structured Storage

Verified structured personal facts are stored in MongoDB.

## AC-05 Vector Storage

Document chunks and embeddings are stored in ChromaDB with sufficient metadata for semantic retrieval.

## AC-06 Provenance

A retrieved personal fact can be traced to its source.

## AC-07 Semantic Understanding

A detected form field can be mapped to a supported ontology concept with confidence information.

## AC-08 Routing

The system selects structured retrieval when canonical information is sufficient and RAG retrieval when contextual document evidence is required.

## AC-09 Conflict Handling

When multiple candidate values conflict, the system does not silently choose an unsafe value.

## AC-10 HITL

The user can confirm or reject ambiguous or sensitive values.

## AC-11 Autofill

A validated value can be inserted into the intended supported form field.

## AC-12 Verification

The system verifies the post-fill state.

## AC-13 Security

Untrusted webpage instructions cannot override trusted system policies.

## AC-14 No Fabrication

Missing personal information is not invented by the LLM.

## AC-15 Feedback

User corrections can be recorded and used by supported adaptive mechanisms.

## AC-16 Auditability

Important system decisions and actions can be traced without unnecessary exposure of sensitive data.

---

# 35. Deployment Requirements

## 35.1 Development Environment

The system shall support development using:
- Windows 11 and/or Ubuntu Linux;
- VS Code;
- Git/GitHub;
- Python;
- Node.js/npm as required by React;
- Docker.

## 35.2 Backend Deployment

FastAPI shall be deployable as a containerized service.

## 35.3 Database Deployment

MongoDB and ChromaDB shall be deployable as independent services.

## 35.4 Extension Deployment

The Chrome Extension shall be packaged according to Manifest V3 requirements.

## 35.5 Configuration

Secrets shall not be hard-coded.

Configuration shall support:
- database URLs;
- LLM provider;
- model names;
- embedding model;
- confidence thresholds;
- upload limits;
- environment mode.

---

# 36. Constraints and Assumptions

## 36.1 Constraints

1. The system depends on browser extension capabilities and permissions.
2. Dynamic websites may use techniques that limit field inspection.
3. OCR quality depends on document quality.
4. LLM output may be probabilistic.
5. External LLM availability may affect latency and reliability.
6. Vector retrieval quality depends on embedding quality and chunking.
7. Ontology coverage limits semantic classification.
8. The project must manage potentially sensitive personal information.
9. Experimental performance cannot be assumed before evaluation.

## 36.2 Assumptions

1. Users provide documents they are authorized to process.
2. The target browser supports Manifest V3.
3. The backend can communicate with MongoDB and ChromaDB.
4. The required LLM and embedding services are available in the configured environment.
5. Users remain responsible for final submission of sensitive applications.
6. The ontology is maintained as an extensible project resource.
7. Network access may be required for remote model services.

---

# 37. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Incorrect semantic classification | High | Multimodal context, ontology, confidence threshold, HITL |
| Wrong candidate value | High | Provenance, conflict resolution, verification |
| Missing information | Medium | Explicit missing-information state |
| OCR error | Medium | OCR confidence, source review, user correction |
| Prompt injection | High | Treat webpage as untrusted; policy isolation |
| LLM hallucination | High | Database-grounded retrieval; no fabrication |
| Browser DOM changes | Medium | Re-analysis and post-fill verification |
| Database failure | High | Error states, retries, consistency handling |
| Vector retrieval failure | Medium | Structured fallback where possible |
| Excessive latency | Medium | Routing, caching, smaller models where appropriate |
| Sensitive-data leakage | High | Data minimization, access control, secure transport |
| Ontology coverage gaps | Medium | Unknown state and ontology extension process |

---

# 38. Traceability Matrix

| Requirement Area | Main Requirement IDs | Verification |
|---|---|---|
| Authentication | FR-AUTH-01–05 | Functional + Security |
| Documents | FR-DOC-01–08 | Functional + Integration |
| OCR | FR-OCR-01–06 | Unit + Integration |
| PDF Parsing | FR-PDF-01–03 | Unit + Integration |
| Extraction | FR-EXT-* | Unit + Accuracy |
| Profile | FR-PROF-* | Functional + Data |
| Form Detection | FR-FORM-* | Browser Integration |
| Semantic Classification | FR-SEM-01–05 | Accuracy Evaluation |
| Routing | FR-ROUTE-* | Unit + Integration |
| Structured Retrieval | FR-SR-01–03 | Integration |
| RAG | FR-RAG-01–04 | Retrieval Evaluation |
| Final Response | FR-RESP-* | Integration |
| HITL | FR-HITL-* | Usability + Functional |
| Autofill | FR-AUTO-* | Browser E2E |
| Verification | FR-VER-* | Browser E2E |
| Security | SEC-* | Security Testing |
| Performance | NFR-* | Benchmarking |
| Usability | UX-* | User Study |

---

# 39. Definition of Done

The capstone implementation shall be considered complete when:

1. The React dashboard is functional.
2. The Manifest V3 extension can communicate with the backend.
3. FastAPI exposes the required application services.
4. User authentication is functional.
5. Document upload and processing are functional.
6. PaddleOCR and pdfplumber are integrated as required.
7. MongoDB stores structured application and profile data.
8. ChromaDB stores document chunks and embeddings.
9. Provenance is preserved.
10. The Universal Field Ontology is implemented for the supported concept set.
11. The Semantic Classification Agent works on supported fields.
12. The Routing Node selects the appropriate retrieval path.
13. Structured Retrieval uses MongoDB.
14. RAG Retrieval uses ChromaDB.
15. The Final Response Node produces a structured decision.
16. Conflict resolution is implemented for supported conflict cases.
17. HITL confirmation is available.
18. Browser autofill is implemented for supported field types.
19. Post-fill verification is implemented.
20. Prompt-injection and sensitive-data safeguards are implemented.
21. Unit and integration tests are available.
22. End-to-end test cases are executed.
23. Evaluation metrics are calculated from actual experiments.
24. No unsupported empirical claims are included in the final report.
25. Documentation is synchronized with the final implementation.

---

# 40. Future Enhancements

The following may be considered after the core capstone implementation:

- broader multilingual ontology coverage;
- additional document types;
- improved multimodal perception;
- more advanced Personal Knowledge Graph representations;
- richer temporal reasoning;
- improved cross-document conflict resolution;
- domain-specific ontology extensions;
- browser support beyond the primary Chromium target;
- offline/local LLM support;
- advanced privacy-preserving inference;
- benchmark expansion;
- continuous evaluation and adaptive personalization;
- use of the semantic understanding engine for applications beyond autofill, such as form validation, accessibility auditing, and interface analytics.

These enhancements shall not be treated as mandatory core-release requirements unless formally added through requirements change control.

---

# 41. Relationship with Other Project Documents

This SRS is part of the complete project documentation set.

| Document | Purpose |
|---|---|
| PRD.md | Product vision, goals, scope and product behavior |
| SRS.md | Detailed software requirements and system behavior |
| USER_FLOWS.md | Step-by-step user journeys |
| SYSTEM_ARCHITECTURE.md | Technical architecture and component relationships |
| DATABASE_DESIGN.md | MongoDB and ChromaDB data design |
| API_SPECIFICATION.md | Detailed API contracts |
| UI_UX_SPECIFICATION.md | Interface and interaction requirements |
| TEST_PLAN.md | Test strategy and test cases |

The SRS defines **what the system must do**. Architecture and database documents define **how major technical components are organized**. The API and UI documents provide implementation-level contracts.

---

# 42. Source and Research Alignment

The SRS is aligned with the project's capstone presentation and supporting FormMind research material.

The supporting research describes the proposed framework as combining:
- multimodal webpage perception;
- Universal Field Ontology;
- persistent personal knowledge;
- semantic/vector retrieval;
- conflict-aware reasoning;
- browser execution;
- human-in-the-loop validation.

It also explicitly emphasizes that current work defines the framework and evaluation protocol and does not claim completed experimental superiority. fileciteturn20file13

The research architecture describes structured knowledge and vector-based memory as complementary: structured facts support deterministic lookup, while vector retrieval supports semantic matching when webpage terminology differs from stored information. fileciteturn20file10

The research further specifies that conflict resolution should consider factors such as source reliability, recency, semantic plausibility, and contextual relevance, and that uncertain decisions should be deferred to human validation. fileciteturn20file12

The capstone presentation identifies the project as the **“Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms”** and lists Ashmit Patil, Sanket Mali, and Pinak Salunke under the guidance of Dr. Nitin Choubey. fileciteturn21file0

---

# 43. Final Summary

This SRS defines a complete requirements baseline for an agentic AI system that understands dynamic web forms semantically and assists users with safe, context-aware form completion.

The central pipeline is:

```text
User Documents
      ↓
OCR / PDF Parsing
      ↓
Extraction + Normalization
      ↓
MongoDB + ChromaDB
      ↓
Dynamic Web Form
      ↓
Field Object Construction
      ↓
Semantic Classification Agent
      ↓
Routing Node
      ↓
 ┌───────────────┬────────────────┐
 │               │                │
 ▼               ▼                │
MongoDB      ChromaDB             │
Structured   RAG Retrieval        │
Retrieval    + Context            │
 └───────────────┴────────────────┘
              ↓
      Candidate Aggregation
              ↓
      Conflict + Confidence
              ↓
       Human Confirmation
              ↓
       Final Response Node
              ↓
         Browser Autofill
              ↓
          Verification
              ↓
       Feedback + Audit

```

The system is therefore not defined as a conventional browser autofill utility. Its core capability is a reusable semantic-understanding and context-aware reasoning pipeline in which autofill is the primary downstream application for the capstone implementation.

**End of Software Requirements Specification**
