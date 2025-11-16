# Quick Start Guide

Get the Agentic Observability Backend running in 5 minutes!

## Prerequisites Check

```bash
python --version  # Should be 3.11+
pip --version     # or poetry --version
```

## Option 1: Poetry (Recommended)

```bash
# 1. Install dependencies
poetry install

# 2. Set up environment
echo 'GOOGLE_API_KEY="your-api-key-here"' > .env
echo 'GEMINI_MODEL_ID="gemini-2.0-flash-exp"' >> .env
echo 'TEMPERATURE=0.7' >> .env
echo 'MAX_TOKENS=8192' >> .env

# 3. Run the server
poetry run uvicorn app.main:app --reload
```

## Option 2: pip + venv

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment (same as above)
echo 'GOOGLE_API_KEY="your-api-key-here"' > .env
echo 'GEMINI_MODEL_ID="gemini-2.0-flash-exp"' >> .env
echo 'TEMPERATURE=0.7' >> .env
echo 'MAX_TOKENS=8192' >> .env

# 4. Run the server
uvicorn app.main:app --reload
```

## Get Your API Key

1. Visit: https://aistudio.google.com/
2. Click "Get API key"
3. Copy the key
4. Paste it in your `.env` file

## Test It!

Open http://localhost:8000/docs in your browser

Try this command:

```bash
curl -X POST http://localhost:8000/api/v1/workflows/start \
  -H "Content-Type: text/plain" \
  -d "ERROR: Pod api-service is in CrashLoopBackOff state"
```

You'll get a `workflow_id` back. Stream the results:

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}/stream
```

## Common Issues

### "Module not found" error
```bash
# Make sure you're in the backend directory
cd backend
poetry install  # or pip install -r requirements.txt
```

### "GOOGLE_API_KEY not found" error
```bash
# Check your .env file exists
ls -la .env
cat .env

# Make sure it contains: GOOGLE_API_KEY="your-key-here"
```

### Port 8000 already in use
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Set up the Kubernetes MCP Server for command approval
3. Explore the API documentation at http://localhost:8000/docs
4. Start a workflow and watch the agents in action!

## Need Help?

- Check the logs: `tail -f logs/app.log`
- Review the API docs: http://localhost:8000/docs
- Open an issue on GitHub

Happy observing! 🚀

