# frontend/services/api_client.py

import requests
import threading
import queue
import json
import sseclient # A dedicated library for consuming SSE streams

class APIClient:
    """
    A client for interacting with the multi-agent backend API.

    This class handles both standard REST API calls to initiate workflows
    and the consumption of Server-Sent Events (SSE) for real-time updates.
    """

    def __init__(self, base_url: str):
        """
        Initializes the API client with the base URL of the backend.

        Args:
            base_url: The base URL for the FastAPI backend (e.g., "http://localhost:8000").
        """
        self.base_url = base_url

    def fetch_logs(self, pull_interval: int=10, filter_pattern: str="*error* or *ERR* or *warning*") -> str:
        """
        Fetches the logs for a specific workflow.
        """
        logs_url = f"{self.base_url}/api/v1/fetchlogs"
        response = requests.get(logs_url, params={"pull_interval": pull_interval, "filter_pattern": filter_pattern})

         # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        return str(response.json())

    def start_workflow(self, logs:str) -> str:
        """
        Sends a request to the backend to start a new agent workflow.

        Args:
            prompt: The user's initial prompt describing the system issue.

        Returns:
            The unique workflow_id for the started process.
        
        Raises:
            requests.exceptions.RequestException: If the API call fails.
        """
        start_url = f"{self.base_url}/api/v1/workflows/start"
        response = requests.post(start_url, data=logs)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        
        return response.json()["workflow_id"]

    def listen_to_stream(self, workflow_id: str, message_queue: queue.Queue):
        """
        Listens to the SSE stream for a given workflow in a background thread.

        This method starts a non-blocking background thread that consumes events
        from the backend and puts them into a thread-safe queue for the main
        Streamlit application to process.

        Args:
            workflow_id: The ID of the workflow to listen to.
            message_queue: A thread-safe queue.Queue object to place messages in.
        """
        
        def run():
            """The target function for the background thread."""
            try:
                stream_url = f"{self.base_url}/api/v1/workflows/{workflow_id}/stream"
                # Use sseclient-py to handle the SSE connection and event parsing
                client = sseclient.SSEClient(requests.get(stream_url, stream=True))
                
                for event in client.events():
                    # The backend sends JSON strings as the 'data' payload
                    if event.data:
                        message = json.loads(event.data)
                        message_queue.put(message)

            except Exception as e:
                # Log the error and signal the end of the stream
                print(f"Error in SSE listener thread: {e}")
                message_queue.put({"agent_name": "System", "status": "ERROR", "data": str(e)})
            
            finally:
                # Put a sentinel value on the queue to signal that the stream has ended.
                message_queue.put(None)

        # Create and start the daemon thread. Daemon threads are terminated when the
        # main program exits, which is suitable for this background task.
        thread = threading.Thread(target=run, daemon=True)
        thread.start()