import asyncio
import traceback
import semantic_kernel as sk
from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion
from semantic_kernel.agents import ChatCompletionAgent

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

You must follow these steps in order:
1.  **Assess the problem**: Use the `MonitoringAgent` to check the current system status. You must invoke this agent first.
2.  **Analyze the situation**:
    - If the `MonitoringAgent` reports a 'CRITICAL' status, you must then invoke the `AnalysisAgent`. Provide it with the status and a simulated block of log data for root cause analysis. (Example logs: "ERROR: Connection pool exhausted.", "WARN: High CPU usage.", "INFO: User login successful.")
    - The `AnalysisAgent` does not use any tools or functions; it analyzes the logs and status using its own reasoning and returns the root cause as a sentence.
    - If the status is 'OK' or 'WARNING', the process is complete. State that no further action is needed.
3.  **Remediate the issue**:
    - If the `AnalysisAgent` provides a root cause, you must then invoke the `RemediationAgent`. Pass the analysis result to it so it can execute a fix.
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



async def debug_invoke_stream(orchestrator_agent, initial_prompt, stream_manager, workflow_id):
    full_response = ""
    idx = 0
    try:
        orchestrator_agent.invoke(initial_prompt)
    except Exception as e:
        print("ERROR invoking orchestrator_agent:", e)
        traceback.print_exc()

    
    import re
    try:
        async for message in orchestrator_agent.invoke(initial_prompt):
            idx += 1
            print(f"\nDEBUG: Message #{idx} received: {message}")

            # Extract content safely
            try:
                content = getattr(message, "content", None)
                print(f"DEBUG: Extracted content: {repr(content)}")
                if hasattr(content, "text"):
                    content_str = content.text
                else:
                    content_str = str(content) if content is not None else ""
            except Exception as e:
                print("ERROR extracting content:", e)
                traceback.print_exc()
                continue

            # Append to full_response
            try:
                if content_str:
                    full_response += content_str
                    print(f"DEBUG: full_response so far (first 200 chars): {full_response[:200]}")
                else:
                    print("DEBUG: content_str is empty or None, skipping append")
            except Exception as e:
                print("ERROR appending content to full_response:", e)
                traceback.print_exc()
                continue

            # Parse agent name and status from content_str
            agent_name = "OrchestratorAgent"
            status = "STREAMING"
            input_ = ""
            output = ""

            # Regex-based agent message parsing
            if re.search(r"Invoking MonitoringAgent", content_str):
                agent_name = "MonitoringAgent"
                status = "IN_PROGRESS"
            monitor_match = re.search(r"MonitoringAgent returned: (.*)", content_str, re.DOTALL)
            if monitor_match:
                agent_name = "MonitoringAgent"
                status = "COMPLETED"
                output = monitor_match.group(1).strip()

            if re.search(r"Invoking AnalysisAgent", content_str):
                agent_name = "AnalysisAgent"
                status = "IN_PROGRESS"
            analysis_match = re.search(r"AnalysisAgent returned: (.*)", content_str, re.DOTALL)
            if analysis_match:
                agent_name = "AnalysisAgent"
                status = "COMPLETED"
                output = analysis_match.group(1).strip()

            if re.search(r"Invoking RemediationAgent", content_str):
                agent_name = "RemediationAgent"
                status = "IN_PROGRESS"
            remediation_match = re.search(r"RemediationAgent returned: (.*)", content_str, re.DOTALL)
            if remediation_match:
                agent_name = "RemediationAgent"
                status = "COMPLETED"
                output = remediation_match.group(1).strip()

            # Publish to stream_manager with detected agent_name and status
            try:
                await stream_manager.publish(
                    workflow_id=workflow_id,
                    agent_name=agent_name,
                    status=status,
                    data=content_str,
                    input_=input_,
                    output=output
                )
                print(f"DEBUG: publish succeeded for {agent_name} with status {status}")
            except Exception as e:
                print("ERROR in stream_manager.publish():", e)
                traceback.print_exc()

    except Exception as e:
        print("ERROR iterating over orchestrator_agent.invoke():", e)
        traceback.print_exc()

    return full_response


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
        await stream_manager.publish(workflow_id, "System", "STARTING", f"Workflow started for prompt: '{initial_prompt}'", input_="", output="")

        kernel = initialize_kernel()

        # --- Register Plugins/Tools ---
        analysis_plugin = kernel.add_plugin(AnalysisTools(), "AnalysisTools")
        monitoring_plugin = kernel.add_plugin(MonitoringTools(), "MonitoringTools")
        remediation_plugin = kernel.add_plugin(RemediationTools(), "RemediationTools")

        # --- Create Specialized Agents ---
        monitoring_agent = create_monitoring_agent(kernel, monitoring_plugin)
        analysis_agent = create_analysis_agent(kernel, None)  # No plugin for analysis agent
        remediation_agent = create_remediation_agent(kernel, remediation_plugin)

        # --- Create the Orchestrator Agent ---
        orchestrator_agent = ChatCompletionAgent(
            kernel=kernel,
            name="OrchestratorAgent",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            plugins=[analysis_plugin, monitoring_plugin, remediation_plugin]  # Only tool plugins, not agent objects
        )

        await stream_manager.publish(workflow_id, "OrchestratorAgent", "THINKING", "Orchestrator is planning the workflow...", input_="", output="")

        # --- Execute the Workflow ---
        full_response = ""

        full_response = await debug_invoke_stream(
            orchestrator_agent=orchestrator_agent,
            initial_prompt=initial_prompt,
            stream_manager=stream_manager,
            workflow_id=workflow_id
        )

        # async for message in orchestrator_agent.invoke(initial_prompt):
        #     content = message.content
        #     if content:
        #         full_response += content
        #         await stream_manager.publish(workflow_id, "OrchestratorAgent", "STREAMING", content, input_="", output="")

        await stream_manager.publish(workflow_id, "OrchestratorAgent", "COMPLETED", "Orchestration process finished.", input_="", output="")
        await stream_manager.publish(workflow_id, "System", "COMPLETED", f"Final Result: {full_response}", input_="", output="")

    except Exception as e:
        print(f"An error occurred during the workflow: {e}")
        await stream_manager.publish(workflow_id, "System", "ERROR", str(e), input_="", output="")
    finally:
        await stream_manager.finish(workflow_id)