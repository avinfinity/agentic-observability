"""
MCP Client for communicating with the Kubernetes MCP Server
"""
import httpx
import json
from typing import Dict, List, Any
from app.core.config import settings


class MCPClient:
    """Client for interacting with the Kubernetes MCP Server"""
    
    def __init__(self, base_url: str = "http://localhost:3100"):
        self.base_url = base_url
        self.timeout = httpx.Timeout(30.0, connect=5.0)
    
    async def propose_remediation(
        self, 
        action: str, 
        commands: List[Dict[str, Any]], 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Propose a remediation action to the MCP server.
        This will require human approval before execution.
        
        Args:
            action: Description of the remediation action
            commands: List of commands to execute
            metadata: Additional metadata (severity, service, namespace)
        
        Returns:
            Response from the MCP server including approval status
        """
        if metadata is None:
            metadata = {}
        
        payload = {
            "action": action,
            "commands": commands,
            "metadata": metadata
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Send to the propose endpoint
                response = await client.post(
                    f"{self.base_url}/api/approvals/propose",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {
                    "error": f"Failed to communicate with MCP server: {str(e)}",
                    "status": "error"
                }
    
    async def get_pending_approvals(self) -> Dict[str, Any]:
        """
        Get list of pending approval requests
        
        Returns:
            List of pending approvals
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/approvals/pending"
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {
                    "error": f"Failed to get pending approvals: {str(e)}",
                    "approvals": []
                }
    
    async def wait_for_approval(self, approval_id: str, poll_interval: int = 2, max_wait: int = 300) -> Dict[str, Any]:
        """
        Wait for an approval to be processed (approved or rejected)
        
        Args:
            approval_id: The ID of the approval request
            poll_interval: How often to check for approval (seconds)
            max_wait: Maximum time to wait (seconds)
        
        Returns:
            Approval result
        """
        import asyncio
        
        elapsed = 0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while elapsed < max_wait:
                try:
                    response = await client.get(
                        f"{self.base_url}/api/approvals/pending"
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if this approval is still pending
                    pending_ids = [a["id"] for a in data.get("approvals", [])]
                    if approval_id not in pending_ids:
                        # Approval was processed
                        return {
                            "status": "processed",
                            "message": "Approval request was processed"
                        }
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                    
                except httpx.HTTPError as e:
                    return {
                        "error": f"Failed to check approval status: {str(e)}",
                        "status": "error"
                    }
            
            return {
                "status": "timeout",
                "message": f"Approval not received within {max_wait} seconds"
            }


# Global MCP client instance
mcp_client = MCPClient()

