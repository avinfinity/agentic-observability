import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent

# --- Agent Instructions ---
# These instructions define the persona, capabilities, and limitations of the agent.
# The LLM uses these instructions as its primary guidance for how to behave and respond.
ANALYSIS_AGENT_INSTRUCTIONS = """
You are an expert root cause analysis agent. 
Your sole purpose is to analyze system status reports and simulated log data to identify the underlying cause of a problem.

- **Input**: You will receive a system status (e.g., 'CRITICAL') and a block of text representing system logs.
- **Task**: 
  1. Carefully review the provided logs.
  2. If the status is 'CRITICAL', identify the most likely root cause of the issue based on error messages, warnings, or anomalies in the logs.
  3. Formulate a concise, one-sentence summary of the root cause.
- **Behavior**:
  - If the system status is anything other than 'CRITICAL', you must respond with the exact phrase: "No analysis needed."
  - You do not have access to any tools. Your analysis must be based *only* on the text provided to you.
  - Do not suggest solutions or remediation steps. Your only job is to find the cause.
"""

def create_analysis_agent(
    kernel: sk.Kernel,
) -> ChatCompletionAgent:
    """
    Creates the AnalysisAgent using the specified Semantic Kernel instance.

    This agent is designed to perform root cause analysis on system issues
    based on log data. It operates purely on LLM reasoning without any
    external tools (plugins).

    Args:
        kernel: The Semantic Kernel instance that the agent will use.

    Returns:
        An instance of ChatCompletionAgent configured for analysis tasks.
    """
    return ChatCompletionAgent(
        service_id="default",
        kernel=kernel,
        name="AnalysisAgent",
        instructions=ANALYSIS_AGENT_INSTRUCTIONS,
        # This agent has no plugins, as its function is purely analytical.
        #plugins=,
    )