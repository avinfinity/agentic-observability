"""
Feedback Storage System for Reinforcement Learning
Stores agent outputs, human feedback, and success metrics
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Literal
from pathlib import Path
from dataclasses import dataclass, asdict
import asyncio
from collections import defaultdict


@dataclass
class RemediationFeedback:
    """
    Feedback record for RemediationAgent output
    Primary learning signal comes from MCP approval/rejection
    """
    feedback_id: str
    workflow_id: str
    timestamp: str
    
    # Input/Output for learning
    input_data: str  # Root cause analysis from AnalysisAgent
    output_data: str  # Remediation plan JSON
    
    # MCP Approval Feedback (PRIMARY SIGNAL)
    approval_status: Optional[Literal["pending", "approved", "rejected"]] = None
    approval_id: Optional[str] = None  # Primary approval_id (for backward compatibility)
    approval_ids: Optional[List[str]] = None  # All approval_ids for this remediation
    rejection_reason: Optional[str] = None
    approved_commands_count: Optional[int] = None
    rejected_commands_count: Optional[int] = None
    
    # Optional UI Feedback (SECONDARY SIGNAL)
    rating: Optional[int] = None  # 1-5 stars
    was_helpful: Optional[bool] = None
    feedback_comments: Optional[str] = None
    improvements_suggested: Optional[str] = None
    
    # Computed metrics
    reward_score: Optional[float] = None  # Computed reward (0-1)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'RemediationFeedback':
        """Create RemediationFeedback from dict, filtering out old/unexpected fields"""
        # Define expected fields for RemediationFeedback
        expected_fields = {
            'feedback_id', 'workflow_id', 'timestamp', 'input_data', 'output_data',
            'approval_status', 'approval_id', 'approval_ids', 'rejection_reason',
            'approved_commands_count', 'rejected_commands_count',
            'rating', 'was_helpful', 'feedback_comments', 'improvements_suggested', 'reward_score'
        }
        
        # Filter to only include expected fields
        filtered_data = {k: v for k, v in data.items() if k in expected_fields}
        
        return RemediationFeedback(**filtered_data)


class FeedbackStore:
    """
    Focused feedback storage for RemediationAgent reinforcement learning
    Uses MCP approval/rejection as primary learning signal
    """
    
    def __init__(self, storage_path: str = "data/feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.remediation_file = self.storage_path / "remediation_feedback.jsonl"
        
        # In-memory cache for fast access (only RemediationAgent)
        self.feedback_cache: List[RemediationFeedback] = []
        
        # Mapping from approval_id to feedback_id for quick lookup
        self.approval_to_feedback: Dict[str, str] = {}
        
        # Load existing feedback
        self._load_feedback()
    
    def _load_feedback(self):
        """Load remediation feedback from disk"""
        if self.remediation_file.exists():
            with open(self.remediation_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            feedback = RemediationFeedback.from_dict(json.loads(line))
                            self.feedback_cache.append(feedback)
                            
                            # Map all approval_ids to this feedback
                            if feedback.approval_ids:
                                for approval_id in feedback.approval_ids:
                                    self.approval_to_feedback[approval_id] = feedback.feedback_id
                            elif feedback.approval_id:
                                # Backward compatibility: single approval_id
                                self.approval_to_feedback[feedback.approval_id] = feedback.feedback_id
                        except Exception as e:
                            print(f"Error loading feedback: {e}")
    
    async def save_remediation_output(
        self,
        workflow_id: str,
        input_data: str,
        output_data: str,
        approval_id: Optional[str] = None
    ) -> str:
        """
        Save remediation agent output for learning
        Links to approval_id from MCP server
        """
        feedback_id = f"{workflow_id}_remediation_{datetime.now().timestamp()}"
        
        feedback = RemediationFeedback(
            feedback_id=feedback_id,
            workflow_id=workflow_id,
            timestamp=datetime.now().isoformat(),
            input_data=input_data,
            output_data=output_data,
            approval_status="pending",
            approval_id=approval_id
        )
        
        # Save to cache
        self.feedback_cache.append(feedback)
        
        # Map approval_id to feedback_id
        if approval_id:
            self.approval_to_feedback[approval_id] = feedback_id
        
        # Append to file
        with open(self.remediation_file, 'a') as f:
            f.write(json.dumps(feedback.to_dict()) + '\n')
        
        print(f"💾 Saved remediation feedback: {feedback_id} (approval_id: {approval_id})")
        return feedback_id
    
    async def add_mcp_approval_feedback(
        self,
        approval_id: str,
        status: Literal["approved", "rejected"],
        rejection_reason: Optional[str] = None,
        approved_count: int = 0,
        rejected_count: int = 0
    ) -> bool:
        """
        Record MCP approval/rejection as primary learning signal
        This is called when human approves/rejects commands in MCP UI
        
        Note: A single feedback entry may have multiple approval_ids.
        We accumulate the counts from all approvals/rejections.
        """
        # Find feedback by approval_id
        feedback_id = self.approval_to_feedback.get(approval_id)
        if not feedback_id:
            print(f"⚠️  No feedback found for approval_id: {approval_id}")
            return False
        
        # Update the feedback
        for i, feedback in enumerate(self.feedback_cache):
            if feedback.feedback_id == feedback_id:
                # Accumulate command counts (since one feedback may have multiple approval_ids)
                current_approved = feedback.approved_commands_count or 0
                current_rejected = feedback.rejected_commands_count or 0
                
                feedback.approved_commands_count = current_approved + approved_count
                feedback.rejected_commands_count = current_rejected + rejected_count
                
                # Update overall status (if any rejection, mark as partial/rejected)
                if status == "rejected":
                    feedback.approval_status = "rejected"
                    # Append rejection reason
                    if rejection_reason:
                        if feedback.rejection_reason:
                            feedback.rejection_reason += f"; {rejection_reason}"
                        else:
                            feedback.rejection_reason = rejection_reason
                elif status == "approved" and feedback.approval_status != "rejected":
                    # Only set to approved if not already rejected
                    feedback.approval_status = "approved"
                
                # Compute reward based on accumulated counts
                feedback.reward_score = self._compute_reward(feedback)
                
                self.feedback_cache[i] = feedback
                self._rewrite_feedback_file()
                
                print(f"✅ Updated feedback {feedback_id}: {status} for approval_id {approval_id}")
                print(f"   Total: {feedback.approved_commands_count} approved, {feedback.rejected_commands_count} rejected (reward: {feedback.reward_score:.2f})")
                return True
        
        return False
    
    async def add_ui_feedback(
        self,
        feedback_id: str,
        rating: Optional[int] = None,
        was_helpful: Optional[bool] = None,
        feedback_comments: Optional[str] = None,
        improvements_suggested: Optional[str] = None
    ) -> bool:
        """
        Add optional UI feedback (secondary signal)
        This enhances MCP approval feedback but is not primary
        """
        for i, feedback in enumerate(self.feedback_cache):
            if feedback.feedback_id == feedback_id:
                feedback.rating = rating
                feedback.was_helpful = was_helpful
                feedback.feedback_comments = feedback_comments
                feedback.improvements_suggested = improvements_suggested
                
                # Recompute reward with UI feedback
                feedback.reward_score = self._compute_reward(feedback)
                
                self.feedback_cache[i] = feedback
                self._rewrite_feedback_file()
                
                return True
        
        return False
    
    def _compute_reward(self, feedback: RemediationFeedback) -> float:
        """
        Compute reward score (0-1) from feedback
        PRIMARY: MCP approval/rejection (higher weight)
        SECONDARY: UI feedback (enhancement)
        """
        rewards = []
        weights = []
        
        # PRIMARY SIGNAL: MCP Approval Status (most important)
        if feedback.approval_status == "approved":
            # Full approval = high reward
            approval_ratio = 1.0
            if feedback.approved_commands_count and feedback.rejected_commands_count is not None:
                total = feedback.approved_commands_count + feedback.rejected_commands_count
                approval_ratio = feedback.approved_commands_count / total if total > 0 else 1.0
            rewards.append(approval_ratio)
            weights.append(4.0)  # 4x weight for approval
        
        elif feedback.approval_status == "rejected":
            # Rejection = low reward (but not zero - can learn from mistakes)
            rewards.append(0.2)
            weights.append(4.0)  # 4x weight for rejection
        
        # SECONDARY SIGNALS: UI Feedback
        if feedback.rating is not None:
            rewards.append(feedback.rating / 5.0)
            weights.append(1.0)
        
        if feedback.was_helpful is not None:
            rewards.append(1.0 if feedback.was_helpful else 0.0)
            weights.append(1.0)
        
        # Compute weighted average
        if rewards:
            total_weight = sum(weights)
            weighted_sum = sum(r * w for r, w in zip(rewards, weights))
            return weighted_sum / total_weight
        
        return 0.5  # Neutral if no feedback yet
    
    def _rewrite_feedback_file(self):
        """Rewrite entire feedback file (after update)"""
        with open(self.remediation_file, 'w') as f:
            for feedback in self.feedback_cache:
                f.write(json.dumps(feedback.to_dict()) + '\n')
    
    def get_top_examples(
        self,
        limit: int = 5,
        min_reward: float = 0.7
    ) -> List[RemediationFeedback]:
        """Get best remediation examples for in-context learning"""
        
        # Filter by reward and approval status
        scored_feedbacks = [
            f for f in self.feedback_cache
            if f.reward_score is not None and f.reward_score >= min_reward
            and f.approval_status is not None
        ]
        
        # Sort by reward score
        scored_feedbacks.sort(key=lambda x: x.reward_score, reverse=True)
        
        return scored_feedbacks[:limit]
    
    def get_statistics(self) -> Dict:
        """Get learning statistics for remediation agent"""
        total_outputs = len(self.feedback_cache)
        
        approved = [f for f in self.feedback_cache if f.approval_status == "approved"]
        rejected = [f for f in self.feedback_cache if f.approval_status == "rejected"]
        pending = [f for f in self.feedback_cache if f.approval_status == "pending"]
        
        scored = [f for f in self.feedback_cache if f.reward_score is not None]
        
        # Calculate total commands (not just feedback entries)
        total_approved_commands = sum(f.approved_commands_count or 0 for f in approved)
        total_rejected_commands = sum(f.rejected_commands_count or 0 for f in rejected)
        total_commands = total_approved_commands + total_rejected_commands
        
        return {
            "total_outputs": total_outputs,
            "approved_count": total_approved_commands,  # Total commands approved
            "rejected_count": total_rejected_commands,  # Total commands rejected
            "pending_count": len(pending),
            "approval_rate": total_approved_commands / total_commands if total_commands > 0 else 0,
            "average_reward": sum(f.reward_score for f in scored) / len(scored) if scored else 0,
            "learning_examples": len([f for f in scored if f.reward_score >= 0.7])
        }
    
    def get_rejection_reasons(self) -> List[str]:
        """Get all rejection reasons to learn from mistakes"""
        reasons = []
        for f in self.feedback_cache:
            if f.rejection_reason:
                reasons.append(f.rejection_reason)
        return reasons
    
    def get_improvement_suggestions(self) -> List[str]:
        """Get all improvement suggestions"""
        suggestions = []
        for f in self.feedback_cache:
            if f.improvements_suggested:
                suggestions.append(f.improvements_suggested)
            if f.rejection_reason:
                suggestions.append(f"Avoid: {f.rejection_reason}")
        return suggestions
    
    # Backward compatibility for orchestrator
    async def save_agent_output(
        self,
        workflow_id: str,
        agent_name: str,
        input_data: str,
        output_data: str
    ) -> str:
        """
        Backward compatibility wrapper
        Only saves if agent is RemediationAgent
        """
        if "Remediation" in agent_name:
            return await self.save_remediation_output(
                workflow_id=workflow_id,
                input_data=input_data,
                output_data=output_data
            )
        # For other agents, return a dummy ID (no storage)
        return f"{workflow_id}_{agent_name}_no_storage"


# Global instance
feedback_store = FeedbackStore()

