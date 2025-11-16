# Agentic Observability Backend

An AI-powered Kubernetes observability and remediation system with reinforcement learning capabilities. This backend service uses multi-agent orchestration powered by **Google Gemini**, **LangChain**, and **LangGraph** to automatically monitor logs, analyze issues, and generate remediation plans for Kubernetes environments.

---

## ✨ Features

* **Multi-Agent Orchestration**: Four specialized AI agents working together:
  - **Monitoring Agent**: Extracts errors and warnings from logs
  - **Analysis Agent**: Performs root cause analysis
  - **Remediation Agent**: Generates actionable remediation plans with kubectl commands
  - **Kubectl Command Agent**: Formats and submits commands to MCP server for human approval

* **Reinforcement Learning**: RemediationAgent learns from human feedback via:
  - **Primary Signal**: MCP approval/rejection of proposed commands
  - **Secondary Signal**: Optional UI feedback (ratings, comments)

* **Real-Time Communication**: Server-Sent Events (SSE) for streaming agent updates to clients

* **Human-in-the-Loop**: Integration with Kubernetes MCP Server for command approval workflow

* **Kubernetes Native**: Direct integration with Kubernetes clusters via kubectl commands

* **Log Processing**: Fetch and analyze logs from Elasticsearch or other sources

---

## 🏛️ Architecture

```
backend/
├── app/
│   ├── agents/                    # AI Agent implementations
│   │   ├── monitoring_agent.py    # Log analysis & error extraction
│   │   ├── analysis_agent.py      # Root cause analysis
│   │   ├── remediation_agent.py   # Remediation plan generation (with RL)
│   │   └── kubectl_command_agent.py # Command formatting & MCP submission
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints.py       # Workflow & log endpoints
│   │       └── feedback_endpoints.py # Reinforcement learning APIs
│   ├── core/
│   │   ├── config.py              # Settings management
│   │   ├── logs_fetcher.py        # Log retrieval from data sources
│   │   └── mcp_client.py          # Kubernetes MCP server client
│   ├── learning/
│   │   ├── feedback_store.py      # Feedback storage & reward computation
│   │   └── example_selector.py    # In-context learning example selection
│   ├── orchestration/
│   │   └── orchestrator.py        # Multi-agent workflow coordinator
│   ├── utils/
│   │   ├── messages.py            # Message formatting utilities
│   │   └── stream_manager.py      # SSE event streaming manager
│   └── main.py                    # FastAPI application entry point
├── data/
│   └── feedback/
│       └── remediation_feedback.jsonl # Persistent feedback storage
├── logs/
│   └── app.log                    # Application logs
├── pyproject.toml                 # Poetry dependencies
└── README.md                      # This file
```

---

## 📚 Documentation

This repository includes comprehensive documentation to help you get started:

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | Get up and running in 5 minutes |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | Complete API reference with examples |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production deployment guide (Docker, Kubernetes, AWS) |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | How to contribute to this project |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and release notes |

**Quick Links:**
- 🚀 New here? Start with [QUICKSTART.md](QUICKSTART.md)
- 🔧 Need API details? See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- 🌐 Deploying to production? Read [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 🛠️ Prerequisites

Ensure you have the following installed:

* **Python**: 3.11 or higher
* **Poetry**: Package manager ([installation guide](https://python-poetry.org/docs/#installation))
* **Google Gemini API Key**: Required for AI agent functionality
* **Kubernetes Cluster** (optional): For testing actual remediation commands
* **Kubernetes MCP Server** (optional): For human-in-the-loop approval workflow

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd agentic-observability/backend
```

### 2. Install Dependencies

Using Poetry (recommended):

```bash
poetry install
```

Or using pip:

```bash
pip install -r requirements.txt  # If you have a requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
cp .env.example .env  # If example exists, otherwise create manually
```

Add the following configuration to your `.env` file:

```bash
# Google Gemini API Configuration
GOOGLE_API_KEY="your-google-gemini-api-key-here"
GEMINI_MODEL_ID="gemini-2.0-flash-exp"
TEMPERATURE=0.7
MAX_TOKENS=8192
```

**How to get a Google Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API key" and create a new API key
3. Copy the key and paste it into your `.env` file

### 4. Set Up Data Directories

The application will automatically create necessary directories, but you can set them up manually:

```bash
mkdir -p data/feedback
mkdir -p logs
```

---

## 🎯 Running the Application

### Quick Start (Recommended)

Use the provided helper scripts for easy startup:

**Unix/Linux/macOS:**
```bash
# Verify setup first (optional)
./run.sh --verify

# Start the server
./run.sh
```

**Windows:**
```bash
# Verify setup first (optional)
run.bat --verify

# Start the server
run.bat
```

### Manual Start

#### Development Mode

Using Poetry:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or activate the virtual environment:

```bash
poetry shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Verify Setup

Before running, you can verify your setup:

```bash
python verify_setup.py
```

This will check:
- Python version compatibility
- Required environment variables
- Dependencies installation
- API key configuration
- Directory structure

The server will start at `http://localhost:8000`

---

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

* **Swagger UI**: http://localhost:8000/docs
* **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Workflow Management

**Start a new workflow**
```bash
POST /api/v1/workflows/start
Content-Type: text/plain

<paste your logs here>
```

Response:
```json
{
  "workflow_id": "uuid-here"
}
```

**Stream workflow updates (SSE)**
```bash
GET /api/v1/workflows/{workflow_id}/stream
```

Returns real-time events as the agents process the workflow.

#### Log Fetching

**Fetch logs from data source**
```bash
GET /api/v1/fetchlogs?pull_interval=10&filter_pattern=*error*
```

Parameters:
- `pull_interval`: Seconds to look back (default: 10)
- `filter_pattern`: Log filter pattern (default: *)

#### Reinforcement Learning

**Submit UI feedback**
```bash
POST /api/v1/feedback/submit
Content-Type: application/json

{
  "feedback_id": "workflow_123_remediation_1234567890",
  "rating": 5,
  "was_helpful": true,
  "feedback_comments": "Great remediation plan!",
  "improvements_suggested": "Add rollback steps"
}
```

**Get learning statistics**
```bash
GET /api/v1/feedback/statistics
```

**MCP approval callback (webhook)**
```bash
POST /api/v1/feedback/mcp-approval
Content-Type: application/json

{
  "approval_id": "approval_123abc",
  "status": "approved",
  "approved_count": 5,
  "rejected_count": 0
}
```

---

## 🔄 Workflow Process

1. **Client sends logs** → `POST /api/v1/workflows/start`
2. **Orchestrator initializes** → Creates workflow ID and queue
3. **Monitoring Agent** → Extracts errors/warnings from logs
4. **Analysis Agent** → Identifies root causes
5. **Remediation Agent** → Generates remediation plan with kubectl commands
6. **Kubectl Command Agent** → Formats and submits commands to MCP server
7. **MCP Server** → Human approves/rejects commands
8. **Feedback Loop** → System learns from approval/rejection

All steps stream real-time updates via SSE to connected clients.

---

## 🧠 Reinforcement Learning System

The **RemediationAgent** improves over time using a dual-signal feedback system:

### Primary Signal: MCP Approval
- Commands submitted to Kubernetes MCP Server
- Human approves or rejects with reasons
- Approval/rejection automatically updates feedback store
- Reward score computed based on approval ratio

### Secondary Signal: UI Feedback
- Users can rate remediation plans (1-5 stars)
- Mark as helpful/not helpful
- Provide comments and improvement suggestions
- Enhances MCP signal for better learning

### Reward Computation
```
Reward = (MCP_Signal × 4.0 + UI_Signal × 1.0) / Total_Weight
```
- MCP signal has 4x weight (primary)
- UI signals enhance learning
- High-reward examples used for in-context learning

---

## 🔌 Integration with Kubernetes MCP Server

This backend integrates with a separate Kubernetes MCP Server for command approval:

**MCP Server Configuration:**
- Default URL: `http://localhost:3100`
- Endpoint: `/api/approvals/propose`

**Setup MCP Server:**
1. Clone/install the Kubernetes MCP Server (separate repo)
2. Configure the MCP server to call back to this backend at:
   ```
   POST http://localhost:8000/api/v1/feedback/mcp-approval
   ```
3. Start the MCP server on port 3100

**Workflow:**
1. Backend proposes commands → MCP Server
2. Human reviews in MCP UI (http://localhost:3100)
3. Approval/rejection → Webhook to backend
4. Backend updates feedback store → Learning cycle

---

## 📊 Monitoring & Logs

Application logs are written to `logs/app.log`

View logs in real-time:
```bash
tail -f logs/app.log
```

Feedback data is stored in:
```
data/feedback/remediation_feedback.jsonl
```

Each line is a JSON record with input, output, rewards, and feedback.

---

## 🧪 Testing the System

### 1. Quick Test with Sample Logs

```bash
curl -X POST http://localhost:8000/api/v1/workflows/start \
  -H "Content-Type: text/plain" \
  -d "ERROR: Pod api-service-7b4f9d in namespace production is in CrashLoopBackOff state"
```

### 2. Stream the Results

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}/stream
```

### 3. Submit Feedback

```bash
curl -X POST http://localhost:8000/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_id": "workflow_xxx_remediation_xxx",
    "rating": 5,
    "was_helpful": true
  }'
```

### 4. Check Statistics

```bash
curl http://localhost:8000/api/v1/feedback/statistics
```

---

## 🐳 Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy application code
COPY app ./app
COPY data ./data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t agentic-observability-backend .
docker run -p 8000:8000 --env-file .env agentic-observability-backend
```

---

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `GEMINI_MODEL_ID` | Gemini model version | `gemini-2.0-flash-exp` |
| `TEMPERATURE` | LLM temperature (creativity) | `0.7` |
| `MAX_TOKENS` | Maximum tokens per response | `8192` |

### Customizing Agents

Agent prompts and behavior can be customized in:
- `app/agents/monitoring_agent.py`
- `app/agents/analysis_agent.py`
- `app/agents/remediation_agent.py`
- `app/agents/kubectl_command_agent.py`

### Feedback Storage

Modify storage paths in `app/learning/feedback_store.py`:

```python
feedback_store = FeedbackStore(storage_path="custom/path")
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📝 License

[Add your license here]

---

## 🙋 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact: avinash.rai@example.com

---

## 🔮 Future Enhancements

- [ ] Support for multiple LLM providers (OpenAI, Anthropic, etc.)
- [ ] Advanced log analysis with embeddings
- [ ] Automated rollback mechanisms
- [ ] Multi-cluster support
- [ ] Prometheus/Grafana integration
- [ ] Slack/Teams notifications
- [ ] Custom agent plugins

---

## 📖 Additional Resources

- [LangChain Documentation](https://python.langchain.com/)
- [Google Gemini API](https://ai.google.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Poetry Documentation](https://python-poetry.org/)

---

**Version**: 2.0.0  
**Last Updated**: November 2025
