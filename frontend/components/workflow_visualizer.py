
import streamlit as st
import re

from streamlit_flow import (
    StreamlitFlowState,
    StreamlitFlowNode,
    StreamlitFlowEdge,
    streamlit_flow,
)
from streamlit_flow.layouts import ManualLayout

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

    initial_nodes = [
        StreamlitFlowNode(
            id="LLM",
            pos=(400, 225),
            targetPosition="left",
            data={"label": "LLM", "base_label": "LLM", "icon": "components/llm_icon.png"},
            style={"backgroundColor": "#FFF3E0", "color": "#6D4C41", "border": "2px solid #FF9800", "boxShadow": "0 0 10px #FF9800"},
        ),
        StreamlitFlowNode(
            id="MonitoringAgent",
            pos=(0, 0),
            data={"label": "Monitoring Agent", "base_label": "Monitoring Agent", "spinner": "components/spinner.gif", "tick": "components/tick.png"},
            style=STYLE_PENDING,
        ),
        StreamlitFlowNode(
            id="AnalysisAgent",
            pos=(0, 150),
            data={"label": "Analysis Agent", "base_label": "Analysis Agent", "spinner": "components/spinner.gif", "tick": "components/tick.png"},
            style=STYLE_PENDING,
        ),
        StreamlitFlowNode(
            id="RemediationAgent",
            pos=(0, 300),
            data={"label": "Remediation Agent", "base_label": "Remediation Agent", "spinner": "components/spinner.gif", "tick": "components/tick.png"},
            style=STYLE_PENDING,
        ),
    ]

    initial_edges = [
        StreamlitFlowEdge(
            id="edge_analysis_to_llm",
            source="AnalysisAgent",
            target="LLM",
            style=EDGE_STYLE_PENDING,
            animated=True,
            type="straight",
        ),
        StreamlitFlowEdge(
            id="edge_monitoring_to_llm",
            source="MonitoringAgent",
            target="LLM",
            style=EDGE_STYLE_PENDING,
            animated=True,
            type="straight",
        ),
        StreamlitFlowEdge(
            id="edge_remediation_to_llm",
            source="RemediationAgent",
            target="LLM",
            style=EDGE_STYLE_PENDING,
            animated=True,
            type="straight",
        ),
        # Directed straight edges between agents
        StreamlitFlowEdge(
            id="edge_analysis_to_monitoring",
            source="MonitoringAgent",
            target="AnalysisAgent",
            style=EDGE_STYLE_PENDING,
            animated=False,
            markerEnd={"type": "arrowclosed", "color": "#1E88E5", "width": 32, "height": 32},
            type="straight",
        ),
        StreamlitFlowEdge(
            id="edge_monitoring_to_remediation",
            source="AnalysisAgent",
            target="RemediationAgent",
            style=EDGE_STYLE_PENDING,
            animated=False,
            markerEnd={"type": "arrowclosed", "color": "#1E88E5", "width": 32, "height": 32},
            type="straight",
        ),
    ]

    return StreamlitFlowState(nodes=initial_nodes, edges=initial_edges)


def update_flow_node_by_message(state: StreamlitFlowState, agent_name: str, status: str, content:str) -> StreamlitFlowState:
    """
    Updates a node's style and label based on a single message from the orchestrator.
    """
    if not agent_name or not status:
        return state

    agent_node = None
    for node in state.nodes:
        if node.id == agent_name:
            agent_node = node
            break
    
    if not agent_node:
        return state
    else:
        if status in ('WORKING', 'THINKING'):
            agent_node.style = STYLE_ACTIVE
            for edge in state.edges:
                if edge.target == agent_name:
                    edge.style = EDGE_STYLE_ACTIVE
                    edge.animated = True
        elif status == 'COMPLETED':
            agent_node.style = STYLE_COMPLETED
            for edge in state.edges:
                if edge.target == agent_name:
                    edge.style = EDGE_STYLE_COMPLETED
                    edge.animated = False

        agent_node.data['label'] = f"{agent_node.data['base_label']}\n{content}"
    
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
        height=400,
        fit_view=True,
        show_controls=False,
        show_minimap=False,
        layout=ManualLayout(),
        get_node_on_click=True,
        get_edge_on_click=True,
        pan_on_drag=True,
        allow_zoom=True,
        min_zoom=0.5,
        enable_pane_menu=False,
        enable_node_menu=False,
        enable_edge_menu=False,
        hide_watermark=True,
    )