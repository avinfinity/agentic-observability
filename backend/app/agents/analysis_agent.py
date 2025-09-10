from semantic_kernel.functions import kernel_function, KernelPlugin
import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatHistory
import json
from app.utils.stream_manager import stream_manager
from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatPromptExecutionSettings


# --- Agent Instructions ---
# These instructions define the persona, capabilities, and limitations of the agent.
# The LLM uses these instructions as its primary guidance for how to behave and respond.
ANALYSIS_AGENT_INSTRUCTIONS = """
You are a root cause analysis assistant.  
You will be given a JSON object containing error and warning log entries that were extracted from OpenTelemetry (OTel) logs.  
Your task is to analyze each entry and suggest the most likely Root Cause(s).  

Instructions:  
- For each **error** entry, carefully analyze the `message`, `service`, and `timestamp` fields to infer possible causes.  
- Provide a clear and concise explanation of what might have led to the error.  
- If multiple root causes are possible, list them all.  
- For **warnings**, also try to suggest potential impact and what could trigger them.  
- If the log message is too vague, output: `"Root cause could not be determined with given information."`  
- In the output, remove the duplicate entries if any.

Output format (JSON):  
{
  "root_causes": [
    {
      "timestamp": "<timestamp>",
      "service": "<service_name>",
      "error_message": "<error_message>",
      "possible_root_causes": [
        "<root_cause_1>",
        "<root_cause_2>"
      ]
    }
  ],
  "warning_analysis": [
    {
      "timestamp": "<timestamp>",
      "service": "<service_name>",
      "warning_message": "<warning_message>",
      "possible_causes": [
        "<cause_1>",
        "<cause_2>"
      ]
    }
  ]
}

"""

class AnalysisTools:
  def __init__(self, kernel: sk.Kernel):
        self.kernel = kernel
  """
  A plugin that provides tools for the AnalysisAgent to analyze logs and status.
  In a real-world scenario, this would use log parsing, anomaly detection, etc.
  """
  @kernel_function(
    description="Analyzes error_logs from previous agent to identify the root cause using LLM.",
    name="analyze_logs",
  )
  async def analyze_logs(self, error_logs: str, workflow_id:str) -> str:
    """
    Parses OTEL logs, checks for errors, and calls LLM to define root cause.
    Args:
      error_logs: The log data to analyze (OTEL format, JSON lines or dicts).
      workflow_id: workflow_id.
    Returns:
      A string describing the root cause or 'No analysis needed.'
    """
    await stream_manager.publish(workflow_id, "AnalysisAgent", "THINKING", "Analysis in progress...")
    
    try:

      execution_settings = GoogleAIChatPromptExecutionSettings()
      chat_history = ChatHistory()
      chat_history.add_system_message(ANALYSIS_AGENT_INSTRUCTIONS)
      chat_history.add_user_message(error_logs)

      root_cause = await self.kernel.get_service().get_chat_message_contents(chat_history = chat_history, settings=execution_settings)

      return json.dumps(root_cause[0].inner_content.to_dict()['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:
      return f"AnalysisAgent failed : {e}"

def create_analysis_agent(
    kernel: sk.Kernel,
     plugin: KernelPlugin,
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
        kernel=kernel,
        name="AnalysisAgent",
        instructions=ANALYSIS_AGENT_INSTRUCTIONS,
        plugins=[plugin],
    )