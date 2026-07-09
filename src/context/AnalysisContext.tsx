import React, { createContext, useState, useEffect, useRef, useCallback } from 'react';
import type { TaskType, MultiAgentStatus, AnalysisContextType, ParsedReport, HistoryItem, ToastMessage } from '../types';
import * as api from '../services/api';

export const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

const initialStatus: MultiAgentStatus = {
  planner: { status: 'waiting', message: 'Waiting...' },
  retriever: { status: 'waiting', message: 'Waiting...' },
  reviewer: { status: 'waiting', message: 'Waiting...' },
  critic: { status: 'waiting', message: 'Waiting...' },
};

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<MultiAgentStatus>(initialStatus);
  const [selectedTask, setSelectedTaskState] = useState<TaskType>('review');
  const [repositoryURL, setRepositoryURLState] = useState<string>('');
  const [uploadedFile, setUploadedFileState] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [parsedReport, setParsedReport] = useState<ParsedReport | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [overallProgress, setOverallProgress] = useState<number>(0);
  const [currentStage, setCurrentStage] = useState<string>('Standby');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pollingIntervalRef = useRef<number | null>(null);
  const currentTaskIdRef = useRef<string | null>(null);

  // Load history on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('devmind_history');
      if (stored) {
        setHistory(JSON.parse(stored));
      }
    } catch (e) {
      console.error('Failed to load history from LocalStorage:', e);
    }
  }, []);

  // Clear polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const addToast = useCallback((type: 'success' | 'info' | 'warning' | 'error', message: string) => {
    const id = `toast_${Math.random().toString(36).substr(2, 9)}`;
    setToasts(prev => [...prev, { id, type, message }]);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const setSelectedTask = useCallback((task: TaskType) => {
    setSelectedTaskState(task);
  }, []);

  const setRepositoryURL = useCallback((url: string) => {
    setRepositoryURLState(url);
    setUploadedFileState(null); // Clear uploaded file if URL is set
  }, []);

  const setUploadedFile = useCallback((file: File | null) => {
    setUploadedFileState(file);
    if (file) {
      setRepositoryURLState(''); // Clear URL if file is uploaded
    }
  }, []);

  const resetAnalysis = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    currentTaskIdRef.current = null;
    setStatus(initialStatus);
    setAnalysisResult(null);
    setParsedReport(null);
    setIsAnalyzing(false);
    setOverallProgress(0);
    setCurrentStage('Standby');
  }, []);

  const clearHistory = useCallback(() => {
    localStorage.removeItem('devmind_history');
    setHistory([]);
    addToast('info', 'Analysis history cleared.');
  }, [addToast]);

  const loadHistoryItem = useCallback((item: HistoryItem) => {
    resetAnalysis();
    setSelectedTaskState(item.taskType);
    if (item.report.repository?.source && item.report.repository.source.endsWith('.zip')) {
      setUploadedFileState(new File([], item.report.repository.source));
      setRepositoryURLState('');
    } else {
      setRepositoryURLState(item.report.repository?.source || '');
      setUploadedFileState(null);
    }
    setAnalysisResult(item.report.markdownReport);
    setParsedReport(item.report);
    setOverallProgress(100);
    setCurrentStage('Loaded from cache');
    addToast('success', `Loaded cached audit report for ${item.repositoryName}`);
  }, [resetAnalysis, addToast]);

  const startAnalysis = useCallback(async () => {
    if (!repositoryURL && !uploadedFile) {
      addToast('error', 'Please provide a GitHub URL or upload a ZIP file.');
      return;
    }

    // Reset old execution states
    resetAnalysis();
    setIsAnalyzing(true);
    setOverallProgress(5);
    setCurrentStage('Initializing Pipeline');
    addToast('info', 'AI Analysis Started');

    try {
      let response: { taskId: string };

      // Select appropriate endpoint depending on input type
      if (uploadedFile) {
        response = await api.uploadRepository(uploadedFile, selectedTask);
      } else {
        response = await api.reviewRepository(repositoryURL, selectedTask);
      }

      currentTaskIdRef.current = response.taskId;

      // Immediately run first status scan
      const firstScan = await api.getStatus(response.taskId);
      setStatus(firstScan.status);
      setOverallProgress(firstScan.progress ?? 5);
      setCurrentStage(firstScan.stage ?? 'Initializing Pipeline');

      // Start interval polling
      pollingIntervalRef.current = window.setInterval(async () => {
        if (!currentTaskIdRef.current) return;

        try {
          const scan = await api.getStatus(currentTaskIdRef.current);
          setStatus(scan.status);
          setOverallProgress(scan.progress ?? 0);
          setCurrentStage(scan.stage ?? 'Scanning');

          if (scan.isDone) {
            setIsAnalyzing(false);
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }

            if (scan.rawResult) {
              const raw = scan.rawResult;
              const parsed: ParsedReport = {
                markdownReport: scan.resultText || '',
                aiOutput: raw.ai_output,
                repository: raw.repository,
                metadata: raw.metadata,
                statistics: raw.statistics,
                chunks: raw.chunks,
              };
              
              setAnalysisResult(scan.resultText);
              setParsedReport(parsed);
              setOverallProgress(100);
              setCurrentStage('Analysis completed successfully');

              // 1. Toast notifications for Cache status / Fallbacks
              const meta = parsed.aiOutput?.ai_metadata;
              const isFallback = parsed.aiOutput?.is_fallback || meta?.fallback_flag;
              
              if (isFallback) {
                addToast('warning', 'Fallback Heuristics Activated (LLMs offline)');
              } else {
                addToast('success', 'AI Analysis Completed successfully!');
                
                if (meta?.cache_hit) {
                  addToast('info', 'Cache Hit: loaded analysis from local cache');
                } else {
                  addToast('success', 'Cache Miss: performed live reasoning scan');
                }

                if (meta?.provider_used_after_failover) {
                  addToast('warning', `Provider failed over. Switched to ${meta.provider_used_after_failover}`);
                }
              }

              // 2. Add to LocalStorage History
              const newHistoryItem: HistoryItem = {
                id: currentTaskIdRef.current,
                timestamp: Date.now(),
                taskType: selectedTask,
                repositoryName: parsed.repository?.name || 'repository',
                repositoryOwner: parsed.repository?.owner || 'Unknown',
                provider: parsed.aiOutput?.ai_metadata?.provider || 'Direct Heuristic',
                model: parsed.aiOutput?.ai_metadata?.model || 'None',
                duration: parsed.aiOutput?.ai_metadata?.latency || 0,
                cacheHit: parsed.aiOutput?.ai_metadata?.cache_hit || false,
                fallbackFlag: !!isFallback,
                report: parsed,
              };

              setHistory(prev => {
                const filtered = prev.filter(item => item.id !== newHistoryItem.id);
                const updated = [newHistoryItem, ...filtered].slice(0, 50);
                localStorage.setItem('devmind_history', JSON.stringify(updated));
                return updated;
              });
            } else {
              setAnalysisResult(scan.resultText);
              addToast('success', 'Analysis completed.');
            }
          }
        } catch (pollError) {
          console.error('Error polling agent status:', pollError);
          setIsAnalyzing(false);
          addToast('error', 'Polling error occurred. Analysis aborted.');
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
        }
      }, 1000);

    } catch (err) {
      console.error('Failed to trigger analysis:', err);
      setIsAnalyzing(false);
      addToast('error', 'Failed to start analysis. Check connection.');
    }
  }, [repositoryURL, uploadedFile, selectedTask, resetAnalysis, addToast]);

  return (
    <AnalysisContext.Provider
      value={{
        status,
        selectedTask,
        repositoryURL,
        uploadedFile,
        analysisResult,
        parsedReport,
        isAnalyzing,
        overallProgress,
        currentStage,
        history,
        toasts,
        setSelectedTask,
        setRepositoryURL,
        setUploadedFile,
        startAnalysis,
        resetAnalysis,
        clearHistory,
        loadHistoryItem,
        removeToast,
        addToast,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
};
