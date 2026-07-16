import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { TaskType, MultiAgentStatus, ParsedReport, HistoryItem, ToastMessage } from '../types';
import * as api from '../services/api';
import { AnalysisUIContext, AnalysisContext, type AnalysisUIContextType, type AnalysisDataContextType } from './AnalysisContext';

const initialStatus: MultiAgentStatus = {
  planner:   { status: 'waiting', message: 'Waiting...' },
  retriever: { status: 'waiting', message: 'Waiting...' },
  reviewer:  { status: 'waiting', message: 'Waiting...' },
  critic:    { status: 'waiting', message: 'Waiting...' },
};

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('devmind_theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    localStorage.setItem('devmind_theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const toggleTheme = useCallback(() => setTheme(prev => (prev === 'dark' ? 'light' : 'dark')), []);

  const addToast = useCallback((type: 'success' | 'info' | 'warning' | 'error', message: string) => {
    setToasts(prev => {
      if (prev.some(t => t.message === message)) return prev;
      const id = `toast_${Math.random().toString(36).substr(2, 9)}`;
      setTimeout(() => setToasts(current => current.filter(t => t.id !== id)), 4000);
      return [...prev, { id, type, message }];
    });
  }, []);

  const removeToast = useCallback((id: string) => setToasts(prev => prev.filter(t => t.id !== id)), []);

  const uiValue = useMemo<AnalysisUIContextType>(() => ({
    theme, toggleTheme, toasts, addToast, removeToast,
  }), [theme, toggleTheme, toasts, addToast, removeToast]);

  const [status,          setStatus]           = useState<MultiAgentStatus>(initialStatus);
  const [selectedTask,    setSelectedTaskState] = useState<TaskType>('review');
  const [repositoryURL,   setRepositoryURLState]= useState<string>('');
  const [uploadedFile,    setUploadedFileState] = useState<File | null>(null);
  const [analysisResult,  setAnalysisResult]   = useState<string | null>(null);
  const [parsedReport,    setParsedReport]      = useState<ParsedReport | null>(null);
  const [isAnalyzing,     setIsAnalyzing]       = useState<boolean>(false);
  const [overallProgress, setOverallProgress]   = useState<number>(0);
  const [currentStage,    setCurrentStage]      = useState<string>('Standby');
  const [history,         setHistory]           = useState<HistoryItem[]>([]);

  const pollingIntervalRef = useRef<number | null>(null);
  const currentTaskIdRef   = useRef<string | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('devmind_history');
      if (stored) setHistory(JSON.parse(stored));
    } catch (e) { console.error('Failed to load history:', e); }
  }, []);

  useEffect(() => {
    return () => { if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current); };
  }, []);

  const setSelectedTask  = useCallback((task: TaskType) => setSelectedTaskState(task), []);
  const setRepositoryURL = useCallback((url: string) => { setRepositoryURLState(url); setUploadedFileState(null); }, []);
  const setUploadedFile  = useCallback((file: File | null) => { setUploadedFileState(file); if (file) setRepositoryURLState(''); }, []);

  const resetAnalysis = useCallback(() => {
    if (pollingIntervalRef.current) { clearInterval(pollingIntervalRef.current); pollingIntervalRef.current = null; }
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

  const deleteHistoryItem = useCallback((id: string) => {
    setHistory(prev => {
      const updated = prev.filter(item => item.id !== id);
      localStorage.setItem('devmind_history', JSON.stringify(updated));
      return updated;
    });
    addToast('info', 'Report cache removed.');
  }, [addToast]);

  const loadHistoryItem = useCallback((item: HistoryItem) => {
    resetAnalysis();
    setSelectedTaskState(item.taskType);
    if (item.report.repository?.source?.endsWith('.zip')) {
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
    if (!repositoryURL && !uploadedFile) { addToast('error', 'Please provide a GitHub URL or upload a ZIP file.'); return; }
    resetAnalysis();
    setIsAnalyzing(true);
    setOverallProgress(5);
    setCurrentStage('Initializing Pipeline');
    addToast('info', 'AI Analysis Started');
    try {
      let response: { taskId: string };
      if (uploadedFile) { response = await api.uploadRepository(uploadedFile, selectedTask); }
      else              { response = await api.reviewRepository(repositoryURL, selectedTask); }
      currentTaskIdRef.current = response.taskId;

      const firstScan = await api.getStatus(response.taskId);
      setStatus(firstScan.status);
      setOverallProgress(firstScan.progress ?? 5);
      setCurrentStage(firstScan.stage ?? 'Initializing Pipeline');

      pollingIntervalRef.current = window.setInterval(async () => {
        if (!currentTaskIdRef.current) return;
        try {
          const scan = await api.getStatus(currentTaskIdRef.current);
          setStatus(scan.status);
          setOverallProgress(scan.progress ?? 0);
          setCurrentStage(scan.stage ?? 'Scanning');
          if (scan.isDone) {
            setIsAnalyzing(false);
            if (pollingIntervalRef.current) { clearInterval(pollingIntervalRef.current); pollingIntervalRef.current = null; }
            if (scan.rawResult) {
              const raw = scan.rawResult;
              const parsed: ParsedReport = {
                markdownReport: scan.resultText || '',
                aiOutput: raw.ai_output, repository: raw.repository,
                task_type: raw.task_type, metadata: raw.metadata,
                statistics: raw.statistics, chunks: raw.chunks,
              };
              setAnalysisResult(scan.resultText);
              setParsedReport(parsed);
              setOverallProgress(100);
              setCurrentStage('Analysis completed successfully');
              const meta = parsed.aiOutput?.ai_metadata;
              const isFallback = parsed.aiOutput?.is_fallback || meta?.fallback_flag;
              if (isFallback) { addToast('warning', 'Fallback Heuristics Activated (LLMs offline)'); }
              else {
                addToast('success', 'AI Analysis Completed successfully!');
                if (meta?.cache_hit)                    addToast('info', 'Cache Hit: loaded analysis from local cache');
                else                                    addToast('success', 'Cache Miss: performed live reasoning scan');
                if (meta?.provider_used_after_failover) addToast('warning', `Provider failed over. Switched to ${meta.provider_used_after_failover}`);
              }
              const newHistoryItem: HistoryItem = {
                id: currentTaskIdRef.current!, timestamp: Date.now(), taskType: selectedTask,
                repositoryName: parsed.repository?.name || 'repository',
                repositoryOwner: parsed.repository?.owner || 'Unknown',
                provider: parsed.aiOutput?.ai_metadata?.provider || 'Direct Heuristic',
                model: parsed.aiOutput?.ai_metadata?.model || 'None',
                duration: parsed.aiOutput?.ai_metadata?.latency || 0,
                cacheHit: parsed.aiOutput?.ai_metadata?.cache_hit || false,
                fallbackFlag: !!isFallback, report: parsed,
              };
              setHistory(prev => {
                const filtered = prev.filter(item => item.id !== newHistoryItem.id);
                const updated  = [newHistoryItem, ...filtered].slice(0, 50);
                localStorage.setItem('devmind_history', JSON.stringify(updated));
                return updated;
              });
            } else { setAnalysisResult(scan.resultText); addToast('success', 'Analysis completed.'); }
          }
        } catch (pollError) {
          console.error('Error polling agent status:', pollError);
          setIsAnalyzing(false);
          addToast('error', 'Polling error occurred. Analysis aborted.');
          if (pollingIntervalRef.current) { clearInterval(pollingIntervalRef.current); pollingIntervalRef.current = null; }
        }
      }, 1000);
    } catch (err) {
      console.error('Failed to trigger analysis:', err);
      setIsAnalyzing(false);
      addToast('error', 'Failed to start analysis. Check connection.');
    }
  }, [repositoryURL, uploadedFile, selectedTask, resetAnalysis, addToast]);

  const dataValue = useMemo<AnalysisDataContextType>(() => ({
    status, selectedTask, repositoryURL, uploadedFile,
    analysisResult, parsedReport, isAnalyzing, overallProgress, currentStage, history,
    setSelectedTask, setRepositoryURL, setUploadedFile,
    startAnalysis, resetAnalysis, clearHistory, deleteHistoryItem, loadHistoryItem,
    addToast, removeToast, theme, toggleTheme,
  }), [
    status, selectedTask, repositoryURL, uploadedFile,
    analysisResult, parsedReport, isAnalyzing, overallProgress, currentStage, history,
    setSelectedTask, setRepositoryURL, setUploadedFile,
    startAnalysis, resetAnalysis, clearHistory, deleteHistoryItem, loadHistoryItem,
    addToast, removeToast, theme, toggleTheme,
  ]);

  return (
    <AnalysisUIContext.Provider value={uiValue}>
      <AnalysisContext.Provider value={dataValue}>
        {children}
      </AnalysisContext.Provider>
    </AnalysisUIContext.Provider>
  );
};
