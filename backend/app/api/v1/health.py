"""Health and dependency status endpoints."""

from fastapi import APIRouter, Request

from app.schemas.health import HealthData, ServiceHealthData
from app.schemas.responses import SuccessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=SuccessResponse[HealthData])
async def get_health(request: Request) -> SuccessResponse[HealthData]:
    return SuccessResponse(
        data=HealthData(application_version=request.app.state.settings.app_version),
        message="API is healthy",
    )


@router.get("/services", response_model=SuccessResponse[ServiceHealthData])
async def get_service_health(request: Request) -> SuccessResponse[ServiceHealthData]:
    service_health = await request.app.state.health_service.get_services()
    return SuccessResponse(data=service_health, message="Service health reported")
