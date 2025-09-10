from typing import Union, Dict, List
from pydantic import BaseModel

class Message(BaseModel):
    agent_name: str
    status: str
    input: str = ""
    output: str = ""
    data: str = ""  # Use only str, serialize dicts/lists to JSON string if needed
