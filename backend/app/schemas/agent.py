"""API schemas for LangGraph agent workflow per API_SPECIFICATION §31-33."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.forms import FieldObject


class AgentRunRequest(BaseModel):
    """Request schema to start a new agent run."""

    model_config = ConfigDict(extra="ignore")

    workflow_id: str = Field(..., description="Unique ID for this form filling workflow")
    page_context: dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the page being filled"
    )
    field_objects: list[FieldObject] = Field(
        ..., description="List of fields to be analyzed and filled"
    )


class AgentRunResponse(BaseModel):
    """Response schema when starting a run."""

    run_id: str = Field(..., description="Unique identifier for the created run")
    status: str = Field(default="started", description="Current status of the agent run")


class AgentStatusResponse(BaseModel):
    """Response schema for retrieving run status."""

    run_id: str = Field(..., description="Run identifier")
    status: str = Field(..., description="Current status")
    state: dict[str, Any] = Field(..., description="Current AgentState dump")
    created_at: str | None = None
    updated_at: str | None = None
