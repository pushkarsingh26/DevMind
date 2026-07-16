import { createContext, useContext } from 'react';
import type { TaskType, MultiAgentStatus, ParsedReport, HistoryItem, ToastMessage } from '../types';

export interface AnalysisUIContextType {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  toasts: ToastMessage[];
  addToast: (type: 'success' | 'info' | 'warning' | 'error', message: string) => void;
  removeToast: (id: string) => void;
}

export interface AnalysisDataContextType {
  status: MultiAgentStatus;
  selectedTask: TaskType;
  repositoryURL: string;
  uploadedFile: File | null;
  analysisResult: string | null;
  parsedReport: ParsedReport | null;
  isAnalyzing: boolean;
  overallProgress: number;
  currentStage: string;
  history: HistoryItem[];
  setSelectedTask: (task: TaskType) => void;
  setRepositoryURL: (url: string) => void;
  setUploadedFile: (file: File | null) => void;
  startAnalysis: () => Promise<void>;
  resetAnalysis: () => void;
  clearHistory: () => void;
  deleteHistoryItem: (id: string) => void;
  loadHistoryItem: (item: HistoryItem) => void;
  addToast: (type: 'success' | 'info' | 'warning' | 'error', message: string) => void;
  removeToast: (id: string) => void;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
}

export type AnalysisContextType = AnalysisDataContextType;

export const AnalysisUIContext = createContext<AnalysisUIContextType | undefined>(undefined);
export const AnalysisContext   = createContext<AnalysisDataContextType | undefined>(undefined);



export function useAnalysisData(): AnalysisDataContextType {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error('useAnalysisData must be used inside <AnalysisProvider>');
  return ctx;
}

export function useAnalysisUI(): AnalysisUIContextType {
  const ctx = useContext(AnalysisUIContext);
  if (!ctx) throw new Error('useAnalysisUI must be used inside <AnalysisProvider>');
  return ctx;
}
