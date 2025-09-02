# backend/app/agents/remediation_agent.py

import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function
from typing import Literal

# --- Agent Instructions ---
# This multi-step instruction set guides the LLM on its role, capabilities,
# and the mandatory use of its tool.
REMEDIATION_AGENT_INSTRUCTIONS = """
You are an expert system remediation agent.
Your goal is to resolve a system issue based on a provided root cause analysis.

- **Input**: You will receive a concise root cause analysis of a system failure.
- **Task**:
  1. Based on the analysis, formulate a single, clear, and actionable remediation plan. For example, if the cause is "database connection pool exhausted," a good plan would be "increase the maximum connection limit in the database configuration."
  2. You MUST execute this plan using the `RemediationTools.execute_remediation_plan` tool.
  3. After executing the tool, you must report the final outcome (e.g., "SUCCESS" or "FAILURE") of the remediation attempt.
- **Behavior**:
  - Be direct and focused on the solution.
  - Do not ask for permission before executing the plan.
  - Your response should only contain the outcome of the tool execution.
"""

class RemediationTools:
    """
    A plugin that provides tools for the RemediationAgent to execute fixes.
    In a real-world scenario, these functions would interact with infrastructure APIs,
    run deployment scripts, or modify configuration files.
    """
    @kernel_function(
        description="Executes a given remediation plan to fix a system issue.",
        name="execute_remediation_plan",
    )
    def execute_remediation_plan(self, plan: str) -> Literal:
        """
        A mock function to simulate the execution of a remediation plan.

        Args:
            plan: A string describing the remediation action to take.

        Returns:
            A string literal indicating if the execution was successful.
        """
        print(f"Remediation: Attempting to execute plan: '{plan}'...")
        # In a real application, this would contain logic to apply the fix.
        # For this simulation, we will assume the fix is always successful.
        print(f"Remediation: Plan '{plan}' executed successfully.")
        return "SUCCESS"

def create_remediation_agent(
    kernel: sk.Kernel,
) -> ChatCompletionAgent:
    """
    Creates the RemediationAgent with its specialized tools.

    This agent is responsible for proposing and executing a fix for a
    diagnosed system issue.

    Args:
        kernel: The Semantic Kernel instance that the agent will use.

    Returns:
        An instance of ChatCompletionAgent configured for remediation tasks.
    """
    return ChatCompletionAgent(
        service_id="default",
        kernel=kernel,
        name="RemediationAgent",
        instructions=REMEDIATION_AGENT_INSTRUCTIONS,
        # The RemediationTools class is provided as a plugin, making its
        # @kernel_function decorated methods available to the agent.
        plugins=,
    )