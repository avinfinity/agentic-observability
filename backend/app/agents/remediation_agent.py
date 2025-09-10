import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function, KernelPlugin
from semantic_kernel.contents import ChatHistory
from typing import Literal
import json
from app.utils.stream_manager import stream_manager
from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatPromptExecutionSettings

# --- Agent Instructions ---
# This multi-step instruction set guides the LLM on its role, capabilities,
# and the mandatory use of its tool.
REMEDIATION_AGENT_INSTRUCTIONS = """
You are a Kubernetes remediation assistant.  
You will be given a JSON object containing log errors, warnings, and their possible root causes.  
Your task is to provide remediation steps using Kubernetes (kubectl) of flagd commands wherever possible.  

Instructions:
- For each error/warning, map the identified root cause to the most appropriate kubectl command(s) or flagd command(s) to remediate the issue. 
- Provide commands that are safe and realistic in a production-like Kubernetes environment.  
- If multiple options exist, suggest the most direct and commonly used commands.  
- If remediation cannot be automated via kubectl, provide a clear explanation and any manual steps needed.  
- Always explain briefly what each command does.  
- If no relevant kubectl or flagd command applies, respond with: `"No direct kubectl/flagd remediation available. Manual investigation required."`
- In the output, remove the duplicate entries if any.

Output format (JSON):
{
  "remediation": [
    {
      "timestamp": "<timestamp>",
      "service": "<service_name>",
      "issue": "<error_or_warning_message>",
      "root_cause": "<identified_root_cause>",
      "kubectl_commands": [
        {
          "command": "kubectl ...",
          "explanation": "This command does ..."
        }
      ]
    }
  ]
}

"""

class RemediationTools:
    def __init__(self, kernel):
        self.kernel = kernel
    """
    A plugin that provides tools for the RemediationAgent to execute fixes.
    In a real-world scenario, these functions would interact with infrastructure APIs,
    run deployment scripts, or modify configuration files.
    """
    @kernel_function(
        description="Executes a given remediation plan to fix a system issue.",
        name="execute_remediation_plan",
    )
    async def execute_remediation_plan(self, root_cause: str, workflow_id: str) -> Literal:
        """
        A mock function to simulate the execution of a remediation plan.

        Args:
            root_cause: A string describing the root cause & remediation action to take.
            workflow_id: workflow_id.
        
        Returns:
            A string literal indicating if the execution was successful.
        """

        #workflow_id = data.get("workflow_id")

        execution_settings = GoogleAIChatPromptExecutionSettings()
        chat_history = ChatHistory()
        chat_history.add_system_message(REMEDIATION_AGENT_INSTRUCTIONS)
        chat_history.add_user_message(root_cause)


        kubectl_commands = await self.kernel.get_service().get_chat_message_contents(chat_history = chat_history, settings=execution_settings)

        return json.dumps(kubectl_commands[0].inner_content.to_dict()['candidates'][0]['content']['parts'][0]['text'])

def create_remediation_agent(
    kernel: sk.Kernel,
    plugin: KernelPlugin,
) -> ChatCompletionAgent:
    """
    Creates the RemediationAgent with its specialized tools.

    This agent is responsible for proposing and executing a fix for a
    diagnosed system issue.

    Args:
        kernel: The Semantic Kernel instance that the agent will use.
        plugin: The KernelPlugin containing the remediation tools.

    Returns:
        An instance of ChatCompletionAgent configured for remediation tasks.
    """
    return ChatCompletionAgent(
        kernel=kernel,
        name="RemediationAgent",
        instructions=REMEDIATION_AGENT_INSTRUCTIONS,
        # The RemediationTools plugin is provided to the agent.
        plugins=[plugin],
    )