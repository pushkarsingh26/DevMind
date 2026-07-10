import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Safely coerce unknown API response to an array. */
function safeArray<T>(data: unknown): T[] {
  return Array.isArray(data) ? (data as T[]) : [];
}

// ─── Workflow Lifecycle ────────────────────────────────────────────────────────

/**
 * Start a new autonomous workflow execution.
 * POST /api/workflows/start
 */
export const startWorkflow = async (
  repositoryId: string,
  goal: string,
  workflowType: string
): Promise<{ workflow_id: string; status: string }> => {
  const response = await client.post('/api/workflows/start', {
    repository_id: repositoryId,
    goal,
    workflow_type: workflowType,
  });
  return response.data;
};

/** @deprecated Use startWorkflow instead */
export const executeWorkflow = startWorkflow;

// ─── Workflow Queries ──────────────────────────────────────────────────────────

/**
 * List all workflow executions, optionally filtered by repository.
 * GET /api/workflows
 */
export const getWorkflows = async (repositoryId?: string): Promise<any[]> => {
  try {
    const response = await client.get('/api/workflows', {
      params: repositoryId ? { repository_id: repositoryId } : {},
    });
    return safeArray(response.data);
  } catch (e) {
    console.error('[agentService] getWorkflows error:', e);
    return [];
  }
};

/** @deprecated Use getWorkflows instead */
export const getHistory = getWorkflows;

/**
 * Get full details for a single workflow execution.
 * GET /api/workflows/{workflowId}
 */
export const getWorkflow = async (workflowId: string): Promise<any> => {
  const response = await client.get(`/api/workflows/${workflowId}`);
  if (!response.data || typeof response.data !== 'object') {
    throw new Error('Invalid workflow detail response from server');
  }
  return response.data;
};

/** @deprecated Use getWorkflow instead */
export const getWorkflowDetail = getWorkflow;

/**
 * List workflows in active execution states.
 * GET /api/workflows/running
 */
export const getRunningWorkflows = async (): Promise<any[]> => {
  try {
    const response = await client.get('/api/workflows/running');
    return safeArray(response.data);
  } catch (e) {
    console.error('[agentService] getRunningWorkflows error:', e);
    return [];
  }
};

/**
 * Get execution logs for a workflow.
 * GET /api/workflows/{workflowId}/logs
 */
export const getWorkflowLogs = async (workflowId: string): Promise<{ logs: any[] }> => {
  try {
    const response = await client.get(`/api/workflows/${workflowId}/logs`);
    return response.data;
  } catch (e) {
    console.error(`[agentService] getWorkflowLogs error for ${workflowId}:`, e);
    return { logs: [] };
  }
};

/**
 * Get lightweight status and progress for a workflow.
 * GET /api/workflows/{workflowId}/status
 */
export const getWorkflowStatus = async (workflowId: string): Promise<any> => {
  const response = await client.get(`/api/workflows/${workflowId}/status`);
  return response.data;
};

/**
 * Get the completed execution report for a workflow.
 * GET /api/workflows/{workflowId}/report
 */
export const getWorkflowReport = async (workflowId: string): Promise<any> => {
  const response = await client.get(`/api/workflows/${workflowId}/report`);
  return response.data;
};

// ─── Workflow Control ──────────────────────────────────────────────────────────

/**
 * Approve or reject pending code changes.
 * POST /api/workflows/{workflowId}/approve
 */
export const approveWorkflow = async (
  workflowId: string,
  approved: boolean,
  reason?: string
): Promise<any> => {
  const response = await client.post(`/api/workflows/${workflowId}/approve`, {
    approved,
    reason,
  });
  return response.data;
};

/**
 * Pause an active workflow execution.
 * POST /api/workflows/{workflowId}/pause
 */
export const pauseWorkflow = async (workflowId: string): Promise<any> => {
  const response = await client.post(`/api/workflows/${workflowId}/pause`);
  return response.data;
};

/**
 * Resume a paused workflow execution.
 * POST /api/workflows/{workflowId}/resume
 */
export const resumeWorkflow = async (workflowId: string): Promise<any> => {
  const response = await client.post(`/api/workflows/${workflowId}/resume`);
  return response.data;
};

/**
 * Cancel an active workflow execution.
 * POST /api/workflows/{workflowId}/cancel
 */
export const cancelWorkflow = async (workflowId: string): Promise<any> => {
  const response = await client.post(`/api/workflows/${workflowId}/cancel`);
  return response.data;
};

/**
 * Delete a workflow record and its filesystem data.
 * DELETE /api/workflows/{workflowId}
 */
export const deleteWorkflow = async (workflowId: string): Promise<any> => {
  const response = await client.delete(`/api/workflows/${workflowId}`);
  return response.data;
};

// ─── SSE Stream URL ────────────────────────────────────────────────────────────

/**
 * Returns the full URL for the global workflow SSE stream.
 */
export const getWorkflowStreamUrl = (): string => {
  return `${API_BASE_URL}/api/workflows/stream`;
};
