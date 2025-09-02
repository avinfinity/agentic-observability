# frontend/app.py

import streamlit as st
import os
import queue
import time

# Import the modular components designed for this application
from services.api_client import APIClient
from components.workflow_visualizer import (
    initialize_flow_state,
    update_flow_state,
    render_flow,
)

# --- Configuration ---
# The backend URL is retrieved from an environment variable, allowing for flexible
# deployment. It defaults to a local address for development. [4]
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
# Streamlit's session state is used to persist variables across script reruns. [5]
# This is crucial for maintaining the state of the workflow, messages, and UI.
if "workflow_id" not in st.session_state:
    st.session_state.workflow_id = None
if "messages" not in st.session_state:
    # A thread-safe queue is used to pass messages from the background SSE
    # listener thread to the main Streamlit thread.
    st.session_state.messages = queue.Queue()
if "flow_state" not in st.session_state:
    st.session_state.flow_state = None
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=BACKEND_URL)
if "listener_started" not in st.session_state:
    st.session_state.listener_started = False
if "logs" not in st.session_state:
    st.session_state.logs =

# --- UI Layout ---
# The main UI is split into two columns for a clean dashboard layout.
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
        # Reset the state for a new workflow run
        st.session_state.logs =
        st.session_state.messages = queue.Queue()  # Clear any old messages
        st.session_state.flow_state = initialize_flow_state()
        st.session_state.listener_started = False
        st.session_state.workflow_id = None

        with st.spinner("Initializing workflow..."):
            try:
                # Make the initial API call to start the backend process [4]
                workflow_id = st.session_state.api_client.start_workflow(prompt_input)
                st.session_state.workflow_id = workflow_id
                st.success(f"Workflow started with ID: `{workflow_id}`")

                # Start the background thread to listen for SSE events
                st.session_state.api_client.listen_to_stream(
                    workflow_id, st.session_state.messages
                )
                st.session_state.listener_started = True
                time.sleep(1)  # Allow a moment for the listener to connect
                st.rerun()  # Trigger an immediate rerun to start processing messages

            except Exception as e:
                st.error(f"Failed to start workflow: {e}")

    st.header("Live Event Logs")
    # A container with a fixed height is used to display raw log messages
    log_container = st.container(height=400)
    with log_container:
        for log in reversed(st.session_state.logs):
            st.expander(f"{log.get('agent_name', 'System')} - {log.get('status', 'INFO')}", expanded=False).json(log)

with col2:
    st.header("Agent Workflow Visualization")
    # An empty placeholder is used to render the flow diagram, allowing it to be
    # replaced on each rerun with the updated visualization.
    flow_placeholder = st.empty()


# --- Real-time Update Logic ---
def process_messages():
    """
    Checks the message queue for new updates from the SSE stream and updates
    the application state accordingly.
    """
    if not st.session_state.listener_started:
        return

    try:
        # Process all messages currently in the queue without blocking
        while not st.session_state.messages.empty():
            message = st.session_state.messages.get_nowait()
            if message is None:  # A 'None' message is a sentinel to end the stream
                st.session_state.listener_started = False
                st.toast("Workflow finished!")
                break

            # Append to logs and update the visual flow state
            st.session_state.logs.append(message)
            if st.session_state.flow_state:
                st.session_state.flow_state = update_flow_state(
                    st.session_state.flow_state, message
                )

    except queue.Empty:
        pass  # It's normal for the queue to be empty between updates
    except Exception as e:
        st.error(f"An error occurred while processing messages: {e}")
        st.session_state.listener_started = False

# This function is called on every script rerun to check for new data
process_messages()

# Render the flow diagram with the latest state
with flow_placeholder:
    if st.session_state.flow_state:
        render_flow(st.session_state.flow_state)
    else:
        st.info("Enter a prompt and start the workflow to see the visualization.")

# If the listener thread is active, schedule a rerun to create a polling effect,
# ensuring the UI continuously checks for new messages.
if st.session_state.listener_started:
    time.sleep(0.1)  # A short delay to prevent excessive CPU usage
    st.rerun()