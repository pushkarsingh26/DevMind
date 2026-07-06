export type TaskType = 'review' | 'explain' | 'tests' | 'bugs';

export type AgentName = 'planner' | 'retriever' | 'reviewer' | 'critic';

export type AgentStatus = 'waiting' | 'processing' | 'completed' | 'failed';

export interface AgentState {
  status: AgentStatus;
  message: string;
  timestamp?: string;
}

export type MultiAgentStatus = Record<AgentName, AgentState>;

export interface AnalysisResult {
  taskId: string;
  taskType: TaskType;
  resultText: string;
  timestamp: string;
}

export interface AnalysisContextType {
  status: MultiAgentStatus;
  selectedTask: TaskType;
  repositoryURL: string;
  uploadedFile: File | null;
  analysisResult: string | null;
  isAnalyzing: boolean;
  setSelectedTask: (task: TaskType) => void;
  setRepositoryURL: (url: string) => void;
  setUploadedFile: (file: File | null) => void;
  startAnalysis: () => Promise<void>;
  resetAnalysis: () => void;
}
