"""Health endpoint response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

ServiceState = Literal["healthy", "unhealthy", "not_configured"]


class HealthData(BaseModel):
    status: Literal["healthy"] = "healthy"
    application_version: str


class ServiceHealthData(BaseModel):
    api: ServiceState
    mongodb: ServiceState
    chromadb: ServiceState
    llm: ServiceState
    embedding_service: ServiceState
    details: dict[str, str] = Field(default_factory=dict)
