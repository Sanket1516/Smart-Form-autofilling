"""Schemas for the asynchronous agent-run API (a wrapper over a form session)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.form_sessions import FieldObject, RecommendationOutput


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workflow_id: str = Field(min_length=1, max_length=200)
    page_context: dict[str, Any] = Field(default_factory=dict)
    field_objects: list[FieldObject] = Field(min_length=1, max_length=300)


class AgentRunResponse(BaseModel):
    run_id: str
    session_id: str
    status: str


class AgentStatusResponse(BaseModel):
    run_id: str
    session_id: str
    status: str
    recommendations: list[RecommendationOutput] = Field(default_factory=list)
