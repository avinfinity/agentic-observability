# API Documentation

Comprehensive API reference for the Agentic Observability Backend.

---

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required. For production use, implement authentication middleware.

---

## Table of Contents

1. [Core Endpoints](#core-endpoints)
2. [Workflow Management](#workflow-management)
3. [Feedback & Learning](#feedback--learning)
4. [Log Management](#log-management)
5. [Error Codes](#error-codes)
6. [Examples](#examples)

---

## Core Endpoints

### GET /

Health check endpoint.

**Response:**
```json
{
  "status": "Backend is running",
  "features": [
    "Multi-Agent Orchestration",
    "Reinforcement Learning",
    "Human-in-the-Loop Feedback",
    "In-Context Learning"
  ],
  "version": "2.0.0"
}
```

---

## Workflow Management

### POST /api/v1/workflows/start

Start a new agent workflow to analyze logs and generate remediation plans.

**Request:**
- Content-Type: `text/plain`
- Body: Raw log text

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/workflows/start \
  -H "Content-Type: text/plain" \
  -d "ERROR: Pod api-service-7b4f9d in namespace production is in CrashLoopBackOff state"
```

**Response:**
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `202` - Accepted, workflow started
- `400` - Bad request (invalid body)
- `500` - Internal server error

---

### GET /api/v1/workflows/{workflow_id}/stream

Stream real-time updates from a running workflow using Server-Sent Events (SSE).

**Parameters:**
- `workflow_id` (path): UUID of the workflow

**Response:** SSE stream

**Event Format:**
```json
{
  "agent": "MonitoringAgent",
  "status": "WORKING",
  "message": "Extracting errors from logs...",
  "timestamp": "2025-11-16T10:30:00.123456"
}
```

**Agent Status Values:**
- `WORKING` - Agent is processing
- `THINKING` - Agent is analyzing
- `COMPLETED` - Agent finished successfully
- `ERROR` - Agent encountered an error
- `INFO` - Informational message

**Example (JavaScript):**
```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/workflows/${workflowId}/stream`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.agent}: ${data.message}`);
};
```

**Example (Python):**
```python
import sseclient
import requests

url = f"http://localhost:8000/api/v1/workflows/{workflow_id}/stream"
response = requests.get(url, stream=True)
client = sseclient.SSEClient(response)

for event in client.events():
    data = json.loads(event.data)
    print(f"{data['agent']}: {data['message']}")
```

**Example (curl):**
```bash
curl -N http://localhost:8000/api/v1/workflows/{workflow_id}/stream
```

---

## Feedback & Learning

### POST /api/v1/feedback/submit

Submit UI feedback for a RemediationAgent output.

**Request Body:**
```json
{
  "feedback_id": "workflow_123_remediation_1234567890",
  "rating": 5,
  "was_helpful": true,
  "feedback_comments": "Excellent remediation plan!",
  "improvements_suggested": "Consider adding rollback steps"
}
```

**Fields:**
- `feedback_id` (required): ID of the remediation output
- `rating` (optional): Rating from 1-5 stars
- `was_helpful` (optional): Boolean indicating helpfulness
- `feedback_comments` (optional): General feedback comments
- `improvements_suggested` (optional): Suggested improvements

**Response:**
```json
{
  "success": true,
  "message": "Feedback submitted successfully. Thank you for helping improve the remediation agent!",
  "feedback_id": "workflow_123_remediation_1234567890"
}
```

**Status Codes:**
- `200` - Success
- `404` - Feedback ID not found
- `422` - Validation error

---

### GET /api/v1/feedback/statistics

Get overall learning statistics for RemediationAgent.

**Response:**
```json
{
  "agent_statistics": {
    "RemediationAgent": {
      "total_outputs": 150,
      "approved_count": 120,
      "rejected_count": 15,
      "pending_count": 15,
      "approval_rate": 0.889,
      "average_reward": 0.82,
      "learning_examples": 95
    }
  },
  "total_feedbacks": 135,
  "average_reward": 0.82
}
```

**Metrics:**
- `total_outputs`: Total remediation plans generated
- `approved_count`: Number of commands approved by humans
- `rejected_count`: Number of commands rejected
- `pending_count`: Plans awaiting approval
- `approval_rate`: Ratio of approved to total reviewed
- `average_reward`: Average reward score (0-1)
- `learning_examples`: High-quality examples for in-context learning

---

### GET /api/v1/feedback/statistics/{agent_name}

Get statistics for a specific agent.

**Parameters:**
- `agent_name` (path): Name of the agent (only "RemediationAgent" has RL)

**Response:**
```json
{
  "agent_name": "RemediationAgent",
  "statistics": {
    "total_outputs": 150,
    "approved_count": 120,
    "rejected_count": 15,
    "pending_count": 15,
    "approval_rate": 0.889,
    "average_reward": 0.82,
    "learning_examples": 95
  }
}
```

For non-RL agents:
```json
{
  "agent_name": "MonitoringAgent",
  "statistics": {
    "message": "This agent doesn't use reinforcement learning"
  }
}
```

---

### GET /api/v1/feedback/improvements/{agent_name}

Get improvement suggestions collected from feedback.

**Parameters:**
- `agent_name` (path): Name of the agent

**Response:**
```json
{
  "agent_name": "RemediationAgent",
  "improvement_suggestions": [
    "Add rollback steps for destructive operations",
    "Avoid: Commands too aggressive, needs investigation first",
    "Include verification steps after remediation"
  ],
  "count": 3
}
```

---

### GET /api/v1/feedback/top-examples/{agent_name}

Get top-rated examples for in-context learning.

**Query Parameters:**
- `limit` (optional, default: 5): Number of examples to return
- `min_reward` (optional, default: 0.7): Minimum reward score

**Response:**
```json
{
  "agent_name": "RemediationAgent",
  "examples_count": 5,
  "examples": [
    {
      "feedback_id": "workflow_abc_remediation_123",
      "timestamp": "2025-11-16T10:00:00",
      "rating": 5,
      "reward_score": 0.95,
      "was_helpful": true,
      "approval_status": "approved",
      "approved_commands": 5,
      "rejected_commands": 0,
      "input_preview": "Root cause: Pod memory limit exceeded...",
      "output_preview": "{\"remediation_plans\": [{\"service\": \"api-service\"..."
    }
  ]
}
```

---

### GET /api/v1/feedback/workflow/{workflow_id}

Get feedback opportunities for a specific workflow.

**Parameters:**
- `workflow_id` (path): UUID of the workflow

**Response:**
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "feedback_opportunities": [
    {
      "feedback_id": "workflow_550e8400_remediation_1700123456",
      "agent_name": "RemediationAgent",
      "timestamp": "2025-11-16T10:30:00",
      "has_ui_feedback": false,
      "approval_status": "pending",
      "approval_id": "approval_abc123"
    }
  ],
  "count": 1
}
```

---

### POST /api/v1/feedback/mcp-approval

Webhook endpoint for MCP server to notify approval/rejection (PRIMARY learning signal).

**Request Body:**
```json
{
  "approval_id": "approval_abc123",
  "status": "approved",
  "approved_count": 5,
  "rejected_count": 0
}
```

Or for rejection:
```json
{
  "approval_id": "approval_abc123",
  "status": "rejected",
  "rejection_reason": "Commands too aggressive, needs investigation first",
  "approved_count": 0,
  "rejected_count": 5
}
```

**Fields:**
- `approval_id` (required): The approval ID from MCP server
- `status` (required): Either "approved" or "rejected"
- `rejection_reason` (optional): Reason if rejected
- `approved_count` (required): Number of commands approved
- `rejected_count` (required): Number of commands rejected

**Response:**
```json
{
  "success": true,
  "message": "Approval status 'approved' recorded successfully",
  "approval_id": "approval_abc123"
}
```

**Status Codes:**
- `200` - Success
- `404` - Approval ID not found
- `422` - Validation error

---

## Log Management

### GET /api/v1/fetchlogs

Fetch logs from a data source (e.g., Elasticsearch).

**Query Parameters:**
- `pull_interval` (optional, default: "10"): Number of seconds to look back
- `filter_pattern` (optional, default: "*"): Query pattern for filtering

**Example:**
```bash
curl "http://localhost:8000/api/v1/fetchlogs?pull_interval=60&filter_pattern=*error*+or+*ERR*"
```

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-11-16T10:25:00",
      "level": "ERROR",
      "message": "Pod api-service crashed",
      "source": "kubernetes"
    }
  ],
  "count": 1
}
```

**Status Codes:**
- `200` - Success
- `204` - No logs found
- `400` - Invalid parameters
- `500` - Error fetching logs

---

## Error Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 400 | Bad Request | Invalid input, malformed JSON, incorrect parameters |
| 404 | Not Found | Workflow ID or feedback ID doesn't exist |
| 422 | Unprocessable Entity | Validation failed (e.g., rating out of range) |
| 500 | Internal Server Error | Server-side error, check logs |

**Error Response Format:**
```json
{
  "detail": "Invalid workflow ID format"
}
```

---

## Examples

### Complete Workflow Example

**1. Start a workflow:**
```bash
WORKFLOW_ID=$(curl -s -X POST http://localhost:8000/api/v1/workflows/start \
  -H "Content-Type: text/plain" \
  -d "ERROR: Pod api-service in CrashLoopBackOff" \
  | jq -r '.workflow_id')

echo "Workflow ID: $WORKFLOW_ID"
```

**2. Stream the results:**
```bash
curl -N http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/stream
```

**3. Get feedback opportunities:**
```bash
FEEDBACK=$(curl -s "http://localhost:8000/api/v1/feedback/workflow/$WORKFLOW_ID")
FEEDBACK_ID=$(echo $FEEDBACK | jq -r '.feedback_opportunities[0].feedback_id')

echo "Feedback ID: $FEEDBACK_ID"
```

**4. Submit UI feedback:**
```bash
curl -X POST http://localhost:8000/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -d "{
    \"feedback_id\": \"$FEEDBACK_ID\",
    \"rating\": 5,
    \"was_helpful\": true,
    \"feedback_comments\": \"Great remediation!\"
  }"
```

**5. Check statistics:**
```bash
curl http://localhost:8000/api/v1/feedback/statistics
```

---

### Python Client Example

```python
import requests
import json

# Start workflow
response = requests.post(
    "http://localhost:8000/api/v1/workflows/start",
    headers={"Content-Type": "text/plain"},
    data="ERROR: Pod api-service in CrashLoopBackOff"
)
workflow_id = response.json()["workflow_id"]
print(f"Workflow ID: {workflow_id}")

# Stream results (simplified)
stream_url = f"http://localhost:8000/api/v1/workflows/{workflow_id}/stream"
with requests.get(stream_url, stream=True) as r:
    for line in r.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            print(f"{data['agent']}: {data['message']}")

# Submit feedback
feedback_response = requests.post(
    "http://localhost:8000/api/v1/feedback/submit",
    json={
        "feedback_id": "your_feedback_id",
        "rating": 5,
        "was_helpful": True
    }
)
print(feedback_response.json())
```

---

### JavaScript Client Example

```javascript
// Start workflow
const startWorkflow = async (logs) => {
  const response = await fetch('http://localhost:8000/api/v1/workflows/start', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: logs
  });
  const data = await response.json();
  return data.workflow_id;
};

// Stream results
const streamWorkflow = (workflowId) => {
  const eventSource = new EventSource(
    `http://localhost:8000/api/v1/workflows/${workflowId}/stream`
  );
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`${data.agent}: ${data.message}`);
  };
  
  return eventSource;
};

// Submit feedback
const submitFeedback = async (feedbackId, rating, helpful) => {
  const response = await fetch('http://localhost:8000/api/v1/feedback/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      feedback_id: feedbackId,
      rating: rating,
      was_helpful: helpful
    })
  });
  return await response.json();
};

// Usage
(async () => {
  const workflowId = await startWorkflow('ERROR: Pod crashed');
  const stream = streamWorkflow(workflowId);
})();
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, implement rate limiting middleware.

---

## Versioning

Current API version: `v1`

All endpoints are prefixed with `/api/v1/`

---

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review server logs: `tail -f logs/app.log`
- Open an issue on GitHub

---

**Last Updated**: November 2025

