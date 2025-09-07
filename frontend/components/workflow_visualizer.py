
import streamlit as st
import re

from streamlit_flow import (
    StreamlitFlowState,
    StreamlitFlowNode,
    StreamlitFlowEdge,
    streamlit_flow,
)
from streamlit_flow.layouts import LayeredLayout

STYLE_PENDING = {"backgroundColor": "#E0E0E0", "color": "#333333"}
STYLE_ACTIVE = {
    "backgroundColor": "#BBDEFB",
    "color": "#1E88E5",
    "border": "2px solid #1E88E5",
    "boxShadow": "0 0 10px #1E88E5",
}
STYLE_COMPLETED = {"backgroundColor": "#C8E6C9", "color": "#388E3C"}
STYLE_ERROR = {"backgroundColor": "#FFCDD2", "color": "#D32F2F"}

EDGE_STYLE_PENDING = {"stroke": "#BDBDBD"}
EDGE_STYLE_ACTIVE = {"stroke": "#1E88E5", "strokeWidth": 2}
EDGE_STYLE_COMPLETED = {"stroke": "#66BB6A", "strokeWidth": 2}


def initialize_flow_state() -> StreamlitFlowState:
    """
    Initializes the visual state of the agent workflow diagram.

    This function defines the initial nodes (agents) and edges (connections)
    and sets their default "pending" styles. It's called once at the
    beginning of a new workflow.

    Returns:
        StreamlitFlowState: An object containing the initial nodes and edges.
    """

def initialize_flow_state() -> StreamlitFlowState:
    initial_nodes = [
        StreamlitFlowNode(
            id="AnalysisAgent",
            pos=(0, 0),
            data={"label": "Analysis Agent", "base_label": "Analysis Agent"},
            style=STYLE_PENDING,
        ),
        StreamlitFlowNode(
            id="MonitoringAgent",
            pos=(250, 0),
            data={"label": "Monitoring Agent", "base_label": "Monitoring Agent"},
            style=STYLE_PENDING,
        ),
        StreamlitFlowNode(
            id="RemediationAgent",
            pos=(500, 0),
            data={"label": "Remediation Agent", "base_label": "Remediation Agent"},
            style=STYLE_PENDING,
        ),
    ]

    initial_edges = [
        StreamlitFlowEdge(
            id="edge_analysis_to_monitoring",
            source="AnalysisAgent",
            target="MonitoringAgent",
            style=EDGE_STYLE_PENDING,
        ),
        StreamlitFlowEdge(
            id="edge_monitoring_to_remediation",
            source="MonitoringAgent",
            target="RemediationAgent",
            style=EDGE_STYLE_PENDING,
        ),
    ]

    return StreamlitFlowState(nodes=initial_nodes, edges=initial_edges)


def update_flow_node_by_message(state: StreamlitFlowState, message: dict) -> StreamlitFlowState:
    """
    Updates a node's style and label based on a single message from the orchestrator.
    """
    content = message.get("data", "")
    if not isinstance(content, str):
        return state

    agent_map = {
        "MonitoringAgent": {"invoked": "Invoking MonitoringAgent", "returned": r"MonitoringAgent returned: (.*)"},
        "AnalysisAgent": {"invoked": "Invoking AnalysisAgent", "returned": r"AnalysisAgent returned: (.*)"},
        "RemediationAgent": {"invoked": "Invoking RemediationAgent", "returned": r"RemediationAgent returned: (.*)"},
    }

    for agent_name, patterns in agent_map.items():
        for node in state.nodes:
            if node.id == agent_name:
                # Check if agent is invoked
                if patterns["invoked"] in content:
                    node.style = STYLE_ACTIVE
                    node.data['label'] = f"{node.data['base_label']}\nStatus: In Progress..."
                    for edge in state.edges:
                        if edge.target == agent_name:
                            edge.style = EDGE_STYLE_ACTIVE
                            edge.animated = True
                
                # Check if agent returned a result
                match = re.search(patterns["returned"], content, re.DOTALL)
                if match:
                    output = match.group(1).strip()
                    node.style = STYLE_COMPLETED
                    summary = (output[:40] + '...') if len(output) > 40 else output
                    node.data['label'] = f"{node.data['base_label']}\nResult: {summary}"
                    for edge in state.edges:
                        if edge.target == agent_name:
                            edge.style = EDGE_STYLE_COMPLETED
                            edge.animated = False
    return state


def update_flow_state(
    state: StreamlitFlowState, message: dict
) -> StreamlitFlowState:
    """
    Updates the visual state of the flow diagram based on a new message.

    This function is the core of the dynamic visualization. It takes the current
    state and a message from the backend, then updates the styles of the
    corresponding nodes and edges to reflect the new status (e.g., active, completed).

    Args:
        state (StreamlitFlowState): The current state of the diagram.
        message (dict): The JSON message received from the backend SSE stream.

    Returns:
        StreamlitFlowState: The new, updated state object.
    """
    agent_name = message.get("agent_name")
    status = message.get("status")

    if not agent_name or not status:
        return state

    # Find the node and edge to update
    for node in state.nodes:
        if node.id == agent_name:
            if status in ("STARTING", "THINKING", "STREAMING"):
                node.style = STYLE_ACTIVE
                # Also activate the edge leading to this node
                for edge in state.edges:
                    if edge.target == agent_name:
                        edge.style = EDGE_STYLE_ACTIVE
                        edge.animated = True
            elif status == "COMPLETED":
                node.style = STYLE_COMPLETED
                # De-animate the edge but keep it highlighted
                for edge in state.edges:
                    if edge.target == agent_name:
                        edge.style = EDGE_STYLE_COMPLETED
                        edge.animated = False
            elif status == "ERROR":
                node.style = STYLE_ERROR
                for edge in state.edges:
                    if edge.target == agent_name:
                        edge.animated = False

    return state


def render_flow(state: StreamlitFlowState):
    """
    Renders the flow diagram component in the Streamlit UI.

    Args:
        state (StreamlitFlowState): The current state object to be rendered.
    """
    streamlit_flow(
        key="agent_flow",
        state=state,
        height=650,
        fit_view=True,
        show_controls=False,
        show_minimap=True,
        # LayeredLayout automatically arranges nodes for a clean look [1]
        layout=LayeredLayout(direction="down", node_layer_spacing=150),
        get_node_on_click=False,
    )