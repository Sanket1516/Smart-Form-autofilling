"""Agent-run API: start a batch analysis and poll its result.

A run is a form session analysed by the same LangGraph pipeline the extension
uses; ``run_id`` equals the session id.
"""

from fastapi import APIRouter, BackgroundTasks, Request

from app.api.v1.auth import User
from app.core.rate_limit import limiter
from app.schemas.agent import AgentRunRequest, AgentRunResponse, AgentStatusResponse
from app.schemas.responses import SuccessResponse

router = APIRouter(tags=["Agent"])


@router.post("/agent/run", response_model=SuccessResponse[AgentRunResponse], status_code=202)
@limiter.limit("20/minute")
async def start_agent_run(
    request: Request, payload: AgentRunRequest, background_tasks: BackgroundTasks, user: User
) -> SuccessResponse[AgentRunResponse]:
    page = payload.page_context
    repo = request.app.state.form_sessions_repo
    session = await repo.create_session(
        user.user_id,
        str(page.get("website_origin") or "agent-api")[:300],
        str(page.get("page_url") or "agent-api")[:2000],
        payload.workflow_id,
    )
    await repo.update_session(
        user.user_id,
        session["_id"],
        {"status": "processing", "total_fields": len(payload.field_objects)},
    )
    background_tasks.add_task(
        request.app.state.form_fill_service.analyze,
        user.user_id,
        session["_id"],
        payload.field_objects,
    )
    return SuccessResponse(
        data=AgentRunResponse(run_id=session["_id"], session_id=session["_id"], status="processing")
    )


@router.get("/agent/runs/{run_id}", response_model=SuccessResponse[AgentStatusResponse])
async def get_agent_run_status(
    run_id: str, request: Request, user: User
) -> SuccessResponse[AgentStatusResponse]:
    service = request.app.state.form_fill_service
    session = await service.require_session(user.user_id, run_id)
    return SuccessResponse(
        data=AgentStatusResponse(
            run_id=run_id,
            session_id=run_id,
            status=session.get("status", "started"),
            recommendations=await service.recommendations_for(user.user_id, run_id),
        )
    )
