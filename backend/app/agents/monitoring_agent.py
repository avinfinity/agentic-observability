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
You are a critical log analysis assistant specialized in reading OpenTelemetry (OTel) logs.  
Your task is to carefully examine the provided log entries and identify any that contain **errors**, **warnings**, or **critical issues**.  
You MUST use the `MonitoringTools.check_system_status` tool to find the error logs

Instructions:  
- Look for log entries containing ANY of these critical keywords (case-insensitive):
  
  **ERROR KEYWORDS:** error, err, exception, fatal, critical, fail, failure, failed, crash, crashed, panic, abort, aborted, invalid, denied, refused, rejected, timeout, timed out, unreachable, unavailable, down, offline
  
  **WARNING KEYWORDS:** warn, warning, caution, alert, notice, deprecated, slow, lag, delay, retry, retries, high, elevated, spike, threshold, limit, quota, exceed, overload, degraded, unstable
  
  **PERFORMANCE KEYWORDS:** high cpu, high memory, high load, high latency, high response time, memory leak, disk full, space low, connection refused, too many connections, rate limit
  
  **HTTP/API KEYWORDS:** 4xx, 5xx, 400, 401, 403, 404, 500, 502, 503, 504, bad request, unauthorized, forbidden, not found, internal server error, bad gateway, service unavailable, gateway timeout
  
- Return only the matching log lines that contain these critical indicators.
- If possible, include the **timestamp, service name, severity level, and error/warning message** in a structured format.  
- If no errors or warnings are found, respond with: "No error or warning logs found."  
- In the output, remove duplicate entries if any.
- Prioritize FATAL > ERROR > WARNING > NOTICE in severity classification.
- Please do not use ''' json ''' or ```json ``` tags in the output.

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
        description="Analyzes logs for critical issues including errors, warnings, failures, high resource usage, and system anomalies using comprehensive keyword detection.",
        name="check_system_status",
    )
    async def check_system_status(self, logs:str,workflow_id:str) -> str:
        """
        Analyzes logs for critical issues and system health problems.
        
        Detects:
        - Errors, exceptions, failures, crashes
        - Warnings, alerts, performance issues  
        - High resource usage, timeouts, connection issues
        - HTTP errors, API failures, authentication problems
        - System degradation, overloads, rate limiting

        Args:
            logs: The log data to analyze (OTEL format, JSON lines).
            workflow_id: workflow_id for tracking.

        Returns:
            str: JSON string with comprehensive analysis of errors, warnings, and summary statistics.
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
    Creates the MonitoringAgent with enhanced critical issue detection capabilities.

    This agent is the first responder, responsible for comprehensive analysis of
    system logs to identify errors, warnings, failures, performance issues,
    and other critical system health indicators.

    Args:
        kernel: The Semantic Kernel instance that the agent will use.
        plugin: The KernelPlugin containing the enhanced monitoring tools.

    Returns:
        An instance of ChatCompletionAgent configured for comprehensive monitoring tasks.
    """
    return ChatCompletionAgent(
        kernel=kernel,
        name="MonitoringAgent",
        instructions=MONITORING_AGENT_INSTRUCTIONS,
        # The MonitoringTools plugin is provided to the agent, giving it the
        # ability to call the check_system_status function.
        plugins=[plugin],
    )