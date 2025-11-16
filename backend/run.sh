#!/bin/bash
# Simple run script for the Agentic Observability Backend

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Agentic Observability Backend${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create a .env file with your configuration.${NC}"
    echo ""
    echo "Example:"
    echo "  GOOGLE_API_KEY=\"your-api-key-here\""
    echo "  GEMINI_MODEL_ID=\"gemini-2.0-flash-exp\""
    echo "  TEMPERATURE=0.7"
    echo "  MAX_TOKENS=8192"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ .env file found${NC}"

# Check if we should run verification
if [ "$1" == "--verify" ] || [ "$1" == "-v" ]; then
    echo -e "${YELLOW}Running setup verification...${NC}"
    python verify_setup.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}Setup verification failed. Please fix the issues above.${NC}"
        exit 1
    fi
    echo ""
fi

# Determine if we're using poetry or pip
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}✓ Using Poetry${NC}"
    echo -e "${YELLOW}Starting server with Poetry...${NC}"
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
elif [ -d "venv" ]; then
    echo -e "${GREEN}✓ Using virtual environment${NC}"
    echo -e "${YELLOW}Activating venv and starting server...${NC}"
    source venv/bin/activate
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo -e "${YELLOW}⚠️  No Poetry or venv found, running directly...${NC}"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi

