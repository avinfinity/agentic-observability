#!/bin/bash

# Test script for Kubernetes MCP Server Integration

echo "🧪 Testing Kubernetes MCP Server Integration"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if MCP server is running
echo "Test 1: Checking if MCP server is running..."
if curl -s http://localhost:3100/api/approvals/pending > /dev/null; then
    echo -e "${GREEN}✓ MCP server is running${NC}"
else
    echo -e "${RED}✗ MCP server is not running${NC}"
    echo "  Please start the server with: npm start"
    exit 1
fi

echo ""

# Test 2: Check pending approvals (should be empty initially)
echo "Test 2: Fetching pending approvals..."
PENDING=$(curl -s http://localhost:3100/api/approvals/pending)
COUNT=$(echo $PENDING | jq '.approvals | length' 2>/dev/null || echo "0")
echo -e "${GREEN}✓ Found $COUNT pending approval(s)${NC}"
echo "  Response: $PENDING"

echo ""

# Test 3: Submit a test approval request
echo "Test 3: Submitting test approval request..."
RESPONSE=$(curl -s -X POST http://localhost:3100/api/approvals/propose \
  -H "Content-Type: application/json" \
  -d '{
    "action": "Test Remediation Action",
    "commands": [
      {
        "command": "kubectl get pods -n default",
        "explanation": "List all pods in default namespace (test command)",
        "safety_level": "SAFE"
      },
      {
        "command": "kubectl get deployments -n default",
        "explanation": "List all deployments (test command)",
        "safety_level": "SAFE"
      }
    ],
    "metadata": {
      "severity": "LOW",
      "service": "test-service",
      "namespace": "default",
      "priority": "P3",
      "root_cause": "Integration test"
    }
  }')

if echo $RESPONSE | grep -q "approval_id"; then
    APPROVAL_ID=$(echo $RESPONSE | jq -r '.approval_id' 2>/dev/null)
    echo -e "${GREEN}✓ Test approval created successfully${NC}"
    echo "  Approval ID: $APPROVAL_ID"
    echo "  View at: http://localhost:3100"
else
    echo -e "${RED}✗ Failed to create test approval${NC}"
    echo "  Response: $RESPONSE"
    exit 1
fi

echo ""

# Test 4: Verify the approval appears in pending list
echo "Test 4: Verifying approval appears in pending list..."
sleep 1
PENDING=$(curl -s http://localhost:3100/api/approvals/pending)
NEW_COUNT=$(echo $PENDING | jq '.approvals | length' 2>/dev/null || echo "0")

if [ "$NEW_COUNT" -gt "$COUNT" ]; then
    echo -e "${GREEN}✓ Test approval found in pending list${NC}"
    echo "  Total pending: $NEW_COUNT"
else
    echo -e "${YELLOW}⚠ Warning: Approval count didn't increase${NC}"
    echo "  Previous: $COUNT, Current: $NEW_COUNT"
fi

echo ""
echo "============================================"
echo -e "${GREEN}✅ Integration tests completed!${NC}"
echo ""
echo "📋 Summary:"
echo "  - MCP Server: Running on http://localhost:3100"
echo "  - Approval UI: http://localhost:3100"
echo "  - API Endpoint: http://localhost:3100/api/approvals/pending"
echo "  - Test Approval ID: $APPROVAL_ID"
echo ""
echo "🎯 Next Steps:"
echo "  1. Open http://localhost:3100 in your browser"
echo "  2. You should see the test approval with 2 commands"
echo "  3. Try approving or rejecting it"
echo "  4. Start your backend and trigger a real workflow"
echo ""
echo "🧹 Cleanup:"
echo "  The test approval will remain in the queue until you approve/reject it"
echo ""

