"""
API Endpoints for Feedback and Reinforcement Learning
FOCUSED: Only RemediationAgent uses reinforcement learning
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from app.learning.feedback_store import feedback_store
import logging

router = APIRouter()


class FeedbackSubmission(BaseModel):
    """
    UI Feedback submission for RemediationAgent (SECONDARY SIGNAL)
    PRIMARY SIGNAL comes from MCP approval/rejection
    """
    feedback_id: str = Field(..., description="ID of the remediation output to rate")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1-5 stars")
    was_helpful: Optional[bool] = Field(None, description="Was the remediation helpful?")
    feedback_comments: Optional[str] = Field(None, description="Additional comments")
    improvements_suggested: Optional[str] = Field(None, description="Suggested improvements")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback"""
    success: bool
    message: str
    feedback_id: str


class StatisticsResponse(BaseModel):
    """Learning statistics for agents"""
    agent_statistics: dict
    total_feedbacks: int
    average_reward: float


@router.post("/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackSubmission):
    """
    Submit UI feedback for RemediationAgent output (SECONDARY SIGNAL)
    
    This enhances the PRIMARY learning signal from MCP approval/rejection.
    Together they help the remediation agent improve over time.
    
    Example:
    ```json
    {
        "feedback_id": "workflow_123_remediation_1234567890",
        "rating": 5,
        "was_helpful": true,
        "feedback_comments": "Excellent remediation plan!",
        "improvements_suggested": "Consider adding rollback steps"
    }
    ```
    """
    
    success = await feedback_store.add_ui_feedback(
        feedback_id=feedback.feedback_id,
        rating=feedback.rating,
        was_helpful=feedback.was_helpful,
        feedback_comments=feedback.feedback_comments,
        improvements_suggested=feedback.improvements_suggested
    )
    
    if success:
        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully. Thank you for helping improve the remediation agent!",
            feedback_id=feedback.feedback_id
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Feedback ID '{feedback.feedback_id}' not found"
        )


@router.get("/feedback/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    Get learning statistics for RemediationAgent
    
    Returns metrics like:
    - Total remediations generated
    - MCP approval/rejection counts
    - Approval rate
    - Average reward score
    - Learning examples available
    
    Note: Only RemediationAgent uses reinforcement learning.
    Monitoring and Analysis agents don't need RL (deterministic tasks).
    """
    
    stats = feedback_store.get_statistics()
    
    # Format for RemediationAgent only
    agent_stats = {
        "RemediationAgent": stats
    }
    
    # Extract metrics
    total_feedbacks = stats.get("approved_count", 0) + stats.get("rejected_count", 0)
    average_reward = stats.get("average_reward", 0)
    
    return StatisticsResponse(
        agent_statistics=agent_stats,
        total_feedbacks=total_feedbacks,
        average_reward=average_reward
    )


@router.get("/feedback/statistics/{agent_name}")
async def get_agent_statistics(agent_name: str):
    """
    Get learning statistics for RemediationAgent
    
    Note: Only RemediationAgent uses RL. Other agents return empty stats.
    """
    
    if agent_name != "RemediationAgent":
        # Return empty stats for non-RL agents
        return {
            "agent_name": agent_name,
            "statistics": {
                "message": "This agent doesn't use reinforcement learning"
            }
        }
    
    stats = feedback_store.get_statistics()
    
    return {
        "agent_name": agent_name,
        "statistics": stats
    }


@router.get("/feedback/improvements/{agent_name}")
async def get_improvement_suggestions(agent_name: str):
    """
    Get improvement suggestions for RemediationAgent
    
    Includes UI feedback suggestions + rejection reasons from MCP
    """
    
    if agent_name != "RemediationAgent":
        return {
            "agent_name": agent_name,
            "improvement_suggestions": [],
            "count": 0,
            "message": "This agent doesn't use reinforcement learning"
        }
    
    suggestions = feedback_store.get_improvement_suggestions()
    
    return {
        "agent_name": agent_name,
        "improvement_suggestions": suggestions,
        "count": len(suggestions)
    }


@router.get("/feedback/top-examples/{agent_name}")
async def get_top_examples(
    agent_name: str,
    limit: int = 5,
    min_reward: float = 0.7
):
    """
    Get top-rated remediation examples (approved by humans)
    
    These are used for in-context learning
    """
    
    if agent_name != "RemediationAgent":
        return {
            "agent_name": agent_name,
            "examples_count": 0,
            "examples": [],
            "message": "This agent doesn't use reinforcement learning"
        }
    
    examples = feedback_store.get_top_examples(
        limit=limit,
        min_reward=min_reward
    )
    
    return {
        "agent_name": agent_name,
        "examples_count": len(examples),
        "examples": [
            {
                "feedback_id": ex.feedback_id,
                "timestamp": ex.timestamp,
                "rating": ex.rating,
                "reward_score": ex.reward_score,
                "was_helpful": ex.was_helpful,
                "approval_status": ex.approval_status,
                "approved_commands": ex.approved_commands_count,
                "rejected_commands": ex.rejected_commands_count,
                "input_preview": ex.input_data[:200] + "..." if len(ex.input_data) > 200 else ex.input_data,
                "output_preview": ex.output_data[:200] + "..." if len(ex.output_data) > 200 else ex.output_data,
            }
            for ex in examples
        ]
    }


@router.get("/feedback/workflow/{workflow_id}")
async def get_workflow_feedback_ids(workflow_id: str):
    """
    Get feedback ID for RemediationAgent in a specific workflow
    
    Use this to get the feedback ID you can rate after a workflow completes
    """
    
    feedback_ids = []
    
    for feedback in feedback_store.feedback_cache:
        if feedback.workflow_id == workflow_id:
            feedback_ids.append({
                "feedback_id": feedback.feedback_id,
                "agent_name": "RemediationAgent",
                "timestamp": feedback.timestamp,
                "has_ui_feedback": feedback.rating is not None,
                "approval_status": feedback.approval_status,
                "approval_id": feedback.approval_id
            })
    
    return {
        "workflow_id": workflow_id,
        "feedback_opportunities": feedback_ids,
        "count": len(feedback_ids)
    }


class MCPApprovalCallback(BaseModel):
    """Callback from MCP server when commands are approved/rejected"""
    approval_id: str = Field(..., description="The approval ID from MCP server")
    status: Literal["approved", "rejected"] = Field(..., description="Approval status")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection if rejected")
    approved_count: int = Field(0, description="Number of commands approved")
    rejected_count: int = Field(0, description="Number of commands rejected")


@router.post("/feedback/mcp-approval")
async def receive_mcp_approval(callback: MCPApprovalCallback):
    """
    Webhook endpoint for MCP server to notify us of approval/rejection

    This is the PRIMARY learning signal for RemediationAgent.
    The MCP server calls this when a human approves or rejects commands.
    
    Example payload from MCP:
    ```json
    {
        "approval_id": "approval_123abc",
        "status": "approved",
        "approved_count": 5,
        "rejected_count": 0
    }
    ```
    
    Or for rejection:
    ```json
    {
        "approval_id": "approval_123abc",
        "status": "rejected",
        "rejection_reason": "Commands too aggressive, needs investigation first",
        "approved_count": 0,
        "rejected_count": 5
    }
    ```
    """
    
    logging.info(f"📥 Received MCP approval callback: {callback.approval_id} - {callback.status}")
    
    success = await feedback_store.add_mcp_approval_feedback(
        approval_id=callback.approval_id,
        status=callback.status,
        rejection_reason=callback.rejection_reason,
        approved_count=callback.approved_count,
        rejected_count=callback.rejected_count
    )
    
    if success:
        logging.info(f"✅ Successfully recorded {callback.status} for approval_id: {callback.approval_id}")
        return {
            "success": True,
            "message": f"Approval status '{callback.status}' recorded successfully",
            "approval_id": callback.approval_id
        }
    else:
        logging.warning(f"⚠️  No matching feedback found for approval_id: {callback.approval_id}")
        raise HTTPException(
            status_code=404,
            detail=f"No feedback found for approval_id: {callback.approval_id}"
        )

