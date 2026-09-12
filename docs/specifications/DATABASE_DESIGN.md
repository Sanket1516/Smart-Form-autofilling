# DATABASE DESIGN DOCUMENT
## Smart Form Auto-Filling System

**Project Title:** Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms

---

# 1. Purpose

This document defines the database design for the Smart Form Auto-Filling System.

The database architecture uses two complementary databases:

1. **MongoDB** — primary structured/document database for users, profiles, document metadata, structured facts, provenance, recommendations, processing records, and feedback.
2. **ChromaDB** — vector database for document chunks, embeddings, and retrieval metadata used by the RAG pipeline.

The design follows the system architecture in which uploaded documents are processed into structured facts and document chunks, while dynamic web-form fields are semantically classified and routed to either structured retrieval or RAG retrieval.

---

# 2. Database Architecture

```text
                         DATABASE ARCHITECTURE
                                  |
                  +---------------+---------------+
                  |                               |
                  v                               v
             MongoDB                         ChromaDB
        Structured Storage               Vector Storage
                  |                               |
       +----------+----------+                    |
       |          |          |                    |
       v          v          v                    v
     Users     Documents    Facts          Document Chunks
     Profile   Metadata     Provenance      + Embeddings
     Feedback  Records      Corrections     + Metadata
       |          |          |
       +----------+----------+
                  |
                  v
          Application / FastAPI
                  |
                  v
           LangGraph Workflow
                  |
          +-------+-------+
          |               |
          v               v
   Structured         RAG Retrieval
    Retrieval
```

---

# 3. Database Responsibilities

| Database | Purpose |
|---|---|
| MongoDB | Structured application and user knowledge storage |
| ChromaDB | Semantic/vector storage for document chunks |
| MongoDB | User identity, profile, facts, documents, provenance, corrections |
| ChromaDB | Embeddings and retrieval metadata |
| MongoDB | Processing and recommendation records |
| ChromaDB | Contextual document retrieval |

The databases should not duplicate the same responsibility unnecessarily.

---

# 4. MongoDB Design

MongoDB is used as the primary structured database.

## 4.1 Collections

Recommended collections:

```text
smart_form_db
|
+-- users
|
+-- profiles
|
+-- documents
|
+-- structured_facts
|
+-- recommendations
|
+-- corrections
|
+-- feedback
|
+-- processing_records
|
+-- form_sessions
```

---

# 5. `users` Collection

## Purpose

Stores account and authentication-related information.

### Document Structure

```json
{
  "_id": "ObjectId",
  "full_name": "User Name",
  "email": "user@example.com",
  "password_hash": "hashed_password",
  "status": "active",
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_login_at": "datetime"
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `_id` | ObjectId | Yes | Unique user identifier |
| `full_name` | String | Yes | User's name |
| `email` | String | Yes | Login email |
| `password_hash` | String | Yes | Hashed password |
| `status` | String | Yes | Account status |
| `created_at` | DateTime | Yes | Account creation time |
| `updated_at` | DateTime | Yes | Last update time |
| `last_login_at` | DateTime | No | Last successful login |

### Constraints

- Email must be unique.
- Password must never be stored in plain text.
- Inactive users must not access protected resources.

### Indexes

```text
Unique Index:
email
```

---

# 6. `profiles` Collection

## Purpose

Stores the user's normalized profile information.

A profile represents the current usable view of information extracted from one or more documents.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "personal": {
    "full_name": "User Name",
    "date_of_birth": "2004-08-15",
    "gender": "Male"
  },
  "contact": {
    "email": "user@example.com",
    "phone": "9876543210"
  },
  "address": {
    "current": "Pune",
    "permanent": "Mumbai"
  },
  "education": [],
  "employment": [],
  "updated_at": "datetime"
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Profile identifier |
| `user_id` | ObjectId | Owner |
| `personal` | Object | Personal information |
| `contact` | Object | Contact information |
| `address` | Object | Address information |
| `education` | Array | Education information |
| `employment` | Array | Employment information |
| `updated_at` | DateTime | Last profile update |

### Relationship

```text
users._id
    |
    | 1 : 1
    v
profiles.user_id
```

---

# 7. `documents` Collection

## Purpose

Stores metadata about uploaded documents.

The original document may be stored separately according to the application's file-storage implementation; MongoDB stores the metadata and processing information.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "file_name": "resume.pdf",
  "file_type": "application/pdf",
  "file_size": 245678,
  "storage_reference": "document-storage-id",
  "document_type": "resume",
  "language": "en",
  "status": "processed",
  "uploaded_at": "datetime",
  "processed_at": "datetime",
  "page_count": 3
}
```

### Status Values

```text
uploaded
processing
processed
failed
deleted
```

### Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `_id` | ObjectId | Yes | Document ID |
| `user_id` | ObjectId | Yes | Owner |
| `file_name` | String | Yes | Original file name |
| `file_type` | String | Yes | MIME/file type |
| `file_size` | Number | Yes | File size |
| `storage_reference` | String | Yes | Reference to stored document |
| `document_type` | String | No | Detected document type |
| `language` | String | No | Document language |
| `status` | String | Yes | Processing status |
| `uploaded_at` | DateTime | Yes | Upload time |
| `processed_at` | DateTime | No | Processing completion |
| `page_count` | Number | No | Number of pages |

### Indexes

```text
Index:
user_id

Compound Index:
user_id + status
```

---

# 8. `structured_facts` Collection

## Purpose

Stores normalized facts extracted from user documents.

This is the main MongoDB collection used by the **Structured Retrieval Node**.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "concept": "date_of_birth",
  "value": "2004-08-15",
  "value_type": "date",
  "source_document_id": "ObjectId",
  "source_page": 1,
  "confidence": 0.98,
  "provenance": {
    "document_name": "aadhaar.pdf",
    "extraction_method": "ocr",
    "extracted_text": "Date of Birth: 15/08/2004"
  },
  "is_user_confirmed": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Fact identifier |
| `user_id` | ObjectId | Owner |
| `concept` | String | Normalized semantic concept |
| `value` | Mixed | Extracted value |
| `value_type` | String | Type of value |
| `source_document_id` | ObjectId | Source document |
| `source_page` | Number | Source page |
| `confidence` | Number | Extraction confidence |
| `provenance` | Object | Source/extraction information |
| `is_user_confirmed` | Boolean | Whether user confirmed it |
| `created_at` | DateTime | Creation time |
| `updated_at` | DateTime | Last update |

### Example Concepts

```text
full_name
first_name
last_name
date_of_birth
phone_number
email
current_address
permanent_address
pan_number
passport_number
degree
university
organization
job_title
work_experience
```

### Important Design Rule

A fact should retain its source and confidence information. This allows the system to compare multiple candidate values instead of treating every extracted value as equally reliable.

---

# 9. Provenance Model

Provenance is important for explaining where a recommended value came from.

```text
Structured Fact
      |
      +-- Source Document
      +-- Source Page
      +-- Extraction Method
      +-- Original Text
      +-- Confidence
      +-- User Confirmation
```

Example:

```json
{
  "concept": "phone_number",
  "value": "9876543210",
  "confidence": 0.96,
  "provenance": {
    "document_id": "DOC123",
    "page": 1,
    "method": "ocr",
    "original_text": "Mobile: 9876543210"
  }
}
```

---

# 10. `recommendations` Collection

## Purpose

Stores field-level recommendations produced by the agent workflow.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "session_id": "ObjectId",
  "field_id": "field_17",
  "field_label": "Date of Birth",
  "concept": "date_of_birth",
  "recommended_value": "2004-08-15",
  "confidence": 0.97,
  "retrieval_type": "structured",
  "source_fact_ids": ["ObjectId"],
  "status": "approved",
  "created_at": "datetime"
}
```

### Status Values

```text
generated
pending_review
approved
edited
rejected
skipped
filled
verified
failed
```

---

# 11. `corrections` Collection

## Purpose

Stores corrections made by users during profile review or form filling.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "session_id": "ObjectId",
  "field_id": "field_17",
  "concept": "current_address",
  "original_value": "Pune",
  "corrected_value": "Mumbai",
  "reason": "User correction",
  "created_at": "datetime"
}
```

### Purpose of Correction Data

Corrections can be used to:

- Improve future recommendations.
- Identify recurring classification mistakes.
- Identify incorrect extraction.
- Evaluate the system.
- Improve confidence thresholds.

---

# 12. `feedback` Collection

## Purpose

Stores user feedback about system recommendations and actions.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "session_id": "ObjectId",
  "field_id": "field_17",
  "concept": "phone_number",
  "recommendation_id": "ObjectId",
  "action": "corrected",
  "original_value": "9123456789",
  "final_value": "9876543210",
  "feedback_type": "incorrect_value",
  "created_at": "datetime"
}
```

### Possible Actions

```text
confirmed
edited
rejected
skipped
corrected
```

---

# 13. `processing_records` Collection

## Purpose

Tracks document-processing jobs and failures.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "document_id": "ObjectId",
  "stage": "ocr",
  "status": "completed",
  "started_at": "datetime",
  "completed_at": "datetime",
  "retry_count": 0,
  "error": null
}
```

### Processing Stages

```text
upload
validation
ocr
parsing
extraction
normalization
embedding
mongodb_storage
chromadb_storage
completed
```

---

# 14. `form_sessions` Collection

## Purpose

Stores metadata about a form-filling session.

### Document Structure

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "website_origin": "https://example.com",
  "page_url": "https://example.com/application",
  "form_id": "form_01",
  "started_at": "datetime",
  "completed_at": "datetime",
  "status": "completed",
  "total_fields": 20,
  "filled_fields": 17,
  "reviewed_fields": 3,
  "failed_fields": 0
}
```

### Status Values

```text
started
processing
review_required
ready
completed
failed
cancelled
```

---

# 15. MongoDB Relationships

MongoDB is document-oriented, but logical relationships still exist.

```text
                    users
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      profiles    documents    form_sessions
                      |
                      v
              structured_facts
                      |
                      v
                 provenance

form_sessions
      |
      +----------+
      |          |
      v          v
recommendations corrections
      |
      v
  feedback
```

---

# 16. User-Level Data Isolation

Every user-specific collection should contain a `user_id`.

```text
User A
 |
 +-- Documents
 +-- Facts
 +-- Profile
 +-- Recommendations
 +-- Corrections
 +-- Feedback

User B
 |
 +-- Documents
 +-- Facts
 +-- Profile
 +-- Recommendations
 +-- Corrections
 +-- Feedback
```

All backend queries must enforce user ownership.

Example:

```text
Query:
{
    user_id: authenticated_user_id,
    concept: "date_of_birth"
}
```

The system must never retrieve another user's facts.

---

# 17. ChromaDB Design

ChromaDB stores semantic document representations.

## Collection

A primary collection can be created for document chunks, for example:

```text
user_document_chunks
```

Depending on implementation, separate collections may be used, but the logical requirement is that each chunk remains associated with its user and source document.

---

# 18. ChromaDB Record Structure

Conceptually:

```json
{
  "id": "chunk_document123_page2_05",
  "document": "Relevant extracted text from the document...",
  "embedding": "[vector]",
  "metadata": {
    "user_id": "USER123",
    "document_id": "DOC123",
    "document_name": "resume.pdf",
    "page_number": 2,
    "language": "en",
    "chunk_index": 5
  }
}
```

### Metadata

| Metadata | Purpose |
|---|---|
| `user_id` | User-level isolation |
| `document_id` | Source-document association |
| `document_name` | Provenance |
| `page_number` | Page-level traceability |
| `language` | Language filtering |
| `chunk_index` | Chunk ordering |

Additional metadata can be added if required by the retrieval implementation.

---

# 19. ChromaDB Data Flow

```text
Normalized Document
       |
       v
Chunking
       |
       v
Document Chunks
       |
       v
Embedding Model
       |
       v
Vector Embeddings
       |
       v
ChromaDB
```

---

# 20. ChromaDB Retrieval Flow

```text
Web Form Field
      |
      v
Semantic Concept
      |
      v
Contextual Query
      |
      v
Query Embedding
      |
      v
ChromaDB Similarity Search
      |
      v
Top-K Relevant Chunks
      |
      v
Metadata / Provenance
      |
      v
LLM Reasoning
```

---

# 21. MongoDB Structured Retrieval Flow

```text
Classified Field
      |
      v
Concept
      |
      v
Structured Retrieval Node
      |
      v
MongoDB Query
      |
      v
Candidate Facts
      |
      v
Confidence + Provenance
      |
      v
LLM / Conflict Resolver
```

---

# 22. Hybrid Retrieval Architecture

The system uses a routing mechanism to select the appropriate retrieval strategy.

```text
                 Classified Field
                       |
                       v
                 Routing Node
                   /       \
                  /         \
                 v           v
        Structured Need   Contextual Need
              |                 |
              v                 v
           MongoDB           ChromaDB
              |                 |
              +--------+--------+
                       |
                       v
                 LLM Reasoning
```

This is a retrieval-path distinction, not a classification of documents into "structured" and "unstructured" categories.

---

# 23. Conflict Resolution Data Model

When multiple candidate facts exist:

```text
Concept = current_address

Candidate 1
Value = Pune
Source = Resume
Confidence = 0.82

Candidate 2
Value = Mumbai
Source = Recent Document
Confidence = 0.95
```

The system can create a candidate set:

```json
{
  "concept": "current_address",
  "candidates": [
    {
      "value": "Pune",
      "source_document_id": "DOC1",
      "confidence": 0.82
    },
    {
      "value": "Mumbai",
      "source_document_id": "DOC2",
      "confidence": 0.95
    }
  ],
  "resolution_status": "pending_review"
}
```

Possible resolution states:

```text
unresolved
automatically_resolved
user_confirmed
user_corrected
```

---

# 24. Data Lifecycle

## Document Lifecycle

```text
Uploaded
   |
   v
Validated
   |
   v
Processing
   |
   v
OCR / Parsing
   |
   v
Extracted
   |
   v
Normalized
   |
   v
Stored
   |
   v
Available for Retrieval
   |
   v
Deleted
```

## Recommendation Lifecycle

```text
Generated
   |
   v
Confidence Check
   |
   +----------------+
   |                |
   v                v
Approved        Human Review
   |                |
   |          +-----+-----+
   |          |     |     |
   |          v     v     v
   |       Confirm Edit Reject
   |          |     |     |
   +----------+-----+-----+
              |
              v
            Filled
              |
              v
           Verified
```

---

# 25. Indexing Strategy

## MongoDB Indexes

Recommended indexes:

```text
users
  - unique(email)

profiles
  - user_id

documents
  - user_id
  - user_id + status

structured_facts
  - user_id + concept
  - user_id + concept + is_user_confirmed
  - source_document_id

recommendations
  - user_id + session_id
  - session_id + field_id

corrections
  - user_id + concept
  - session_id

feedback
  - user_id + created_at

processing_records
  - document_id
  - user_id + status

form_sessions
  - user_id + started_at
```

Indexes should be adjusted after observing actual query patterns.

---

# 26. Data Validation

The application layer should validate:

### User Data

- Valid email
- Password requirements
- Required fields
- Unique account

### Document Data

- Supported file type
- File size
- Valid document reference
- User ownership

### Structured Facts

- Valid concept
- Appropriate value type
- Confidence in range `0.0–1.0`
- Valid source document
- User ownership

### Recommendations

- Valid field ID
- Valid concept
- Recommendation status
- Confidence in range `0.0–1.0`

---

# 27. Data Consistency Rules

1. Every user-specific record must contain a valid `user_id`.
2. Every structured fact should reference a source document where applicable.
3. Every document chunk should contain source metadata.
4. MongoDB facts and ChromaDB chunks must be associated with the same user.
5. Deleting a document must remove or invalidate its associated structured facts and vector chunks.
6. User corrections must not silently overwrite historical recommendation information.
7. Important recommendation decisions should retain their status and provenance.
8. A failed processing job must not be treated as successfully processed.

---

# 28. Document Deletion and Cascading Cleanup

When a user deletes a document:

```text
Delete Document
      |
      v
Find document_id
      |
      +-------------------------+
      |                         |
      v                         v
MongoDB                    ChromaDB
      |                         |
      v                         v
Delete / Invalidate        Delete Chunks
Structured Facts
      |                         |
      +-------------+-----------+
                    |
                    v
              Update Profile
                    |
                    v
              Record Deletion
```

The exact physical deletion mechanism for ChromaDB should follow the selected implementation/API.

---

# 29. Backup and Recovery

## MongoDB

Recommended backup considerations:

- Scheduled database backups
- Point-in-time recovery where available
- Backup encryption
- Access-controlled backup storage

## ChromaDB

Because ChromaDB contains generated embeddings and document chunks:

- Persist the ChromaDB storage.
- Back up the persistent data.
- Maintain source document references.
- Support re-embedding/re-indexing from source documents if vector data is lost.

---

# 30. Security Considerations

The database layer contains sensitive personal information.

### Requirements

- Authentication before access.
- Authorization on every user-specific operation.
- User-level data isolation.
- Secure database credentials.
- No passwords in plain text.
- Encrypted transport between application and database services.
- Restricted database network access.
- Controlled backups.
- Audit important changes.
- Avoid exposing raw personal information in logs.

---

# 31. Auditability

Important operations should be traceable.

```text
User Action
    |
    v
Application Event
    |
    v
Audit / Processing Record
    |
    +-- Timestamp
    +-- User
    +-- Operation
    +-- Resource
    +-- Status
```

Examples:

```text
Document uploaded
Document processed
Fact extracted
Fact corrected
Recommendation generated
Recommendation confirmed
Recommendation rejected
Field autofilled
Verification completed
Document deleted
```

---

# 32. Privacy Requirements

The database must be designed around the principle that personal information is sensitive.

### Privacy Rules

- Store only required information.
- Associate data with the correct user.
- Restrict cross-user access.
- Do not expose personal information through error messages.
- Avoid logging sensitive values unnecessarily.
- Delete associated derived data when a user requests document deletion.
- Maintain provenance without unnecessarily exposing sensitive document content.

---

# 33. Example End-to-End Data Flow

### Input

User uploads:

```text
resume.pdf
aadhaar.pdf
certificate.pdf
```

### Processing

```text
Documents
   |
   v
OCR / Parsing
   |
   v
Extraction
   |
   v
Normalization
   |
   +--------------------------+
   |                          |
   v                          v
Structured Facts          Document Chunks
   |                          |
   v                          v
MongoDB                  Embedding Model
                              |
                              v
                          ChromaDB
```

### Web Form

```text
"Date of Birth"
      |
      v
Semantic Classification
      |
      v
Concept = date_of_birth
      |
      v
Routing Node
      |
      v
Structured Retrieval
      |
      v
MongoDB
      |
      v
Candidate Fact
      |
      v
LLM / Validation
      |
      v
Final Recommendation
      |
      v
Chrome Extension
      |
      v
Autofill
      |
      v
Verification
```

---

# 34. Example RAG Data Flow

For a contextual field:

```text
"Describe your project experience"
          |
          v
Semantic Classification
          |
          v
Routing Node
          |
          v
RAG Retrieval
          |
          v
Create Query Embedding
          |
          v
ChromaDB
          |
          v
Top-K Resume Chunks
          |
          v
LLM
          |
          v
Contextual Recommendation
          |
          v
Human Review if Required
          |
          v
Autofill
```

---

# 35. Database-to-Agent Mapping

| Agent / Module | Database Interaction |
|---|---|
| Document Processing | Writes document metadata and extracted information |
| Extraction Module | Produces structured facts |
| Normalization Module | Standardizes fact values |
| Semantic Classification Agent | Produces concept used for retrieval |
| Routing Node | Selects retrieval mechanism |
| Structured Retrieval Node | Reads MongoDB |
| RAG Retrieval Node | Queries ChromaDB |
| LLM | Consumes retrieved data |
| Conflict Resolver | Compares candidate facts/provenance |
| HITL | Receives candidate values and stores user decision |
| Final Response Node | Produces recommendation record |
| Autofill | Consumes approved recommendation |
| Feedback Module | Stores corrections and feedback |

---

# 36. Database Design Principles

1. **MongoDB is the structured source for application and personal facts.**
2. **ChromaDB is the semantic vector source for document retrieval.**
3. **Every user-owned record must be associated with a user ID.**
4. **Facts should preserve provenance and confidence.**
5. **Document chunks should preserve document/page metadata.**
6. **Historical recommendations and corrections should be retained where needed for evaluation and traceability.**
7. **Database operations must support safe failure and recovery.**
8. **Deletion must consider both original and derived data.**
9. **Sensitive information must not be unnecessarily exposed through logs.**
10. **The database design must support the LangGraph retrieval workflow.**

---

# 37. Final Database Architecture

```text
                         SMART FORM SYSTEM
                                |
                                v
                            FastAPI
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
       Document Pipeline                    LangGraph Agent
             |                                     |
             v                                     v
      OCR / Parsing                       Semantic Classification
             |                                     |
             v                                     v
      Extraction / Normalization              Routing Node
             |                               /           \
             |                              /             \
             v                             v               v
        Structured Facts              MongoDB          ChromaDB
             |                             |               |
             v                             |               |
          MongoDB <-------------------------+               |
             |                                             |
             |                                             v
             |                                      RAG Retrieval
             |                                             |
             +----------------------+----------------------+
                                    |
                                    v
                              LLM Reasoning
                                    |
                                    v
                         Conflict / Confidence
                                    |
                           +--------+--------+
                           |                 |
                           v                 v
                      Auto Approved      Human Review
                           |                 |
                           +--------+--------+
                                    |
                                    v
                              Recommendation
                                    |
                                    v
                                 Autofill
                                    |
                                    v
                               Verification
                                    |
                                    v
                                 Feedback
                                    |
                                    v
                          MongoDB Feedback Data
```

---

# 38. Summary

The database architecture uses **MongoDB and ChromaDB as complementary storage layers**.

### MongoDB

Responsible for:

- Users
- Profiles
- Documents
- Structured facts
- Provenance
- Recommendations
- Corrections
- Feedback
- Processing records
- Form sessions

### ChromaDB

Responsible for:

- Document chunks
- Embeddings
- Document/page metadata
- Semantic retrieval

Together, they provide the knowledge foundation required by the LangGraph agent workflow to perform context-aware semantic form understanding, retrieval, reasoning, conflict handling, human review, autofill, and verification.

**End of DATABASE_DESIGN.md**
