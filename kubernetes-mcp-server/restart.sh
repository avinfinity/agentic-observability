#!/bin/bash

###############################################################################
# MCP Server Restart Script
# 
# This script:
# 1. Kills any process running on port 3100
# 2. Installs/updates npm dependencies
# 3. Starts the MCP server
#
# Usage:
#   ./restart.sh           # Normal restart
#   ./restart.sh --clean   # Clean restart (removes node_modules first)
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   MCP Server Restart Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Kill existing process
echo -e "${YELLOW}[1/3] Stopping existing MCP server...${NC}"
if lsof -ti :3100 >/dev/null 2>&1; then
    lsof -ti :3100 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✓ Stopped process on port 3100${NC}"
else
    echo -e "${GREEN}✓ No process running on port 3100${NC}"
fi
echo ""

# Step 2: Install dependencies
echo -e "${YELLOW}[2/3] Installing dependencies...${NC}"

# Check if --clean flag is provided
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}   Performing clean install (removing node_modules)...${NC}"
    rm -rf node_modules package-lock.json
    echo -e "${GREEN}✓ Cleaned node_modules${NC}"
fi

npm install
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 3: Start server
echo -e "${YELLOW}[3/3] Starting MCP server...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ MCP Server starting on http://localhost:3100${NC}"
echo -e "${GREEN}✓ Approval UI: http://localhost:3100${NC}"
echo -e "${GREEN}✓ Webhook target: http://localhost:8000/api/v1/feedback/mcp-approval${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
npm start

