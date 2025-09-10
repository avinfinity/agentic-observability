import asyncio
import json
from typing import Dict, AsyncGenerator, Any
from .messages import Message

class stream_manager:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.active: Dict[str, bool] = {}

    async def create_queue(self, workflow_id: str):
        self.queues[workflow_id] = asyncio.Queue()
        self.active[workflow_id] = True

    async def publish(self, workflow_id: str, agent_name: str, status: str, data: Any, input_: str = "", output: str = ""):
        if self.active.get(workflow_id):

            # Serialize data to string if not already
            if not isinstance(data, str):
                data = json.dumps(data)
            msg_obj = Message(
                agent_name=agent_name,
                status=status,
                input=input_,
                output=output,
                data=data
            )

            await self.queues[workflow_id].put(msg_obj.json())

            # message = Message(
            #     agent_name=agent_name,
            #     status=status,
            #     input=input_,
            #     output=output,
            #     data=data
            # )

            # await self.queues[workflow_id].put(message.json())

    async def finish(self, workflow_id: str):
        if self.active.get(workflow_id):
            self.active[workflow_id] = False
            await self.queues[workflow_id].put(None) # Sentinel value to end subscription



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
            yield message  # Yield only the JSON string
        # Clean up the queue after the stream is finished
        del self.queues[workflow_id]

stream_manager = stream_manager()