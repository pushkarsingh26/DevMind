import axios from 'axios';
import type { TaskType, MultiAgentStatus } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const reviewRepository = async (repoUrl: string, task: TaskType): Promise<{ taskId: string }> => {
  try {
    const response = await client.post('/review', {
      repo_url: repoUrl,
      task: task,
    });
    return { taskId: response.data.job_id };
  } catch (error) {
    console.error('API connection error in reviewRepository:', error);
    throw new Error('Cannot connect to DevMind backend.');
  }
};

export const uploadRepository = async (file: File, task: TaskType): Promise<{ taskId: string }> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('task', task);
    
    const response = await client.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return { taskId: response.data.job_id };
  } catch (error) {
    console.error('API connection error in uploadRepository:', error);
    throw new Error('Cannot connect to DevMind backend.');
  }
};

export const getStatus = async (taskId: string): Promise<{
  status: MultiAgentStatus;
  resultText: string | null;
  isDone: boolean;
}> => {
  try {
    const response = await client.get(`/status/${taskId}`);
    const { status: jobStatus, progress, stage } = response.data;

    const isDone = jobStatus === 'completed' || progress === 100;
    const isFailed = jobStatus === 'failed';

    // Virtualize simple backend progress variables into the 4 frontend agents
    const status: MultiAgentStatus = {
      planner: { status: 'waiting', message: 'Waiting...' },
      retriever: { status: 'waiting', message: 'Waiting...' },
      reviewer: { status: 'waiting', message: 'Waiting...' },
      critic: { status: 'waiting', message: 'Waiting...' },
    };

    if (isDone) {
      status.planner = { status: 'completed', message: 'Completed' };
      status.retriever = { status: 'completed', message: 'Completed' };
      status.reviewer = { status: 'completed', message: 'Completed' };
      status.critic = { status: 'completed', message: 'Completed' };
    } else if (isFailed) {
      if (progress < 25) {
        status.planner = { status: 'failed', message: stage };
      } else if (progress < 50) {
        status.planner = { status: 'completed', message: 'Completed' };
        status.retriever = { status: 'failed', message: stage };
      } else if (progress < 75) {
        status.planner = { status: 'completed', message: 'Completed' };
        status.retriever = { status: 'completed', message: 'Completed' };
        status.reviewer = { status: 'failed', message: stage };
      } else {
        status.planner = { status: 'completed', message: 'Completed' };
        status.retriever = { status: 'completed', message: 'Completed' };
        status.reviewer = { status: 'completed', message: 'Completed' };
        status.critic = { status: 'failed', message: stage };
      }
    } else {
      if (progress < 25) {
        status.planner = { status: 'processing', message: stage };
      } else if (progress < 50) {
        status.planner = { status: 'completed', message: 'Completed' };
        status.retriever = { status: 'processing', message: stage };
      } else if (progress < 75) {
        status.planner = { status: 'completed', message: 'Completed' };
        status.retriever = { status: 'completed', message: 'Completed' };
        status.reviewer = { status: 'processing', message: stage };
      } else {
        status.planner = { status: 'completed', message: 'Completed' };
        status.retriever = { status: 'completed', message: 'Completed' };
        status.reviewer = { status: 'completed', message: 'Completed' };
        status.critic = { status: 'processing', message: stage };
      }
    }

    let resultText: string | null = null;
    if (isDone) {
      const resultResponse = await client.get(`/result/${taskId}`);
      resultText = resultResponse.data.result || null;
    } else if (isFailed) {
      resultText = `### Pipeline Failed\n\n**Error Details**: ${stage}\n`;
    }

    return {
      status,
      resultText,
      isDone: isDone || isFailed,
    };
  } catch (error) {
    console.error('API connection error in getStatus:', error);
    throw new Error('Cannot connect to DevMind backend.');
  }
};

export const getResult = async (jobId: string): Promise<{ status: string; result: string | null }> => {
  try {
    const response = await client.get(`/result/${jobId}`);
    return response.data;
  } catch (error) {
    console.error('API connection error in getResult:', error);
    throw new Error('Cannot connect to DevMind backend.');
  }
};
