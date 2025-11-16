import asyncio
import traceback
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.utils.stream_manager import stream_manager

# Import agent creation functions from the agents directory
from app.agents.monitoring_agent import create_monitoring_agent
from app.agents.analysis_agent import create_analysis_agent
from app.agents.remediation_agent import create_remediation_agent
from app.agents.kubectl_command_agent import create_kubectl_command_agent

# Import feedback store for reinforcement learning
from app.learning.feedback_store import feedback_store


def initialize_llm() -> ChatGoogleGenerativeAI:
    """
    Initializes the LangChain LLM with Google Gemini.

    Returns:
        An instance of ChatGoogleGenerativeAI.
    """
    
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_ID,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.TEMPERATURE,
        max_tokens=settings.MAX_TOKENS,
        convert_system_message_to_human=True,  # Required for Gemini
    )
    
    return llm


async def run_workflow(workflow_id: str, initial_logs: str):
    """
    Runs the full multi-agent workflow to diagnose and resolve a system issue.

    This function orchestrates the interaction between the Monitoring, Analysis,
    and Remediation agents in a sequential manner.

    Args:
        workflow_id: A unique identifier for this workflow run.
        initial_logs: The initial set of logs.
    """
    try:
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "WORKING", 
            f"Workflow started for id: '{workflow_id}'", 
            input_="", 
            output=""
        )

        # Initialize the LLM
        llm = initialize_llm()

        # Create specialized agents
        monitoring_agent = create_monitoring_agent(llm, workflow_id)
        analysis_agent = create_analysis_agent(llm, workflow_id)
        remediation_agent = create_remediation_agent(llm, workflow_id)
        kubectl_command_agent = create_kubectl_command_agent(llm, workflow_id)

        print(f"Initial logs:\n{initial_logs}\n")

        # Step 1: Monitoring Agent - Extract errors/warnings from logs
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "WORKING", 
            "Invoking MonitoringAgent to analyze logs..."
        )
        
        error_logs = await invoke_agent(
            monitoring_agent, 
            initial_logs, 
            workflow_id, 
            "MonitoringAgent"
        )
        
        if not error_logs or error_logs == "":
            await stream_manager.publish(
                workflow_id, 
                "OrchestratorAgent", 
                "COMPLETED", 
                "No errors or warnings found in logs. Workflow complete."
            )
            return

        # Step 2: Analysis Agent - Perform root cause analysis
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "WORKING", 
            "Invoking AnalysisAgent for root cause analysis..."
        )
        
        root_cause = await invoke_agent(
            analysis_agent, 
            error_logs, 
            workflow_id, 
            "AnalysisAgent"
        )
        
        if not root_cause or root_cause == "":
            await stream_manager.publish(
                workflow_id, 
                "OrchestratorAgent", 
                "COMPLETED", 
                "Could not determine root cause. Workflow complete."
            )
            return

        # Step 3: Remediation Agent - Generate remediation plan with kubectl commands
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "WORKING", 
            "Invoking RemediationAgent to generate remediation plan..."
        )
        
        remediation_plan = await invoke_agent(
            remediation_agent, 
            root_cause, 
            workflow_id, 
            "RemediationAgent"
        )
        
        if not remediation_plan or remediation_plan == "":
            await stream_manager.publish(
                workflow_id, 
                "OrchestratorAgent", 
                "COMPLETED", 
                "Could not generate remediation plan. Workflow complete."
            )
            return

        # Step 4: Kubectl Command Agent - Extract commands and submit to MCP server
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "WORKING", 
            "Invoking KubectlCommandAgent to extract and submit commands to MCP server..."
        )
        
        mcp_submission_result = await invoke_agent(
            kubectl_command_agent,
            remediation_plan,
            workflow_id,
            "KubectlCommandAgent",
            save_feedback=False  # No feedback needed for kubectl command agent
        )
        
        # Link approval_ids from MCP to the remediation feedback
        try:
            import json
            submission_data = json.loads(mcp_submission_result)
            submissions = submission_data.get("submissions", [])
            
            # Get the approval_ids from submissions
            approval_ids = [
                sub.get("approval_id") 
                for sub in submissions 
                if sub.get("approval_id")
            ]
            
            if approval_ids:
                # Update the most recent remediation feedback with ALL approval_ids
                # (The one we just saved in step 3)
                print(f"🔗 Linking {len(approval_ids)} approval_ids to remediation feedback: {approval_ids}")
                
                # Find the latest remediation feedback for this workflow
                for feedback in reversed(feedback_store.feedback_cache):
                    if (feedback.workflow_id == workflow_id and 
                        feedback.approval_ids is None):  # Not yet linked
                        # Link ALL approval_ids to this feedback
                        feedback.approval_ids = approval_ids
                        feedback.approval_id = approval_ids[0]  # Primary ID for backward compatibility
                        
                        # Map all approval_ids to this feedback_id
                        for approval_id in approval_ids:
                            feedback_store.approval_to_feedback[approval_id] = feedback.feedback_id
                        
                        # Rewrite the file to persist the update
                        feedback_store._rewrite_feedback_file()
                        print(f"✅ Linked {len(approval_ids)} approval_ids to feedback {feedback.feedback_id}")
                        break
        except Exception as e:
            print(f"⚠️  Failed to link approval_id to feedback: {e}")
            # Continue anyway - not critical for workflow completion

        # Final summary
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "COMPLETED", 
            f"Workflow completed successfully. Commands submitted to MCP server for approval."
        )
        
    except Exception as e:
        print(f"An error occurred during the workflow: {e}")
        traceback.print_exc()
        await stream_manager.publish(
            workflow_id, 
            "OrchestratorAgent", 
            "ERROR", 
            str(e), 
            input_="", 
            output=""
        )
    finally:
        await stream_manager.finish(workflow_id)


async def invoke_agent(agent_executor, input_data: str, workflow_id: str, agent_name: str, save_feedback: bool = True) -> str:
    """
    Invokes a LangChain agent executor with the given input.
    
    Optionally saves the input/output to feedback store for reinforcement learning.

    Args:
        agent_executor: The LangChain AgentExecutor to invoke.
        input_data: The input data to pass to the agent.
        workflow_id: Unique workflow identifier.
        agent_name: Name of the agent being invoked.
        save_feedback: Whether to save output to feedback store (default: True).

    Returns:
        The output from the agent as a string.
    """
    
    if input_data is None or input_data == "":
        return ""
    
    try:
        await stream_manager.publish(
            workflow_id, 
            agent_name, 
            "WORKING", 
            f"Agent '{agent_name}' started processing..."
        )

        # Invoke the agent
        result = await agent_executor.ainvoke({"input": input_data})
        
        # Extract output from result
        output = result.get("output", "")
        
        # Save to feedback store for reinforcement learning (if enabled)
        if save_feedback:
            feedback_id = await feedback_store.save_agent_output(
                workflow_id=workflow_id,
                agent_name=agent_name,
                input_data=input_data,
                output_data=output
            )
            print(f"💾 Saved for learning - Feedback ID: {feedback_id}")
        
        await stream_manager.publish(
            workflow_id, 
            agent_name, 
            "COMPLETED", 
            output
        )
        
        print(f"\n{agent_name} output:\n{output}\n")
        
        return output
        
    except Exception as e:
        error_msg = f"{agent_name} failed: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        await stream_manager.publish(
            workflow_id, 
            agent_name, 
            "ERROR", 
            error_msg
        )
        return ""
