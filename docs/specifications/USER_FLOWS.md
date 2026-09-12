# USER FLOWS
## Smart Form Auto-Filling System

**Project Title:** Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms

---

## 1. Actors

| Actor | Responsibility |
|---|---|
| End User | Uploads documents, manages profile, reviews recommendations, confirms/corrects values, and reviews forms |
| Chrome Extension | Detects web forms, extracts field context, communicates with the backend, and performs autofill |
| Target Website | Provides the dynamic web form |
| FastAPI Backend | Handles authentication, APIs, document processing requests, and agent execution |
| Document Processing Pipeline | Performs OCR, parsing, extraction, and normalization |
| MongoDB | Stores structured user/profile information, document metadata, facts, provenance, and corrections |
| ChromaDB | Stores document chunks, embeddings, and retrieval metadata |
| LangGraph Agent | Orchestrates classification, routing, retrieval, reasoning, and final response generation |
| LLM | Performs contextual reasoning and candidate-value generation |
| Human-in-the-Loop Module | Requests user confirmation for ambiguous, conflicting, sensitive, or low-confidence values |

---

# 2. High-Level User Journey

```text
User Registration / Login
          |
          v
Upload Personal Documents
          |
          v
OCR + Document Parsing
          |
          v
Entity Extraction + Normalization
          |
          +-----------------------+
          |                       |
          v                       v
     MongoDB                  ChromaDB
 Structured Facts       Chunks + Embeddings
          |                       |
          +-----------+-----------+
                      |
                      v
              Open Web Form
                      |
                      v
          Detect Dynamic Form
                      |
                      v
           Extract Form Fields
                      |
                      v
       Semantic Field Classification
                      |
                      v
               Routing Node
                 /       \
                /         \
               v           v
       Structured       RAG Retrieval
        Retrieval
          \               /
           \             /
            v           v
              LLM Reasoning
                    |
                    v
          Conflict / Confidence Check
                    |
             +------+------+
             |             |
             v             v
        Auto Approved   Human Review
             |             |
             +------+------+
                    |
                    v
              Final Response
                    |
                    v
                Autofill
                    |
                    v
               Verification
                    |
                    v
              User Review
                    |
                    v
              Form Submission
                    |
                    v
             Feedback / Correction
```

---

# 3. Flow 1 — User Registration

### Objective
Create a user account so that personal documents, structured facts, and generated knowledge can be associated with the correct user.

### Main Flow

1. User opens the Smart Form Auto-Filling System.
2. System displays Login and Register options.
3. User selects **Register**.
4. System displays the registration form.
5. User enters:
   - Full Name
   - Email
   - Password
   - Confirm Password
6. Frontend validates the input.
7. Registration request is sent to FastAPI.
8. Backend validates the request.
9. System checks whether the email already exists.

### Decision

**If the email already exists:**

```text
Email Exists
    |
    v
Show "Account Already Exists"
    |
    v
Redirect to Login
```

**If the email does not exist:**

```text
Create User
    |
    v
Create User Profile
    |
    v
Return Registration Success
    |
    v
Login / Dashboard
```

### Postcondition
A user account and associated profile are created.

---

# 4. Flow 2 — User Login

```text
User
  |
  v
Enter Email + Password
  |
  v
Frontend Validation
  |
  v
FastAPI Authentication API
  |
  v
Verify Credentials
  |
  v
Credentials Valid?
  |             |
 NO             YES
  |              |
  v              v
Show Error    Create Session /
              Authentication Token
                     |
                     v
               Load User Profile
                     |
                     v
                 Dashboard
```

The system must ensure that a user can access only their own documents, profile information, structured facts, and retrieval data.

---

# 5. Flow 3 — Personal Document Upload

### Objective
Allow the user to provide documents containing personal information.

### Examples

- Passport
- Aadhaar
- PAN
- Resume
- Certificates
- Salary documents
- Other supported personal documents

### Detailed Flow

```text
Dashboard
    |
    v
Select "Add Document"
    |
    v
Select File
    |
    v
Validate File
    |
    v
Upload to Backend
    |
    v
Store Document / Metadata
    |
    v
Start Processing
```

### Validation

The system checks:

- File type
- File size
- File accessibility
- User ownership
- Duplicate document
- Processing status

### Invalid File

```text
Invalid Document
      |
      v
Show Error
      |
      v
User Selects Another File
```

### Valid File

```text
Valid Document
      |
      v
Processing Queue
      |
      v
OCR + Parsing
```

---

# 6. Flow 4 — Document OCR and Parsing

### Objective
Convert uploaded documents into machine-readable information.

```text
Uploaded Document
       |
       v
Determine Document Type
       |
       v
Document Readable?
      / \
    NO   YES
    |      |
    v      v
   OCR   Direct Parsing
    |      |
    +------+
       |
       v
Extract Text
       |
       v
Extract Tables / Fields / Layout
       |
       v
Normalized Document Representation
```

### Failure Flow

```text
OCR / Parsing Failure
        |
        v
      Retry
        |
        v
Successful?
    /       \
  YES        NO
   |          |
   v          v
Continue   Mark Processing Failed
              |
              v
         Notify User
```

---

# 7. Flow 5 — Entity Extraction and Normalization

After OCR and parsing, the system identifies useful entities and converts them into a normalized representation.

```text
Extracted Text
      |
      v
Entity Extraction
      |
      v
Identify Entities
      |
      v
Normalize Values
      |
      v
Generate Structured Facts
```

### Example

Input document text:

```text
Date of Birth: 15/08/2004
```

Normalized representation:

```text
Concept: date_of_birth
Value: 2004-08-15
Source: Source Document
Confidence: 0.98
```

Possible concepts include:

- Name
- Date of Birth
- Phone
- Email
- Address
- Education
- Organization
- Experience
- Identification information

---

# 8. Flow 6 — Knowledge Storage in MongoDB and ChromaDB

The system uses two complementary storage systems.

## MongoDB

MongoDB stores structured information such as:

```text
User
 |
 +-- Profile
 +-- Structured Facts
 +-- Document Metadata
 +-- Provenance
 +-- Confidence
 +-- User Corrections
```

## ChromaDB

ChromaDB stores:

```text
Document Chunk
 |
 +-- Text
 +-- Embedding
 +-- Document ID
 +-- Page Number
 +-- Language
 +-- Metadata
```

### Processing Flow

```text
Normalized Document
        |
        +--------------------+
        |                    |
        v                    v
Structured Facts      Document Chunks
        |                    |
        v                    v
    MongoDB             Embedding
                             |
                             v
                         ChromaDB
```

---

# 9. Flow 7 — Review and Correct User Profile

### Objective
Allow the user to inspect information extracted from documents.

```text
Dashboard
    |
    v
My Profile
    |
    v
View Extracted Information
    |
    v
Select Category
```

Possible categories:

- Personal Information
- Contact Information
- Address
- Education
- Employment
- Identification
- Other extracted information

### User Actions

The user can:

- View information
- Edit information
- Correct information
- Remove information
- Review source/provenance

### Correction Flow

```text
User Edits Value
      |
      v
Validate Value
      |
      v
Update MongoDB
      |
      v
Record Correction
      |
      v
Use Corrected Value in Future Retrieval
```

---

# 10. Flow 8 — Chrome Extension Authentication

### First-Time Flow

```text
Install Chrome Extension
        |
        v
Open Extension
        |
        v
Login
        |
        v
Authenticate with Backend
        |
        v
Authenticated Session
        |
        v
Extension Ready
```

### If User Is Not Logged In

```text
Web Form Detected
       |
       v
Check Authentication
       |
       v
Not Logged In
       |
       v
Show "Please Login"
       |
       v
User Logs In
       |
       v
Continue Form Processing
```

---

# 11. Flow 9 — Dynamic Web Form Detection

### Objective
Detect form elements on a website and prepare them for semantic understanding.

```text
User Opens Website
       |
       v
Chrome Extension Active
       |
       v
Detect Form Elements
       |
       v
Identify Input Controls
       |
       v
Read Available Field Information
       |
       v
Create Field Objects
```

A Field Object may contain:

```text
Field ID
Field Name
Label
Placeholder
Input Type
DOM Information
Nearby Text
Section
Position
Accessibility Information
```

---

# 12. Flow 10 — Dynamic Form Perception

For complex dynamic forms, multiple contextual signals can be combined.

```text
DOM / HTML
     +
Accessibility Information
     +
Screenshot / Visual Context
     +
Nearby Text
     +
Section Context
     |
     v
Field Object
```

### Example

```html
<label>Permanent Address</label>
<textarea name="address"></textarea>
```

The system should not rely only on the HTML name. It should construct a semantic representation using available context.

```text
Label = Permanent Address
Type = textarea
Section = Personal Information
Context = Nearby form information
```

---

# 13. Flow 11 — Semantic Field Classification

### Objective
Determine the meaning of a web form field.

```text
Field Object
     |
     v
Semantic Classification Agent
     |
     v
Analyze:
- Label
- Placeholder
- DOM
- Input Type
- Context
- Section
     |
     v
Predict Concept
     |
     v
Calculate Confidence
```

### Example

```text
"Enter your father's full name"
              |
              v
Concept = parent_name
              |
              v
Confidence = 0.94
```

Another example:

```text
"Current Residential Address"
              |
              v
Concept = current_address
```

---

# 14. Flow 12 — Classification Confidence Decision

```text
Concept + Confidence
        |
        v
Confidence Check
        |
        v
Acceptable Confidence?
       / \
     YES  NO
      |    |
      v    v
Retrieval  Additional Context /
           Reasoning
                |
                v
          Still Uncertain?
             /       \
           NO         YES
           |           |
           v           v
       Retrieval    Human Review
```

The system should avoid blindly filling fields when the semantic meaning is uncertain.

---

# 15. Flow 13 — LangGraph Agent Orchestration

The LangGraph workflow coordinates the form-understanding and retrieval process.

```text
Form Field
    |
    v
Semantic Classification Agent
    |
    v
Routing Node
    |
    v
Select Retrieval Strategy
```

The routing decision is based on the information required by the field and the appropriate retrieval mechanism.

---

# 16. Flow 14 — Routing Node

```text
Classified Field
      |
      v
Routing Node
      |
      v
Does Structured Information Answer the Field?
       / \
     YES  NO
      |    |
      v    v
Structured RAG Retrieval
Retrieval
```

---

# 17. Flow 15 — Structured Retrieval

Example:

```text
Field:
"Enter your date of birth"
```

Flow:

```text
Concept = date_of_birth
       |
       v
Routing Node
       |
       v
Structured Retrieval Node
       |
       v
Query MongoDB
       |
       v
Retrieve:
- Value
- Confidence
- Source
- Metadata
       |
       v
Return Candidate Value
```

Example candidate:

```text
Concept: date_of_birth
Value: 15/08/2004
Source: Aadhaar
Confidence: 0.98
```

---

# 18. Flow 16 — RAG Retrieval

Some fields require contextual information that cannot be reliably answered from a single structured fact.

Example:

```text
"Describe your responsibilities in your previous organization."
```

Flow:

```text
Field Concept
      |
      v
Routing Node
      |
      v
RAG Retrieval Node
      |
      v
Generate Query / Embedding
      |
      v
Search ChromaDB
      |
      v
Similarity Search
      |
      v
Retrieve Relevant Chunks
      |
      v
Return:
- Chunk
- Document
- Page
- Similarity
- Metadata
```

---

# 19. Flow 17 — LLM Reasoning

```text
Field Meaning
     +
User Context
     +
Retrieved Information
     +
Source Metadata
     +
Confidence
     |
     v
LLM
     |
     v
Candidate Answer
```

The LLM should:

1. Understand the requested field.
2. Examine retrieved information.
3. Respect source and provenance information.
4. Avoid inventing missing information.
5. Identify conflicting values.
6. Generate a candidate recommendation.

---

# 20. Flow 18 — Conflict Detection

Example:

```text
MongoDB:
Address = Pune

Recent Document:
Address = Mumbai
```

Flow:

```text
Retrieve Relevant Facts
        |
        v
Group Values by Concept
        |
        v
Multiple Candidate Values?
       / \
     NO   YES
     |     |
     v     v
Continue  Conflict Resolver
```

The system can consider:

- Source
- Confidence
- Document metadata
- Contextual relevance
- Recency where available
- User-confirmed values

---

# 21. Flow 19 — Automatic Conflict Resolution

```text
Conflict Detected
       |
       v
Compare Candidate Values
       |
       v
Analyze Confidence + Provenance
       |
       v
Clear Winner?
      / \
    YES  NO
     |    |
     v    v
 Select  Human Review
 Value
     |
     v
 Continue
```

If the system cannot confidently determine the correct value, it must request user input.

---

# 22. Flow 20 — Human-in-the-Loop Review

### Trigger Conditions

Human review may be required when:

- Semantic classification confidence is low.
- Multiple values conflict.
- Retrieved information is insufficient.
- The field is sensitive or high-risk.
- The system cannot confidently determine the correct answer.

### User Flow

```text
System Detects Uncertainty
          |
          v
Pause Autofill
          |
          v
Display Field
          |
          v
Display Suggested Value(s)
          |
          v
Display Source / Reason
          |
          v
User Reviews
```

Options:

```text
[Confirm] [Edit] [Reject] [Skip]
```

### Confirm

```text
Confirm
   |
   v
Use Value
   |
   v
Fill Field
```

### Edit

```text
Edit Value
   |
   v
Validate
   |
   v
Use Corrected Value
   |
   v
Record Feedback
```

### Reject

```text
Reject
   |
   v
Do Not Fill
   |
   v
Mark Unresolved
```

### Skip

```text
Skip
   |
   v
Leave Field Empty
   |
   v
Continue
```

---

# 23. Flow 21 — Final Response Node

After retrieval, reasoning, conflict resolution, and human confirmation where required:

```text
Retrieved Information
        +
Reasoning
        +
Conflict Resolution
        +
Human Confirmation
        |
        v
Final Response Node
        |
        v
Validated Field Recommendation
```

A recommendation should conceptually contain:

```text
Field
Recommended Value
Confidence
Source / Provenance
Reason
Action
```

---

# 24. Flow 22 — Browser Autofill

```text
Validated Recommendation
        |
        v
Chrome Extension
        |
        v
Locate Corresponding Field
        |
        v
Check Field Compatibility
        |
        v
Insert Value
        |
        v
Trigger Required Input Events
        |
        v
Update Web Form
```

Example:

```text
Website Field:
"First Name"

Semantic Concept:
first_name

Stored Value:
User's first name

        |
        v

Chrome Extension
        |
        v

Web Form Field Filled
```

---

# 25. Flow 23 — Autofill Verification

Autofill should be verified after writing the value.

```text
Field Filled
     |
     v
Verify DOM Value
     |
     v
Verify UI State
     |
     v
Value Accepted?
     / \
   YES   NO
    |     |
    v     v
Verified Retry / Re-detect
          |
          v
       Successful?
         / \
       YES  NO
       |     |
       v     v
    Verified  Mark Failed
                 |
                 v
             User Review
```

---

# 26. Flow 24 — Complete Form Processing

```text
Form Detected
      |
      v
Extract Fields
      |
      v
Classify Field
      |
      v
Retrieve Value
      |
      v
Resolve Conflict
      |
      v
Human Review if Required
      |
      v
Fill Field
      |
      v
Verify Field
      |
      v
More Fields?
     / \
   YES  NO
    |    |
    v    v
Next   Form Review
Field
```

---

# 27. Flow 25 — Final Form Review

After all fields are processed:

```text
All Fields Processed
        |
        v
Generate Form Summary
        |
        v
Show:
- Filled Fields
- Unfilled Fields
- Low-Confidence Fields
- User-Corrected Fields
- Conflicts
        |
        v
User Reviews
```

The user can:

- Edit a value
- Clear a value
- Refill a field
- Ignore a recommendation
- Continue to website submission

---

# 28. Flow 26 — User Submission

The system should distinguish between **autofilling** and **final submission**.

```text
Form Filled
    |
    v
User Reviews
    |
    v
User Clicks Website Submit
    |
    v
Website Validates Form
    |
    v
Submission Successful?
       / \
     YES  NO
      |    |
      v    v
   Success Website Error
           |
           v
      Identify Field
           |
           v
       User Corrects
           |
           v
        Re-verify
```

The final submission should remain under user control unless the project explicitly defines automated submission as a separate approved feature.

---

# 29. Flow 27 — User Correction and Feedback

```text
System Recommendation
        |
        v
User Changes Value
        |
        v
Detect Correction
        |
        v
Store Feedback
        |
        v
Associate With:
- Field Concept
- Original Value
- Corrected Value
- Context
        |
        v
Use Feedback in Future Recommendations
```

---

# 30. Flow 28 — Multiple Documents Containing the Same Information

Example:

```text
Resume       -> Phone = 9876543210
Aadhaar      -> Phone = 9876543210
Application  -> Phone = 9123456789
```

Flow:

```text
Retrieve All Relevant Facts
          |
          v
Group by Concept
          |
          v
Multiple Values?
        /   \
      NO     YES
      |       |
      v       v
 Continue  Compare:
           - Provenance
           - Confidence
           - Context
           - Recency
              |
              v
          Consistent?
           /    \
         YES     NO
          |       |
          v       v
       Select   Conflict
       Value    Resolution
                  |
                  v
              Human Review
              if needed
```

---

# 31. Flow 29 — Missing Information

Example:

```text
Form Field:
"Passport Number"
        |
        v
Semantic Classification
        |
        v
MongoDB Lookup
        |
        v
No Result
        |
        v
ChromaDB Retrieval
        |
        v
No Relevant Result
        |
        v
Information Missing
```

The system should not invent a value.

```text
Missing Information
        |
        v
Show "Information Not Found"
        |
        v
User Enters Value
        |
        v
Optional Confirmation
        |
        v
Fill Field
```

---

# 32. Flow 30 — Low Classification Confidence

```text
Field
 |
 v
Semantic Classifier
 |
 v
Confidence = 0.42
 |
 v
Below Threshold
 |
 v
Additional Context Analysis
 |
 v
Confidence Improved?
      / \
    YES  NO
     |    |
     v    v
Retrieval Human Review
```

---

# 33. Flow 31 — Sensitive / High-Risk Field

For sensitive or consequential information:

```text
Field Detected
      |
      v
Sensitive / High-Risk?
      |
     YES
      |
      v
Retrieve Candidate
      |
      v
Mandatory Human Confirmation
      |
      v
User Confirms?
     / \
   YES  NO
    |    |
    v    v
  Fill  Do Not Fill
```

---

# 34. Flow 32 — User Logout

```text
Dashboard
    |
    v
Logout
    |
    v
Invalidate Session
    |
    v
Clear Extension Authentication State
    |
    v
Return to Login
```

Logout does not delete stored documents or profile information.

---

# 35. Flow 33 — Delete Document

```text
My Documents
     |
     v
Select Document
     |
     v
Delete
     |
     v
Confirmation
     |
     v
User Confirms
     |
     v
Delete Original Document
     |
     +-------------------------+
     |                         |
     v                         v
Delete Associated        Delete Associated
Structured Facts        ChromaDB Chunks
     |                         |
     +-------------+-----------+
                   |
                   v
              Update Profile
                   |
                   v
              Record Deletion
```

Deletion must account for both structured and vector representations of personal information.

---

# 36. Flow 34 — Complete End-to-End Job Application Scenario

### Scenario

A user wants to fill a job application using information from their resume and personal documents.

```text
1. User logs into the system
          |
          v
2. User has uploaded Resume + Personal Documents
          |
          v
3. Documents are processed
          |
          v
4. OCR / Parsing
          |
          v
5. Entity Extraction
          |
          v
6. Structured Facts -> MongoDB
          |
          v
7. Document Chunks + Embeddings -> ChromaDB
          |
          v
8. User opens Job Application Website
          |
          v
9. Chrome Extension detects form
          |
          v
10. Form fields are extracted
          |
          v
11. Semantic Classification Agent classifies fields
          |
          v
12. Routing Node chooses retrieval method
          |
          +-------------------+
          |                   |
          v                   v
    MongoDB Retrieval    ChromaDB RAG
          |                   |
          +---------+---------+
                    |
                    v
13. LLM reasons over retrieved information
                    |
                    v
14. Conflict detected?
              /           \
            NO             YES
            |               |
            v               v
         Continue      Resolve Conflict
                           |
                           v
                     Can Resolve?
                      /       \
                    YES        NO
                    |           |
                    v           v
                 Continue    Human Review
                                |
                                v
15. Confidence acceptable?
              /          \
            YES           NO
             |             |
             v             v
         Continue      Human Review
             |             |
             +------+------+
                    |
                    v
16. Final Response Node
                    |
                    v
17. Chrome Extension fills fields
                    |
                    v
18. Verification performed
                    |
                    v
19. Failed fields shown to user
                    |
                    v
20. User reviews completed form
                    |
                    v
21. User corrects values if required
                    |
                    v
22. User submits form
                    |
                    v
23. Completion outcome recorded
                    |
                    v
24. User corrections become feedback
```

---

# 37. Complete Exception Flow

The system should have a defined path for failures.

```text
Request
  |
  v
Process Request
  |
  v
Success?
 / \
NO  YES
|    |
v    v
Identify  Continue
Error
 |
 +------------------+
 |        |         |
 v        v         v
Retry   User      Skip /
        Action    Stop
 |
 v
Successful?
 / \
YES  NO
 |    |
 v    v
Continue Log Failure
          |
          v
       Notify User
```

Potential failures include:

- Invalid document
- OCR failure
- Extraction failure
- Backend unavailable
- Authentication failure
- Classification failure
- Retrieval failure
- Missing information
- Conflicting information
- Browser field changed
- Autofill failure
- Verification failure
- Website validation failure

---

# 38. Overall System State Model

```text
UNAUTHENTICATED
       |
       v
AUTHENTICATED
       |
       v
DOCUMENT_READY
       |
       v
PROCESSING
       |
       v
KNOWLEDGE_READY
       |
       v
FORM_DETECTED
       |
       v
FIELDS_EXTRACTED
       |
       v
CLASSIFYING
       |
       v
ROUTING
       |
       v
RETRIEVING
       |
       v
REASONING
       |
       +----------------+
       |                |
       v                v
AUTO_APPROVED      HUMAN_REVIEW
       |                |
       +--------+-------+
                |
                v
          READY_TO_FILL
                |
                v
             FILLING
                |
                v
            VERIFYING
             /      \
            /        \
           v          v
       VERIFIED     FAILED
           |          |
           |          v
           |     RETRY / REVIEW
           |          |
           +----------+
                |
                v
          FORM_READY
                |
                v
        USER_SUBMISSION
                |
                v
           COMPLETED
```

---

# 39. Primary User Flows

For the final capstone documentation, the complete system can be grouped into the following primary flows:

1. **User Registration and Login**
2. **Personal Document Upload**
3. **Document OCR, Extraction and Normalization**
4. **MongoDB and ChromaDB Knowledge Creation**
5. **Profile Review and Correction**
6. **Chrome Extension Authentication**
7. **Dynamic Web Form Detection**
8. **Semantic Field Classification and Routing**
9. **Structured Retrieval / RAG Retrieval**
10. **LLM Reasoning, Conflict Resolution and Human-in-the-Loop**
11. **Autofill and Verification**
12. **Feedback, Correction and Continuous Improvement**

---

# 40. User Flow Design Principles

The system should follow these principles throughout the flows:

- **Do not hallucinate personal information.**
- **Do not automatically fill uncertain fields without an appropriate confidence/review mechanism.**
- **Preserve source and provenance information.**
- **Keep the user in control of sensitive or consequential information.**
- **Verify values after browser autofill.**
- **Treat webpage content as potentially untrusted input.**
- **Maintain separation between structured retrieval and contextual RAG retrieval.**
- **Record user corrections as feedback.**
- **Maintain user-level isolation for documents and personal information.**
- **Allow the user to review the final form before submission.**

---

## 41. End-to-End Summary

```text
DOCUMENT SIDE

Documents
   ↓
OCR / Parsing
   ↓
Extraction
   ↓
Normalization
   ↓
+-----------------------+
|                       |
v                       v
MongoDB              ChromaDB
Structured Facts     Vectors + Chunks
|                       |
+-----------+-----------+
            |
            v

FORM SIDE

Dynamic Web Form
       ↓
Form Detection
       ↓
Field Objects
       ↓
Semantic Classification
       ↓
Routing
   /           \
  v             v
MongoDB      ChromaDB
  |             |
  +------ + ----+
         |
         v
    LLM Reasoning
         |
         v
Conflict / Confidence
         |
    +----+----+
    |         |
    v         v
Automatic   Human
Decision    Review
    |         |
    +----+----+
         |
         v
Final Response
         |
         v
Browser Autofill
         |
         v
Verification
         |
         v
User Review
         |
         v
Submission
         |
         v
Feedback
```

**End of USER_FLOWS.md**
