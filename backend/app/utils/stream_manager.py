import asyncio
import json
from typing import Dict, AsyncGenerator

class stream_manager:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.active: Dict[str, bool] = {}

    async def create_queue(self, workflow_id: str):
        self.queues[workflow_id] = asyncio.Queue()
        self.active[workflow_id] = True

    async def publish(self, workflow_id: str, agent_name: str, status: str, data: any):
        if self.active.get(workflow_id):
            message = {
                "agent_name": agent_name,
                "status": status, # e.g., "STARTING", "THINKING", "INVOKING_TOOL", "COMPLETED"
                "data": str(data)
            }
            await self.queues[workflow_id].put(json.dumps(message))

    async def finish(self, workflow_id: str):
        if self.active.get(workflow_id):
            self.active[workflow_id] = False
            await self.queues[workflow_id].put(None) # Sentinel value to end subscription

    async def subscribe(self, workflow_id: str) -> AsyncGenerator[str, None]:
        if workflow_id not in self.queues:
            return

        queue = self.queues[workflow_id]
        while self.active.get(workflow_id, True):
            message = await queue.get()
            if message is None: # Sentinel value received
                break
            yield f"data: {message}\n\n"
        
        # Clean up the queue after the stream is finished
        del self.queues[workflow_id]

stream_manager = stream_manager()