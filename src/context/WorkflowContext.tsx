import { createContext, useContext } from 'react';

export interface WorkflowState {
  id: string;
  repository_id: string;
  repository_name: string;
  goal: string;
  workflow_type: string;
  status: 'queued' | 'starting' | 'retrieving' | 'planning' | 'executing' | 'waiting_approval' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step: string;
  logs: any[];
  planSteps: any[];
  currentStepIdx: number;
  retrievedChunks: any[];
  tokensUsed: number;
  providersUsed: string[];
  duration: number;
  confidence: number;
  analytics: any;
  executionReport: any;
  approvalDiff: string | null;
  approvalFiles: string[];
  approvalReason: string;
  collaboration?: {
    findings_count: number;
    validated_count: number;
    conflicts_count: number;
    confidence: number;
    consensus_id: string | null;
  };
}

export interface WorkflowContextType {
  workflows: Record<string, WorkflowState>;
  activeWorkflowId: string | null;
  selectedWorkflowId: string | null;
  historyWorkflows: any[];
  isLoadingHistory: boolean;
  runningWorkflows: WorkflowState[];
  
  startWorkflow: (repositoryId: string, goal: string, template: string) => Promise<string>;
  pauseWorkflow: (workflowId: string) => Promise<void>;
  resumeWorkflow: (workflowId: string) => Promise<void>;
  cancelWorkflow: (workflowId: string) => Promise<void>;
  approveWorkflow: (workflowId: string, approved: boolean, reason?: string) => Promise<void>;
  deleteWorkflow: (workflowId: string) => Promise<void>;
  loadWorkflowDetails: (workflowId: string) => Promise<void>;
  fetchHistory: (repositoryId?: string) => Promise<void>;
  setActiveWorkflowId: (id: string | null) => void;
  setSelectedWorkflowId: (id: string | null) => void;
  clearWorkspace: () => void;
}

export const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);


export const useWorkflow = (): WorkflowContextType => {
  const ctx = useContext(WorkflowContext);
  if (!ctx) throw new Error('useWorkflow must be used inside <WorkflowProvider>');
  return ctx;
};
