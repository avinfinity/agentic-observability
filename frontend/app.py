# frontend/app.py

import streamlit as st
import os
import queue
import time
import re

from services.api_client import APIClient
from components.workflow_visualizer import (
    initialize_flow_state,
    update_flow_node_by_message,
    render_flow,
)

# --- Configuration ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# --- Page Setup ---
st.set_page_config(
    page_title="Multi-Agent System Orchestrator",
    page_icon="🤖",
    layout="wide",
)
st.title("🤖 Multi-Agent System Orchestrator")
st.markdown(
    "Describe a system issue, and the AI agents will work together to monitor, analyze, and resolve it. "
    "Watch their collaboration in real-time below."
)

# --- Session State Initialization ---
if "workflow_id" not in st.session_state:
    st.session_state.workflow_id = None
if "messages" not in st.session_state:
    st.session_state.messages = queue.Queue()
if "flow_state" not in st.session_state:
    st.session_state.flow_state = None
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=BACKEND_URL)
if "listener_started" not in st.session_state:
    st.session_state.listener_started = False
if "agent_details" not in st.session_state:
    st.session_state.agent_details = {}

# --- Helper Functions ---
def reset_workflow_state():
    """Resets all session state variables for a new workflow run."""
    st.session_state.messages = queue.Queue()
    st.session_state.flow_state = initialize_flow_state()
    st.session_state.listener_started = False
    st.session_state.workflow_id = None
    st.session_state.agent_details = {
        "MonitoringAgent": {"input": "", "output": "", "status": "pending"},
        "AnalysisAgent": {"input": "", "output": "", "status": "pending"},
        "RemediationAgent": {"input": "", "output": "", "status": "pending"},
    }

# --- UI Layout ---
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Control Panel")
    prompt_input = st.text_area(
        "Enter the system issue to resolve:",
        "The primary database server is reporting high latency and occasional connection timeouts.",
        height=150,
        key="prompt_input",
    )

    if st.button("🚀 Start Agent Workflow", use_container_width=True, type="primary"):
        reset_workflow_state()
        with st.spinner("Initializing workflow..."):
            try:
                workflow_id = st.session_state.api_client.start_workflow(prompt_input)
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

    st.header("Agent Activity Details")
    if st.session_state.workflow_id:
        with st.container(border=True):
            details = st.session_state.agent_details["MonitoringAgent"]
            st.subheader("1. Monitoring Agent")
            st.write(f"**Status:** {details['status']}")
            if details['output']:
                st.write("**Result:**")
                st.info(f"📊 {details['output']}")

        with st.container(border=True):
            details = st.session_state.agent_details["AnalysisAgent"]
            st.subheader("2. Analysis Agent")
            st.write(f"**Status:** {details['status']}")
            if details['input']:
                st.write("**Input (Simulated Logs):**")
                st.code(details['input'], language='log')
            if details['output']:
                st.write("**Output (Root Cause):**")
                st.warning(f"🔍 {details['output']}")

        with st.container(border=True):
            details = st.session_state.agent_details.get("RemediationAgent", {})
            st.subheader("3. Remediation Agent")
            st.write(f"**Status:** {details.get('status', 'N/A')}")
            if details.get('input'):
                st.write("**Input (Analysis):**")
                st.code(details.get('input'), language='text')
            if details.get('output'):
                st.write("**Output (Result):**")
                st.success(f"✅ {details.get('output')}")
    else:
        st.info("Start a workflow to see agent activity.")

with col2:
    st.header("Agent Workflow Visualization")
    flow_placeholder = st.empty()

# --- Real-time Update Logic ---
def parse_and_update_state(message):
    """Parses orchestrator messages and updates both agent_details and flow_state."""
    agent = message.get("agent_name")
    status = message.get("status")
    content = message.get("data", "")
    input_ = message.get("input", "")
    output = message.get("output", "")


    print("DEBUG MESSAGE RECEIVED:", message)

    # Update agent status directly from message fields
    if agent in st.session_state.agent_details and status:
        st.session_state.agent_details[agent]["status"] = status
    if agent in st.session_state.agent_details and input_:
        st.session_state.agent_details[agent]["input"] = input_
    if agent in st.session_state.agent_details and output:
        st.session_state.agent_details[agent]["output"] = output

    # Optionally, keep regex-based parsing for legacy content
    # Monitoring Agent Logic
    if "Invoking MonitoringAgent" in content:
        st.session_state.agent_details["MonitoringAgent"]["status"] = "In Progress..."
    monitor_match = re.search(r"MonitoringAgent returned: (.*)", content, re.DOTALL)
    if monitor_match:
        output = monitor_match.group(1).strip()
        st.session_state.agent_details["MonitoringAgent"]["status"] = "Completed"
        st.session_state.agent_details["MonitoringAgent"]["output"] = output

    # Analysis Agent Logic
    if "Invoking AnalysisAgent" in content:
        st.session_state.agent_details["AnalysisAgent"]["status"] = "In Progress..."
        log_match = re.search(r"with simulated logs: (.*)", content, re.DOTALL)
        if log_match:
            st.session_state.agent_details["AnalysisAgent"]["input"] = log_match.group(1).strip()
    analysis_match = re.search(r"AnalysisAgent returned: (.*)", content, re.DOTALL)
    if analysis_match:
        output = analysis_match.group(1).strip()
        st.session_state.agent_details["AnalysisAgent"]["status"] = "Completed"
        st.session_state.agent_details["AnalysisAgent"]["output"] = output

    # Remediation Agent Logic
    if "Invoking RemediationAgent" in content:
        st.session_state.agent_details["RemediationAgent"]["status"] = "In Progress..."
        remediation_input_match = re.search(r"with the analysis: (.*)", content, re.DOTALL)
        if remediation_input_match:
            st.session_state.agent_details["RemediationAgent"]["input"] = remediation_input_match.group(1).strip()
    remediation_match = re.search(r"RemediationAgent returned: (.*)", content, re.DOTALL)
    if remediation_match:
        output = remediation_match.group(1).strip()
        st.session_state.agent_details["RemediationAgent"]["status"] = "Completed"
        st.session_state.agent_details["RemediationAgent"]["output"] = output

    # Update the flow diagram state based on the same message
    if st.session_state.flow_state:
        st.session_state.flow_state = update_flow_node_by_message(
            st.session_state.flow_state, message
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
    time.sleep(0.1)
    st.rerun()