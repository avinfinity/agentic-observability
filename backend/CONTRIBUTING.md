# Contributing to Agentic Observability Backend

Thank you for considering contributing to this project! We welcome contributions of all kinds.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Project Structure](#project-structure)
5. [How to Contribute](#how-to-contribute)
6. [Coding Standards](#coding-standards)
7. [Testing](#testing)
8. [Documentation](#documentation)
9. [Pull Request Process](#pull-request-process)

---

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Assume good intentions

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/agentic-observability.git
   cd agentic-observability/backend
   ```
3. **Set up the development environment** (see below)
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- Google Gemini API key
- Git

### Setup Steps

1. **Install dependencies:**
   ```bash
   poetry install
   # or
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Verify setup:**
   ```bash
   python verify_setup.py
   ```

4. **Run the application:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

5. **Test your changes:**
   - Open http://localhost:8000/docs
   - Try the API endpoints
   - Check logs in `logs/app.log`

---

## Project Structure

```
backend/
├── app/
│   ├── agents/           # AI agent implementations
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Core utilities (config, logs, MCP)
│   ├── learning/         # Reinforcement learning system
│   ├── orchestration/    # Multi-agent orchestration
│   └── utils/            # Helper utilities
├── data/                 # Persistent data storage
├── logs/                 # Application logs
└── tests/                # Test files (to be added)
```

### Key Components

- **Agents**: Specialized AI agents for different tasks
- **Orchestrator**: Coordinates agent workflow
- **Feedback Store**: Manages reinforcement learning data
- **MCP Client**: Communicates with Kubernetes MCP server
- **Stream Manager**: Handles SSE event streaming

---

## How to Contribute

### Types of Contributions

1. **Bug Fixes**: Fix issues or bugs
2. **Features**: Add new functionality
3. **Documentation**: Improve docs, add examples
4. **Tests**: Add or improve test coverage
5. **Refactoring**: Improve code quality
6. **Performance**: Optimize performance

### Finding Issues

- Check the [Issues](https://github.com/your-repo/issues) page
- Look for `good-first-issue` labels
- Look for `help-wanted` labels

### Suggesting Features

1. Check if the feature already exists or is planned
2. Open a new issue with the `feature-request` label
3. Describe the feature and its use case
4. Discuss implementation approach

---

## Coding Standards

### Python Style

Follow [PEP 8](https://pep8.org/) style guide:

```python
# Good
def extract_errors(logs: str) -> List[str]:
    """Extract error messages from logs.
    
    Args:
        logs: Raw log text
        
    Returns:
        List of error messages
    """
    errors = []
    for line in logs.split('\n'):
        if 'ERROR' in line:
            errors.append(line)
    return errors

# Bad
def extract_errors(logs):
    errors=[]
    for line in logs.split('\n'):
        if 'ERROR' in line:errors.append(line)
    return errors
```

### Type Hints

Always use type hints:

```python
# Good
from typing import List, Optional

def process_logs(
    logs: str,
    filter_pattern: Optional[str] = None
) -> List[dict]:
    pass

# Bad
def process_logs(logs, filter_pattern=None):
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def create_agent(llm: ChatGoogleGenerativeAI) -> AgentExecutor:
    """Create an AI agent with the given LLM.
    
    Args:
        llm: The language model to use
        
    Returns:
        Configured agent executor
        
    Raises:
        ValueError: If LLM is not configured properly
        
    Example:
        >>> llm = initialize_llm()
        >>> agent = create_agent(llm)
    """
    pass
```

### Error Handling

Handle errors gracefully:

```python
# Good
try:
    result = await agent.ainvoke(input_data)
except Exception as e:
    logger.error(f"Agent failed: {str(e)}")
    await stream_manager.publish(
        workflow_id,
        "AgentName",
        "ERROR",
        f"Failed: {str(e)}"
    )
    return ""

# Bad
result = await agent.ainvoke(input_data)  # No error handling
```

### Logging

Use proper logging:

```python
import logging

# Good
logger = logging.getLogger(__name__)
logger.info("Starting workflow")
logger.error(f"Failed to process: {error}")

# Bad
print("Starting workflow")  # Don't use print for production
```

### Async/Await

Use async properly:

```python
# Good
async def run_workflow(workflow_id: str, logs: str):
    result = await agent.ainvoke({"input": logs})
    await stream_manager.publish(workflow_id, "Agent", "COMPLETED", result)

# Bad
def run_workflow(workflow_id: str, logs: str):
    result = asyncio.run(agent.ainvoke({"input": logs}))  # Don't nest event loops
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=app tests/
```

### Writing Tests

Create test files in `tests/` directory:

```python
# tests/test_agents.py
import pytest
from app.agents.monitoring_agent import create_monitoring_agent

@pytest.mark.asyncio
async def test_monitoring_agent():
    """Test that monitoring agent extracts errors"""
    # Arrange
    logs = "ERROR: Something went wrong\nINFO: All good"
    
    # Act
    result = await agent.ainvoke({"input": logs})
    
    # Assert
    assert "ERROR" in result["output"]
    assert "INFO" not in result["output"]
```

### Test Coverage

Aim for:
- 80%+ code coverage
- All critical paths tested
- Edge cases covered

---

## Documentation

### Updating Documentation

When making changes, update:

1. **Docstrings** in code
2. **README.md** for major features
3. **API_DOCUMENTATION.md** for API changes
4. **CHANGELOG.md** for version changes

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams for complex flows
- Keep it up-to-date

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Commit messages are clear

### Commit Messages

Use conventional commits:

```bash
# Good
feat: add support for OpenAI models
fix: resolve memory leak in stream manager
docs: update API documentation for feedback endpoints
test: add tests for remediation agent
refactor: simplify orchestrator logic

# Bad
update code
fix bug
changes
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance

### Creating a Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a PR** on GitHub

3. **Fill out the PR template:**
   - Description of changes
   - Related issues
   - Testing done
   - Screenshots (if UI changes)

4. **Request review** from maintainers

5. **Address feedback** and update as needed

### PR Template

```markdown
## Description
Brief description of what this PR does

## Related Issues
Fixes #123

## Changes Made
- Added feature X
- Fixed bug Y
- Updated documentation Z

## Testing
- [ ] Manual testing done
- [ ] Unit tests added/updated
- [ ] Integration tests pass

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)
```

---

## Development Tips

### Debugging

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use ipdb for breakpoints
import ipdb; ipdb.set_trace()
```

### Testing Locally

```bash
# Run with debug logs
LOG_LEVEL=DEBUG uvicorn app.main:app --reload

# Monitor logs in real-time
tail -f logs/app.log

# Test endpoints
curl -X POST http://localhost:8000/api/v1/workflows/start \
  -H "Content-Type: text/plain" \
  -d "test logs"
```

### Common Issues

**ImportError:**
```bash
# Reinstall dependencies
poetry install
# or
pip install -r requirements.txt
```

**Port already in use:**
```bash
# Use different port
uvicorn app.main:app --reload --port 8001
```

**API key errors:**
```bash
# Check .env file
cat .env
# Make sure GOOGLE_API_KEY is set
```

---

## Community

### Communication

- **GitHub Issues**: For bugs and features
- **GitHub Discussions**: For questions and ideas
- **Pull Requests**: For code contributions

### Getting Help

- Read the [README.md](README.md)
- Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Search existing issues
- Ask in GitHub Discussions
- Contact maintainers

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Acknowledged in the project

---

## Questions?

Feel free to reach out:
- Open an issue
- Start a discussion
- Contact: avinash.rai@example.com

---

**Thank you for contributing!** 🎉

