#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as k8s from "@kubernetes/client-node";
import express from "express";
import cors from "cors";
import { v4 as uuidv4 } from "uuid";
import fetch from "node-fetch";

// Backend webhook URL for learning feedback
// Use 127.0.0.1 instead of localhost to force IPv4 (avoid IPv6 connection issues)
const BACKEND_WEBHOOK_URL = process.env.BACKEND_WEBHOOK_URL || "http://127.0.0.1:8000/api/v1/feedback/mcp-approval";

// Pending approval queue
const pendingApprovals = new Map();

// ============================================================================
// JOB QUEUE SYSTEM
// ============================================================================
// This queue handles command execution and webhook notifications asynchronously
// to prevent blocking the Approval UI.

class JobQueue {
  constructor() {
    this.queue = [];
    this.processing = false;
  }

  // Add a job to the queue
  enqueue(job) {
    this.queue.push(job);
    console.error(`📋 Job queued: ${job.type} (Queue size: ${this.queue.length})`);
    
    // Start processing if not already running
    if (!this.processing) {
      this.processQueue();
    }
  }

  // Process jobs from the queue one at a time
  async processQueue() {
    if (this.processing) {
      return; // Already processing
    }

    this.processing = true;

    while (this.queue.length > 0) {
      const job = this.queue.shift();
      
      try {
        console.error(`⚙️  Processing job: ${job.type} (${job.approvalId})`);
        await this.executeJob(job);
        console.error(`✅ Job completed: ${job.type} (${job.approvalId})`);
      } catch (error) {
        console.error(`❌ Job failed: ${job.type} (${job.approvalId}) - ${error.message}`);
      }
    }

    this.processing = false;
    console.error(`📭 Queue empty - worker idle`);
  }

  // Execute a single job
  async executeJob(job) {
    switch (job.type) {
      case "approve":
        return await this.handleApprovalJob(job);
      case "reject":
        return await this.handleRejectionJob(job);
      default:
        throw new Error(`Unknown job type: ${job.type}`);
    }
  }

  // Handle approval job: execute commands + notify backend
  async handleApprovalJob(job) {
    const { approvalId, approval } = job;

    try {
      // Execute kubectl commands
      console.error(`✅ Processing approval for ${approvalId}: ${approval.commands.length} commands`);
      console.error(`🔧 Executing commands for approval ${approvalId}...`);
      const result = await executeKubernetesAction(approval.action, approval.commands);
      console.error(`✅ Commands executed successfully for approval ${approvalId}`);

      // Notify backend for reinforcement learning
      try {
        const webhookData = {
          approval_id: approvalId,
          status: "approved",
          approved_count: approval.commands.length,
          rejected_count: 0
        };
        
        console.error(`📡 Sending approval webhook:`, JSON.stringify(webhookData));
        await notifyBackendApproval(webhookData);
        console.error(`✅ Backend notified successfully: Approval ${approvalId} approved (${approval.commands.length} commands)`);
      } catch (webhookError) {
        console.error(`❌ WEBHOOK FAILED for approval ${approvalId}:`);
        console.error(`   Error: ${webhookError.message}`);
        console.error(`   Stack: ${webhookError.stack}`);
      }

      // Call resolve callback if it exists (for MCP tool calls)
      if (approval.resolve) {
        approval.resolve({ approved: true, result });
      }

    } catch (error) {
      console.error(`❌ Approval ${approvalId} execution failed:`, error.message);

      // Notify backend about failure
      try {
        const webhookData = {
          approval_id: approvalId,
          status: "rejected",
          rejection_reason: `Execution failed: ${error.message}`,
          approved_count: 0,
          rejected_count: approval.commands.length
        };
        
        console.error(`📡 Sending execution failure webhook:`, JSON.stringify(webhookData));
        await notifyBackendApproval(webhookData);
        console.error(`✅ Backend notified about execution failure`);
      } catch (webhookError) {
        console.error(`❌ WEBHOOK FAILED for execution failure:`);
        console.error(`   Error: ${webhookError.message}`);
      }

      if (approval.reject) {
        approval.reject(error);
      }
    }
  }

  // Handle rejection job: notify backend
  async handleRejectionJob(job) {
    const { approvalId, approval, reason } = job;

    try {
      console.error(`🚫 Processing rejection for ${approvalId}: ${approval.commands.length} commands`);
      console.error(`   Rejection reason: ${reason || "Rejected by user"}`);
      
      // Notify backend
      const webhookData = {
        approval_id: approvalId,
        status: "rejected",
        rejection_reason: reason || "Rejected by user",
        approved_count: 0,
        rejected_count: approval.commands.length
      };
      
      console.error(`📡 Sending rejection webhook:`, JSON.stringify(webhookData));
      await notifyBackendApproval(webhookData);
      console.error(`✅ Backend notified successfully: Approval ${approvalId} rejected (${approval.commands.length} commands)`);

      // Call resolve callback if it exists (for MCP tool calls)
      if (approval.resolve) {
        approval.resolve({ approved: false, reason: reason || "Rejected by user" });
      }

    } catch (webhookError) {
      console.error(`❌ WEBHOOK FAILED for rejection ${approvalId}:`);
      console.error(`   Error: ${webhookError.message}`);
      console.error(`   Stack: ${webhookError.stack}`);
    }
  }
}

// Create the global job queue
const jobQueue = new JobQueue();

// ============================================================================
// END JOB QUEUE SYSTEM
// ============================================================================

// Kubernetes client setup
const kc = new k8s.KubeConfig();
try {
  kc.loadFromDefault();
} catch (error) {
  console.error("Warning: Could not load Kubernetes config. Some features may not work.");
}

const k8sApi = kc.makeApiClient(k8s.CoreV1Api);
const k8sAppsApi = kc.makeApiClient(k8s.AppsV1Api);
const k8sBatchApi = kc.makeApiClient(k8s.BatchV1Api);

// Express server for approval callback
const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static("src"));

const APPROVAL_PORT = 3100;

// Serve approval UI
app.get("/", (req, res) => {
  res.sendFile("approval-ui.html", { root: "src" });
});

// Approval endpoints
app.get("/api/approvals/pending", (req, res) => {
  const approvals = Array.from(pendingApprovals.values()).map(approval => ({
    id: approval.id,
    action: approval.action,
    commands: approval.commands,
    timestamp: approval.timestamp,
    metadata: approval.metadata,
  }));
  res.json({ approvals });
});

// Add endpoint to receive remediation proposals directly from Python backend
app.post("/api/approvals/propose", async (req, res) => {
  const { action, commands, metadata = {} } = req.body;
  
  try {
    const approvalId = uuidv4();
    
    // Store in pending approvals (without promise initially for immediate response)
    pendingApprovals.set(approvalId, {
      id: approvalId,
      action,
      commands,
      metadata,
      timestamp: new Date().toISOString(),
      resolve: null,
      reject: null,
    });
    
    console.error(`\n🔔 New Approval Request (ID: ${approvalId})`);
    console.error(`Action: ${action}`);
    console.error(`Commands: ${commands.length} command(s)`);
    console.error(`View at: http://localhost:${APPROVAL_PORT}/\n`);
    
    res.json({ 
      status: "pending", 
      approval_id: approvalId,
      message: "Remediation queued for approval",
      approval_url: `http://localhost:${APPROVAL_PORT}/`
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post("/api/approvals/:id/approve", async (req, res) => {
  const { id } = req.params;
  const approval = pendingApprovals.get(id);
  
  if (!approval) {
    return res.status(404).json({ error: "Approval request not found" });
  }

  try {
    // Remove from pending list IMMEDIATELY (before queuing job)
    // This ensures the UI updates instantly
    pendingApprovals.delete(id);
    
    // Respond to UI immediately
    console.error(`✅ Approval ${id} approved - queuing execution job...`);
    res.json({ status: "approved", message: "Commands queued for execution" });
    
    // Queue the job for background processing
    jobQueue.enqueue({
      type: "approve",
      approvalId: id,
      approval: approval
    });
    
  } catch (error) {
    console.error(`❌ Approval ${id} failed:`, error.message);
    res.status(500).json({ error: error.message });
  }
});

app.post("/api/approvals/:id/reject", async (req, res) => {
  const { id } = req.params;
  const { reason } = req.body;
  const approval = pendingApprovals.get(id);
  
  if (!approval) {
    return res.status(404).json({ error: "Approval request not found" });
  }

  try {
    // Remove from pending list IMMEDIATELY (before queuing job)
    // This ensures the UI updates instantly
    pendingApprovals.delete(id);
    
    // Respond to UI immediately
    console.error(`🚫 Approval ${id} rejected: ${reason || "No reason provided"}`);
    res.json({ status: "rejected", reason: reason || "Rejected by user" });
    
    // Queue the job for background processing
    jobQueue.enqueue({
      type: "reject",
      approvalId: id,
      approval: approval,
      reason: reason
    });
    
  } catch (error) {
    console.error(`❌ Reject failed:`, error.message);
    res.status(500).json({ error: error.message });
  }
});

// Start the Express server
app.listen(APPROVAL_PORT, () => {
  console.error(`Approval server listening on http://localhost:${APPROVAL_PORT}`);
  console.error(`View pending approvals at: http://localhost:${APPROVAL_PORT}/api/approvals/pending`);
});

// Helper function to execute Kubernetes actions
async function executeKubernetesAction(action, commands) {
  const results = [];
  
  for (const cmd of commands) {
    try {
      const result = await executeCommand(cmd);
      results.push({
        command: cmd.command,
        status: "success",
        output: result,
      });
    } catch (error) {
      results.push({
        command: cmd.command,
        status: "error",
        error: error.message,
      });
    }
  }
  
  return results;
}

// Execute individual kubectl command
async function executeCommand(cmd) {
  const { command, explanation } = cmd;
  
  // Parse kubectl command
  const parts = command.split(" ");
  
  if (!parts[0].includes("kubectl")) {
    throw new Error("Only kubectl commands are supported");
  }

  const action = parts[1]; // get, delete, scale, etc.
  const resource = parts[2]; // pod, deployment, etc.
  
  // Extract namespace
  const nsIndex = parts.indexOf("-n");
  const namespace = nsIndex !== -1 ? parts[nsIndex + 1] : "default";
  
  // Execute based on action type
  switch (action) {
    case "get":
      return await handleGet(resource, namespace, parts);
    case "delete":
      return await handleDelete(resource, namespace, parts);
    case "scale":
      return await handleScale(resource, namespace, parts);
    case "rollout":
      return await handleRollout(resource, namespace, parts);
    case "describe":
      return await handleDescribe(resource, namespace, parts);
    default:
      return { 
        message: `Command queued for manual execution: ${command}`,
        explanation 
      };
  }
}

// Kubernetes API handlers
async function handleGet(resource, namespace, parts) {
  const resourceName = parts[3]?.split("/")[1] || parts[3];
  
  try {
    switch (resource.toLowerCase()) {
      case "pods":
      case "pod":
        if (resourceName && resourceName !== "-n") {
          const { body } = await k8sApi.readNamespacedPod(resourceName, namespace);
          return { resource: "pod", name: resourceName, status: body.status.phase };
        } else {
          const { body } = await k8sApi.listNamespacedPod(namespace);
          return { 
            resource: "pods", 
            count: body.items.length,
            items: body.items.map(p => ({ name: p.metadata.name, status: p.status.phase }))
          };
        }
      
      case "deployments":
      case "deployment":
        if (resourceName && resourceName !== "-n") {
          const { body } = await k8sAppsApi.readNamespacedDeployment(resourceName, namespace);
          return { 
            resource: "deployment", 
            name: resourceName, 
            replicas: body.status.replicas,
            available: body.status.availableReplicas 
          };
        } else {
          const { body } = await k8sAppsApi.listNamespacedDeployment(namespace);
          return { 
            resource: "deployments", 
            count: body.items.length,
            items: body.items.map(d => ({ 
              name: d.metadata.name, 
              replicas: d.status.replicas 
            }))
          };
        }
      
      case "services":
      case "service":
      case "svc":
        const { body } = await k8sApi.listNamespacedService(namespace);
        return { 
          resource: "services", 
          count: body.items.length,
          items: body.items.map(s => ({ name: s.metadata.name, type: s.spec.type }))
        };
      
      default:
        return { message: `Get ${resource} - queued for manual execution` };
    }
  } catch (error) {
    throw new Error(`Failed to get ${resource}: ${error.message}`);
  }
}

async function handleDelete(resource, namespace, parts) {
  const resourceName = parts[3]?.split("/")[1] || parts[3];
  
  if (!resourceName || resourceName === "-n") {
    throw new Error("Resource name is required for delete operation");
  }
  
  try {
    switch (resource.toLowerCase()) {
      case "pod":
        await k8sApi.deleteNamespacedPod(resourceName, namespace);
        return { message: `Pod ${resourceName} deleted successfully` };
      
      case "deployment":
        await k8sAppsApi.deleteNamespacedDeployment(resourceName, namespace);
        return { message: `Deployment ${resourceName} deleted successfully` };
      
      default:
        return { message: `Delete ${resource} ${resourceName} - queued for manual execution` };
    }
  } catch (error) {
    throw new Error(`Failed to delete ${resource}: ${error.message}`);
  }
}

async function handleScale(resource, namespace, parts) {
  // kubectl scale deployment/my-deployment --replicas=3 -n namespace
  const resourceName = parts[2]?.split("/")[1];
  const replicasArg = parts.find(p => p.startsWith("--replicas="));
  const replicas = replicasArg ? parseInt(replicasArg.split("=")[1]) : null;
  
  if (!resourceName || replicas === null) {
    throw new Error("Resource name and replicas are required for scale operation");
  }
  
  try {
    const { body } = await k8sAppsApi.readNamespacedDeployment(resourceName, namespace);
    body.spec.replicas = replicas;
    await k8sAppsApi.replaceNamespacedDeployment(resourceName, namespace, body);
    return { message: `Deployment ${resourceName} scaled to ${replicas} replicas` };
  } catch (error) {
    throw new Error(`Failed to scale deployment: ${error.message}`);
  }
}

async function handleRollout(resource, namespace, parts) {
  // kubectl rollout restart deployment/my-deployment -n namespace
  const subcommand = parts[2]; // restart, undo, status
  const resourceType = parts[3]?.split("/")[0];
  const resourceName = parts[3]?.split("/")[1];
  
  if (subcommand === "restart" && resourceType === "deployment") {
    try {
      const { body } = await k8sAppsApi.readNamespacedDeployment(resourceName, namespace);
      
      // Add/update restart annotation to trigger rollout
      if (!body.spec.template.metadata.annotations) {
        body.spec.template.metadata.annotations = {};
      }
      body.spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = new Date().toISOString();
      
      await k8sAppsApi.replaceNamespacedDeployment(resourceName, namespace, body);
      return { message: `Deployment ${resourceName} restart initiated` };
    } catch (error) {
      throw new Error(`Failed to restart deployment: ${error.message}`);
    }
  }
  
  return { message: `Rollout ${subcommand} ${resource} - queued for manual execution` };
}

async function handleDescribe(resource, namespace, parts) {
  const resourceName = parts[3];
  
  try {
    switch (resource.toLowerCase()) {
      case "pod":
        const { body } = await k8sApi.readNamespacedPod(resourceName, namespace);
        return {
          name: body.metadata.name,
          namespace: body.metadata.namespace,
          status: body.status.phase,
          conditions: body.status.conditions,
          containers: body.spec.containers.map(c => ({
            name: c.name,
            image: c.image,
            state: body.status.containerStatuses?.find(cs => cs.name === c.name)?.state
          }))
        };
      
      default:
        return { message: `Describe ${resource} - queued for manual execution` };
    }
  } catch (error) {
    throw new Error(`Failed to describe ${resource}: ${error.message}`);
  }
}

// Notify backend webhook for reinforcement learning
async function notifyBackendApproval(approvalData) {
  try {
    const response = await fetch(BACKEND_WEBHOOK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(approvalData),
    });
    
    if (!response.ok) {
      throw new Error(`Backend webhook returned ${response.status}: ${await response.text()}`);
    }
    
    const result = await response.json();
    console.error(`✅ Backend learning webhook success: ${result.message}`);
    return result;
  } catch (error) {
    console.error(`❌ Backend webhook error: ${error.message}`);
    throw error;
  }
}

// Request human approval
async function requestApproval(action, commands, metadata = {}) {
  const approvalId = uuidv4();
  
  return new Promise((resolve, reject) => {
    pendingApprovals.set(approvalId, {
      id: approvalId,
      action,
      commands,
      metadata,
      timestamp: new Date().toISOString(),
      resolve,
      reject,
    });
    
    console.error(`\n🔔 Approval Required (ID: ${approvalId})`);
    console.error(`Action: ${action}`);
    console.error(`Commands: ${commands.length} command(s)`);
    console.error(`Approve at: http://localhost:${APPROVAL_PORT}/api/approvals/pending\n`);
  });
}

// MCP Server setup
const server = new Server(
  {
    name: "kubernetes-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "propose_remediation",
        description: "Propose remediation actions for Kubernetes issues. Requires human approval before execution.",
        inputSchema: {
          type: "object",
          properties: {
            action: {
              type: "string",
              description: "Description of the remediation action to take",
            },
            commands: {
              type: "array",
              description: "Array of kubectl commands to execute",
              items: {
                type: "object",
                properties: {
                  command: {
                    type: "string",
                    description: "The kubectl command to execute",
                  },
                  explanation: {
                    type: "string",
                    description: "Explanation of what this command does",
                  },
                  safety_level: {
                    type: "string",
                    description: "Safety level: SAFE, CAUTION, or DESTRUCTIVE",
                  },
                },
                required: ["command", "explanation"],
              },
            },
            metadata: {
              type: "object",
              description: "Additional metadata about the remediation",
              properties: {
                severity: { type: "string" },
                service: { type: "string" },
                namespace: { type: "string" },
              },
            },
          },
          required: ["action", "commands"],
        },
      },
      {
        name: "execute_kubectl",
        description: "Execute a kubectl command directly (requires approval for destructive operations)",
        inputSchema: {
          type: "object",
          properties: {
            command: {
              type: "string",
              description: "The kubectl command to execute",
            },
            namespace: {
              type: "string",
              description: "Kubernetes namespace",
              default: "default",
            },
          },
          required: ["command"],
        },
      },
      {
        name: "get_pending_approvals",
        description: "Get list of pending approval requests",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "propose_remediation": {
        const { action, commands, metadata = {} } = args;
        
        // Request approval
        const result = await requestApproval(action, commands, metadata);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "execute_kubectl": {
        const { command, namespace = "default" } = args;
        
        // Check if command is destructive
        const destructiveActions = ["delete", "drain", "cordon"];
        const isDestructive = destructiveActions.some(action => 
          command.toLowerCase().includes(action)
        );
        
        if (isDestructive) {
          // Require approval for destructive commands
          const result = await requestApproval(
            `Execute: ${command}`,
            [{ command, explanation: "Direct kubectl execution", safety_level: "DESTRUCTIVE" }],
            { namespace }
          );
          
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        } else {
          // Execute safe commands directly
          const result = await executeCommand({ command, explanation: "Direct execution" });
          
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }
      }

      case "get_pending_approvals": {
        const approvals = Array.from(pendingApprovals.values()).map(approval => ({
          id: approval.id,
          action: approval.action,
          timestamp: approval.timestamp,
          commands: approval.commands.length,
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ pending: approvals.length, approvals }, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ error: error.message }, null, 2),
        },
      ],
      isError: true,
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Kubernetes MCP Server running with Human-in-the-Loop approval");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

