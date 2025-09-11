import asyncio
import uuid
from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.core.logs_fetcher import LogsFetcher
import json

# Import the core orchestration logic and the stream manager
from app.orchestration.orchestrator import run_workflow
from app.utils.stream_manager import stream_manager

router = APIRouter()

@router.get("/fetchlogs", status_code=200)
async def fetch_logs():
    """
    Endpoint to fetch logs.
    """
    logs = LogsFetcher().fetch_logs()
    return logs

@router.post("/workflows/start", status_code=202)
async def start_workflow(request: Request, background_tasks: BackgroundTasks):
    """
    Starts a new agent workflow.

    This endpoint generates a unique ID for the workflow, creates a message
    queue for it, and starts the agent orchestration process in the background.
    It immediately returns the workflow ID to the client.
    """
    workflow_id = str(uuid.uuid4())
    logs = await request.body()
    logs = str(logs)

    # last_5_mins_logs = LogsFetcher().fetch_last_5min_logs()

    # print(last_5_mins_logs)
    # print("-----------------------------------------------------------------")
    
    # Create a dedicated message queue for this workflow run
    await stream_manager.create_queue(workflow_id)
    
    # Add the long-running agent workflow as a background task.
    # This allows the API to return a response immediately without waiting
    # for the entire agent process to complete.
    background_tasks.add_task(
        run_workflow, workflow_id=workflow_id, initial_logs=logs
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