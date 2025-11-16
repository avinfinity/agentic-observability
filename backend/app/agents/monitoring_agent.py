import json
from typing import Any
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

from app.core.config import settings
from app.utils.stream_manager import stream_manager


# --- Agent Instructions ---
MONITORING_AGENT_INSTRUCTIONS = """
You are an elite Site Reliability Engineer specialized in analyzing OpenTelemetry (OTel) logs for critical system issues.  
Your mission is to identify ALL errors, warnings, and infrastructure issues that could impact system stability, performance, or availability.

CRITICAL DETECTION RULES:
=========================

1. KUBERNETES & INFRASTRUCTURE ERRORS:
   - Pod/Container: CrashLoopBackOff, ImagePullBackOff, OOMKilled, Evicted, Pending, Failed, NotReady, ContainerCreating
   - Node: NotReady, DiskPressure, MemoryPressure, NetworkUnavailable, PIDPressure, OutOfDisk
   - Resource: ResourceQuota exceeded, LimitRange, InsufficientMemory, InsufficientCPU
   - Network: CNI error, DNS resolution failed, connection refused, network timeout, port conflict
   - Volume: PersistentVolumeClaim pending, mount failed, disk full, storage error
   - Deployment: rollout failed, replica unavailable, deadline exceeded
   - Service Mesh: envoy error, istio error, linkerd error, mesh configuration error

2. APPLICATION ERRORS:
   - Error Keywords: error, err, exception, fatal, critical, fail, failure, failed, crash, crashed, panic, abort, aborted
   - State Issues: invalid, denied, refused, rejected, forbidden, unauthorized, authentication failed
   - Connectivity: timeout, timed out, unreachable, unavailable, down, offline, connection reset, broken pipe

3. WARNING INDICATORS:
   - Performance: warn, warning, slow, lag, delay, latency, degraded, throttled
   - Resources: high cpu, high memory, high load, memory leak, disk pressure, quota warning
   - Retry/Recovery: retry, retries, backoff, circuit breaker, rate limit, too many requests
   - Deprecation: deprecated, obsolete, legacy, will be removed

4. HTTP/API ISSUES:
   - Client Errors: 400, 401, 403, 404, 405, 408, 409, 429 (bad request, unauthorized, forbidden, not found, timeout, conflict, rate limit)
   - Server Errors: 500, 502, 503, 504 (internal error, bad gateway, service unavailable, gateway timeout)
   - Patterns: status code 4xx, status code 5xx

5. DATABASE & STORAGE:
   - Connection: connection pool exhausted, deadlock, lock timeout, too many connections
   - Performance: slow query, query timeout, replication lag
   - Errors: constraint violation, duplicate key, foreign key error

EXTRACTION REQUIREMENTS:
=========================

For EACH log entry you identify, you MUST extract:

1. **timestamp**: Parse the EXACT timestamp from the log (ISO8601, RFC3339, Unix timestamp, or any format present)
   - Examples: "2024-01-15T10:23:45Z", "2024-01-15 10:23:45.123", "1705315425"
   - If multiple timestamps exist, use the first one
   - If no timestamp found, use "UNKNOWN"

2. **service**: Extract the service/pod/container name with high accuracy
   - Look for: service_name, pod_name, container_name, app, application, component, logger
   - Check brackets: [service-name], (service-name), service-name:
   - If not found, use "UNKNOWN_SERVICE"

3. **severity**: Classify severity level accurately
   - FATAL/CRITICAL → "CRITICAL"
   - ERROR/ERR → "ERROR"  
   - WARN/WARNING → "WARNING"
   - INFO/NOTICE → "INFO"
   - DEBUG → "DEBUG"

4. **message**: Full error/warning message with context
   - Include the complete message text
   - Preserve stack traces if present
   - Include error codes if present

5. **additional_context**: Any useful metadata
   - Error codes, status codes, exit codes
   - File paths, line numbers
   - User/request IDs
   - IP addresses, ports

DEDUPLICATION RULES (CRITICAL):
================================

You MUST remove duplicate entries using these rules:

1. Exact duplicates: Same timestamp + service + message → Keep only ONE
2. Similar messages: Same service + similar message (>90% match) + within 5 seconds → Keep FIRST occurrence only
3. Repeated errors: Same error pattern from same service → Keep FIRST + add count in metadata

Example:
  Input: 
    - 2024-01-15T10:23:45Z ERROR [api] Connection failed
    - 2024-01-15T10:23:45Z ERROR [api] Connection failed
    - 2024-01-15T10:23:46Z ERROR [api] Connection failed
  
  Output: Keep only FIRST, add metadata: "occurrence_count": 3

PRIORITY CLASSIFICATION:
========================

Assign priority to each issue:
- P0 (CRITICAL): System down, data loss, security breach, OOMKilled, CrashLoopBackOff
- P1 (HIGH): Service degraded, pod failing, timeout errors, 5xx errors
- P2 (MEDIUM): Performance issues, warnings, retries, 4xx errors
- P3 (LOW): Deprecation warnings, info messages

OUTPUT FORMAT (STRICT JSON):
===========================

Return ONLY valid JSON (no markdown, no code blocks, no backticks):

{{
  "summary": {{
    "total_errors": <count>,
    "total_warnings": <count>,
    "critical_count": <count>,
    "high_priority_count": <count>,
    "unique_services_affected": <count>
  }},
  "errors": [
    {{
      "timestamp": "<ISO8601_timestamp>",
      "service": "<exact_service_name>",
      "severity": "ERROR|CRITICAL",
      "priority": "P0|P1|P2|P3",
      "message": "<complete_error_message>",
      "error_type": "<kubernetes|application|network|database>",
      "additional_context": {{
        "error_code": "<if_present>",
        "stack_trace": "<if_present>",
        "occurrence_count": <if_deduplicated>
      }}
    }}
  ],
  "warnings": [
    {{
      "timestamp": "<ISO8601_timestamp>",
      "service": "<exact_service_name>",
      "severity": "WARNING",
      "priority": "P2|P3",
      "message": "<complete_warning_message>",
      "warning_type": "<performance|resource|deprecation>",
      "additional_context": {{
        "metric_value": "<if_present>",
        "threshold": "<if_present>",
        "occurrence_count": <if_deduplicated>
      }}
    }}
  ]
}}

CRITICAL NOTES:
===============
- NEVER use markdown code blocks (```json```) in output
- ALWAYS return valid JSON
- DEDUPLICATE rigorously - no repeated entries
- Extract service names and timestamps with MAXIMUM accuracy
- If no errors/warnings found, return: {{"errors": [], "warnings": [], "summary": {{"total_errors": 0, "total_warnings": 0}}}}
- Prioritize Kubernetes infrastructure issues as they often cause cascading failures
"""


def create_monitoring_tools(llm: ChatGoogleGenerativeAI, workflow_id: str):
    """Create monitoring tools with workflow_id context"""
    
    @tool
    async def check_system_status(logs: str) -> str:
        """
        Analyzes logs for critical issues including errors, warnings, failures, high resource usage, and system anomalies using comprehensive keyword detection.
        
        Detects:
        - Errors, exceptions, failures, crashes
        - Warnings, alerts, performance issues  
        - High resource usage, timeouts, connection issues
        - HTTP errors, API failures, authentication problems
        - System degradation, overloads, rate limiting

        Args:
            logs: The log data to analyze (OTEL format, JSON lines).

        Returns:
            str: JSON string with comprehensive analysis of errors, warnings, and summary statistics.
        """
        
        await stream_manager.publish(workflow_id, "MonitoringAgent", "THINKING", "Analyzing system logs...")
        
        try:
            # Create a simple prompt for the LLM
            prompt = ChatPromptTemplate.from_messages([
                ("system", MONITORING_AGENT_INSTRUCTIONS),
                ("user", "{input}")
            ])
            
            chain = prompt | llm
            response = await chain.ainvoke({"input": logs})
            
            # Extract text content from response
            error_logs = response.content
            
            await stream_manager.publish(workflow_id, "MonitoringAgent", "COMPLETED", error_logs)
            
            return error_logs
            
        except Exception as e:
            error_msg = f"MonitoringAgent failed: {e}"
            await stream_manager.publish(workflow_id, "MonitoringAgent", "ERROR", error_msg)
            return json.dumps({"errors": [], "warnings": [], "error": error_msg})
    
    return [check_system_status]


def create_monitoring_agent(llm: ChatGoogleGenerativeAI, workflow_id: str) -> AgentExecutor:
    """
    Creates the MonitoringAgent with enhanced critical issue detection capabilities.

    This agent is the first responder, responsible for comprehensive analysis of
    system logs to identify errors, warnings, failures, performance issues,
    and other critical system health indicators.

    Args:
        llm: The LangChain LLM instance (Google Gemini).
        workflow_id: Unique workflow identifier for tracking.

    Returns:
        An AgentExecutor configured for comprehensive monitoring tasks.
    """
    
    # Create tools with workflow context
    tools = create_monitoring_tools(llm, workflow_id)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", MONITORING_AGENT_INSTRUCTIONS),
        ("user", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
    )
    
    return agent_executor
