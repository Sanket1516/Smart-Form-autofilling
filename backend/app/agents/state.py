"""Agent state definitions for the workflow per SRS §30.1."""

from typing import Any, TypedDict

class AgentState(TypedDict, total=False):
    """LangGraph state schema for form autofilling agent."""
    
    workflow_id: str
    user_id: str
    page_context: dict[str, Any]
    field_objects: list[dict[str, Any]]
    current_field: dict[str, Any] | None
    
    semantic_result: dict[str, Any] | None
    retrieval_route: str | None
    
    structured_candidates: list[dict[str, Any]]
    rag_candidates: list[dict[str, Any]]
    
    conflict_result: dict[str, Any] | None
    confidence: float | None
    human_decision: dict[str, Any] | None
    final_value: dict[str, Any] | None
    final_response_status: str | None
    reasoning_trace: list[str]
    
    execution_result: dict[str, Any] | None
    verification_result: dict[str, Any] | None
    
    errors: list[str]
    status: str
