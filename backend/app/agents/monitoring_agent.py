import random
from typing import Literal
import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function, KernelPlugin

# --- Agent Instructions ---
# Defines the agent's specific role and constraints.
# It MUST use the provided tool to accomplish its task.
MONITORING_AGENT_INSTRUCTIONS = """
You are a system monitoring agent. 
Your sole responsibility is to check the operational status of a given system component.
You MUST use the `MonitoringTools.check_system_status` tool to get the status.
After using the tool, report only the status (e.g., 'OK', 'WARNING', or 'CRITICAL') and nothing else.
"""

class MonitoringTools:
    """
    A plugin that provides tools for the MonitoringAgent.
    In a real-world scenario, this would query a monitoring service like
    Prometheus, Datadog, or a cloud provider's health API.
    """
    @kernel_function(
        description="Checks the current operational status of a system component.",
        name="check_system_status",
    )
    def check_system_status(self, component_id: str) -> str:
        """
        A mock function to simulate checking a system's status.
        
        Args:
            component_id: The identifier of the system component to check.

        Returns:
            The current status as 'OK', 'WARNING', or 'CRITICAL'.
        """
        print(f"Monitoring: Checking status for component '{component_id}'...")
        # Simulate a random status for demonstration purposes.
        status = random.choice(["OK", "WARNING", "CRITICAL"])
        print(f"Monitoring: Status for '{component_id}' is {status}.")
        return status

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