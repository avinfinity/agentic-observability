# Changelog

All notable changes to the Agentic Observability Backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Support for multiple LLM providers (OpenAI, Anthropic, etc.)
- Advanced log analysis with embeddings
- Automated rollback mechanisms
- Multi-cluster support
- Prometheus/Grafana integration
- Slack/Teams notifications
- Custom agent plugins
- Automated testing suite

---

## [2.0.0] - 2025-11-16

### Added
- **Reinforcement Learning System**
  - RemediationAgent learns from human feedback
  - Dual-signal learning (MCP approval + UI feedback)
  - Reward computation and example selection
  - Persistent feedback storage in JSONL format

- **Kubectl Command Agent**
  - Automatic kubectl command extraction
  - Integration with Kubernetes MCP Server
  - Command approval workflow
  - Safety level classification

- **Feedback API Endpoints**
  - `/api/v1/feedback/submit` - Submit UI feedback
  - `/api/v1/feedback/statistics` - Get learning metrics
  - `/api/v1/feedback/mcp-approval` - MCP webhook
  - `/api/v1/feedback/workflow/{workflow_id}` - Get feedback opportunities
  - `/api/v1/feedback/top-examples/{agent_name}` - Get learning examples

- **MCP Integration**
  - MCP client for Kubernetes command approval
  - Automatic linking of approval IDs to feedback
  - Webhook support for approval callbacks

- **Documentation**
  - Comprehensive README.md
  - API_DOCUMENTATION.md with examples
  - QUICKSTART.md for fast setup
  - CONTRIBUTING.md for developers
  - Setup verification script

- **Developer Tools**
  - `verify_setup.py` - Setup verification script
  - `run.sh` / `run.bat` - Convenient startup scripts
  - `requirements.txt` - Pip dependencies

### Changed
- Upgraded to Google Gemini 2.0 Flash Exp model
- Improved agent prompts for better accuracy
- Enhanced error handling and logging
- Optimized SSE streaming performance

### Improved
- Better feedback store with multiple approval IDs per remediation
- Enhanced reward computation algorithm
- More robust error handling in agents
- Improved logging throughout the application

### Fixed
- JSON parsing issues with LLM responses
- SSE stream disconnection handling
- Feedback linking for multiple commands
- Environment variable loading

---

## [1.0.0] - 2025-10-01

### Added
- **Multi-Agent System**
  - MonitoringAgent for log analysis
  - AnalysisAgent for root cause analysis
  - RemediationAgent for generating remediation plans
  - Orchestrator for workflow coordination

- **Core Features**
  - FastAPI backend with REST API
  - Server-Sent Events (SSE) for real-time streaming
  - LangChain integration for agent orchestration
  - Google Gemini integration for AI capabilities

- **API Endpoints**
  - `/api/v1/workflows/start` - Start new workflow
  - `/api/v1/workflows/{workflow_id}/stream` - Stream updates
  - `/api/v1/fetchlogs` - Fetch logs from sources

- **Configuration**
  - Environment-based configuration
  - Pydantic settings management
  - Poetry dependency management

- **Infrastructure**
  - Logging system
  - Stream manager for SSE
  - Message formatting utilities

### Technical Details
- Python 3.11+ support
- FastAPI 0.116.0+
- LangChain 0.3.0+
- Google Gemini API integration

---

## Version History

| Version | Release Date | Major Changes |
|---------|-------------|---------------|
| 2.0.0 | 2025-11-16 | Reinforcement learning, MCP integration, kubectl agent |
| 1.0.0 | 2025-10-01 | Initial release with multi-agent system |

---

## Upgrade Guide

### From 1.0.0 to 2.0.0

**Breaking Changes:**
- None (backward compatible)

**New Requirements:**
- Kubernetes MCP Server (optional, for command approval)
- Updated dependencies (run `poetry install` or `pip install -r requirements.txt`)

**Migration Steps:**
1. Update dependencies:
   ```bash
   poetry install
   # or
   pip install -r requirements.txt
   ```

2. Update `.env` file (optional):
   ```bash
   # Add MCP server configuration (if using)
   MCP_SERVER_URL="http://localhost:3100"
   ```

3. Create feedback storage directory:
   ```bash
   mkdir -p data/feedback
   ```

4. Restart the application:
   ```bash
   ./run.sh
   ```

**New Features Available:**
- Submit feedback via `/api/v1/feedback/submit`
- View learning statistics at `/api/v1/feedback/statistics`
- Integrate with MCP server for command approval
- Access learning examples for better performance

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute to this changelog.

When adding entries:
1. Follow the format above
2. Use present tense ("Add feature" not "Added feature")
3. Include relevant issue/PR numbers
4. Group changes by type (Added, Changed, Fixed, etc.)

---

## Links

- [Project Repository](https://github.com/your-repo/agentic-observability)
- [Issue Tracker](https://github.com/your-repo/issues)
- [Documentation](README.md)

---

**Last Updated**: November 16, 2025

