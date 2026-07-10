import React, { createContext, useState, useEffect, useRef, useCallback, useContext, useMemo } from 'react';
import { AnalysisUIContext } from './AnalysisContext';
import * as api from '../services/agentService';

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

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [workflows, setWorkflows] = useState<Record<string, WorkflowState>>({});
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [historyWorkflows, setHistoryWorkflows] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(true);

  const uiContext = useContext(AnalysisUIContext);
  const addToast = uiContext?.addToast || (() => {});
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const reconnectAttemptRef = useRef<number>(0);
  const connectGlobalStreamRef = useRef<(() => void) | null>(null);

  // Load history runs
  const fetchHistory = useCallback(async (repositoryId?: string) => {
    setIsLoadingHistory(true);
    try {
      const runs = await api.getHistory(repositoryId);
      setHistoryWorkflows(runs);
    } catch (e) {
      console.error('[WorkflowContext] Error fetching history:', e);
      setHistoryWorkflows([]);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Sync details from backend
  const loadWorkflowDetails = useCallback(async (id: string) => {
    try {
      const data = await api.getWorkflowDetail(id);
      setWorkflows(prev => ({
        ...prev,
        [id]: {
          id: data.id,
          repository_id: data.repository_id,
          repository_name: data.repository_name || 'Unknown',
          goal: data.goal,
          workflow_type: data.workflow_type,
          status: data.status,
          progress: data.progress || 0,
          current_step: data.current_step || '',
          logs: prev[id]?.logs || [],
          planSteps: data.steps || [],
          currentStepIdx: data.steps ? data.steps.findIndex((s: any) => s.status === 'running' || s.step === data.current_step) : -1,
          retrievedChunks: data.report?.chunks_used || data.report?.retrieved_chunks || [],
          tokensUsed: data.analytics?.tokens_used || 0,
          providersUsed: data.analytics?.providers_used || [],
          duration: data.duration || 0,
          confidence: data.report?.confidence || 1.0,
          analytics: data.analytics || null,
          executionReport: data.report && Object.keys(data.report).length > 0 ? data.report : null,
          approvalDiff: data.diff || null,
          approvalFiles: data.affected_files || [],
          approvalReason: data.approval_reason || ''
        }
      }));
      // If completed, fetch logs too
      const logsData = await api.getWorkflowLogs(id);
      setWorkflows(prev => {
        if (prev[id]) {
          return {
            ...prev,
            [id]: {
              ...prev[id],
              logs: logsData.logs || []
            }
          };
        }
        return prev;
      });
    } catch (e) {
      console.error(`[WorkflowContext] Error loading workflow details for ${id}:`, e);
    }
  }, []);

  const sseEventBufferRef = useRef<any[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  // Flush buffered events inside a single animation frame tick
  const flushSseEvents = useCallback(() => {
    if (sseEventBufferRef.current.length === 0) {
      animationFrameRef.current = null;
      return;
    }
    
    const events = [...sseEventBufferRef.current];
    sseEventBufferRef.current = [];
    animationFrameRef.current = null;
    
    setWorkflows(prev => {
      const copy = { ...prev };
      
      for (const event of events) {
        const { workflow_id, type, data } = event;
        const current = copy[workflow_id];
        if (!current) {
          setTimeout(() => loadWorkflowDetails(workflow_id), 100);
          continue;
        }

        let updatedLogs = [...current.logs];
        let updatedPlan = [...current.planSteps];
        let updatedIdx = current.currentStepIdx;
        let progressVal = current.progress;
        let statusVal = current.status;
        let currentStepVal = current.current_step;
        let approvalDiffVal = current.approvalDiff;
        let approvalFilesVal = current.approvalFiles;
        let approvalReasonVal = current.approvalReason;
        let durationVal = current.duration;
        let tokensVal = current.tokensUsed;
        let reportVal = current.executionReport;

        if (type === 'workflow_started') {
          statusVal = data.status || 'starting';
          progressVal = data.progress || 0;
        } else if (type === 'workflow_progress') {
          statusVal = data.status || statusVal;
          progressVal = data.progress || progressVal;
          currentStepVal = data.current_step || currentStepVal;
          if (data.step_index !== undefined) {
            updatedIdx = data.step_index;
          }
          if (data.completed_steps) {
            updatedPlan = data.completed_steps;
          }
          if (data.diff !== undefined) approvalDiffVal = data.diff;
          if (data.affected_files !== undefined) approvalFilesVal = data.affected_files;
          if (data.approval_reason !== undefined) approvalReasonVal = data.approval_reason;
        } else if (type === 'workflow_log') {
          const timeOffset = current.duration || 0;
          updatedLogs.push({
            level: 'INFO',
            message: data,
            timestamp: timeOffset
          });
        } else if (type === 'workflow_finished') {
          statusVal = 'completed';
          progressVal = 100;
          reportVal = data.report || null;
          durationVal = data.duration || durationVal;
          tokensVal = data.tokens_used || tokensVal;
          updatedLogs.push({
            level: 'SUCCESS',
            message: 'Workflow execution successfully finished!',
            timestamp: durationVal
          });

          addToast(
            'success',
            `\u2714 ${current.workflow_type} finished in ${(data.duration || 0).toFixed(1)}s \u2014 ${(data.tokens_used || 0).toLocaleString()} tokens used.`
          ); 
          fetchHistory();
        } else if (type === 'workflow_failed') {
          statusVal = 'failed';
          updatedLogs.push({
            level: 'ERROR',
            message: `Execution failed: ${data.error || 'Unknown error'}`,
            timestamp: durationVal
          });
          addToast('error', `Workflow '${current.workflow_type}' failed: ${data.error || 'Internal error'}`);
          fetchHistory();
        } else if (type === 'workflow_cancelled') {
          statusVal = 'cancelled';
          updatedLogs.push({
            level: 'WARNING',
            message: 'Workflow execution was cancelled by user.',
            timestamp: durationVal
          });
          addToast('warning', `Workflow '${current.workflow_type}' was cancelled.`);
          fetchHistory();
        }

        copy[workflow_id] = {
          ...current,
          status: statusVal,
          progress: progressVal,
          current_step: currentStepVal,
          currentStepIdx: updatedIdx,
          planSteps: updatedPlan,
          logs: updatedLogs,
          approvalDiff: approvalDiffVal,
          approvalFiles: approvalFilesVal,
          approvalReason: approvalReasonVal,
          duration: durationVal,
          tokensUsed: tokensVal,
          executionReport: reportVal
        };
      }
      
      return copy;
    });
  }, [addToast, fetchHistory, loadWorkflowDetails]);

  // Connect global SSE Stream
  const connectGlobalStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const streamUrl = api.getWorkflowStreamUrl();
    const source = new EventSource(streamUrl);
    eventSourceRef.current = source;

    source.onopen = () => {
      console.log('[WorkflowContext] Connected to global workflows SSE stream.');
      reconnectAttemptRef.current = 0;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { workflow_id, type, data } = payload;
        if (!workflow_id) return;

        sseEventBufferRef.current.push({ workflow_id, type, data });

        if (!animationFrameRef.current) {
          animationFrameRef.current = requestAnimationFrame(flushSseEvents);
        }
      } catch (err) {
        console.error('[WorkflowContext] Error parsing SSE payload:', err);
      }
    };

    source.onerror = () => {
      console.warn('[WorkflowContext] SSE stream disconnected. Probing endpoint before reconnect...');
      source.close();
      eventSourceRef.current = null;

      const attempt = reconnectAttemptRef.current;
      if (attempt >= 6) {
        console.warn('[WorkflowContext] Max SSE reconnect attempts reached. Stopping reconnect loop.');
        return;
      }

      const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
      reconnectAttemptRef.current = attempt + 1;

      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(async () => {
        try {
          const probe = await fetch(api.getWorkflowStreamUrl(), {
            method: 'GET',
            headers: { Accept: 'text/event-stream' },
            signal: AbortSignal.timeout(5000),
          });
          if (probe.status >= 400 && probe.status < 500) {
            console.warn(
              `[WorkflowContext] SSE endpoint returned HTTP ${probe.status}. Not reconnecting (client error).`
            );
            return;
          }
          console.log(`[WorkflowContext] Reconnecting SSE stream (attempt ${attempt + 1})...`);
          connectGlobalStreamRef.current?.();
        } catch {
          console.log(`[WorkflowContext] SSE probe failed (network). Attempt ${attempt + 1}, retrying...`);
          connectGlobalStreamRef.current?.();
        }
      }, delay);
    };
  }, [flushSseEvents]);

  // Keep ref up to date
  useEffect(() => {
    connectGlobalStreamRef.current = connectGlobalStream;
  }, [connectGlobalStream]);

  // Discover currently running workflows on mount
  const restoreRunningWorkflows = useCallback(async () => {
    try {
      const activeRuns = await api.getRunningWorkflows();
      if (activeRuns.length > 0) {
        const mapping: Record<string, WorkflowState> = {};
        for (const run of activeRuns) {
          mapping[run.id] = {
            id: run.id,
            repository_id: run.repository_id,
            repository_name: run.repository_name || 'Repository',
            goal: run.goal,
            workflow_type: run.workflow_type,
            status: run.status,
            progress: run.progress || 0,
            current_step: run.current_step || '',
            logs: [],
            planSteps: run.steps || [],
            currentStepIdx: -1,
            retrievedChunks: [],
            tokensUsed: 0,
            providersUsed: [],
            duration: run.duration || 0,
            confidence: 1.0,
            analytics: null,
            executionReport: null,
            approvalDiff: run.diff || null,
            approvalFiles: run.affected_files || [],
            approvalReason: run.approval_reason || ''
          };
        }
        setWorkflows(prev => ({ ...prev, ...mapping }));
        
        // Pick the first running workflow as the active one if none is selected yet
        setActiveWorkflowId(prev => prev || activeRuns[0].id);
        setSelectedWorkflowId(prev => prev || activeRuns[0].id);
        
        // Refresh details for each running workflow in background
        activeRuns.forEach(run => loadWorkflowDetails(run.id));
      }
    } catch (e) {
      console.error('[WorkflowContext] Error restoring running workflows:', e);
    }
  }, [loadWorkflowDetails]);

  useEffect(() => {
    // Initial data setup
    restoreRunningWorkflows();
    fetchHistory();
    connectGlobalStream();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [restoreRunningWorkflows, fetchHistory, connectGlobalStream]);

  // Start executing a workflow
  const startWorkflow = useCallback(async (repositoryId: string, goal: string, template: string) => {
    const { workflow_id, status } = await api.startWorkflow(repositoryId, goal, template);
    
    // Add local placeholder
    setWorkflows(prev => ({
      ...prev,
      [workflow_id]: {
        id: workflow_id,
        repository_id: repositoryId,
        repository_name: 'Scanning Repository...',
        goal,
        workflow_type: template,
        status: status as any || 'queued',
        progress: 0,
        current_step: 'Queued',
        logs: [{ level: 'INFO', message: 'Workflow queued inside Background Engine', timestamp: 0 }],
        planSteps: [],
        currentStepIdx: -1,
        retrievedChunks: [],
        tokensUsed: 0,
        providersUsed: [],
        duration: 0,
        confidence: 1.0,
        analytics: null,
        executionReport: null,
        approvalDiff: null,
        approvalFiles: [],
        approvalReason: ''
      }
    }));
    
    setActiveWorkflowId(workflow_id);
    setSelectedWorkflowId(workflow_id);
    addToast('info', `Workflow '${template}' queued for background execution.`);
    return workflow_id;
  }, [addToast]);

  const pauseWorkflow = useCallback(async (workflowId: string) => {
    await api.pauseWorkflow(workflowId);
    setWorkflows(prev => {
      if (prev[workflowId]) {
        return {
          ...prev,
          [workflowId]: {
            ...prev[workflowId],
            status: 'paused'
          }
        };
      }
      return prev;
    });
  }, []);

  const resumeWorkflow = useCallback(async (workflowId: string) => {
    await api.resumeWorkflow(workflowId);
    setWorkflows(prev => {
      if (prev[workflowId]) {
        return {
          ...prev,
          [workflowId]: {
            ...prev[workflowId],
            status: 'executing'
          }
        };
      }
      return prev;
    });
  }, []);

  const cancelWorkflow = useCallback(async (workflowId: string) => {
    await api.cancelWorkflow(workflowId);
    setWorkflows(prev => {
      if (prev[workflowId]) {
        return {
          ...prev,
          [workflowId]: {
            ...prev[workflowId],
            status: 'cancelled'
          }
        };
      }
      return prev;
    });
  }, []);

  const approveWorkflow = useCallback(async (workflowId: string, approved: boolean, reason?: string) => {
    await api.approveWorkflow(workflowId, approved, reason);
    setWorkflows(prev => {
      if (prev[workflowId]) {
        return {
          ...prev,
          [workflowId]: {
            ...prev[workflowId],
            status: 'executing',
            approvalDiff: null // clear diff panel
          }
        };
      }
      return prev;
    });
  }, []);

  const deleteWorkflow = useCallback(async (workflowId: string) => {
    await api.deleteWorkflow(workflowId);
    setWorkflows(prev => {
      const copy = { ...prev };
      delete copy[workflowId];
      return copy;
    });
    if (activeWorkflowId === workflowId) {
      setActiveWorkflowId(null);
    }
    if (selectedWorkflowId === workflowId) {
      setSelectedWorkflowId(null);
    }
    fetchHistory();
  }, [activeWorkflowId, selectedWorkflowId, fetchHistory]);

  const clearWorkspace = useCallback(() => {
    setActiveWorkflowId(null);
    setSelectedWorkflowId(null);
  }, []);

  // Derived state: list of currently active workflows
  const runningWorkflows = useMemo(() => {
    const list = Object.values(workflows);
    const activeStatuses = ['queued', 'starting', 'retrieving', 'planning', 'executing', 'waiting_approval', 'paused'];
    return list.filter(w => activeStatuses.includes(w.status));
  }, [workflows]);

  const contextValue = useMemo<WorkflowContextType>(() => ({
    workflows,
    activeWorkflowId,
    selectedWorkflowId,
    historyWorkflows,
    isLoadingHistory,
    runningWorkflows,
    startWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    cancelWorkflow,
    approveWorkflow,
    deleteWorkflow,
    loadWorkflowDetails,
    fetchHistory,
    setActiveWorkflowId,
    setSelectedWorkflowId,
    clearWorkspace
  }), [
    workflows,
    activeWorkflowId,
    selectedWorkflowId,
    historyWorkflows,
    isLoadingHistory,
    runningWorkflows,
    startWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    cancelWorkflow,
    approveWorkflow,
    deleteWorkflow,
    loadWorkflowDetails,
    fetchHistory
  ]);

  return (
    <WorkflowContext.Provider value={contextValue}>
      {children}
    </WorkflowContext.Provider>
  );
};

export const useWorkflow = (): WorkflowContextType => {
  const ctx = useContext(WorkflowContext);
  if (!ctx) throw new Error('useWorkflow must be used inside <WorkflowProvider>');
  return ctx;
};
