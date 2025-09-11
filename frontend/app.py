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

def reset_workflow_state():
    """Resets all session state variables for a new workflow run."""
    st.session_state.messages = queue.Queue()
    st.session_state.flow_state = initialize_flow_state()
    st.session_state.listener_started = False
    st.session_state.workflow_id = None
    st.session_state.fetched_logs = ""
    st.session_state.agent_details = {
        "MonitoringAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "AnalysisAgent": {"input": "", "output": "", "status": "pending", "content": ""},
        "RemediationAgent": {"input": "", "output": "", "status": "pending", "content": ""},
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


st.title("✨ Multi-Agent Framework for Microservice Observability ✨")
st.markdown('''
- AI agents will work together to monitor, analyze, and remediate the infra problems at real-time.
- Watch their collaboration in real-time below.
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

    st.session_state.agent_details[agent]["status"] = status
    st.session_state.agent_details[agent]["content"] = content

    if st.session_state.flow_state:
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
                st.rerun()
                st.toast("Workflow finished!")
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