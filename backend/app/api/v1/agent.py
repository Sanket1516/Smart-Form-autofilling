"""Agent execution and tracking endpoints per API_SPECIFICATION §31-33."""

import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.schemas.agent import AgentRunRequest, AgentRunResponse, AgentStatusResponse
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agent"])

async def execute_agent_background(run_id: str, request: Request) -> None:
    """Background task to run the LangGraph state machine."""
    agent_store = request.app.state.agent_store
    agent_graph = request.app.state.agent_graph
    
    run_doc = await agent_store.get_run(run_id)
    if not run_doc:
        logger.error(f"Run {run_id} not found in background task")
        return
        
    state = run_doc.get("state", {})
    
    try:
        final_state = await agent_graph.run(state)
        # Final state should have status=completed or failed based on nodes
        await agent_store.update_run(run_id, final_state)
    except Exception as e:
        logger.exception(f"Error executing graph for run {run_id}")
        state["status"] = "failed"
        state["errors"] = state.get("errors", []) + [str(e)]
        await agent_store.update_run(run_id, state)


@router.post(
    "/agent/run",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an agentic workflow run"
)
async def start_agent_run(
    payload: AgentRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Starts an asynchronous agent run for autofilling form fields.
    """
    run_id = str(uuid.uuid4())
    # The spec states the user_id must be derived securely or attached to the run.
    # Assuming user_id can be obtained from auth context or mocked for now.
    user_id = getattr(request.state, "user_id", "anonymous")
    
    # Initialize the AgentState
    initial_state: AgentState = {
        "workflow_id": payload.workflow_id,
        "user_id": user_id,
        "page_context": payload.page_context,
        "field_objects": [f.model_dump() for f in payload.field_objects],
        "current_field": payload.field_objects[0].model_dump() if payload.field_objects else None,
        "status": "started",
    }
    
    agent_store = request.app.state.agent_store
    await agent_store.create_run(run_id, initial_state)
    
    # Enqueue execution
    background_tasks.add_task(execute_agent_background, run_id, request)
    
    return AgentRunResponse(run_id=run_id, status="started")


@router.get(
    "/agent/runs/{run_id}",
    response_model=AgentStatusResponse,
    summary="Get status and state of an agent run"
)
async def get_agent_run_status(run_id: str, request: Request):
    """
    Retrieves the current status and state of an agent workflow run.
    """
    agent_store = request.app.state.agent_store
    run_doc = await agent_store.get_run(run_id)
    
    if not run_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
        
    return AgentStatusResponse(
        run_id=run_doc["run_id"],
        status=run_doc["status"],
        state=run_doc["state"],
        created_at=run_doc.get("created_at").isoformat() if run_doc.get("created_at") else None,
        updated_at=run_doc.get("updated_at").isoformat() if run_doc.get("updated_at") else None,
    )
