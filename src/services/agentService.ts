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

export const executeWorkflow = async (
  repositoryId: string,
  goal: string,
  workflowType: string
): Promise<{ workflow_id: string }> => {
  const response = await client.post('/agents/execute', {
    repository_id: repositoryId,
    goal,
    workflow_type: workflowType,
  });
  return response.data;
};

/** Always returns an array — never throws on empty or malformed responses. */
export const getHistory = async (repositoryId?: string): Promise<any[]> => {
  try {
    const response = await client.get('/agents/history', {
      params: repositoryId ? { repository_id: repositoryId } : {},
    });
    return safeArray(response.data);
  } catch (e) {
    console.error('[agentService] getHistory error:', e);
    return [];
  }
};

export const getWorkflowDetail = async (workflowId: string): Promise<any> => {
  const response = await client.get(`/agents/history/${workflowId}`);
  if (!response.data || typeof response.data !== 'object') {
    throw new Error('Invalid workflow detail response from server');
  }
  return response.data;
};

export const approveWorkflow = async (
  workflowId: string,
  approved: boolean,
  reason?: string
): Promise<any> => {
  const response = await client.post(`/agents/history/${workflowId}/approve`, {
    approved,
    reason,
  });
  return response.data;
};

export const deleteWorkflow = async (workflowId: string): Promise<any> => {
  const response = await client.delete(`/agents/history/${workflowId}`);
  return response.data;
};

export const getWorkflowStreamUrl = (workflowId: string): string => {
  return `${API_BASE_URL}/agents/stream/${workflowId}`;
};
