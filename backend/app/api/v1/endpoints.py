import asyncio
import uuid
from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Import the core orchestration logic and the stream manager
from app.orchestration.orchestrator import run_workflow
from app.utils.stream_manager import stream_manager

router = APIRouter()

# --- Pydantic Models ---
# Define a Pydantic model for the request body to ensure type safety.
class WorkflowStartRequest(BaseModel):
    prompt: str

# --- API Endpoints ---

@router.post("/workflows/start", status_code=202)
async def start_workflow(
    request: WorkflowStartRequest, background_tasks: BackgroundTasks
):
    """
    Starts a new agent workflow.

    This endpoint generates a unique ID for the workflow, creates a message
    queue for it, and starts the agent orchestration process in the background.
    It immediately returns the workflow ID to the client.
    """
    workflow_id = str(uuid.uuid4())
    
    # Create a dedicated message queue for this workflow run
    await stream_manager.create_queue(workflow_id)
    
    # Add the long-running agent workflow as a background task.
    # This allows the API to return a response immediately without waiting
    # for the entire agent process to complete.
    background_tasks.add_task(
        run_workflow, workflow_id=workflow_id, initial_prompt=request.prompt
    )
    
    return {"workflow_id": workflow_id}


@router.get("/workflows/{workflow_id}/stream")
async def stream_workflow_status(request: Request, workflow_id: str):
    """
    Endpoint to stream agent actions for a specific workflow using SSE.

    The client subscribes to this endpoint to receive real-time updates
    from the running agent workflow.
    """
    
    async def event_generator():
        """
        An async generator that yields messages from the workflow's queue.
        """
        # The generator will listen to the queue associated with the workflow_id
        async for message in stream_manager.subscribe(workflow_id):
            # If the client disconnects, we break the loop.
            if await request.is_disconnected():
                print(f"Client disconnected from workflow {workflow_id}")
                break
            # Yield as dict for proper SSE formatting
            yield {"data": message}
            
    return EventSourceResponse(event_generator())