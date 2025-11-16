import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.utils.stream_manager import stream_manager
from app.core.mcp_client import mcp_client


# --- Agent Instructions ---
KUBECTL_COMMAND_AGENT_INSTRUCTIONS = """
You are a Kubernetes command extraction and validation specialist.

Your mission is to parse remediation plans and extract kubectl commands in the EXACT format required by the MCP server API.

INPUT FORMAT:
=============

You will receive a remediation plan in JSON format containing steps with kubectl commands. Example:

{{
  "remediation_plans": [
    {{
      "service": "api-service",
      "issue": "Pod CrashLoopBackOff",
      "severity": "CRITICAL",
      "priority": "P0",
      "steps": [
        {{
          "phase": "INVESTIGATE",
          "commands": [
            {{
              "command": "kubectl describe pod api-service-7b4f9d -n production",
              "explanation": "Check pod events for crash details",
              "safety_level": "SAFE"
            }}
          ]
        }}
      ]
    }}
  ]
}}

MCP SERVER API FORMAT:
======================

The MCP server API expects EXACTLY this format:

{{
  "action": string,        # Brief description of the remediation
  "commands": [            # List of kubectl commands
    {{
      "command": string,
      "explanation": string,
      "safety_level": string
    }}
  ],
  "metadata": {{            # Additional context
    "severity": string,
    "priority": string,
    "service": string,
    "workflow_id": string,
    ... any other fields
  }}
}}

OUTPUT FORMAT (STRICT JSON):
============================

CRITICAL: Return ONLY raw JSON - NO markdown, NO code blocks, NO backticks, NO ```json```.
Start your response directly with [ and end with ].

Return as a LIST of MCP API payloads:

[
  {{
    "action": "<brief_description_of_remediation>",
    "commands": [
      {{
        "command": "kubectl ...",
        "explanation": "<what_this_does>",
        "safety_level": "SAFE|CAUTION|DESTRUCTIVE"
      }}
    ],
    "metadata": {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "priority": "P0|P1|P2|P3",
      "service": "<service_name>",
      "issue": "<original_issue>",
      "root_cause": "<if_available>",
      "phase": "<INVESTIGATE|REMEDIATE|VERIFY>"
    }}
  }}
]

SEVERITY MAPPING:
=================

Map plan priorities to metadata severity:
- P0/CRITICAL → "CRITICAL"
- P1/HIGH → "HIGH"
- P2/MEDIUM → "MEDIUM"
- P3/LOW → "LOW"

CRITICAL REQUIREMENTS:
======================

1. ✅ Output must be a JSON ARRAY of MCP API payloads
2. ✅ Each payload must have: action, commands, metadata
3. ✅ PRESERVE exact command text - do not modify kubectl commands
4. ✅ GROUP commands by remediation plan (one API call per plan)
5. ✅ Include all relevant metadata fields
6. ✅ NO MARKDOWN: Return pure JSON only - NO ```json``` blocks!
7. ✅ Start with [ and end with ] - nothing else
8. ✅ If no commands found, return empty array: []

EXAMPLES:
=========

Input:
{{
  "remediation_plans": [{{
    "service": "postgres-db",
    "issue": "High memory usage",
    "severity": "CRITICAL",
    "priority": "P0",
    "steps": [{{
      "phase": "REMEDIATE",
      "commands": [{{
        "command": "kubectl scale deployment/postgres --replicas=3 -n database",
        "explanation": "Scale up to handle load",
        "safety_level": "CAUTION"
      }}]
    }}]
  }}]
}}

Output:
[
  {{
    "action": "Scale postgres-db deployment to handle increased load",
    "commands": [
      {{
        "command": "kubectl scale deployment/postgres --replicas=3 -n database",
        "explanation": "Scale up to handle load",
        "safety_level": "CAUTION"
      }}
    ],
    "metadata": {{
      "severity": "CRITICAL",
      "priority": "P0",
      "service": "postgres-db",
      "issue": "High memory usage",
      "phase": "REMEDIATE"
    }}
  }}
]

REMEMBER:
=========
- Output format MUST match MCP server API exactly
- No conversion needed - this goes directly to the API
- One API payload per remediation plan
- Preserve all command details accurately
- DO NOT wrap output in ```json``` or any markdown - raw JSON only!
- Your first character must be [ and last character must be ]
"""


class KubectlCommandAgentExecutor:
    """
    Simple executor that formats commands and submits to MCP server.
    Not using LangChain agent pattern to avoid tool-calling complexity.
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, workflow_id: str):
        self.llm = llm
        self.workflow_id = workflow_id
    
    async def ainvoke(self, inputs: dict) -> dict:
        """Execute the kubectl command extraction and submission"""
        remediation_plan = inputs.get("input", "")
        
        await stream_manager.publish(
            self.workflow_id, 
            "KubectlCommandAgent", 
            "THINKING", 
            "Extracting kubectl commands from remediation plan..."
        )
        
        print("[KubectlCommandAgent] Starting command extraction and submission")
        
        try:
            # Use LLM to parse and structure commands in MCP API format
            prompt = ChatPromptTemplate.from_messages([
                ("system", KUBECTL_COMMAND_AGENT_INSTRUCTIONS),
                ("user", "{input}")
            ])
            
            chain = prompt | self.llm
            response = await chain.ainvoke({"input": remediation_plan})
            
            # Extract MCP API payloads (already in correct format)
            mcp_payloads_json = response.content
            print(f"[KubectlCommandAgent] LLM response: {mcp_payloads_json[:500]}...")
            
            # Strip markdown code blocks if present
            mcp_payloads_json = mcp_payloads_json.strip()
            if mcp_payloads_json.startswith("```json"):
                mcp_payloads_json = mcp_payloads_json[7:]  # Remove ```json
            elif mcp_payloads_json.startswith("```"):
                mcp_payloads_json = mcp_payloads_json[3:]  # Remove ```
            if mcp_payloads_json.endswith("```"):
                mcp_payloads_json = mcp_payloads_json[:-3]  # Remove ```
            mcp_payloads_json = mcp_payloads_json.strip()
            
            print(f"[KubectlCommandAgent] After markdown strip: {mcp_payloads_json[:200]}...")
            
            # Parse the LLM output (should be a list of MCP API payloads)
            try:
                mcp_payloads = json.loads(mcp_payloads_json)
                
                # Handle empty list
                if not mcp_payloads or len(mcp_payloads) == 0:
                    await stream_manager.publish(
                        self.workflow_id,
                        "KubectlCommandAgent",
                        "INFO",
                        "No commands found in remediation plan"
                    )
                    return {
                        "output": json.dumps({
                            "status": "no_commands",
                            "message": "No kubectl commands to submit"
                        })
                    }
                
                # Submit each payload directly to MCP server
                submission_results = []
                
                for payload in mcp_payloads:
                    service = payload.get("metadata", {}).get("service", "unknown")
                    num_commands = len(payload.get("commands", []))
                    
                    await stream_manager.publish(
                        self.workflow_id,
                        "KubectlCommandAgent",
                        "THINKING",
                        f"Submitting {num_commands} commands for {service} to MCP server..."
                    )
                    
                    # Add workflow_id to metadata
                    if "metadata" not in payload:
                        payload["metadata"] = {}
                    payload["metadata"]["workflow_id"] = self.workflow_id
                    
                    # Send to MCP server directly
                    print(f"[KubectlCommandAgent] Sending payload to MCP server: {payload['action']}")
                    mcp_response = await mcp_client.propose_remediation(
                        action=payload.get("action", "Remediation action"),
                        commands=payload.get("commands", []),
                        metadata=payload.get("metadata", {})
                    )
                    
                    print(f"[KubectlCommandAgent] MCP Response: {mcp_response}")
                    
                    # Track results
                    if "error" in mcp_response:
                        await stream_manager.publish(
                            self.workflow_id,
                            "KubectlCommandAgent",
                            "ERROR",
                            f"❌ MCP server error for {service}: {mcp_response['error']}"
                        )
                        submission_results.append({
                            "service": service,
                            "status": "error",
                            "error": mcp_response["error"]
                        })
                    elif "approval_id" in mcp_response:
                        await stream_manager.publish(
                            self.workflow_id,
                            "KubectlCommandAgent",
                            "INFO",
                            f"✅ Commands submitted for {service}! Approval ID: {mcp_response['approval_id']}"
                        )
                        submission_results.append({
                            "service": service,
                            "status": "submitted",
                            "approval_id": mcp_response["approval_id"]
                        })
                    else:
                        submission_results.append({
                            "service": service,
                            "status": "submitted",
                            "message": "Awaiting approval"
                        })
                
                # Final summary
                success_count = sum(1 for r in submission_results if r["status"] == "submitted")
                error_count = sum(1 for r in submission_results if r["status"] == "error")
                
                summary_message = f"📊 Submission Summary:\n"
                summary_message += f"  ✅ Successfully submitted: {success_count}\n"
                summary_message += f"  ❌ Failed: {error_count}\n"
                summary_message += f"  👉 Approve commands at: http://localhost:3100"
                
                await stream_manager.publish(
                    self.workflow_id,
                    "KubectlCommandAgent",
                    "COMPLETED",
                    summary_message
                )
                
                output = json.dumps({
                    "status": "completed",
                    "submissions": submission_results,
                    "total_submissions": len(submission_results),
                    "success_count": success_count,
                    "error_count": error_count
                })
                
                print(f"[KubectlCommandAgent] Completed successfully: {output}")
                return {"output": output}
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse LLM response as JSON: {str(e)}"
                print(f"[KubectlCommandAgent] JSON Parse Error: {error_msg}")
                print(f"[KubectlCommandAgent] Raw response: {mcp_payloads_json[:1000]}")
                await stream_manager.publish(
                    self.workflow_id,
                    "KubectlCommandAgent",
                    "ERROR",
                    error_msg
                )
                return {"output": json.dumps({"status": "error", "error": error_msg})}
            
        except Exception as e:
            error_msg = f"KubectlCommandAgent failed: {str(e)}"
            print(f"[KubectlCommandAgent] Exception: {error_msg}")
            import traceback
            traceback.print_exc()
            await stream_manager.publish(
                self.workflow_id,
                "KubectlCommandAgent",
                "ERROR",
                error_msg
            )
            return {"output": json.dumps({"status": "error", "error": error_msg})}


def create_kubectl_command_agent(llm: ChatGoogleGenerativeAI, workflow_id: str) -> KubectlCommandAgentExecutor:
    """
    Creates the KubectlCommandAgent with command extraction and MCP submission capabilities.
    
    Uses a simple executor pattern instead of LangChain agent to ensure commands are always submitted.
    
    Args:
        llm: The LangChain LLM instance (Google Gemini).
        workflow_id: Unique workflow identifier for tracking.
    
    Returns:
        A KubectlCommandAgentExecutor configured for kubectl command extraction and submission.
    """
    return KubectlCommandAgentExecutor(llm, workflow_id)

