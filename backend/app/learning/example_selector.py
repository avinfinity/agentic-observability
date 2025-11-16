"""
Example Selector for In-Context Learning
Focused on RemediationAgent using MCP approval feedback
"""

from typing import List, Dict, Optional
from app.learning.feedback_store import feedback_store, RemediationFeedback
import json


class RemediationExampleSelector:
    """
    Selects best remediation examples for in-context learning
    Uses MCP approval/rejection as primary signal
    """
    
    def get_few_shot_examples(
        self,
        num_examples: int = 3,
        min_reward: float = 0.85
    ) -> str:
        """Get few-shot examples formatted for prompt"""
        
        examples = feedback_store.get_top_examples(
            limit=num_examples,
            min_reward=min_reward
        )
        
        if not examples:
            return ""
        
        return self._format_examples(examples)
    
    def _format_examples(self, examples: List[RemediationFeedback]) -> str:
        """Format examples for inclusion in prompt"""
        
        if not examples:
            return ""
        
        formatted = "\n\n📚 LEARNING FROM APPROVED REMEDIATIONS:\n"
        formatted += "=" * 80 + "\n\n"
        formatted += "These remediation plans were APPROVED by humans and successfully resolved issues.\n"
        formatted += "Study them carefully and follow similar patterns:\n\n"
        
        for i, example in enumerate(examples, 1):
            status_emoji = "✅" if example.approval_status == "approved" else "⚠️"
            formatted += f"### {status_emoji} Example {i} (Reward: {example.reward_score:.2f}, Status: {example.approval_status})\n\n"
            
            # Show input (root cause)
            formatted += "**Root Cause Analysis (Input):**\n"
            formatted += self._truncate(example.input_data, 600) + "\n\n"
            
            # Show output (remediation plan)
            formatted += "**Remediation Plan (Output - APPROVED):**\n"
            formatted += self._truncate(example.output_data, 1000) + "\n\n"
            
            # Show approval details
            if example.approval_status == "approved":
                formatted += f"**✅ APPROVED:** {example.approved_commands_count} commands executed successfully\n\n"
            
            # Show feedback
            if example.feedback_comments:
                formatted += f"**Human Feedback:** {example.feedback_comments}\n\n"
            
            formatted += "-" * 80 + "\n\n"
        
        formatted += "**Key Learnings:**\n"
        formatted += "- These remediation plans were validated by humans\n"
        formatted += "- Focus on similar command structure and safety considerations\n"
        formatted += "- Follow the proven pattern: INVESTIGATE → REMEDIATE → VERIFY\n\n"
        
        return formatted
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "... [truncated]"
    
    def get_rejection_examples(self, num_examples: int = 2) -> str:
        """Get examples of REJECTED remediations to learn what to avoid"""
        
        rejected = [
            f for f in feedback_store.feedback_cache
            if f.approval_status == "rejected"
        ]
        
        rejected.sort(key=lambda x: x.reward_score if x.reward_score else 0)
        rejected = rejected[:num_examples]
        
        if not rejected:
            return ""
        
        formatted = "\n\n❌ REJECTED REMEDIATIONS - LEARN WHAT TO AVOID:\n"
        formatted += "=" * 80 + "\n\n"
        formatted += "These remediation plans were REJECTED by humans. Study the rejection reasons:\n\n"
        
        for i, example in enumerate(rejected, 1):
            formatted += f"### ❌ Rejected Example {i}\n\n"
            
            # Show what was wrong
            if example.rejection_reason:
                formatted += f"**Why It Was Rejected:** {example.rejection_reason}\n\n"
            
            # Show part of the bad output
            formatted += "**What NOT To Do:**\n"
            formatted += self._truncate(example.output_data, 500) + "\n\n"
            
            if example.improvements_suggested:
                formatted += f"**How to Fix It:** {example.improvements_suggested}\n\n"
            
            formatted += "-" * 80 + "\n\n"
        
        formatted += "**Remember:** Avoid these patterns and always consider human safety preferences.\n\n"
        
        return formatted
    
    def enhance_prompt(self, base_prompt: str) -> str:
        """Enhance prompt with approved examples and rejection warnings"""
        positive_examples = self.get_few_shot_examples(num_examples=3, min_reward=0.85)
        rejection_examples = self.get_rejection_examples(num_examples=1)
        
        enhanced = base_prompt
        
        if positive_examples:
            enhanced += "\n\n" + positive_examples
        
        if rejection_examples:
            enhanced += "\n\n" + rejection_examples
        
        return enhanced

