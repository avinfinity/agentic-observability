"""
Feedback Panel Component for Reinforcement Learning
FOCUSED: Only RemediationAgent uses reinforcement learning
"""

import streamlit as st


def render_feedback_panel(api_client, workflow_id: str):
    """
    Renders the feedback panel for RemediationAgent only.
    
    This UI feedback is SECONDARY (20% weight).
    PRIMARY signal (80%) comes from MCP approval/rejection.
    
    Args:
        api_client: The API client instance
        workflow_id: The workflow ID to get feedback for
    """
    
    st.markdown("---")
    
    with st.expander("📊 Reinforcement Learning", expanded=True):
        st.markdown("""
        **Two Ways This Agent Learns:**
        1. 🎯 **PRIMARY**: Your approval/rejection of commands
        2. 💬 **SECONDARY**: This UI feedback (optional enhancement)
        
        Your input helps improve future suggestions!
        """)
        
        try:
            # Get feedback opportunities
            feedback_data = api_client.get_feedback_opportunities(workflow_id)
            opportunities = feedback_data.get("feedback_opportunities", [])
            
            if not opportunities:
                st.info("No feedback opportunities available for this workflow.")
                return
            
            # Filter for RemediationAgent only
            remediation_opps = [
                opp for opp in opportunities 
                if opp["agent_name"] == "RemediationAgent"
            ]
            
            if remediation_opps:
                render_agent_feedback(
                    api_client,
                    "RemediationAgent",
                    remediation_opps[0]
                )
            else:
                st.info("No feedback available for this workflow yet.")
        
        except Exception as e:
            st.error(f"Error loading feedback opportunities: {e}")


def render_agent_feedback(api_client, agent_name: str, feedback_opp: dict):
    """
    Renders feedback form for RemediationAgent.
    
    Args:
        api_client: The API client instance
        agent_name: Name of the agent (should be RemediationAgent)
        feedback_opp: Feedback opportunity dictionary
    """
    
    feedback_id = feedback_opp["feedback_id"]
    has_ui_feedback = feedback_opp.get("has_ui_feedback", False)
    approval_status = feedback_opp.get("approval_status", "pending")
    approval_id = feedback_opp.get("approval_id")
    
    # Show command approval status
    if approval_status == "approved":
        st.success("✅ Commands were APPROVED (Primary Learning Signal)")
    elif approval_status == "rejected":
        st.error("❌ Commands were REJECTED (Primary Learning Signal)")
    else:
        st.info(f"⏳ Commands pending approval (ID: {approval_id})")
    
    # Show UI feedback status
    if has_ui_feedback:
        st.success("✅ UI feedback already submitted!")
        if st.button(f"Update UI Feedback", key=f"update_{feedback_id}"):
            has_ui_feedback = False  # Allow re-rating
    
    if not has_ui_feedback:
        st.subheader("Optional: Enhance Learning with UI Feedback")
        st.caption("This is secondary feedback. Primary signal comes from command approval.")
        
        # Rating (1-5 stars)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.write("**Overall Rating:**")
        with col2:
            rating = st.select_slider(
                "Rating",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: "⭐" * x,
                key=f"rating_{feedback_id}",
                label_visibility="collapsed"
            )
        
        # Was helpful checkbox
        was_helpful = st.checkbox(
            "✅ Solution was helpful",
            value=True,
            key=f"helpful_{feedback_id}",
            help="Was the suggested solution clear and useful?"
        )
        
        # Comments
        with st.expander("💬 Additional Comments (Optional)", expanded=False):
            feedback_comments = st.text_area(
                "What did you like or dislike?",
                key=f"comments_{feedback_id}",
                placeholder="e.g., 'Commands were well-structured' or 'Missing investigation steps'",
                height=100
            )
            
            improvements_suggested = st.text_area(
                "Suggestions for improvement?",
                key=f"improvements_{feedback_id}",
                placeholder="e.g., 'Should include more rollback commands'",
                height=80
            )
        
        # Submit button
        if st.button(
            "🚀 Submit UI Feedback",
            type="primary",
            key=f"submit_{feedback_id}",
            use_container_width=True
        ):
            with st.spinner("Submitting feedback..."):
                try:
                    result = api_client.submit_feedback(
                        feedback_id=feedback_id,
                        rating=rating,
                        was_helpful=was_helpful,
                        feedback_comments=feedback_comments if feedback_comments else None,
                        improvements_suggested=improvements_suggested if improvements_suggested else None
                    )
                    
                    if result.get("success"):
                        st.success(f"✅ {result.get('message', 'UI feedback submitted!')}")
                        st.balloons()
                        
                        # Show learning info
                        st.info("💾 Your feedback helps make the agent better!")
                    else:
                        st.error("❌ Failed to submit feedback. Please try again.")
                
                except Exception as e:
                    st.error(f"Error submitting feedback: {e}")


def render_learning_statistics(api_client):
    """
    Renders learning statistics for RemediationAgent only.
    
    Shows MCP approval metrics (primary signal) + UI feedback (secondary).
    
    Args:
        api_client: The API client instance
    """
    
    try:
        stats = api_client.get_learning_statistics()
        
        st.sidebar.markdown("---")
        
        # Collapsible Reinforcement Learning section
        with st.sidebar.expander("📊 Reinforcement Learning", expanded=True):
            agent_stats = stats.get("agent_statistics", {}).get("RemediationAgent", {})
            
            if agent_stats and "message" not in agent_stats:
                # Command Approval Metrics (PRIMARY)
                st.markdown("**🎯 Command Approvals**")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Approved",
                        agent_stats.get('approved_count', 0),
                        help="Commands approved"
                    )
                
                with col2:
                    st.metric(
                        "Rejected",
                        agent_stats.get('rejected_count', 0),
                        help="Commands rejected"
                    )
                
                st.metric(
                    "Approval Rate",
                    f"{agent_stats.get('approval_rate', 0):.0%}",
                    help="% of commands approved"
                )
                
                # Learning Metrics
                st.markdown("---")
                st.markdown("**📚 Learning Pool**")
                
                st.metric(
                    "Learning Examples",
                    agent_stats.get('learning_examples', 0),
                    help="High-quality examples for training"
                )
                
                st.metric(
                    "Avg Reward",
                    f"{agent_stats.get('average_reward', 0):.2f}",
                    help="Combined reward score"
                )
                
                st.info("💡 Provide feedback to help make the agent better!")
            else:
                st.info("No learning data yet. Run a workflow to start!")
    
    except Exception as e:
        st.sidebar.error(f"Error loading statistics: {e}")

