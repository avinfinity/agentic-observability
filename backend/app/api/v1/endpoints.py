import asyncio
import uuid
import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from sse_starlette.sse import EventSourceResponse
from app.core.logs_fetcher import LogsFetcher
import json

# Import the core orchestration logic and the stream manager
from app.orchestration.orchestrator import run_workflow
from app.utils.stream_manager import stream_manager

router = APIRouter()

@router.get("/fetchlogs", status_code=200)
async def fetch_logs(
    pull_interval: str = Query(default="10", description="Number of seconds to look back for logs"),
    filter_pattern: str = Query(default="*", description="Query pattern for log filtering")
):
    """
    Endpoint to fetch logs via query parameters.
    
    Args:
        pull_interval: Number of seconds to look back (as string)
        filter_pattern: Query pattern for log filtering

    Example: GET /fetchlogs?pull_interval=10&filter_pattern=*error*+or+*ERR*+or+*warning*
    """
    try:
        try:
            past_seconds = int(pull_interval)
            if past_seconds <= 0:
                raise ValueError("pull_interval must be a positive integer")
        except ValueError as e:
            logging.error(f"Invalid pull_interval parameter: {pull_interval}, error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid pull_interval: {str(e)}")
        
        print(f"Fetching logs from the last {past_seconds} seconds with filter: {filter_pattern}")

        logs = LogsFetcher().fetch_logs(
            pull_interval_in_sec=past_seconds,
            filter_pattern=filter_pattern
        )
        if not logs:
            return JSONResponse(status_code=204, content={"message": "No logs found for the given parameters"})
        return logs
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Unexpected error in fetch_logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching logs")

@router.post("/workflows/start", status_code=202)
async def start_workflow(request: Request, background_tasks: BackgroundTasks):
    """
    Starts a new agent workflow.

    This endpoint generates a unique ID for the workflow, creates a message
    queue for it, and starts the agent orchestration process in the background.
    It immediately returns the workflow ID to the client.
    """
    try:
        workflow_id = str(uuid.uuid4())
        
        # Get request body with error handling
        try:
            logs = await request.body()
        except Exception as e:
            logging.error(f"Failed to read request body: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid request body")
        
        print(type(logs))
        
        # Decode logs with error handling
        try:
            initial_logs = str(logs, 'utf-8')
        except UnicodeDecodeError as e:
            logging.error(f"Failed to decode request body as UTF-8: {str(e)}")
            raise HTTPException(status_code=400, detail="Request body must be valid UTF-8")
        
        print(initial_logs)
        
        # last_5_mins_logs = LogsFetcher().fetch_last_5min_logs()
        
        # print(last_5_mins_logs)
        # print("-----------------------------------------------------------------")
        
        # Create a dedicated message queue for this workflow run
        try:
            await stream_manager.create_queue(workflow_id)
        except Exception as e:
            logging.error(f"Failed to create queue for workflow {workflow_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize workflow queue")
        
        # Add the long-running agent workflow as a background task.
        # This allows the API to return a response immediately without waiting
        # for the entire agent process to complete.
        try:
            background_tasks.add_task(
                run_workflow, workflow_id=workflow_id, initial_logs=initial_logs
            )
        except Exception as e:
            logging.error(f"Failed to start background task for workflow {workflow_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to start workflow")
        
        return {"workflow_id": workflow_id}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Unexpected error in start_workflow: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while starting workflow")

@router.get("/workflows/{workflow_id}/stream")
async def stream_workflow_status(request: Request, workflow_id: str):
    """
    Endpoint to stream agent actions for a specific workflow using SSE.

    The client subscribes to this endpoint to receive real-time updates
    from the running agent workflow.
    """
    
    # Validate workflow_id format
    try:
        uuid.UUID(workflow_id)
    except ValueError:
        logging.error(f"Invalid workflow_id format: {workflow_id}")
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")
    
    async def event_generator():
        """
        An async generator that yields messages from the workflow's queue.
        """
        try:
            # The generator will listen to the queue associated with the workflow_id
            async for message in stream_manager.subscribe(workflow_id):
                try:
                    # If the client disconnects, we break the loop.
                    if await request.is_disconnected():
                        print(f"Client disconnected from workflow {workflow_id}")
                        break
                    # Yield as dict for proper SSE formatting
                    yield {"data": message}
                except Exception as e:
                    logging.error(f"Error processing message for workflow {workflow_id}: {str(e)}")
                    # Send error message to client and continue
                    yield {"data": json.dumps({"error": "Error processing message", "type": "error"})}
                    
        except Exception as e:
            logging.error(f"Error in event generator for workflow {workflow_id}: {str(e)}")
            # Send final error message before closing stream
            yield {"data": json.dumps({"error": "Stream error occurred", "type": "error"})}
            
    try:
        return EventSourceResponse(event_generator())
    except Exception as e:
        logging.error(f"Failed to create EventSourceResponse for workflow {workflow_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize event stream")