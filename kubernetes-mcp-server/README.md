# Kubernetes MCP Server with Human-in-the-Loop Approval

A Model Context Protocol (MCP) server that provides Kubernetes remediation capabilities with human approval workflow.

## Features

- **Human-in-the-Loop Approval**: All remediation actions require explicit approval before execution
- **Web-based Approval Interface**: RESTful API for approving/rejecting proposed actions
- **Kubernetes Integration**: Direct integration with Kubernetes API for executing kubectl commands
- **Safety First**: Destructive operations always require approval

## Prerequisites

- Node.js 18+
- Access to a Kubernetes cluster (kubeconfig configured)
- kubectl installed and configured

## Installation

```bash
cd kubernetes-mcp-server
npm install
```

## Usage

### Start the MCP Server

```bash
npm start
```

The server will:
- Start an MCP server on stdio (for agent communication)
- Start a web server on port 3100 (for approval interface)

### Approval Interface

View pending approvals:
```bash
curl http://localhost:3100/api/approvals/pending
```

Approve an action:
```bash
curl -X POST http://localhost:3100/api/approvals/{id}/approve
```

Reject an action:
```bash
curl -X POST http://localhost:3100/api/approvals/{id}/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "Not safe to execute"}'
```

## MCP Tools

### propose_remediation

Propose remediation actions that require approval before execution.

**Parameters:**
- `action` (string): Description of the remediation action
- `commands` (array): Array of kubectl commands with explanations
- `metadata` (object): Additional context (severity, service, namespace)

**Example:**
```json
{
  "action": "Restart crashed pods",
  "commands": [
    {
      "command": "kubectl delete pod api-service-7b4f9d -n production",
      "explanation": "Delete the OOMKilled pod to trigger restart",
      "safety_level": "CAUTION"
    }
  ],
  "metadata": {
    "severity": "HIGH",
    "service": "api-service",
    "namespace": "production"
  }
}
```

### execute_kubectl

Execute a kubectl command directly. Destructive operations require approval.

**Parameters:**
- `command` (string): The kubectl command to execute
- `namespace` (string): Kubernetes namespace (default: "default")

### get_pending_approvals

Get list of all pending approval requests.

## Integration with Remediation Agent

The remediation agent can send proposed actions to this MCP server:

```python
import httpx

async def send_to_mcp_server(remediation_plan):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:3100/api/mcp/propose",
            json=remediation_plan
        )
        return response.json()
```

## Supported Kubernetes Operations

- **Get**: List/describe pods, deployments, services
- **Delete**: Delete pods, deployments (requires approval)
- **Scale**: Scale deployments
- **Rollout**: Restart deployments, rollback
- **Describe**: Get detailed resource information

## Safety Features

1. All destructive operations require explicit approval
2. Approval requests are queued and tracked
3. Each action has a unique ID for auditability
4. Commands are validated before execution
5. Detailed logging of all operations

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│ Remediation     │─────▶│ Kubernetes MCP   │─────▶│ Kubernetes  │
│ Agent (Python)  │      │ Server (Node.js) │      │ Cluster     │
└─────────────────┘      └──────────────────┘      └─────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Web Approval UI  │
                         │ (Port 3100)      │
                         └──────────────────┘
```

## Development

Run in development mode with auto-reload:
```bash
npm run dev
```

## Environment Variables

- `APPROVAL_PORT`: Port for approval server (default: 3100)
- `KUBECONFIG`: Path to kubeconfig file (default: ~/.kube/config)

## Security Considerations

- The approval server should be protected with authentication in production
- Network policies should restrict access to the approval endpoint
- All operations are logged for audit purposes
- Consider implementing approval expiration timeouts

