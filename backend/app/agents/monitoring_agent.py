import random
from typing import Literal
import json
import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function, KernelPlugin

from app.utils.stream_manager import stream_manager

from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatPromptExecutionSettings


# --- Agent Instructions ---
# Defines the agent's specific role and constraints.
# It MUST use the provided tool to accomplish its task.
MONITORING_AGENT_INSTRUCTIONS = """
You are a log analysis assistant specialized in reading OpenTelemetry (OTel) logs.  
Your task is to carefully examine the provided log entries and identify any that contain **errors** or **warnings**.  
You MUST use the `MonitoringTools.check_system_status` tool to find the error logs

Instructions:  
- Look for log entries with severity levels such as "ERROR", "ERR", "WARN", "WARNING", or similar indicators.  
- Return only the relevant log lines that are errors or warnings.  
- If possible, include the **timestamp, service name, and error/warning message** in a structured format.  
- If no errors or warnings are found, respond with: "No error or warning logs found."  
- In the output, remove the duplicate entries if any.

Output format (JSON):  
{
  "errors": [
    {
      "timestamp": "<timestamp>",
      "service": "<service_name>",
      "message": "<error_message>"
    }
  ],
  "warnings": [
    {
      "timestamp": "<timestamp>",
      "service": "<service_name>",
      "message": "<warning_message>"
    }
  ]
}
"""

class MonitoringTools:
    def __init__(self, kernel : sk.Kernel):
        self.kernel = kernel
    """
    A plugin that provides tools for the MonitoringAgent.
    """
    @kernel_function(
        description="Checks the current operational status of a system component.",
        name="check_system_status",
    )
    async def check_system_status(self, logs:str,workflow_id:str) -> str:
        """
        Checks the current operational status of a system component.

        Args:
            logs: The log data to analyze (OTEL format, JSON lines).
            workflow_id: workflow_id.

        Returns:
            str: JSON string with errors and warnings found in the logs.
        """
        # logs = data.get("logs")
        # workflow_id = data.get("workflow_id")

        execution_settings = GoogleAIChatPromptExecutionSettings()

        chat_history = ChatHistory()
        chat_history.add_system_message(MONITORING_AGENT_INSTRUCTIONS)
        chat_history.add_user_message(logs)

        error_logs = await self.kernel.get_service().get_chat_message_contents(chat_history = chat_history, settings=execution_settings)

        #print(error_logs)
        return json.dumps(error_logs[0].inner_content.to_dict()['candidates'][0]['content']['parts'][0]['text'])

def create_monitoring_agent(
    kernel: sk.Kernel,
    plugin: KernelPlugin,
) -> ChatCompletionAgent:
    """
    Creates the MonitoringAgent with its specialized tools.

    This agent is the first responder, responsible for checking the initial
    status of a system component.

    Args:
        kernel: The Semantic Kernel instance that the agent will use.
        plugin: The KernelPlugin containing the monitoring tools.

    Returns:
        An instance of ChatCompletionAgent configured for monitoring tasks.
    """
    return ChatCompletionAgent(
        kernel=kernel,
        name="MonitoringAgent",
        instructions=MONITORING_AGENT_INSTRUCTIONS,
        # The MonitoringTools plugin is provided to the agent, giving it the
        # ability to call the check_system_status function.
        plugins=[plugin],
    )