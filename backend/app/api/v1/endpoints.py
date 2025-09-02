from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from app.utils.stream_manager import stream_manager # To be created

router = APIRouter()

#... (POST endpoint to start the workflow)

@router.get("/workflows/{workflow_id}/stream")
async def stream_workflow_status(request: Request, workflow_id: str):
    """Endpoint to stream agent actions for a specific workflow."""
    
    async def event_generator():
        # This generator will yield messages from a queue
        # associated with the workflow_id
        async for message in stream_manager.subscribe(workflow_id):
            if await request.is_disconnected():
                break
            yield message
            
    return EventSourceResponse(event_generator())