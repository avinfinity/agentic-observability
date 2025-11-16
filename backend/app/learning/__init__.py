"""
Reinforcement Learning Module - Focused on RemediationAgent

DESIGN PHILOSOPHY:
- Only RemediationAgent needs reinforcement learning
- MCP approval/rejection is the PRIMARY learning signal  
- Human UI feedback is SECONDARY enhancement
- Monitoring & Analysis agents don't need RL (deterministic tasks)

LEARNING PIPELINE:
1. RemediationAgent generates remediation plan
2. KubectlCommandAgent sends to MCP for approval
3. Human approves/rejects in MCP UI  
4. Feedback stored with approval status + reason
5. Future remediation plans learn from approved examples
"""

from app.learning.feedback_store import feedback_store, RemediationFeedback
from app.learning.example_selector import RemediationExampleSelector

__all__ = [
    'feedback_store',
    'RemediationFeedback',
    'RemediationExampleSelector',
]
