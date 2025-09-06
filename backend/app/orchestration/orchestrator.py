import asyncio
import semantic_kernel as sk
from semantic_kernel.connectors.ai.google.vertex_ai import VertexAIChatCompletion
from semantic_kernel.agents import ChatCompletionAgent

from app.core.config import settings
from app.utils.stream_manager import stream_manager

# Import agent creation functions and tool classes from the agents directory
from app.agents.monitoring_agent import MonitoringTools, create_monitoring_agent
from app.agents.analysis_agent import create_analysis_agent
from app.agents.remediation_agent import RemediationTools, create_remediation_agent

# --- Orchestrator Agent Instructions ---
# These instructions are critical as they define the master plan for the LLM.
# It explicitly tells the agent to use the other agents as tools in a logical sequence.
ORCHESTRATOR_INSTRUCTIONS = """
You are a master orchestrator agent for a system reliability team.
Your primary responsibility is to resolve a user-reported system issue by intelligently delegating tasks to a team of specialized agents.

You must follow these steps in order:
1.  **Assess the problem**: Use the `MonitoringAgent` to check the current system status. You must invoke this agent first.
2.  **Analyze the situation**:
    - If the `MonitoringAgent` reports a 'CRITICAL' status, you must then invoke the `AnalysisAgent`. Provide it with the status and a simulated block of log data for root cause analysis. (Example logs: "ERROR: Connection pool exhausted.", "WARN: High CPU usage.", "INFO: User login successful.")
    - If the status is 'OK' or 'WARNING', the process is complete. State that no further action is needed.
3.  **Remediate the issue**:
    - If the `AnalysisAgent` provides a root cause, you must then invoke the `RemediationAgent`. Pass the analysis result to it so it can execute a fix.
4.  **Report the final outcome**: Conclude by summarizing the entire process, from monitoring to final remediation status.

Throughout the process, you must provide clear, step-by-step updates on your actions. For each step, explicitly state which agent you are invoking and why.
"""

def initialize_kernel() -> sk.Kernel:
    """
    Initializes the Semantic Kernel and configures it with the Google Gemini service.

    Returns:
        An instance of semantic_kernel.Kernel.
    """
    kernel = sk.Kernel()


    # Configure the Gemini chat completion service [3]
    gemini_service = VertexAIChatCompletion(
        api_key=settings.GOOGLE_API_KEY,
    )

    # Add the service to the kernel. The "default" service ID is used by agents
    # unless another service is specified.
    kernel.add_service(gemini_service)

    return kernel


async def run_workflow(workflow_id: str, initial_prompt: str):
    """
    Runs the full multi-agent workflow to diagnose and resolve a system issue.

    This function orchestrates the interaction between the Monitoring, Analysis,
    and Remediation agents through a primary OrchestratorAgent.

    Args:
        workflow_id: A unique identifier for this workflow run.
        initial_prompt: The user's initial problem description.
    """
    try:
        await stream_manager.publish(workflow_id, "System", "STARTING", f"Workflow started for prompt: '{initial_prompt}'")

        kernel = initialize_kernel()

        # --- Register Plugins/Tools ---
        # Make the native Python functions in the Tools classes available to the kernel.
        monitoring_plugin = kernel.add_plugin(MonitoringTools(), "MonitoringTools")
        remediation_plugin = kernel.add_plugin(RemediationTools(), "RemediationTools")

        # --- Create Specialized Agents ---
        monitoring_agent = create_monitoring_agent(kernel, monitoring_plugin)
        analysis_agent = create_analysis_agent(kernel)
        remediation_agent = create_remediation_agent(kernel, remediation_plugin)

        # --- Create the Orchestrator Agent ---
        # The orchestrator uses the other agents as its plugins (tools).[4]
        orchestrator_agent = ChatCompletionAgent(
            service_id="default",
            kernel=kernel,
            name="OrchestratorAgent",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            plugins=[monitoring_agent, analysis_agent, remediation_agent],
        )

        await stream_manager.publish(workflow_id, "OrchestratorAgent", "THINKING", "Orchestrator is planning the workflow...")

        # --- Execute the Workflow ---
        # Invoke the orchestrator and stream its response.
        full_response = ""
        async for message in orchestrator_agent.invoke(initial_prompt):
            content = message.content
            if content:
                full_response += content
                # Stream the raw thought process to the frontend
                await stream_manager.publish(workflow_id, "OrchestratorAgent", "STREAMING", content)

        await stream_manager.publish(workflow_id, "OrchestratorAgent", "COMPLETED", "Orchestration process finished.")
        await stream_manager.publish(workflow_id, "System", "COMPLETED", f"Final Result: {full_response}")

    except Exception as e:
        print(f"An error occurred during the workflow: {e}")
        await stream_manager.publish(workflow_id, "System", "ERROR", str(e))
    finally:
        # Signal the end of the stream to the frontend client.
        await stream_manager.finish(workflow_id)