"""Readiness and dependency status endpoints (no authentication, no user data)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.health import HealthData, ServiceHealthData
from app.schemas.responses import SuccessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=SuccessResponse[HealthData])
async def get_health(request: Request) -> JSONResponse:
    ready = await request.app.state.health_service.ready()
    data = HealthData(
        status="healthy" if ready else "degraded",
        application_version=request.app.state.settings.app_version,
        database="healthy" if ready else "unhealthy",
    )
    body = SuccessResponse(data=data, message="API is healthy" if ready else "Database unavailable")
    return JSONResponse(status_code=200 if ready else 503, content=body.model_dump(mode="json"))


@router.get("/services", response_model=SuccessResponse[ServiceHealthData])
async def get_service_health(request: Request) -> SuccessResponse[ServiceHealthData]:
    return SuccessResponse(
        data=await request.app.state.health_service.get_services(), message="Service health"
    )
