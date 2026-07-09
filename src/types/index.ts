export type TaskType = 'review' | 'explain' | 'tests' | 'bugs';

export type AgentName = 'planner' | 'retriever' | 'reviewer' | 'critic';

export type AgentStatus = 'waiting' | 'processing' | 'completed' | 'failed';

export interface AgentState {
  status: AgentStatus;
  message: string;
  timestamp?: string;
}

export type MultiAgentStatus = Record<AgentName, AgentState>;

export interface ContextChunk {
  id?: string;
  chunk_id?: string;
  path: string;
  start_line: number;
  end_line: number;
  content: string;
  score?: number;
}

export interface AIMetadata {
  provider: string;
  provider_used_after_failover?: string | null;
  model: string;
  latency: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  retry_count: number;
  cache_hit: boolean;
  fallback_flag: boolean;
  request_id: string;
  started_timestamp: number;
  completed_timestamp: number;
  estimated_cost?: number;
}

export interface ParsedReport {
  markdownReport: string;
  aiOutput?: {
    is_fallback: boolean;
    executive_summary?: string;
    strengths?: string[];
    improvements?: string[];
    security_observations?: string[];
    performance_observations?: string[];
    maintainability_observations?: string[];
    recommendations?: string[];
    
    // Explain Schema
    high_level_architecture?: string[];
    entry_points?: string[];
    component_relationships?: string[];
    important_modules?: string[];
    execution_flow?: string[];
    data_flow?: string;

    // Tests Schema
    unit_test_suggestions?: string[];
    integration_test_suggestions?: string[];
    coverage_status?: string[];
    mock_opportunities?: string[];
    edge_cases?: string[];

    // Bugs Schema
    logical_issues?: string[];
    risk_areas?: string[];
    error_prone_patterns?: string[];
    null_handling_concerns?: string[];
    async_concerns?: string[];
    resource_management_observations?: string[];
    performance_concerns?: string[];
    
    ai_metadata?: AIMetadata;
  };
  repository?: {
    id?: string;
    name: string;
    owner: string;
    source: string;
    framework?: string;
    language?: string;
    repository_hash?: string;
  };
  metadata?: {
    primary_language?: string;
    framework?: string;
    package_managers?: string[];
    dependencies?: Record<string, string>;
    license?: string;
    tests_present?: boolean;
    readme_present?: boolean;
    docker_support?: boolean;
    github_actions?: boolean;
    cicd?: boolean;
  };
  statistics?: {
    total_files: number;
    total_directories: number;
    extensions: Record<string, number>;
    largest_files: Array<{ path: string; size: number }>;
  };
  chunks?: ContextChunk[];
}

export interface HistoryItem {
  id: string;
  timestamp: number;
  taskType: TaskType;
  repositoryName: string;
  repositoryOwner: string;
  provider: string;
  model: string;
  duration: number;
  cacheHit: boolean;
  fallbackFlag: boolean;
  report: ParsedReport;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
}

export interface AnalysisContextType {
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
  toasts: ToastMessage[];
  setSelectedTask: (task: TaskType) => void;
  setRepositoryURL: (url: string) => void;
  setUploadedFile: (file: File | null) => void;
  startAnalysis: () => Promise<void>;
  resetAnalysis: () => void;
  clearHistory: () => void;
  loadHistoryItem: (item: HistoryItem) => void;
  removeToast: (id: string) => void;
  addToast: (type: 'success' | 'info' | 'warning' | 'error', message: string) => void;
}
