import asyncio

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def get_health(request: Request) -> JSONResponse:
    """Return the live connectivity state of required Phase 1 dependencies."""
    mongo, chroma = await asyncio.gather(
        request.app.state.mongodb.health_check(),
        request.app.state.chromadb.health_check(),
    )
    healthy = mongo.available and chroma.available
    payload = {
        "success": healthy,
        "data": {
            "status": "healthy" if healthy else "unhealthy",
            "application_version": request.app.state.settings.app_version,
            "services": {"mongodb": mongo.to_dict(), "chromadb": chroma.to_dict()},
        },
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )

