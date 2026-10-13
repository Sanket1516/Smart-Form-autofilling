"""Health endpoint response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

ServiceState = Literal["healthy", "unhealthy", "not_loaded", "configured", "mock"]


class HealthData(BaseModel):
    status: Literal["healthy", "degraded"] = "healthy"
    application_version: str
    database: Literal["healthy", "unhealthy"] = "healthy"


class ServiceHealthData(BaseModel):
    api: ServiceState
    mongodb: ServiceState
    chromadb: ServiceState
    llm: ServiceState
    embedding_service: ServiceState
    details: dict[str, str] = Field(default_factory=dict)
