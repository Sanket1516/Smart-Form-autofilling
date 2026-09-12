# API SPECIFICATION DOCUMENT
## Smart Form Auto-Filling System

**Project Title:** Agentic AI Framework for Context-Aware Semantic Understanding and Intelligent Assistance of Dynamic Web Forms

---

# 1. Document Purpose

This document specifies the REST API contract for the Smart Form Auto-Filling System.

The API is implemented using **FastAPI** and acts as the service interface between:

- React.js web application
- Chrome Extension (Manifest V3)
- Document processing pipeline
- LangGraph agent workflow
- MongoDB
- ChromaDB
- LLM and embedding services

The API supports the complete application lifecycle:

```text
Authentication
     ↓
Document Management
     ↓
Document Processing
     ↓
Profile / Structured Knowledge
     ↓
Dynamic Form Understanding
     ↓
Semantic Classification
     ↓
Retrieval
     ↓
LLM Reasoning
     ↓
Conflict Resolution / Human Review
     ↓
Recommendations
     ↓
Autofill / Verification
     ↓
Feedback
```

---

# 2. API Design Principles

The API follows these principles:

1. REST-style HTTP endpoints.
2. JSON request/response bodies unless file upload is required.
3. Authentication for protected resources.
4. User-level authorization and data isolation.
5. Consistent response structures.
6. Explicit processing states.
7. Validation before database operations.
8. No hallucinated personal information.
9. Human confirmation for ambiguous or high-risk recommendations.
10. Error responses must be machine-readable.
11. Sensitive information should not unnecessarily appear in logs.
12. API contracts should remain independent of internal database implementation where possible.

---

# 3. Base URL

Development:

```text
http://localhost:8000/api/v1
```

Production:

```text
https://<backend-domain>/api/v1
```

The production domain is deployment-specific.

---

# 4. Content Types

## JSON APIs

```http
Content-Type: application/json
```

## File Upload

```http
Content-Type: multipart/form-data
```

## Response

```http
Content-Type: application/json
```

---

# 5. Authentication

Protected APIs require an authenticated user.

Example:

```http
Authorization: Bearer <access_token>
```

The exact token mechanism can be implemented using the authentication strategy selected for the project.

---

# 6. Common Response Structure

## Successful Response

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully"
}
```

## Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {}
  }
}
```

---

# 7. HTTP Status Codes

| Code | Meaning |
|---:|---|
| 200 | Successful request |
| 201 | Resource created |
| 202 | Request accepted for asynchronous processing |
| 204 | Successful request with no response body |
| 400 | Bad request |
| 401 | Authentication required/failed |
| 403 | Access denied |
| 404 | Resource not found |
| 409 | Conflict |
| 413 | Payload too large |
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 502 | External AI/service failure |
| 503 | Service unavailable |

---

# 8. Authentication APIs

## 8.1 Register User

### Endpoint

```http
POST /auth/register
```

### Request

```json
{
  "full_name": "Sanket Mali",
  "email": "user@example.com",
  "password": "StrongPassword123",
  "confirm_password": "StrongPassword123"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "user_id": "USER_ID",
    "full_name": "Sanket Mali",
    "email": "user@example.com"
  },
  "message": "User registered successfully"
}
```

### Errors

```text
400 VALIDATION_ERROR
409 EMAIL_ALREADY_EXISTS
```

---

# 9. Login

### Endpoint

```http
POST /auth/login
```

### Request

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "access_token": "<token>",
    "token_type": "bearer",
    "user": {
      "user_id": "USER_ID",
      "full_name": "Sanket Mali",
      "email": "user@example.com"
    }
  },
  "message": "Login successful"
}
```

### Errors

```text
401 INVALID_CREDENTIALS
422 VALIDATION_ERROR
```

---

# 10. Get Current User

### Endpoint

```http
GET /auth/me
```

### Authentication

Required.

### Response

```json
{
  "success": true,
  "data": {
    "user_id": "USER_ID",
    "full_name": "Sanket Mali",
    "email": "user@example.com",
    "status": "active"
  }
}
```

---

# 11. Logout

### Endpoint

```http
POST /auth/logout
```

### Authentication

Required.

### Response

```json
{
  "success": true,
  "message": "Logout successful"
}
```

---

# 12. Document APIs

## 12.1 Upload Document

### Endpoint

```http
POST /documents
```

### Authentication

Required.

### Content Type

```http
multipart/form-data
```

### Form Data

```text
file: <document>
```

### Response

```json
{
  "success": true,
  "data": {
    "document_id": "DOC_ID",
    "file_name": "resume.pdf",
    "document_type": "resume",
    "status": "uploaded"
  },
  "message": "Document uploaded successfully"
}
```

### Possible Errors

```text
400 INVALID_FILE
413 FILE_TOO_LARGE
409 DUPLICATE_DOCUMENT
422 VALIDATION_ERROR
```

---

# 13. List User Documents

### Endpoint

```http
GET /documents
```

### Query Parameters

```text
status
document_type
page
limit
```

Example:

```http
GET /documents?status=processed&page=1&limit=20
```

### Response

```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "document_id": "DOC123",
        "file_name": "resume.pdf",
        "document_type": "resume",
        "status": "processed",
        "uploaded_at": "2026-09-09T10:00:00Z"
      }
    ],
    "page": 1,
    "limit": 20,
    "total": 1
  }
}
```

---

# 14. Get Document

### Endpoint

```http
GET /documents/{document_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "document_id": "DOC123",
    "file_name": "resume.pdf",
    "file_type": "application/pdf",
    "document_type": "resume",
    "status": "processed",
    "page_count": 3,
    "uploaded_at": "2026-09-09T10:00:00Z",
    "processed_at": "2026-09-09T10:01:30Z"
  }
}
```

---

# 15. Process Document

### Endpoint

```http
POST /documents/{document_id}/process
```

### Response

```json
{
  "success": true,
  "data": {
    "document_id": "DOC123",
    "processing_status": "processing"
  },
  "message": "Document processing started"
}
```

The document pipeline may execute:

```text
Validation
   ↓
OCR / Parsing
   ↓
Extraction
   ↓
Normalization
   ↓
Structured Fact Creation
   ↓
Embedding
   ↓
MongoDB Storage
   ↓
ChromaDB Storage
```

---

# 16. Get Document Processing Status

### Endpoint

```http
GET /documents/{document_id}/status
```

### Response

```json
{
  "success": true,
  "data": {
    "document_id": "DOC123",
    "status": "processing",
    "current_stage": "extraction",
    "progress": 65,
    "error": null
  }
}
```

### Processing Statuses

```text
uploaded
processing
processed
failed
deleted
```

---

# 17. Delete Document

### Endpoint

```http
DELETE /documents/{document_id}
```

### Response

```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

The operation should also remove or invalidate associated structured facts and ChromaDB document chunks.

---

# 18. Profile APIs

## 18.1 Get Profile

### Endpoint

```http
GET /profile
```

### Response

```json
{
  "success": true,
  "data": {
    "user_id": "USER_ID",
    "personal": {
      "full_name": "Sanket Mali",
      "date_of_birth": "2004-08-15"
    },
    "contact": {
      "email": "user@example.com",
      "phone": "9876543210"
    },
    "address": {
      "current": "Pune",
      "permanent": "Mumbai"
    }
  }
}
```

---

# 19. Update Profile

### Endpoint

```http
PUT /profile
```

### Request

```json
{
  "personal": {
    "full_name": "Updated Name"
  },
  "contact": {
    "phone": "9876543210"
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "updated": true
  },
  "message": "Profile updated successfully"
}
```

---

# 20. Get Structured Facts

### Endpoint

```http
GET /profile/facts
```

### Query Parameters

```text
concept
source_document_id
confirmed
```

Example:

```http
GET /profile/facts?concept=date_of_birth
```

### Response

```json
{
  "success": true,
  "data": {
    "facts": [
      {
        "fact_id": "FACT123",
        "concept": "date_of_birth",
        "value": "2004-08-15",
        "confidence": 0.98,
        "is_user_confirmed": true,
        "source": {
          "document_id": "DOC123",
          "page": 1
        }
      }
    ]
  }
}
```

---

# 21. Update Structured Fact

### Endpoint

```http
PUT /profile/facts/{fact_id}
```

### Request

```json
{
  "value": "2004-08-16"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "fact_id": "FACT123",
    "value": "2004-08-16",
    "is_user_confirmed": true
  },
  "message": "Fact updated successfully"
}
```

A user correction should be recorded rather than silently destroying the historical recommendation/extraction context.

---

# 22. Form Session APIs

## 22.1 Create Form Session

### Endpoint

```http
POST /forms/sessions
```

### Request

```json
{
  "website_origin": "https://example.com",
  "page_url": "https://example.com/application",
  "form_id": "form_01"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "session_id": "SESSION123",
    "status": "started"
  }
}
```

---

# 23. Get Form Session

### Endpoint

```http
GET /forms/sessions/{session_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "session_id": "SESSION123",
    "website_origin": "https://example.com",
    "form_id": "form_01",
    "status": "processing",
    "total_fields": 15,
    "filled_fields": 8,
    "reviewed_fields": 2
  }
}
```

---

# 24. Analyze Dynamic Form

### Endpoint

```http
POST /forms/sessions/{session_id}/analyze
```

### Request

```json
{
  "fields": [
    {
      "field_id": "field_01",
      "label": "First Name",
      "name": "fname",
      "placeholder": "Enter first name",
      "input_type": "text",
      "section": "Personal Information",
      "dom_context": {},
      "accessibility_context": {}
    }
  ]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "session_id": "SESSION123",
    "status": "processing",
    "field_count": 1
  },
  "message": "Form analysis started"
}
```

---

# 25. Semantic Field Classification

### Endpoint

```http
POST /forms/classify-field
```

### Request

```json
{
  "field": {
    "field_id": "field_01",
    "label": "Permanent Address",
    "name": "address",
    "placeholder": "",
    "input_type": "textarea",
    "section": "Personal Information",
    "dom_context": {},
    "accessibility_context": {}
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "field_id": "field_01",
    "concept": "permanent_address",
    "confidence": 0.95,
    "status": "classified"
  }
}
```

---

# 26. Batch Field Classification

### Endpoint

```http
POST /forms/classify-fields
```

### Request

```json
{
  "fields": [
    {
      "field_id": "field_01",
      "label": "First Name",
      "input_type": "text"
    },
    {
      "field_id": "field_02",
      "label": "Date of Birth",
      "input_type": "date"
    }
  ]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "classifications": [
      {
        "field_id": "field_01",
        "concept": "first_name",
        "confidence": 0.99
      },
      {
        "field_id": "field_02",
        "concept": "date_of_birth",
        "confidence": 0.98
      }
    ]
  }
}
```

---

# 27. Field Recommendation API

### Endpoint

```http
POST /forms/recommend
```

### Request

```json
{
  "session_id": "SESSION123",
  "field": {
    "field_id": "field_01",
    "label": "Date of Birth",
    "concept": "date_of_birth",
    "context": {}
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "recommendation_id": "REC123",
    "field_id": "field_01",
    "concept": "date_of_birth",
    "recommended_value": "2004-08-15",
    "confidence": 0.97,
    "retrieval_type": "structured",
    "status": "pending_review",
    "provenance": [
      {
        "document_id": "DOC123",
        "page": 1
      }
    ]
  }
}
```

---

# 28. Batch Recommendation API

### Endpoint

```http
POST /forms/recommendations
```

### Request

```json
{
  "session_id": "SESSION123",
  "fields": [
    {
      "field_id": "field_01",
      "concept": "first_name",
      "context": {}
    },
    {
      "field_id": "field_02",
      "concept": "date_of_birth",
      "context": {}
    }
  ]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "recommendation_id": "REC001",
        "field_id": "field_01",
        "concept": "first_name",
        "recommended_value": "Sanket",
        "confidence": 0.99,
        "status": "approved"
      },
      {
        "recommendation_id": "REC002",
        "field_id": "field_02",
        "concept": "date_of_birth",
        "recommended_value": "2004-08-15",
        "confidence": 0.97,
        "status": "approved"
      }
    ]
  }
}
```

---

# 29. Structured Retrieval API

This endpoint represents the structured retrieval operation used internally by the LangGraph workflow.

### Endpoint

```http
POST /retrieval/structured
```

### Request

```json
{
  "user_id": "USER_ID",
  "concept": "date_of_birth",
  "context": {
    "field_label": "Date of Birth"
  }
}
```

The backend should normally obtain the user identity from authentication rather than trusting a client-supplied `user_id`.

### Response

```json
{
  "success": true,
  "data": {
    "concept": "date_of_birth",
    "candidates": [
      {
        "value": "2004-08-15",
        "confidence": 0.98,
        "source_document_id": "DOC123",
        "source_page": 1
      }
    ]
  }
}
```

---

# 30. RAG Retrieval API

### Endpoint

```http
POST /retrieval/rag
```

### Request

```json
{
  "query": "previous organization responsibilities",
  "top_k": 5,
  "filters": {
    "document_type": "resume",
    "language": "en"
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "chunk_id": "CHUNK123",
        "text": "Relevant document content...",
        "similarity": 0.89,
        "metadata": {
          "document_id": "DOC123",
          "page_number": 2,
          "language": "en"
        }
      }
    ]
  }
}
```

The backend should enforce the authenticated user's ownership when querying ChromaDB.

---

# 31. Agent Execution API

### Endpoint

```http
POST /agent/run
```

### Purpose

Starts the LangGraph workflow for a field or form.

### Request

```json
{
  "session_id": "SESSION123",
  "field": {
    "field_id": "field_01",
    "label": "Permanent Address",
    "input_type": "textarea",
    "context": {}
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "run_id": "RUN123",
    "status": "started"
  },
  "message": "Agent workflow started"
}
```

---

# 32. Agent Workflow

The internal logical sequence is:

```text
POST /agent/run
        |
        v
Semantic Classification Agent
        |
        v
Routing Node
       / \
      v   v
 MongoDB ChromaDB
      \   /
       v v
    LLM Reasoning
        |
        v
Conflict / Confidence Check
        |
        +----------------+
        |                |
        v                v
   Auto Approved      HITL Required
        |                |
        +-------+--------+
                |
                v
        Final Response Node
```

---

# 33. Get Agent Run Status

### Endpoint

```http
GET /agent/runs/{run_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "run_id": "RUN123",
    "status": "waiting_for_review",
    "current_node": "human_review",
    "recommendation_id": "REC123"
  }
}
```

### Possible States

```text
started
classifying
routing
retrieving
reasoning
conflict_resolution
waiting_for_review
completed
failed
```

---

# 34. Human Review APIs

## 34.1 Get Pending Reviews

### Endpoint

```http
GET /reviews/pending
```

### Response

```json
{
  "success": true,
  "data": {
    "reviews": [
      {
        "review_id": "REV123",
        "session_id": "SESSION123",
        "field_id": "field_05",
        "concept": "current_address",
        "suggested_value": "Mumbai",
        "confidence": 0.71,
        "reason": "Multiple source values detected",
        "sources": [
          {
            "document_id": "DOC1"
          },
          {
            "document_id": "DOC2"
          }
        ]
      }
    ]
  }
}
```

---

# 35. Submit Human Review Decision

### Endpoint

```http
POST /reviews/{review_id}/decision
```

### Request — Confirm

```json
{
  "decision": "confirm"
}
```

### Request — Edit

```json
{
  "decision": "edit",
  "value": "Mumbai"
}
```

### Request — Reject

```json
{
  "decision": "reject"
}
```

### Request — Skip

```json
{
  "decision": "skip"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "review_id": "REV123",
    "decision": "confirm",
    "status": "completed"
  }
}
```

---

# 36. Recommendation APIs

## Get Recommendation

```http
GET /recommendations/{recommendation_id}
```

## Get Session Recommendations

```http
GET /forms/sessions/{session_id}/recommendations
```

### Response

```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "recommendation_id": "REC123",
        "field_id": "field_01",
        "concept": "first_name",
        "recommended_value": "Sanket",
        "confidence": 0.99,
        "status": "approved"
      }
    ]
  }
}
```

---

# 37. Autofill APIs

The actual DOM manipulation occurs inside the Chrome Extension.

The backend provides approved recommendations.

### Get Approved Values

```http
GET /forms/sessions/{session_id}/approved-values
```

### Response

```json
{
  "success": true,
  "data": {
    "fields": [
      {
        "field_id": "field_01",
        "value": "Sanket",
        "concept": "first_name",
        "status": "approved"
      }
    ]
  }
}
```

### Architecture

```text
FastAPI
   |
   v
Approved Recommendation
   |
   v
Chrome Extension
   |
   v
DOM Field
   |
   v
Autofill
```

The backend should not assume that writing a recommendation means that the browser successfully filled the field.

---

# 38. Autofill Verification API

### Endpoint

```http
POST /forms/sessions/{session_id}/verify
```

### Request

```json
{
  "results": [
    {
      "field_id": "field_01",
      "expected_value": "Sanket",
      "actual_value": "Sanket",
      "status": "verified"
    }
  ]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "verified": 1,
    "failed": 0,
    "results": [
      {
        "field_id": "field_01",
        "status": "verified"
      }
    ]
  }
}
```

---

# 39. User Correction API

### Endpoint

```http
POST /corrections
```

### Request

```json
{
  "session_id": "SESSION123",
  "field_id": "field_05",
  "concept": "current_address",
  "original_value": "Pune",
  "corrected_value": "Mumbai",
  "reason": "Incorrect recommendation"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "correction_id": "CORR123",
    "status": "recorded"
  }
}
```

---

# 40. Feedback API

### Endpoint

```http
POST /feedback
```

### Request

```json
{
  "session_id": "SESSION123",
  "field_id": "field_05",
  "recommendation_id": "REC123",
  "action": "corrected",
  "feedback_type": "incorrect_value",
  "original_value": "Pune",
  "final_value": "Mumbai"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "feedback_id": "FDB123"
  },
  "message": "Feedback recorded successfully"
}
```

---

# 41. Form Session Completion

### Endpoint

```http
POST /forms/sessions/{session_id}/complete
```

### Request

```json
{
  "total_fields": 20,
  "filled_fields": 18,
  "reviewed_fields": 4,
  "failed_fields": 0,
  "submission_status": "user_submitted"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "session_id": "SESSION123",
    "status": "completed"
  }
}
```

---

# 42. API for Document Facts by Source

### Endpoint

```http
GET /documents/{document_id}/facts
```

### Response

```json
{
  "success": true,
  "data": {
    "facts": [
      {
        "fact_id": "FACT1",
        "concept": "full_name",
        "value": "Sanket Mali",
        "confidence": 0.99,
        "source_page": 1
      }
    ]
  }
}
```

---

# 43. Health Check

### Endpoint

```http
GET /health
```

### Response

```json
{
  "success": true,
  "data": {
    "status": "healthy"
  }
}
```

---

# 44. Service Health

### Endpoint

```http
GET /health/services
```

### Response

```json
{
  "success": true,
  "data": {
    "api": "healthy",
    "mongodb": "healthy",
    "chromadb": "healthy",
    "llm": "healthy",
    "embedding_service": "healthy"
  }
}
```

---

# 45. Error Specification

## Standard Error Object

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

---

# 46. Error Codes

| Error Code | Meaning |
|---|---|
| `VALIDATION_ERROR` | Invalid input |
| `UNAUTHORIZED` | Authentication required |
| `FORBIDDEN` | User is not allowed to access resource |
| `RESOURCE_NOT_FOUND` | Requested resource does not exist |
| `EMAIL_ALREADY_EXISTS` | Account already exists |
| `INVALID_CREDENTIALS` | Login failed |
| `INVALID_FILE` | Unsupported/invalid document |
| `FILE_TOO_LARGE` | File exceeds allowed size |
| `DUPLICATE_DOCUMENT` | Document already exists |
| `DOCUMENT_PROCESSING_FAILED` | Document processing failed |
| `OCR_FAILED` | OCR failure |
| `EXTRACTION_FAILED` | Entity extraction failure |
| `EMBEDDING_FAILED` | Embedding generation failure |
| `RETRIEVAL_FAILED` | Retrieval failure |
| `LLM_FAILED` | LLM service failure |
| `CLASSIFICATION_FAILED` | Semantic classification failure |
| `CONFLICT_REQUIRES_REVIEW` | User review required |
| `RECOMMENDATION_NOT_APPROVED` | Value cannot be used yet |
| `AUTOFILL_FAILED` | Browser filling failed |
| `VERIFICATION_FAILED` | Filled value could not be verified |
| `RATE_LIMITED` | Too many requests |
| `SERVICE_UNAVAILABLE` | Dependency unavailable |
| `INTERNAL_ERROR` | Unexpected server error |

---

# 47. Authentication and Authorization Rules

Protected endpoints must:

1. Validate the access token.
2. Identify the authenticated user.
3. Verify resource ownership.
4. Reject cross-user resource access.
5. Avoid trusting client-supplied user IDs.
6. Restrict administrative/internal endpoints.

Example:

```text
Request
   |
   v
Authenticate Token
   |
   v
Get user_id
   |
   v
Check Resource Ownership
   |
   +---- NO ----> 403 Forbidden
   |
  YES
   |
   v
Process Request
```

---

# 48. Chrome Extension API Flow

```text
Chrome Extension
      |
      | POST /forms/sessions
      v
FastAPI
      |
      v
Create Session
      |
      | POST /forms/sessions/{id}/analyze
      v
FastAPI
      |
      v
LangGraph
      |
      v
Recommendations
      |
      | GET /forms/sessions/{id}/approved-values
      v
Chrome Extension
      |
      v
Autofill
      |
      | POST /forms/sessions/{id}/verify
      v
FastAPI
```

---

# 49. Document Processing API Flow

```text
React Application
      |
      | POST /documents
      v
FastAPI
      |
      v
Store Document Metadata
      |
      | POST /documents/{id}/process
      v
Processing Pipeline
      |
      +--> OCR / Parsing
      |
      +--> Extraction
      |
      +--> Normalization
      |
      +--> MongoDB
      |
      +--> Embeddings
      |
      +--> ChromaDB
      |
      v
Processing Complete
```

---

# 50. Agent API Flow

```text
Chrome Extension
       |
       v
POST /agent/run
       |
       v
LangGraph
       |
       v
Semantic Classification
       |
       v
Routing
      / \
     /   \
    v     v
MongoDB ChromaDB
    \     /
     \   /
      v v
    LLM
      |
      v
Conflict / Confidence
      |
   +--+--+
   |     |
   v     v
Auto   HITL
   |     |
   +--+--+
      |
      v
Final Response
      |
      v
Recommendation API
```

---

# 51. API Security

The API handles sensitive personal information and therefore must implement:

- HTTPS in production.
- Secure authentication.
- Password hashing.
- Authorization checks.
- Input validation.
- File validation.
- Request size limits.
- Rate limiting where required.
- Secure CORS configuration.
- Controlled Chrome Extension origins.
- No sensitive data in normal application logs.
- Secure database credentials.
- Safe handling of LLM-generated output.

---

# 52. LLM and Prompt-Safety Boundary

Webpage content must be treated as untrusted input.

```text
Web Page
   |
   v
Field Context
   |
   v
Validation / Context Isolation
   |
   v
Semantic Classification
   |
   v
Agent Workflow
```

Instructions found inside a webpage must not automatically be treated as system-level instructions.

The LLM should only receive the contextual information required for the task.

---

# 53. API Idempotency

Operations that can be retried should be designed to avoid duplicate effects.

Examples:

- Document processing requests
- Feedback submission
- Human-review decisions
- Form-session completion

Where appropriate, the client may provide:

```http
Idempotency-Key: <unique-key>
```

The backend can use this key to prevent duplicate processing.

---

# 54. Asynchronous Processing

Document processing and full form analysis may take longer than a normal HTTP request.

Recommended pattern:

```text
POST /documents/{id}/process
          |
          v
HTTP 202 Accepted
          |
          v
processing job
          |
          v
GET /documents/{id}/status
```

Similarly:

```text
POST /agent/run
       |
       v
HTTP 202 Accepted
       |
       v
GET /agent/runs/{run_id}
```

---

# 55. Pagination

List APIs should support:

```text
page
limit
```

Example:

```http
GET /documents?page=2&limit=20
```

Response:

```json
{
  "page": 2,
  "limit": 20,
  "total": 75,
  "documents": []
}
```

---

# 56. API Versioning

The initial API version is:

```text
/api/v1
```

Example:

```text
/api/v1/auth/login
/api/v1/documents
/api/v1/profile
/api/v1/forms/sessions
```

Future incompatible changes should use a new API version rather than silently changing existing contracts.

---

# 57. API-to-Database Mapping

| API Group | Primary Data Store |
|---|---|
| `/auth/*` | MongoDB |
| `/documents/*` | MongoDB + document storage |
| `/profile/*` | MongoDB |
| `/forms/sessions/*` | MongoDB |
| `/forms/classify-*` | LangGraph / model services |
| `/forms/recommend*` | LangGraph + MongoDB/ChromaDB |
| `/retrieval/structured` | MongoDB |
| `/retrieval/rag` | ChromaDB |
| `/agent/*` | LangGraph + MongoDB/ChromaDB |
| `/reviews/*` | MongoDB |
| `/corrections` | MongoDB |
| `/feedback` | MongoDB |
| `/health/*` | Application/dependencies |

---

# 58. API-to-Agent Mapping

| API | Agent / Module |
|---|---|
| `/forms/classify-field` | Semantic Classification Agent |
| `/retrieval/structured` | Structured Retrieval Node |
| `/retrieval/rag` | RAG Retrieval Node |
| `/agent/run` | LangGraph Orchestrator |
| `/reviews/*` | Human-in-the-Loop |
| `/forms/recommend*` | Final Response / Recommendation Layer |
| `/forms/sessions/{id}/verify` | Verification Layer |
| `/feedback` | Feedback Layer |

---

# 59. API-to-Frontend Mapping

## React.js

Primarily uses:

```text
/auth/*
/documents/*
/profile/*
/reviews/*
/feedback
/forms/sessions/*
```

## Chrome Extension

Primarily uses:

```text
/forms/sessions
/forms/sessions/{id}/analyze
/agent/run
/agent/runs/{id}
/forms/sessions/{id}/recommendations
/forms/sessions/{id}/approved-values
/forms/sessions/{id}/verify
/reviews/*
```

---

# 60. Complete API Flow

```text
                         React.js
                            |
                            v
                         FastAPI
                            |
       +--------------------+--------------------+
       |                    |                    |
       v                    v                    v
 Authentication       Documents             Profile
                            |
                            v
                    Document Processing
                            |
                    +-------+-------+
                    |               |
                    v               v
                 MongoDB         ChromaDB
                    |               |
                    +-------+-------+
                            |
                            v
                     Chrome Extension
                            |
                            v
                       Form Session
                            |
                            v
                    Field Extraction
                            |
                            v
                Semantic Classification
                            |
                            v
                       LangGraph
                            |
                         Routing
                        /       \
                       v         v
                  MongoDB     ChromaDB
                       \         /
                        \       /
                         v     v
                       LLM
                         |
                         v
                Conflict / Confidence
                         |
                   +-----+-----+
                   |           |
                   v           v
                Approved      HITL
                   |           |
                   +-----+-----+
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
                       User
                         |
                         v
                      Feedback
```

---

# 61. Minimal Required API Set

For the first working prototype, the minimum implementation can be:

```text
POST   /auth/register
POST   /auth/login
GET    /auth/me

POST   /documents
GET    /documents
GET    /documents/{document_id}
POST   /documents/{document_id}/process
GET    /documents/{document_id}/status
DELETE /documents/{document_id}

GET    /profile
PUT    /profile
GET    /profile/facts
PUT    /profile/facts/{fact_id}

POST   /forms/sessions
GET    /forms/sessions/{session_id}
POST   /forms/sessions/{session_id}/analyze

POST   /agent/run
GET    /agent/runs/{run_id}

GET    /forms/sessions/{session_id}/recommendations
GET    /forms/sessions/{session_id}/approved-values

GET    /reviews/pending
POST   /reviews/{review_id}/decision

POST   /forms/sessions/{session_id}/verify
POST   /corrections
POST   /feedback

POST   /forms/sessions/{session_id}/complete

GET    /health
GET    /health/services
```

---

# 62. API Development Priority

## Phase 1 — Authentication

```text
/auth/register
/auth/login
/auth/me
```

## Phase 2 — Documents

```text
/documents
/documents/{id}
/documents/{id}/process
/documents/{id}/status
```

## Phase 3 — Knowledge

```text
/profile
/profile/facts
```

## Phase 4 — Form Understanding

```text
/forms/sessions
/forms/sessions/{id}/analyze
/forms/classify-field
```

## Phase 5 — Agent

```text
/agent/run
/agent/runs/{id}
/retrieval/structured
/retrieval/rag
```

## Phase 6 — HITL and Recommendations

```text
/forms/sessions/{id}/recommendations
/reviews/pending
/reviews/{id}/decision
```

## Phase 7 — Browser Integration

```text
/forms/sessions/{id}/approved-values
/forms/sessions/{id}/verify
```

## Phase 8 — Learning and Completion

```text
/corrections
/feedback
/forms/sessions/{id}/complete
```

---

# 63. Final API Architecture Summary

```text
+---------------------------------------------------------+
|                    CLIENTS                              |
|                                                         |
| React.js Web App              Chrome Extension MV3      |
+----------------------+----------------+-----------------+
                       |
                       v
+---------------------------------------------------------+
|                    FASTAPI                              |
|                                                         |
| Auth | Documents | Profile | Forms | Agent | Feedback  |
+----------------------+----------------------------------+
                       |
          +------------+-------------+
          |                          |
          v                          v
+----------------------+    +-----------------------------+
|  DOCUMENT PIPELINE  |    |     LANGGRAPH WORKFLOW       |
|                      |    |                             |
| OCR / Parsing        |    | Semantic Classification     |
| Extraction           |    | Routing Node                |
| Normalization        |    | Structured Retrieval       |
+----------+-----------+    | RAG Retrieval               |
           |                | LLM Reasoning              |
           |                | Conflict Resolution        |
           |                | HITL                        |
           |                | Final Response             |
           |                +-------------+---------------+
           |                              |
           v                              v
+----------------------+       +--------------------------+
|       MongoDB        |       |        ChromaDB          |
|                      |       |                          |
| Users                |       | Document Chunks          |
| Profiles             |       | Embeddings               |
| Documents            |       | Metadata                 |
| Structured Facts     |       +--------------------------+
| Recommendations      |
| Corrections          |
| Feedback             |
| Sessions             |
+----------------------+
                       |
                       v
              Chrome Extension
                       |
                       v
                    Autofill
                       |
                       v
                  Verification
                       |
                       v
                    Feedback
```

---

# 64. Conclusion

The API layer provides a controlled interface between the user interfaces, browser extension, document-processing pipeline, databases, and LangGraph agent workflow.

The core API architecture is:

```text
React.js / Chrome Extension
            ↓
          FastAPI
            ↓
       LangGraph Agent
        /           \
       ↓             ↓
   MongoDB        ChromaDB
       \             /
        \           /
         ↓         ↓
        LLM Reasoning
              ↓
       HITL / Validation
              ↓
         Recommendation
              ↓
           Autofill
              ↓
         Verification
              ↓
           Feedback
```

This API design supports the project's main objective of context-aware semantic understanding and intelligent assistance for dynamic web forms while maintaining structured retrieval, semantic retrieval, provenance, human review, and verification as separate but connected responsibilities.

**End of API_SPECIFICATION.md**
