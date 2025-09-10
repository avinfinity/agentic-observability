import asyncio
import traceback
import semantic_kernel as sk
from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion, GoogleAIChatPromptExecutionSettings
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import KernelArguments

from app.core.config import settings
from app.utils.stream_manager import stream_manager

# Import agent creation functions and tool classes from the agents directory
from app.agents.analysis_agent import AnalysisTools
from app.agents.monitoring_agent import MonitoringTools, create_monitoring_agent
from app.agents.analysis_agent import create_analysis_agent
from app.agents.remediation_agent import RemediationTools, create_remediation_agent

# --- Orchestrator Agent Instructions ---
# These instructions are critical as they define the master plan for the LLM.
# It explicitly tells the agent to use the other agents as tools in a logical sequence.
ORCHESTRATOR_INSTRUCTIONS = """
You are a master orchestrator agent for a system reliability team.
Your primary responsibility is to resolve a user-reported system issue by intelligently delegating tasks to a team of specialized agents.
You are an orchestrator agent responsible for coordinating three plugins in order:
1. Monitor
2. Analyze
3. Remediate

Rules:
- Always call the plugins strictly in this sequence: Monitor → Analyze → Remediate.
- Do not skip or change the order.
- while calling plugin methods , map the parameter automatically if name matches with keys present while invoking orchestration agent
- Each plugin receives original arguments and the output of the previous plugin.
- After Remediate is executed, return its output as the final answer.
4.  **Report the final outcome**: Conclude by summarizing the entire process, from monitoring to final remediation status.

Throughout the process, you must provide clear, step-by-step updates on your actions. For each step, explicitly state which agent you are invoking and why. Do not attempt to call any analysis tools or functions; the analysis step is handled by the agent's reasoning only.
"""

def initialize_kernel() -> sk.Kernel:
    """
    Initializes the Semantic Kernel and configures it with the Google Gemini service.

    Returns:
        An instance of semantic_kernel.Kernel.
    """
    kernel = sk.Kernel()


    # Configure the Gemini chat completion service [3]
    gemini_service = GoogleAIChatCompletion(
        api_key=settings.GOOGLE_API_KEY,
        gemini_model_id=settings.GEMINI_MODEL_ID,
    )

    # Add the service to the kernel. The "default" service ID is used by agents
    # unless another service is specified.
    kernel.add_service(gemini_service)

    return kernel

async def run_workflow(workflow_id: str, initial_logs: str):
    """
    Runs the full multi-agent workflow to diagnose and resolve a system issue.

    This function orchestrates the interaction between the Monitoring, Analysis,
    and Remediation agents through a primary OrchestratorAgent.

    Args:
        workflow_id: A unique identifier for this workflow run.
        initial_logs: The initial set of logs.
    """
    try:
        await stream_manager.publish(workflow_id, "OrchestratorAgent", "STARTING", f"Workflow started for id: '{workflow_id}'", input_="", output="")

        kernel = initialize_kernel()

        # --- Register Plugins/Tools ---
        monitoring_plugin = kernel.add_plugin(MonitoringTools(kernel), "MonitoringTools")
        analysis_plugin = kernel.add_plugin(AnalysisTools(kernel), "AnalysisTools")
        remediation_plugin = kernel.add_plugin(RemediationTools(kernel), "RemediationTools")

        # --- Create Specialized Agents ---
        monitoring_agent = create_monitoring_agent(kernel, monitoring_plugin)
        analysis_agent = create_analysis_agent(kernel, analysis_plugin) 
        remediation_agent = create_remediation_agent(kernel, remediation_plugin)

        args = KernelArguments()
        args['workflow_id'] = workflow_id
        args['logs'] = initial_logs

        error_logs = ""
        async for msg in monitoring_agent.invoke(messages= initial_logs, arguments=args, kernel=kernel):
            error_logs += msg.content.inner_content.text
        args['error_logs'] = error_logs

        root_cause = ""
        async for msg in analysis_agent.invoke(messages=error_logs, arguments=args, kernel=kernel):
            root_cause += msg.content.inner_content.text
        args['root_cause'] = root_cause

        kubectl_commands = ""
        async for msg in remediation_agent.invoke(messages=root_cause, arguments=args, kernel=kernel):
            kubectl_commands += msg.content.inner_content.text
        print(kubectl_commands)

    except Exception as e:
        print(f"An error occurred during the workflow: {e}")
        await stream_manager.publish(workflow_id, "OrchestratorAgent", "ERROR", str(e), input_="", output="")
    finally:
        await stream_manager.finish(workflow_id)