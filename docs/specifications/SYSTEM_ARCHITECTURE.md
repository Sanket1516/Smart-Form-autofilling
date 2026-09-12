# SYSTEM ARCHITECTURE
## Smart Form Auto-Filling System

**Project Title:** Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms

---

## 1. Architecture Overview

The Smart Form Auto-Filling System is an agentic AI-based architecture designed to understand dynamic web forms semantically and provide context-aware recommendations using information extracted from the user's documents.

The architecture is divided into two major processing sides:

1. **Document and Knowledge Preparation Pipeline**
2. **Dynamic Web Form Understanding and Autofill Pipeline**

The two sides meet through the knowledge layer consisting of:

- **MongoDB** for structured information and metadata.
- **ChromaDB** for vector embeddings and document chunks.

The web-form processing workflow is orchestrated using **LangGraph**, with FastAPI providing backend APIs and a Chrome Extension providing browser-level interaction.

---

# 2. High-Level Architecture

```text
                         SMART FORM AUTO-FILLING SYSTEM
                                      |
             +------------------------+------------------------+
             |                                                 |
             v                                                 v
   DOCUMENT PROCESSING SIDE                         WEB FORM PROCESSING SIDE
             |                                                 |
             v                                                 v
      Document Upload                                  User Opens Website
             |                                                 |
             v                                                 v
       OCR / Parsing                              Chrome Extension (MV3)
             |                                                 |
             v                                                 v
   Entity Extraction /                             Dynamic Form Detection
      Normalization                                          |
             |                                                 v
       +-----+-----+                                  Field Object Builder
       |           |                                          |
       v           v                                          v
   Structured   Document                             Semantic Classification
      Facts      Chunks                                      Agent
       |           |                                          |
       v           v                                          v
    MongoDB    Embeddings                                Routing Node
                   |                                  /             \
                   v                                 v               v
               ChromaDB                       Structured         RAG Retrieval
                                               Retrieval             |
                                                  |                  |
                                                  +--------+---------+
                                                           |
                                                           v
                                                    LLM Reasoning
                                                           |
                                                           v
                                              Conflict / Confidence Check
                                                           |
                                                +----------+----------+
                                                |                     |
                                                v                     v
                                           Auto Approved         Human Review
                                                |                     |
                                                +----------+----------+
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
                                                     Submission
```

---

# 3. Architectural Layers

The system can be understood through the following layers:

```text
+---------------------------------------------------------------+
|                    PRESENTATION LAYER                         |
| React.js Web Application + Chrome Extension (Manifest V3)     |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|                    API / SERVICE LAYER                        |
|                         FastAPI                               |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|                  AGENT ORCHESTRATION LAYER                   |
|                       LangGraph                              |
|                                                               |
| Semantic Classification → Routing → Retrieval → Reasoning    |
| → Conflict Handling → Final Response                         |
+---------------------------------------------------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+-----------------------------+   +-----------------------------+
|      KNOWLEDGE LAYER        |   |    DOCUMENT PROCESSING      |
|                             |   |                             |
| MongoDB                     |   | OCR / Parsing               |
| ChromaDB                    |   | Extraction                  |
|                             |   | Normalization                |
+-----------------------------+   +-----------------------------+
              |                               |
              +---------------+---------------+
                              |
                              v
+---------------------------------------------------------------+
|                    EXTERNAL AI SERVICES                       |
|             Embedding Model + LLM Provider                    |
+---------------------------------------------------------------+
```

---

# 4. Presentation Layer

## 4.1 React.js Web Application

The React.js application provides the user-facing interface.

### Responsibilities

- User registration
- User login
- Dashboard
- Document upload
- Document status
- Profile information
- Extracted facts
- User corrections
- Recommendation review
- System status
- Authentication management

### Main Interfaces

```text
React Application
      |
      +-- Login
      +-- Registration
      +-- Dashboard
      +-- Documents
      +-- Profile
      +-- Recommendations
      +-- Review / Confirmation
      +-- Settings
```

---

# 5. Chrome Extension Layer

The Chrome Extension is responsible for interaction with live web forms.

The project uses **Chrome Extension Manifest V3**.

## Responsibilities

- Detect forms on web pages.
- Detect input fields.
- Extract field context.
- Collect DOM-related information.
- Communicate with the backend.
- Receive field recommendations.
- Fill approved values.
- Verify filled values.
- Display review prompts to the user.

### Extension Flow

```text
Web Page
   |
   v
Content Script
   |
   v
Detect Form Elements
   |
   v
Create Field Information
   |
   v
Extension Background / Service Worker
   |
   v
Backend API
```

---

# 6. API / Backend Layer

## FastAPI

FastAPI acts as the backend service layer between the frontend, browser extension, processing modules, databases, and agent workflow.

### Main Responsibilities

- Authentication APIs
- User APIs
- Document APIs
- Profile APIs
- Form-processing APIs
- Agent execution APIs
- Retrieval APIs
- Recommendation APIs
- Feedback APIs
- Error handling

### Simplified Flow

```text
React / Chrome Extension
          |
          v
       FastAPI
          |
    +-----+-----+
    |           |
    v           v
Document     Agent Workflow
Processing     Execution
```

---

# 7. Document Processing Architecture

The document-processing side converts user-provided documents into reusable knowledge.

```text
Document
   |
   v
Upload
   |
   v
File Validation
   |
   v
OCR / Parsing
   |
   v
Text + Tables + Fields + Layout
   |
   v
Entity Extraction
   |
   v
Normalization
   |
   +-------------------------+
   |                         |
   v                         v
Structured Facts       Document Chunks
   |                         |
   v                         v
MongoDB                 Embeddings
                             |
                             v
                         ChromaDB
```

---

# 8. OCR and Document Parsing

The document-processing architecture uses OCR and parsing technologies specified for the project.

### OCR

**PaddleOCR** can be used to extract text from scanned or image-based documents.

### Parsing

**pdfplumber** can be used for text and table extraction from suitable PDF documents.

### Supporting Processing

**OpenCV** can support image preprocessing when required.

```text
Input Document
      |
      v
Image / PDF Processing
      |
      +----------+
      |          |
      v          v
   PaddleOCR   pdfplumber
      |          |
      +----+-----+
           |
           v
     Normalized Text
```

---

# 9. Entity Extraction and Normalization Layer

After OCR/parsing, extracted content is transformed into structured concepts.

```text
Raw Extracted Content
        |
        v
Entity Extraction
        |
        v
Identify Concepts
        |
        v
Normalize Values
        |
        v
Structured Fact Objects
```

Example:

```text
Document:
"Date of Birth: 15/08/2004"

             ↓

Structured Fact:

Concept: date_of_birth
Value: 2004-08-15
Source: Document ID
Confidence: 0.98
```

---

# 10. Knowledge Layer

The knowledge layer contains two complementary storage systems.

## 10.1 MongoDB

MongoDB is the structured database.

### Stores

- User information
- Profile information
- Document metadata
- Structured facts
- Source/provenance information
- Confidence values
- User corrections
- Processing status
- Recommendation records
- Feedback

### Conceptual Structure

```text
MongoDB
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
```

---

# 11. ChromaDB

ChromaDB is the vector database used for semantic document retrieval.

### Stores

- Document chunks
- Embeddings
- Document IDs
- Page numbers
- Language information
- Metadata
- Retrieval-related information

### Flow

```text
Document Chunk
      |
      v
Embedding Model
      |
      v
Vector Embedding
      |
      v
ChromaDB
```

---

# 12. MongoDB + ChromaDB Relationship

The two databases serve different retrieval requirements.

```text
                     USER KNOWLEDGE
                           |
              +------------+------------+
              |                         |
              v                         v
        STRUCTURED DATA          SEMANTIC CONTENT
              |                         |
              v                         v
          MongoDB                   ChromaDB
              |                         |
              |                         |
              v                         v
     Exact / structured          Similarity /
     fact retrieval              contextual retrieval
```

The databases are complementary rather than alternatives.

---

# 13. Dynamic Web Form Perception Layer

When the user opens a website, the Chrome Extension observes the page and extracts relevant form information.

### Input Sources

- DOM / HTML
- Field labels
- Input types
- Placeholder text
- Nearby text
- Section context
- Accessibility information
- Visual context where supported

```text
                 Web Page
                    |
        +-----------+-----------+
        |           |           |
       DOM       Context    Accessibility
        |           |           |
        +-----------+-----------+
                    |
                    v
              Field Object
```

---

# 14. Field Object Builder

The extracted form information is represented as a Field Object.

### Conceptual Field Object

```text
Field Object
 |
 +-- field_id
 +-- field_name
 +-- label
 +-- placeholder
 +-- input_type
 +-- DOM_context
 +-- nearby_text
 +-- section
 +-- accessibility_context
 +-- position
```

Example:

```text
Field:
  label = "Permanent Address"
  type = textarea
  section = Personal Information
  name = address
```

This object is passed to the semantic classification component.

---

# 15. Semantic Classification Agent

The Semantic Classification Agent determines the meaning of the field.

```text
Field Object
      |
      v
Semantic Classification Agent
      |
      +-- Label Analysis
      +-- Placeholder Analysis
      +-- DOM Analysis
      +-- Context Analysis
      +-- Section Analysis
      |
      v
Universal / Project Field Concept
      |
      v
Confidence Score
```

Example:

```text
Input:
"Enter your father's full name"

Output:
Concept = parent_name
Confidence = 0.94
```

---

# 16. LangGraph Agent Orchestration Layer

LangGraph coordinates the stateful agent workflow.

### Main Nodes

```text
                    START
                      |
                      v
        Semantic Classification Agent
                      |
                      v
                Routing Node
                 /          \
                /            \
               v              v
      Structured Retrieval   RAG Retrieval
               \              /
                \            /
                 v          v
                  LLM Reasoning
                       |
                       v
              Conflict / Confidence
                       |
                       v
                Final Response
                       |
                      END
```

The workflow can branch depending on field semantics, available information, confidence, and conflict conditions.

---

# 17. Routing Node

The Routing Node selects the retrieval path required by the classified field.

```text
Classified Field
      |
      v
Routing Node
      |
      +--------------------------+
      |                          |
      v                          v
Structured Information       Contextual Information
      |                          |
      v                          v
Structured Retrieval          RAG Retrieval
```

The routing decision is based on the retrieval requirement of the field, not on treating documents as simply "structured" or "unstructured."

---

# 18. Structured Retrieval Node

For fields that correspond to known structured facts:

```text
Field Concept
      |
      v
Structured Retrieval Node
      |
      v
MongoDB Query
      |
      v
Candidate Fact
      |
      v
Value + Confidence + Provenance
```

Example:

```text
Concept = date_of_birth

MongoDB
   |
   v
date_of_birth = 2004-08-15
   |
   v
Return Candidate
```

---

# 19. RAG Retrieval Node

For contextual or document-dependent fields:

```text
Field Concept / Query
       |
       v
Embedding
       |
       v
ChromaDB Similarity Search
       |
       v
Relevant Document Chunks
       |
       v
Metadata + Provenance
       |
       v
LLM Reasoning
```

Example:

```text
Field:
"Describe your previous work responsibilities"

       |
       v

ChromaDB retrieves relevant resume chunks

       |
       v

LLM generates contextual recommendation
```

---

# 20. LLM Reasoning Layer

The LLM receives contextual information from the agent workflow.

### Inputs

- Field concept
- Field context
- User context
- Retrieved structured facts
- Retrieved document chunks
- Confidence scores
- Provenance
- Conflict information

### Output

- Candidate value
- Explanation/reasoning information
- Confidence
- Conflict indication
- Recommended action

```text
Field Context
      +
Retrieved Knowledge
      +
Provenance
      +
Confidence
      |
      v
     LLM
      |
      v
Candidate Recommendation
```

The system must not fabricate personal information when relevant information is unavailable.

---

# 21. Conflict Resolution Architecture

Conflicts can occur when multiple documents or sources provide different values for the same concept.

```text
Candidate Values
      |
      v
Conflict Detection
      |
      v
Multiple Values?
     / \
   NO   YES
   |     |
   v     v
Continue Conflict Resolver
          |
          v
   Compare:
   - Provenance
   - Confidence
   - Context
   - Recency where available
          |
          v
     Clear Winner?
       /       \
     YES        NO
      |          |
      v          v
 Select Value  Human Review
```

---

# 22. Human-in-the-Loop Layer

Human review acts as a safety and confidence gate.

### Trigger Conditions

- Low semantic classification confidence
- Conflicting values
- Insufficient retrieval
- Sensitive/high-risk field
- Uncertain LLM recommendation

### Flow

```text
Candidate Recommendation
          |
          v
Confidence / Risk Check
          |
          v
Human Review Required?
       /       \
     NO         YES
     |           |
     v           v
Continue    Show User:
            - Field
            - Suggested Value
            - Source
            - Reason
                 |
                 v
            User Decision
           /    |    |    \
          v     v    v     v
       Confirm Edit Reject Skip
```

---

# 23. Final Response Node

The Final Response Node converts the result of the agent workflow into a validated recommendation for the browser extension.

```text
Retrieval
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
Validated Recommendation
```

Conceptually:

```text
{
    field,
    concept,
    recommended_value,
    confidence,
    provenance,
    action
}
```

---

# 24. Browser Autofill Layer

The Chrome Extension receives validated recommendations.

```text
Final Recommendation
        |
        v
Chrome Extension
        |
        v
Locate Matching DOM Field
        |
        v
Compatibility Check
        |
        v
Insert Value
        |
        v
Trigger Required Events
        |
        v
Web Form Updated
```

The extension should fill only approved/validated values.

---

# 25. Verification Layer

After autofill, the system verifies that the intended value was actually applied.

```text
Field Filled
     |
     v
DOM Verification
     |
     v
UI State Verification
     |
     v
Value Correct?
    / \
  YES  NO
   |    |
   v    v
Verified Retry / Re-detect
        |
        v
     Success?
      /   \
    YES    NO
     |      |
     v      v
 Verified  User Review
```

---

# 26. Feedback and Adaptation Layer

The system records user corrections and feedback.

```text
Recommendation
      |
      v
User Correction
      |
      v
Capture Feedback
      |
      v
Store:
- Original Recommendation
- Corrected Value
- Field Concept
- Context
- User Decision
      |
      v
Future Improvement
```

This feedback can support future refinement of classification and recommendation behavior.

---

# 27. End-to-End Architecture Flow

```text
                         USER
                           |
              +------------+------------+
              |                         |
              v                         v
       React Web App              Chrome Extension
              |                         |
              +------------+------------+
                           |
                           v
                         FastAPI
                           |
        +------------------+------------------+
        |                                     |
        v                                     v
Document Processing                  LangGraph Agent
        |                                     |
        v                                     v
OCR / Parsing                    Semantic Classification
        |                                     |
        v                                     v
Extraction                             Routing Node
        |                              /           \
        v                             v             v
Normalization                 Structured         RAG
        |                     Retrieval          Retrieval
        |                         |                 |
        |                         v                 v
        |                     MongoDB           ChromaDB
        |                         \                 /
        |                          \               /
        |                           v             v
        |                          LLM Reasoning
        |                               |
        |                               v
        |                      Conflict / Confidence
        |                               |
        |                         +-----+-----+
        |                         |           |
        |                         v           v
        |                    Auto Approved  HITL
        |                         |           |
        |                         +-----+-----+
        |                               |
        |                               v
        |                         Final Response
        |                               |
        |                               v
        |                            Autofill
        |                               |
        |                               v
        |                           Verification
        |                               |
        +-------------------------------+
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

---

# 28. Component Responsibilities

| Component | Primary Responsibility |
|---|---|
| React.js | User-facing web interface |
| Chrome Extension | Browser interaction and autofill |
| FastAPI | Backend APIs and service coordination |
| OCR Module | Text extraction from scanned documents |
| Parsing Module | Text/table/layout extraction |
| Extraction Module | Entity and field information extraction |
| Normalization Module | Standardization of extracted values |
| MongoDB | Structured facts and application metadata |
| Embedding Model | Converts document chunks/queries to vectors |
| ChromaDB | Vector storage and semantic retrieval |
| Semantic Classification Agent | Determines field meaning |
| Routing Node | Chooses retrieval path |
| Structured Retrieval Node | Retrieves structured facts from MongoDB |
| RAG Retrieval Node | Retrieves contextual document chunks from ChromaDB |
| LLM | Contextual reasoning and recommendation generation |
| Conflict Resolver | Handles multiple competing candidate values |
| HITL Module | Obtains human confirmation when required |
| Final Response Node | Produces validated recommendation |
| Autofill Module | Writes approved values to browser fields |
| Verification Module | Confirms successful field filling |
| Feedback Module | Records user corrections and decisions |

---

# 29. Data Flow

## Document Data Flow

```text
User Document
     |
     v
OCR / Parsing
     |
     v
Extracted Content
     |
     v
Entity Extraction
     |
     v
Normalization
     |
     +-----------------------+
     |                       |
     v                       v
Structured Facts       Document Chunks
     |                       |
     v                       v
 MongoDB                Embedding Model
                             |
                             v
                         ChromaDB
```

## Form Data Flow

```text
Web Form
   |
   v
Chrome Extension
   |
   v
Field Object
   |
   v
Semantic Classification
   |
   v
Routing
   |
   +---------------------+
   |                     |
   v                     v
MongoDB              ChromaDB
   |                     |
   +----------+----------+
              |
              v
         LLM Reasoning
              |
              v
      Recommendation
              |
              v
        Human Review
        if required
              |
              v
           Autofill
              |
              v
         Verification
```

---

# 30. Security Architecture

Security is required because the system processes personal information.

### Security Principles

- User authentication
- User-level data isolation
- Authorization for document/profile access
- Secure API communication
- Protected document storage
- Controlled browser-extension permissions
- Provenance tracking
- Human confirmation for high-risk fields
- Validation of model outputs
- Logging of important actions

### Untrusted Web Content

Web pages should be treated as untrusted input.

```text
Web Page Content
       |
       v
Sanitize / Validate Context
       |
       v
Semantic Processing
       |
       v
Do Not Treat Page Instructions as System Instructions
```

This is particularly important for protecting the agent against prompt injection or malicious webpage content.

---

# 31. Error Handling Architecture

```text
Component Failure
       |
       v
Detect Error
       |
       v
Classify Error
       |
       +--------------------+
       |         |          |
       v         v          v
     Retry    User Review  Fail Safely
       |         |          |
       +---------+----------+
                 |
                 v
             Log Event
                 |
                 v
             Notify User
```

Possible failure sources:

- OCR failure
- Parsing failure
- Database unavailable
- Embedding failure
- Retrieval failure
- LLM failure
- Classification failure
- Browser interaction failure
- Verification failure
- Website validation failure

---

# 32. Deployment Architecture

A conceptual deployment can be organized as follows:

```text
+------------------------+
| User Computer          |
|                        |
| Chrome Browser         |
| + Chrome Extension     |
| + Web Application      |
+-----------+------------+
            |
            | HTTPS
            v
+------------------------+
| Backend Server         |
|                        |
| FastAPI                |
| LangGraph              |
| Processing Services    |
+-----------+------------+
            |
       +----+----+
       |         |
       v         v
+----------+  +----------+
| MongoDB  |  | ChromaDB |
+----------+  +----------+
       |
       |
       v
+------------------------+
| AI Services            |
|                        |
| Embedding Model        |
| LLM Provider           |
+------------------------+
```

Docker can be used to package application services and maintain a consistent development/deployment environment.

---

# 33. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React.js |
| Browser Integration | Chrome Extension Manifest V3 |
| Backend | FastAPI |
| Agent Orchestration | LangGraph |
| Agent Framework | LangChain |
| Structured Database | MongoDB |
| Vector Database | ChromaDB |
| OCR | PaddleOCR |
| PDF Processing | pdfplumber |
| Image Processing | OpenCV |
| Embeddings | BGE-M3 / project-selected embedding model |
| LLM | GPT-class / Llama / Qwen-class model |
| Containerization | Docker |
| Development | VS Code |
| Version Control | Git / GitHub |
| Supported OS | Windows 11 / Ubuntu Linux |

---

# 34. Architecture Sequence

The complete logical sequence is:

```text
1. User Authentication
          |
2. Document Upload
          |
3. OCR / Parsing
          |
4. Entity Extraction
          |
5. Normalization
          |
6. MongoDB + ChromaDB Knowledge Creation
          |
7. User Opens Dynamic Web Form
          |
8. Chrome Extension Detects Form
          |
9. Field Object Creation
          |
10. Semantic Field Classification
          |
11. Routing
          |
12. Structured Retrieval / RAG Retrieval
          |
13. LLM Reasoning
          |
14. Conflict Resolution
          |
15. Confidence / Risk Check
          |
16. Human Review if Required
          |
17. Final Response
          |
18. Browser Autofill
          |
19. Verification
          |
20. User Review
          |
21. Form Submission
          |
22. Feedback / Correction Capture
```

---

# 35. Architectural Principles

The system architecture follows these principles:

1. **Separation of concerns** — document processing, knowledge storage, form understanding, reasoning, and browser interaction are separated.
2. **Agentic orchestration** — LangGraph coordinates stateful processing and conditional routing.
3. **Semantic understanding** — fields are understood by meaning and context rather than only HTML names.
4. **Hybrid retrieval** — MongoDB handles structured facts while ChromaDB handles semantic document retrieval.
5. **Human-in-the-loop safety** — ambiguous, conflicting, sensitive, or high-risk cases can require user confirmation.
6. **Provenance-aware recommendations** — candidate values should retain their source information.
7. **Verification** — browser actions are verified after execution.
8. **Feedback-driven improvement** — user corrections are recorded for future system improvement.
9. **Privacy and isolation** — personal information must remain associated with the authorized user.
10. **Safe failure** — missing or uncertain information should not be fabricated.

---

# 36. Final Architecture Summary

```text
                    SMART FORM AUTO-FILLING SYSTEM

             +---------------------------------------+
             |              USER LAYER               |
             | React.js + Chrome Extension MV3       |
             +-------------------+-------------------+
                                 |
                                 v
             +---------------------------------------+
             |             FASTAPI LAYER              |
             | Authentication + APIs + Services       |
             +-------------------+-------------------+
                                 |
              +------------------+------------------+
              |                                     |
              v                                     v
     DOCUMENT PROCESSING                    LANGGRAPH AGENT
              |                                     |
       OCR / Parsing                    Semantic Classification
              |                                     |
        Extraction                           Routing Node
              |                              /         \
       Normalization                        /           \
              |                            v             v
              +-----> MongoDB       Structured        RAG
                       |             Retrieval       Retrieval
                       |                 |               |
                       |                 +-------+-------+
                       |                         |
                       |                         v
                       |                    LLM Reasoning
                       |                         |
                       |                         v
                       |                Conflict Resolution
                       |                         |
                       |                  Human-in-the-Loop
                       |                         |
                       +-------------------------+
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
                                            Submission
                                                 |
                                                 v
                                             Feedback
                                                 |
                                                 v
                                        Future Improvement
```

**End of SYSTEM_ARCHITECTURE.md**
