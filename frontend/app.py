import streamlit as st
import os
import queue
import time
from services.api_client import APIClient
from components.workflow_visualizer import (
    initialize_flow_state,
    update_flow_node_by_message,
    render_flow,
)
from components.feedback_panel import (
    render_feedback_panel,
    render_learning_statistics
)

# --- Configuration ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if "workflow_id" not in st.session_state:
    st.session_state.workflow_id = None
if "listener_started" not in st.session_state:
    st.session_state.listener_started = False
if "flow_state" not in st.session_state:
    st.session_state.flow_state = initialize_flow_state()
if "agent_details" not in st.session_state:
    st.session_state.agent_details = {
       "MonitoringAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "AnalysisAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "RemediationAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "KubectlCommandAgent": {"input": "", "output": "", "status": "pending", "content": ""},  # Hidden from UI
        "OrchestratorAgent": {"input": "", "output": "", "status": "pending", "content": ""}
    }
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(BACKEND_URL)
if "log_pull_interval_in_sec" not in st.session_state:
    st.session_state.log_pull_interval_in_sec = "10"
if "filter_pattern" not in st.session_state:
    st.session_state.filter_pattern = "*error* or *ERR* or *warning*"
if "fetched_logs" not in st.session_state:
    st.session_state.fetched_logs = ""
if "workflow_complete" not in st.session_state:
    st.session_state.workflow_complete = False
if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False

def reset_workflow_state():
    """Resets all session state variables for a new workflow run."""
    st.session_state.messages = queue.Queue()
    st.session_state.flow_state = initialize_flow_state()
    st.session_state.listener_started = False
    st.session_state.workflow_id = None
    st.session_state.fetched_logs = ""
    st.session_state.workflow_complete = False
    st.session_state.show_feedback = False
    st.session_state.agent_details = {
        "MonitoringAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "AnalysisAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "RemediationAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "KubectlCommandAgent": {"input": "", "output": "", "status": "pending", "content": ""},  # Hidden from UI
        "OrchestratorAgent": {"input": "", "output": "", "status": "pending", "content": ""}
    }

st.set_page_config(layout="wide")

with st.sidebar:
    st.header("Control Panel")
    with st.expander("Start Workflow", expanded=False):
        if st.button("🚀 Start Agent Workflow", use_container_width=True, type="primary"):
            reset_workflow_state()
            with st.spinner("Initializing workflow..."):
                try:
                    logs = st.session_state.api_client.fetch_logs(
                        pull_interval=st.session_state.log_pull_interval_in_sec,
                        filter_pattern=st.session_state.filter_pattern
                    )
                    st.session_state.fetched_logs = logs
                    st.success(f"Logs fetched successfully!")
                    
                    workflow_id = st.session_state.api_client.start_workflow(logs)
                    st.session_state.workflow_id = workflow_id
                    st.success(f"Workflow started with ID: `{workflow_id}`")
                    
                    st.session_state.api_client.listen_to_stream(
                        workflow_id, st.session_state.messages
                    )
                    st.session_state.listener_started = True
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start workflow: {e}")

        if st.button("Refresh workflow", use_container_width=True, type="secondary"):
            st.rerun()
        
        # Text boxes for configuration
        st.session_state.log_pull_interval_in_sec = st.text_input(
            "Log Pull Interval (sec)", 
            value=st.session_state.log_pull_interval_in_sec,
            placeholder="Enter interval in seconds"
        )
        
        st.session_state.filter_pattern = st.text_input(
            "Filter Pattern", 
            value=st.session_state.filter_pattern,
            placeholder="Enter filter pattern"
        )
    
    # Add learning statistics to sidebar
    if st.session_state.workflow_id:
        try:
            render_learning_statistics(st.session_state.api_client)
        except Exception as e:
            pass  # Silently fail if stats not available


st.title("✨ Multi-Agent Framework with Reinforcement Learning ✨")
st.markdown('''
- AI agents work together to monitor, analyze, and remediate infrastructure problems in real-time.
- **NEW:** Agents learn from your feedback and improve over time!
- Watch their collaboration below and rate their performance to help them learn.
            '''
)

# --- Workflow Visualization at Top ---
flow_placeholder = st.empty()

# --- Tabs for Agent Messages ---
if st.session_state.workflow_id:

    tabs = st.tabs(["Fetched Logs","Monitoring Agent", "Analysis Agent", "Remediation Agent"])
    agent_keys = ["MonitoringAgent", "AnalysisAgent", "RemediationAgent"]
    
    # Handle agent tabs
    agent_tab_indices = [1, 2, 3]  # Skipping index 0 which is for Fetched Logs
    for i, tab_index in enumerate(agent_tab_indices):
        details = st.session_state.agent_details.get(agent_keys[i], {})
        with tabs[tab_index]:
            st.subheader(agent_keys[i].replace("Agent", " Agent"))
            st.write(f"**Status:** {details.get('status', 'N/A')}")
            last_msg = details.get('content') or "No message yet."
            st.write(f"**Last Message:**")
            st.code(last_msg)
    
    # Handle Fetched Logs tab (index 2)
    with tabs[0]:
        st.subheader("Fetched Logs")
        if st.session_state.fetched_logs:
            st.write("**Logs retrieved from the system:**")
            st.code(st.session_state.fetched_logs, language="text")
        else:
            st.info("No logs have been fetched yet. Start a workflow to see logs.")
else:
    st.info("Start a workflow to see agent activity.")

# --- Real-time Update Logic ---
def parse_and_update_state(message):
    """Parses orchestrator messages and updates both agent_details and flow_state."""
    agent = message.get("agent_name")
    status = message.get("status")
    content = message.get("data", "")

    print("DEBUG MESSAGE RECEIVED:", agent, status)

    # Update agent details if agent exists in our tracking
    if agent in st.session_state.agent_details:
        st.session_state.agent_details[agent]["status"] = status
        st.session_state.agent_details[agent]["content"] = content

    # Skip KubectlCommandAgent in flow visualization (internal agent, not shown to users)
    if agent != "KubectlCommandAgent" and st.session_state.flow_state:
        st.session_state.flow_state = update_flow_node_by_message(
            st.session_state.flow_state, agent_name=agent, status=status, content=content
        )

def process_messages():
    """Checks the queue for new messages and updates the application state."""
    if not st.session_state.listener_started:
        return
    try:
        while not st.session_state.messages.empty():
            message = st.session_state.messages.get_nowait()
            if message is None:
                st.session_state.listener_started = False
                st.session_state.workflow_complete = True
                st.toast("✅ Workflow finished! You can now provide feedback.")
                st.rerun()
                break
            parse_and_update_state(message)
    except queue.Empty:
        pass
    except Exception as e:
        st.error(f"An error occurred while processing messages: {e}")
        st.session_state.listener_started = False

process_messages()

with flow_placeholder:
    if st.session_state.flow_state:
        render_flow(st.session_state.flow_state)
    else:
        st.info("Enter a prompt and start the workflow to see the visualization.")

if st.session_state.listener_started:
    time.sleep(1)
    st.rerun()

# --- Feedback Section (appears after workflow completion) ---
if st.session_state.workflow_complete and st.session_state.workflow_id:
    # Add a prominent button to show feedback
    if not st.session_state.show_feedback:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "📝 Provide Feedback (Help Agents Learn!)",
                use_container_width=True,
                type="primary",
                key="show_feedback_btn"
            ):
                st.session_state.show_feedback = True
                st.rerun()
    
    # Show feedback panel if requested
    if st.session_state.show_feedback:
        render_feedback_panel(st.session_state.api_client, st.session_state.workflow_id)
        
        # Add button to hide feedback
        if st.button("Hide Feedback Panel", key="hide_feedback_btn"):
            st.session_state.show_feedback = False
            st.rerun()