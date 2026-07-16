import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { 
  Play, Bot, Terminal, ScrollText, CheckCircle2, XCircle, AlertCircle, 
  History, FileText, Copy, FolderOpen,
  Check, Download, Trash2, ArrowRight, Server, Database, Code, RefreshCw, 
  Search, SlidersHorizontal, ArrowUpDown, Info, PieChart, Activity
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardContent, CardFooter, Button, Badge } from '../components/ui';
import { useWorkflow } from '../context/WorkflowContext';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const EMPTY_ARRAY: any[] = [];

/** Safely normalise any API response into an array. Logs bad payloads in dev. */
function toSafeArray<T>(data: unknown, label = 'response'): T[] {
  if (Array.isArray(data)) return data as T[];
  if (import.meta.env.DEV) {
    console.warn(`[DevMind] Expected array for "${label}" but received:`, typeof data, data);
  }
  return [];
}

// Predefined workflow templates list matching backend config
const TEMPLATE_PRESETS = [
  { name: 'Security Audit', desc: 'Find security vulnerabilities, verify JWT configurations, check exceptions logic.' },
  { name: 'Performance Audit', desc: 'Trace speed bottlenecks, redundant SQL calls, unbuffered read streams.' },
  { name: 'Architecture Review', desc: 'Analyze structural design patterns, module layers, SOLID decoupling.' },
  { name: 'Documentation Generation', desc: 'Find undocumented files and automatically generate block comments/readmes.' },
  { name: 'Test Generation', desc: 'Scan code gaps and draft comprehensive unit test spec frameworks.' },
  { name: 'Bug Investigation', desc: 'Trace bug locations, scan logic flaws, and draft bugfix refactorings.' },
  { name: 'Dependency Review', desc: 'Inspect package manager manifests, versions deprecations, and library sizing.' },
  { name: 'Refactoring Plan', desc: 'Locate structural smells, duplication patterns, and suggest modular refactoring plans.' },
];

// Reusable Skeletons for Loading States
const LoaderSkeleton: React.FC = () => (
  <div className="space-y-4 animate-pulse">
    <div className="h-10 bg-dark-800/40 rounded-xl w-3/4" />
    <div className="h-32 bg-dark-800/40 rounded-xl" />
    <div className="grid grid-cols-3 gap-4">
      <div className="h-20 bg-dark-800/40 rounded-xl" />
      <div className="h-20 bg-dark-800/40 rounded-xl" />
      <div className="h-20 bg-dark-800/40 rounded-xl" />
    </div>
  </div>
);

// Reusable Empty State Card
const EmptyState: React.FC<{ message: string; actionText?: string; onAction?: () => void }> = ({ 
  message, actionText, onAction 
}) => (
  <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-border-primary rounded-2xl min-h-[180px] bg-dark-950/10">
    <AlertCircle className="w-8 h-8 text-dark-500 mb-3" />
    <p className="text-xs text-dark-400 font-mono mb-4">{message}</p>
    {actionText && onAction && (
      <Button variant="glass" size="sm" onClick={onAction}>
        {actionText}
      </Button>
    )}
  </div>
);

// -------------------------------------------------------------
// Interactive Graph Node Visualizer
// -------------------------------------------------------------
interface GraphNodeProps {
  step: any;
  index: number;
  isActive: boolean;
  isCompleted: boolean;
  onClick: (index: number) => void;
}

const GraphNode: React.FC<GraphNodeProps> = React.memo(({ 
  step, index, isActive, isCompleted, onClick 
}) => {
  return (
    <div 
      onClick={() => onClick(index)}
      className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border text-[11px] font-mono transition-all duration-300 cursor-pointer select-none hover:border-cyan-accent/50 ${
        isActive 
          ? 'bg-cyan-accent/15 border-cyan-accent text-cyan-accent shadow-[0_0_15px_rgba(6,182,212,0.25)] scale-105 z-10' 
          : isCompleted
          ? 'bg-green-accent/10 border-green-accent/30 text-green-accent hover:bg-green-accent/15'
          : 'bg-dark-900/60 border-border-primary text-dark-400 hover:text-dark-200'
      }`}
    >
      {isCompleted ? (
        <CheckCircle2 className="w-4 h-4 text-green-accent shrink-0" />
      ) : (
        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${isActive ? 'bg-cyan-accent animate-ping' : 'bg-dark-600'}`} />
      )}
      <div className="text-left leading-tight min-w-[100px]">
        <span className="block font-bold text-[8px] uppercase tracking-wider opacity-75">{step.agent}</span>
        <span className="block mt-0.5 text-xs font-semibold text-dark-100 truncate max-w-[140px]">{step.name}</span>
      </div>
    </div>
  );
});

// -------------------------------------------------------------
// Execution Analytics Dashboard
// -------------------------------------------------------------
interface AnalyticsProps {
  analytics: any;
  duration: number;
  providers: string[];
}

const AnalyticsDashboard: React.FC<AnalyticsProps> = React.memo(({ 
  analytics, duration, providers 
}) => {
  if (!analytics) return null;
  return (
    <Card variant="soft" className="border border-border-primary/60 bg-dark-950/20 text-left">
      <CardHeader className="pb-3 border-b border-border-primary/30 flex items-center gap-2">
        <PieChart className="w-4 h-4 text-cyan-accent" />
        <h4 className="text-xs font-bold font-display uppercase tracking-wider text-dark-200">Execution Analytics Cockpit</h4>
      </CardHeader>
      <CardContent className="py-4 grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-[10px]">
        <div className="space-y-1.5 p-3 bg-dark-900/40 rounded-xl border border-border-primary/50">
          <span className="text-dark-500 block uppercase tracking-wider">Elapsed Time</span>
          <span className="text-dark-100 font-bold text-sm block">{duration.toFixed(1)}s</span>
        </div>
        <div className="space-y-1.5 p-3 bg-dark-900/40 rounded-xl border border-border-primary/50">
          <span className="text-dark-500 block uppercase tracking-wider">Failover Retries</span>
          <span className="text-amber-500 font-bold text-sm block">{analytics.retry_count || 0} attempts</span>
        </div>
        <div className="space-y-1.5 p-3 bg-dark-900/40 rounded-xl border border-border-primary/50">
          <span className="text-dark-500 block uppercase tracking-wider">Cache Hits/Misses</span>
          <span className="text-green-accent font-bold text-sm block">
            {analytics.cache_hits || 0} hits / {analytics.cache_misses || 0} miss
          </span>
        </div>
        <div className="space-y-1.5 p-3 bg-dark-900/40 rounded-xl border border-border-primary/50">
          <span className="text-dark-500 block uppercase tracking-wider">Model Providers</span>
          <span className="text-purple-accent font-bold text-sm block truncate" title={providers.join(', ') || 'N/A'}>
            {providers.join(', ') || 'Standby'}
          </span>
        </div>
      </CardContent>
      {analytics.agent_durations && Object.keys(analytics.agent_durations).length > 0 && (
        <CardContent className="pt-0 pb-4 px-5">
          <span className="text-[9px] text-dark-500 font-mono uppercase tracking-wider block mb-2.5">Agent Cost Allocation</span>
          <div className="space-y-2">
            {Object.entries(analytics.agent_durations).map(([agent, timeVal]: [string, any]) => (
              <div key={agent} className="space-y-1">
                <div className="flex justify-between text-[9px] font-mono">
                  <span className="text-dark-300">{agent}</span>
                  <span className="text-cyan-accent">{timeVal.toFixed(1)}s</span>
                </div>
                <div className="w-full bg-dark-950 rounded-full h-1 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-cyan-accent to-purple-accent h-full"
                    style={{ width: `${Math.min(100, (timeVal / (duration || 1)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
});


export const AgentWorkspacePage: React.FC = () => {
  const navigate = useNavigate();

  const {
    workflows,
    activeWorkflowId,
    historyWorkflows,
    isLoadingHistory,
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
  } = useWorkflow();

  const activeWorkflow = activeWorkflowId ? workflows[activeWorkflowId] : null;

  const executionStatus = activeWorkflow ? activeWorkflow.status : 'idle';
  const logs = activeWorkflow ? activeWorkflow.logs : EMPTY_ARRAY;
  const planSteps = activeWorkflow ? activeWorkflow.planSteps : EMPTY_ARRAY;
  const currentStepIdx = activeWorkflow ? activeWorkflow.currentStepIdx : -1;
  const retrievedChunks = activeWorkflow ? activeWorkflow.retrievedChunks : EMPTY_ARRAY;
  const tokensUsed = activeWorkflow ? activeWorkflow.tokensUsed : 0;
  const providersUsed = activeWorkflow ? activeWorkflow.providersUsed : EMPTY_ARRAY;
  const duration = activeWorkflow ? activeWorkflow.duration : 0;
  const confidence = activeWorkflow ? activeWorkflow.confidence : 1.0;
  const analytics = activeWorkflow ? activeWorkflow.analytics : null;
  const executionReport = activeWorkflow ? activeWorkflow.executionReport : null;
  const approvalDiff = activeWorkflow ? activeWorkflow.approvalDiff : null;
  const approvalFiles = activeWorkflow ? activeWorkflow.approvalFiles : EMPTY_ARRAY;
  const approvalReason = activeWorkflow ? activeWorkflow.approvalReason : '';
  const streamingProgress = activeWorkflow ? activeWorkflow.current_step || activeWorkflow.status : 'Standby';
  const workflowId = activeWorkflowId;

  // Selected node in timeline
  const [selectedNodeIdx, setSelectedNodeIdx] = useState<number | null>(null);

  // local approval metadata
  const [approvalRisk] = useState<string>('Low');
  const [approvalImpact] = useState<string>('');
  const [approvalConfidence] = useState<number>(1.0);
  const [approvalSubmitting, setApprovalSubmitting] = useState<boolean>(false);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [showSideBySide, setShowSideBySide] = useState<boolean>(false);

  // Config state
  const [repositories, setRepositories] = useState<any[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');
  const [goal, setGoal] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('Security Audit');
  const [isLoadingRepos, setIsLoadingRepos] = useState<boolean>(true);
  const [repoError, setRepoError] = useState<string | null>(null);

  // History Runs & Filter State
  const [filterSearch, setFilterSearch] = useState<string>('');
  const [filterWorkflow, setFilterWorkflow] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  const logContainerRef = useRef<HTMLDivElement | null>(null);
  const [logScrollTop, setLogScrollTop] = useState(0);
  const containerHeight = 280; // approximate viewport height of log container minus padding
  const itemHeight = 22; // average line height for log entries
  
  const historyRuns = historyWorkflows;

  // Fetch registered repos
  const fetchRepositories = useCallback(async () => {
    setIsLoadingRepos(true);
    setRepoError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/repositories`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data: unknown = await response.json();
      const repos = toSafeArray<any>(data, 'repositories');
      setRepositories(repos);
      if (repos.length > 0 && !selectedRepoId) {
        setSelectedRepoId(repos[0].id);
      }
    } catch (e: any) {
      const msg = e?.message || 'Failed to load repositories.';
      console.error('[DevMind] fetchRepositories error:', e);
      setRepoError(msg);
      setRepositories([]);
    } finally {
      setIsLoadingRepos(false);
    }
  }, [selectedRepoId]);

  // Load repositories & history on mount
  useEffect(() => {
    fetchRepositories();
    fetchHistory();
  }, [fetchRepositories, fetchHistory]);

  // Scroll logs to bottom of the container when logs update
  useEffect(() => {
    if (logContainerRef.current) {
      const sh = logContainerRef.current.scrollHeight;
      logContainerRef.current.scrollTop = sh;
      setLogScrollTop(Math.max(0, sh - containerHeight));
    }
  }, [logs]);

  const handleLogScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setLogScrollTop(e.currentTarget.scrollTop);
  }, []);

  const startIndex = Math.max(0, Math.floor(logScrollTop / itemHeight) - 4);
  const endIndex = Math.min(logs.length, Math.floor((logScrollTop + containerHeight) / itemHeight) + 4);

  const visibleLogs = useMemo(() => {
    return logs.slice(startIndex, endIndex).map((log, i) => ({
      log,
      actualIndex: startIndex + i
    }));
  }, [logs, startIndex, endIndex]);

  const totalLogsHeight = logs.length * itemHeight;



  // Execute workflow trigger
  const handleStartWorkflow = useCallback(async () => {
    if (!selectedRepoId || !goal.trim()) return;
    setSelectedNodeIdx(null);
    try {
      await startWorkflow(selectedRepoId, goal, selectedTemplate);
    } catch (e) {
      console.error('Failed to trigger workflow:', e);
    }
  }, [selectedRepoId, goal, selectedTemplate, startWorkflow]);

  // Submit Approval decision
  const handleApprovalDecision = useCallback(async (approved: boolean) => {
    if (!workflowId) return;
    setApprovalSubmitting(true);
    try {
      await approveWorkflow(workflowId, approved, approved ? 'Approved via cockpit UI' : 'Rejected via cockpit UI');
    } catch (e) {
      console.error('Failed to submit approval:', e);
    } finally {
      setApprovalSubmitting(false);
    }
  }, [workflowId, approveWorkflow]);

  // Fetch detailed report of a completed run from history
  const handleLoadHistoryRun = useCallback(async (id: string) => {
    setSelectedNodeIdx(null);
    setActiveWorkflowId(id);
    setSelectedWorkflowId(id);
    await loadWorkflowDetails(id);
  }, [setActiveWorkflowId, setSelectedWorkflowId, loadWorkflowDetails]);

  // Delete history run
  const handleDeleteRun = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this run record?')) return;
    try {
      await deleteWorkflow(id);
    } catch (err) {
      console.error('Delete run failed:', err);
    }
  }, [deleteWorkflow]);

  // Rerun a previous workflow from history
  const handleRerunWorkflow = useCallback((run: any, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!run?.repository_id || !run?.goal) return;
    setSelectedRepoId(run.repository_id);
    setGoal(run.goal);
    setSelectedTemplate(run.workflow_type || 'Security Audit');
    setActiveWorkflowId(null);
    setSelectedWorkflowId(null);
  }, [setActiveWorkflowId, setSelectedWorkflowId]);

  // Export report to markdown file
  const handleExportReport = useCallback(() => {
    if (!executionReport) return;
    const markdownContent = `
# Autonomous Execution Report: ${executionReport.goal}
- **Workflow**: ${selectedTemplate}
- **Duration**: ${duration.toFixed(1)}s
- **Confidence Rating**: ${(confidence * 100).toFixed(0)}%
- **Agents Used**: ${executionReport.agents_used?.join(', ')}
- **Tools Executed**: ${executionReport.tools_used?.join(', ')}

## Recommendations
${executionReport.recommendations?.map((r: string) => `- ${r}`).join('\n')}

## Executive Report Summary
${executionReport.executive_summary || 'Analysis complete.'}
`;
    const blob = new Blob([markdownContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution_report_${workflowId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [executionReport, selectedTemplate, duration, confidence, workflowId]);

  // Copy Diff to clipboard
  const handleCopyDiff = useCallback(() => {
    if (!approvalDiff) return;
    navigator.clipboard.writeText(approvalDiff);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  }, [approvalDiff]);

  // Export Diff to file
  const handleExportDiff = useCallback(() => {
    if (!approvalDiff) return;
    const blob = new Blob([approvalDiff], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `refactoring_${workflowId}.diff`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [approvalDiff, workflowId]);

  // Filter & Sort History Runs list
  const processedHistory = useMemo(() => {
    const safeRuns = Array.isArray(historyRuns) ? historyRuns : [];
    let result = [...safeRuns];
    
    // Search filter
    if (filterSearch.trim()) {
      const q = filterSearch.toLowerCase();
      result = result.filter(r => 
        (r.goal && r.goal.toLowerCase().includes(q)) ||
        (r.repository_name && r.repository_name.toLowerCase().includes(q)) ||
        (r.workflow_type && r.workflow_type.toLowerCase().includes(q))
      );
    }

    // Template filter
    if (filterWorkflow !== 'ALL') {
      result = result.filter(r => r.workflow_type === filterWorkflow);
    }

    // Status filter
    if (filterStatus !== 'ALL') {
      result = result.filter(r => r.status === filterStatus);
    }

    // Sort order
    result.sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });

    return result;
  }, [historyRuns, filterSearch, filterWorkflow, filterStatus, sortOrder]);

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* 1. Header Banner */}
      <div className="relative overflow-hidden rounded-2xl glass-lvl2 p-6 shadow-premium border border-border-primary/80 bg-gradient-to-r from-cyan-accent/5 to-purple-accent/5 animate-fade-in">
        <div className="absolute top-[-20%] right-[-10%] w-80 h-80 bg-cyan-accent/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex items-center justify-between gap-6 relative z-10 flex-col sm:flex-row">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-cyan-accent/10 border border-cyan-accent/20 rounded-xl">
              <Bot className="w-6 h-6 text-cyan-accent animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-dark-50 font-display tracking-tight flex items-center gap-2">
                Autonomous Agent Workspace
                <Badge variant={
                  executionStatus === 'completed' ? 'success' :
                  executionStatus === 'failed' ? 'danger' :
                  executionStatus === 'cancelled' ? 'neutral' :
                  ['waiting_approval', 'paused'].includes(executionStatus) ? 'warning' :
                  'primary'
                }>
                  {executionStatus.toUpperCase()}
                </Badge>
              </h1>
              <p className="text-xs text-dark-400 font-sans mt-1">
                Phase 7.1 Dynamic cockpit. Run automated reviews, test mappings, and check unified/side-by-side refactoring approvals.
              </p>
            </div>
          </div>
          
          {['queued', 'starting', 'retrieving', 'planning', 'executing', 'waiting_approval', 'paused'].includes(executionStatus) && (
            <div className="flex items-center gap-4 flex-wrap sm:flex-nowrap">
              <div className="flex items-center gap-3 bg-dark-900/60 border border-cyan-accent/25 px-4.5 py-2.5 rounded-xl text-xs font-mono">
                <Activity className={`w-4 h-4 text-cyan-accent ${executionStatus === 'paused' ? '' : 'animate-spin'}`} />
                <div>
                  <span className="text-dark-500 block text-[9px] uppercase">Active Status</span>
                  <span className="text-cyan-accent font-bold uppercase">{executionStatus}: {streamingProgress}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {executionStatus === 'paused' ? (
                  <Button
                    variant="glass"
                    size="sm"
                    className="border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 text-[10px] font-mono uppercase cursor-pointer"
                    onClick={() => resumeWorkflow(workflowId!)}
                  >
                    Resume
                  </Button>
                ) : (
                  <Button
                    variant="glass"
                    size="sm"
                    className="border-amber-500/20 text-amber-400 hover:bg-amber-500/10 text-[10px] font-mono uppercase cursor-pointer"
                    onClick={() => pauseWorkflow(workflowId!)}
                    disabled={executionStatus === 'queued' || executionStatus === 'waiting_approval'}
                  >
                    Pause
                  </Button>
                )}
                
                <Button
                  variant="danger"
                  size="sm"
                  className="text-[10px] font-mono uppercase cursor-pointer"
                  onClick={() => cancelWorkflow(workflowId!)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. Cockpit Layout Grid (3-column layout) */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 items-start">
        
        {/* Left Panel: Configuration */}
        <div className="xl:col-span-1 space-y-6">
          <Card variant="soft" className="p-6">
            <CardHeader className="border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <Server className="w-4 h-4 text-cyan-accent" />
                <span>Configure Agent Run</span>
              </h3>
            </CardHeader>
            <CardContent className="space-y-5">
              
              {isLoadingRepos ? (
                <div className="space-y-2">
                  <div className="h-3 w-20 bg-dark-800 animate-pulse rounded-lg" />
                  <div className="h-9 bg-dark-800 animate-pulse rounded-xl" />
                </div>
              ) : repoError ? (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400 font-mono space-y-2">
                  <div className="flex items-center gap-2 font-bold">
                    <XCircle className="w-4 h-4 shrink-0" />
                    <span>Repository API Error</span>
                  </div>
                  <p className="text-[10px] text-red-300/80 leading-relaxed">{repoError}</p>
                  <Button variant="glass" size="sm" onClick={fetchRepositories} className="w-full mt-1 flex items-center gap-1.5 justify-center text-[9px]">
                    <RefreshCw className="w-3 h-3" /> Retry
                  </Button>
                </div>
              ) : repositories.length === 0 ? (
                <div className="p-4 bg-dark-900/40 border border-dashed border-border-primary rounded-xl text-center space-y-3">
                  <FolderOpen className="w-7 h-7 text-dark-500 mx-auto" />
                  <p className="text-[10px] text-dark-400 font-sans leading-relaxed">
                    Select a repository to begin analysis.
                  </p>
                  <Button variant="primary" size="sm" onClick={() => navigate('/repositories')} className="w-full flex items-center gap-1.5 justify-center text-[9px]">
                    <FolderOpen className="w-3 h-3" /> Go to Repository Analysis
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-[10px] text-dark-50 font-mono font-bold uppercase">Target Repository</label>
                  <select
                    value={selectedRepoId}
                    onChange={(e) => setSelectedRepoId(e.target.value)}
                    disabled={['queued', 'starting', 'retrieving', 'planning', 'executing', 'waiting_approval', 'paused'].includes(executionStatus)}
                    className="w-full bg-[#0a0f1d] border border-border-primary text-dark-200 rounded-xl px-3.5 py-2.5 text-xs focus:border-cyan-accent/50 outline-none cursor-pointer"
                  >
                    {Array.isArray(repositories) && repositories.map((repo) => (
                      <option key={repo.id} value={repo.id}>
                        {repo.owner}/{repo.name} ({repo.language || 'Codebase'})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-[10px] text-dark-50 font-mono font-bold uppercase">Workflow Template</label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  disabled={['queued', 'starting', 'retrieving', 'planning', 'executing', 'waiting_approval', 'paused'].includes(executionStatus)}
                  className="w-full bg-[#0a0f1d] border border-border-primary text-dark-200 rounded-xl px-3.5 py-2.5 text-xs focus:border-cyan-accent/50 outline-none cursor-pointer"
                >
                  {TEMPLATE_PRESETS.map((tpl) => (
                    <option key={tpl.name} value={tpl.name}>
                      {tpl.name}
                    </option>
                  ))}
                  <option value="Custom Goal">Custom Goal (Dynamic Planner)</option>
                </select>
                <p className="text-[10px] text-dark-400 font-sans italic leading-relaxed px-1">
                  {TEMPLATE_PRESETS.find(t => t.name === selectedTemplate)?.desc || 'Dynamic Planner will draft custom sequences on model execution.'}
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-dark-50 font-mono font-bold uppercase">Natural Language Goal</label>
                <textarea
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  disabled={['queued', 'starting', 'retrieving', 'planning', 'executing', 'waiting_approval', 'paused'].includes(executionStatus)}
                  placeholder="e.g., Audit security vulnerabilities in auth module or refactor unhandled JWT signature decodes"
                  rows={4}
                  className="w-full bg-[#0a0f1d] border border-border-primary text-dark-200 rounded-xl p-3.5 text-xs focus:border-cyan-accent/50 outline-none resize-none font-sans"
                />
              </div>

            </CardContent>
            <CardFooter className="border-t border-border-primary/30 pt-4 mt-4">
              {['queued', 'starting', 'retrieving', 'planning', 'executing', 'waiting_approval', 'paused'].includes(executionStatus) ? (
                <div className="w-full flex items-center justify-center gap-3 p-3 rounded-xl bg-purple-accent/5 border border-purple-accent/25">
                  <div className="w-4 h-4 border-2 border-t-cyan-accent border-r-transparent rounded-full animate-spin" />
                  <span className="text-xs text-cyan-accent font-mono uppercase font-bold tracking-wider">{executionStatus.toUpperCase()}...</span>
                </div>
              ) : (
                <Button
                  variant="primary"
                  glow
                  onClick={handleStartWorkflow}
                  disabled={!selectedRepoId || !goal.trim()}
                  className="w-full flex items-center justify-center gap-4 cursor-pointer"
                >
                  <Play className="w-4 h-4" />
                  <span>START AGENTS FLIGHT</span>
                </Button>
              )}
            </CardFooter>
          </Card>
        </div>

        {/* Center Panel: Graph, Logs, Timeline */}
        <div className="xl:col-span-2 space-y-6">
          
          {/* Timeline & Graph Card */}
          <Card variant="soft" className="p-6">
            <CardHeader className="border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-accent" />
                <span>Interactive Agent Workflow Graph</span>
              </h3>
            </CardHeader>
            <CardContent>
              {planSteps.length > 0 ? (
                <div className="space-y-3 bg-dark-950/20 border border-border-primary/50 rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] text-dark-500 font-mono font-bold uppercase tracking-wider">Step Chain Graph</span>
                    <span className="text-[9px] text-cyan-accent/80 font-mono">Click a node to inspect agent telemetry</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    {planSteps.map((step, idx) => {
                      const isActive = idx === currentStepIdx;
                      const isCompleted = idx < currentStepIdx || executionStatus === 'completed';
                      return (
                        <React.Fragment key={idx}>
                          <GraphNode
                            step={step}
                            index={idx}
                            isActive={isActive}
                            isCompleted={isCompleted}
                            onClick={setSelectedNodeIdx}
                          />
                          {idx < planSteps.length - 1 && (
                            <ArrowRight className="w-3.5 h-3.5 text-dark-600 shrink-0" />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <EmptyState message="Choose a workflow template." />
              )}

              {/* Node Metadata Detail Panel (Opens when node clicked) */}
              {selectedNodeIdx !== null && planSteps[selectedNodeIdx] && (
                <div className="p-4 bg-purple-accent/5 border border-purple-accent/25 rounded-xl space-y-3 animate-fade-in text-xs leading-relaxed mt-4">
                  <div className="flex justify-between items-center border-b border-border-primary/30 pb-2">
                    <span className="font-display font-bold text-dark-200">
                      Step Detail: {planSteps[selectedNodeIdx].name}
                    </span>
                    <button 
                      onClick={() => setSelectedNodeIdx(null)}
                      className="text-[10px] font-mono text-dark-500 hover:text-dark-300 bg-transparent border-none cursor-pointer font-semibold uppercase"
                    >
                      Close [x]
                    </button>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-[9px] text-dark-400">
                    <div>
                      <span className="block text-dark-500 uppercase">Assigned Agent</span>
                      <span className="text-cyan-accent font-semibold block mt-0.5">{planSteps[selectedNodeIdx].agent}</span>
                    </div>
                    <div>
                      <span className="block text-dark-500 uppercase">Status</span>
                      <Badge variant={selectedNodeIdx < currentStepIdx || executionStatus === 'completed' ? 'success' : selectedNodeIdx === currentStepIdx ? 'primary' : 'neutral'} className="mt-0.5">
                        {selectedNodeIdx < currentStepIdx || executionStatus === 'completed' ? 'COMPLETED' : selectedNodeIdx === currentStepIdx ? 'RUNNING' : 'STANDBY'}
                      </Badge>
                    </div>
                    <div>
                      <span className="block text-dark-500 uppercase">Expected Output</span>
                      <span className="text-dark-200 block mt-0.5 truncate max-w-[120px]" title={planSteps[selectedNodeIdx].expected_output}>
                        {planSteps[selectedNodeIdx].expected_output || 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="block text-dark-500 uppercase">Instruction</span>
                      <span className="text-dark-200 block mt-0.5 truncate max-w-[120px]" title={planSteps[selectedNodeIdx].description}>
                        {planSteps[selectedNodeIdx].description || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Execution Timeline Card */}
          <Card variant="soft" className="p-6">
            <CardHeader className="border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-accent" />
                <span>Execution Timeline</span>
              </h3>
            </CardHeader>
            <CardContent>
              {planSteps.length === 0 ? (
                <div className="text-center py-6 text-dark-500 font-mono text-xs">
                  Choose a workflow template.
                </div>
              ) : (
                <div className="relative border-l border-border-primary/60 ml-3 space-y-6">
                  {planSteps.map((step, idx) => {
                    const isCompleted = idx < currentStepIdx || executionStatus === 'completed';
                    const isActive = idx === currentStepIdx;
                    return (
                      <div key={idx} className="relative pl-6">
                        {/* Dot indicator */}
                        <div className={`absolute -left-1.5 top-1 w-3 h-3 rounded-full border ${
                          isCompleted ? 'bg-green-accent border-green-accent shadow-[0_0_8px_rgba(16,185,129,0.3)]' :
                          isActive ? 'bg-cyan-accent border-cyan-accent animate-pulse ring-2 ring-cyan-accent/20' :
                          'bg-[#070b14] border-border-primary/80'
                        }`} />
                        <div className="text-left leading-tight">
                          <span className="text-[8px] font-mono text-dark-500 uppercase tracking-widest font-bold">{step.agent}</span>
                          <h4 className={`text-xs font-semibold mt-0.5 ${isActive ? 'text-cyan-accent font-bold' : 'text-dark-200'}`}>{step.name}</h4>
                          <p className="text-[10px] text-dark-400 font-sans mt-1">{step.description}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Streaming Logs Card */}
          <Card variant="soft" className="p-6">
            <CardHeader className="border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-accent" />
                <span>Streaming Logs Console</span>
              </h3>
            </CardHeader>
            <CardContent>
              <div ref={logContainerRef} onScroll={handleLogScroll} className="w-full min-h-[220px] max-h-[320px] overflow-y-auto bg-[#040811]/90 border border-border-primary rounded-xl p-4 font-mono text-[11px] leading-relaxed scrollbar-thin">
                {logs.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-dark-600 italic py-16">
                    <span>Logs output standby...</span>
                  </div>
                ) : (
                  <div style={{ height: totalLogsHeight, position: 'relative', width: '100%' }}>
                    {visibleLogs.map(({ log, actualIndex }) => {
                      const isWarn = log.level === 'WARNING';
                      const isErr = log.level === 'ERROR';
                      const isSucc = log.level === 'SUCCESS';
                      return (
                        <div 
                          key={actualIndex} 
                          style={{
                            position: 'absolute',
                            top: actualIndex * itemHeight,
                            left: 0,
                            right: 0,
                            height: itemHeight
                          }}
                          className="flex gap-2.5 text-left items-start overflow-hidden whitespace-nowrap"
                        >
                          <span className="text-dark-600 shrink-0 select-none">[{log.timestamp ? log.timestamp.toFixed(1) + 's' : 'info'}]</span>
                          <span className={`shrink-0 select-none font-bold ${isErr ? 'text-red-500' : isWarn ? 'text-amber-500' : isSucc ? 'text-green-accent' : 'text-cyan-accent'}`}>
                              {isErr ? '✗' : isWarn ? '!' : isSucc ? '✓' : 'ℹ'}
                          </span>
                          <span className={isErr ? 'text-red-400' : isWarn ? 'text-amber-400' : isSucc ? 'text-green-300' : 'text-dark-300'}>
                            {log.message}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

        </div>

        {/* Right Panel: Telemetry & Memory */}
        <div className="xl:col-span-1 space-y-6">
          
          {/* Telemetry Card */}
          <Card variant="soft" className="p-6">
            <CardHeader className="border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-accent" />
                <span>Telemetry parameters</span>
              </h3>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 text-left font-mono text-[9px] bg-dark-950/30 p-3 rounded-xl border border-border-primary/50">
                <div className="space-y-1">
                  <span className="text-dark-500 block uppercase">Tokens</span>
                  <span className="text-dark-100 font-bold">{tokensUsed.toLocaleString()}</span>
                </div>
                <div className="space-y-1">
                  <span className="text-dark-500 block uppercase">Latency</span>
                  <span className="text-dark-100 font-bold">{duration.toFixed(1)}s</span>
                </div>
                <div className="space-y-1 mt-2">
                  <span className="text-dark-500 block uppercase">Confidence</span>
                  <span className="text-cyan-accent font-bold">{(confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="space-y-1 mt-2">
                  <span className="text-dark-500 block uppercase">Providers</span>
                  <span className="text-purple-accent font-bold truncate max-w-[80px] block">{providersUsed.join(', ') || 'N/A'}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Repository Memory Card */}
          <Card variant="soft" className="p-6">
            <CardHeader className="border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-accent" />
                <span>Repository Memory</span>
              </h3>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <label className="text-[10px] text-dark-500 font-mono font-bold uppercase block text-left">Analyzed Files ({retrievedChunks.length})</label>
                <div className="space-y-2 max-h-[260px] overflow-y-auto scrollbar-thin">
                  {retrievedChunks.length === 0 ? (
                    <div className="text-[10px] text-dark-500 italic p-4 text-center border border-dashed border-border-primary rounded-xl">
                      Select a repository to begin analysis.
                    </div>
                  ) : (
                    Array.from(new Set(retrievedChunks.map(c => c.path))).map((path, idx) => {
                      const matchChunks = retrievedChunks.filter(c => c.path === path);
                      return (
                        <div key={idx} className="p-3 bg-dark-900/30 border border-border-primary/50 rounded-xl flex items-start gap-2.5">
                          <FileText className="w-4 h-4 text-cyan-accent mt-0.5 shrink-0" />
                          <div className="min-w-0 text-left leading-none">
                            <span className="text-xs font-semibold text-dark-200 block truncate" title={path}>{path.split('/').pop() || path}</span>
                            <span className="text-[8px] text-dark-500 font-mono block mt-1.5">
                              {matchChunks.length} chunks · lines {Math.min(...matchChunks.map(c => c.start_line))}-{Math.max(...matchChunks.map(c => c.end_line))}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Analytics Cockpit Card */}
          {analytics && (
            <AnalyticsDashboard
              analytics={analytics}
              duration={duration}
              providers={providersUsed}
            />
          )}

        </div>

      </div>

      {/* 3. Bottom Panels: Report, Approvals, History */}
      <div className="space-y-6 w-full">
        
        {/* Enhanced Approval Panel */}
        {executionStatus === 'waiting_approval' && approvalDiff && (
          <Card variant="soft" className="border-2 border-amber-500/50 bg-amber-500/5 text-left p-6">
            <CardHeader className="pb-3 border-b border-amber-500/20 flex justify-between items-center mb-4">
              <div>
                <h3 className="text-xs font-bold text-amber-400 font-display uppercase tracking-wider flex items-center gap-2">
                  <Code className="w-4 h-4 animate-pulse" />
                  <span>Human Approval Decision Required</span>
                </h3>
                <p className="text-[9px] text-amber-500/80 font-mono mt-0.5">Workflow suspended. Code edits generated for workspace files.</p>
              </div>
              <Badge variant="warning">AWAITING CODE APPROVAL</Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              
              {/* Meta details */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-[9px] text-dark-300 bg-dark-950/40 p-3 rounded-xl border border-border-primary/50">
                <div>
                  <span className="block text-dark-500 uppercase">Risk Assessment</span>
                  <span className={`font-bold mt-0.5 block ${approvalRisk === 'High' ? 'text-red-400' : approvalRisk === 'Medium' ? 'text-amber-400' : 'text-green-accent'}`}>
                    {approvalRisk.toUpperCase()}
                  </span>
                </div>
                <div>
                  <span className="block text-dark-500 uppercase">Impact Metric</span>
                  <span className="text-dark-200 mt-0.5 block truncate max-w-[150px]" title={approvalImpact}>{approvalImpact || 'Improves safety'}</span>
                </div>
                <div>
                  <span className="block text-dark-500 uppercase">Confidence rating</span>
                  <span className="text-cyan-accent font-bold mt-0.5 block">{(approvalConfidence * 100).toFixed(0)}%</span>
                </div>
              </div>

              <div className="bg-dark-950/30 p-3.5 rounded-xl border border-border-primary/50 space-y-2">
                <span className="text-[10px] text-dark-500 font-mono font-bold uppercase block">Modifications Rationale</span>
                <p className="text-xs text-dark-200 leading-relaxed font-sans">{approvalReason}</p>
                
                <span className="text-[10px] text-dark-500 font-mono font-bold uppercase block pt-2">Affected Files</span>
                <div className="flex flex-wrap gap-2">
                  {approvalFiles.map((f, i) => (
                    <Badge key={i} variant="secondary" className="font-mono text-[9px]">{f}</Badge>
                  ))}
                </div>
              </div>

              {/* Diff Viewer toggles */}
              <div className="space-y-2">
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-dark-500 font-mono font-bold uppercase">Diff Preview</span>
                    <button
                      onClick={() => setShowSideBySide(!showSideBySide)}
                      className="text-[9px] text-purple-accent hover:text-purple-400 font-mono font-bold bg-transparent border-none cursor-pointer uppercase underline"
                    >
                      {showSideBySide ? 'View Unified Diff' : 'View Side-by-Side View'}
                    </button>
                  </div>
                  <div className="flex gap-4">
                    <button
                      onClick={handleCopyDiff}
                      className="text-[9px] text-cyan-accent hover:text-cyan-400 font-mono font-bold bg-transparent border-none cursor-pointer flex items-center gap-1 uppercase"
                    >
                      {isCopied ? <Check className="w-3 h-3 text-green-accent" /> : <Copy className="w-3 h-3" />}
                      <span>Copy</span>
                    </button>
                    <button
                      onClick={handleExportDiff}
                      className="text-[9px] text-cyan-accent hover:text-cyan-400 font-mono font-bold bg-transparent border-none cursor-pointer flex items-center gap-1 uppercase"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export</span>
                    </button>
                  </div>
                </div>

                {showSideBySide ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <span className="text-[9px] text-dark-500 font-mono uppercase block">Original Workspace Files</span>
                      <pre className="overflow-x-auto bg-[#03060c] border border-red-500/20 rounded-xl p-3 font-mono text-[9px] leading-normal max-h-[220px] scrollbar-thin text-red-300 select-text">
                        {approvalDiff.split('\n').filter(l => l.startsWith('-') && !l.startsWith('---')).map(l => l.substring(1)).join('\n') || 'No lines deleted.'}
                      </pre>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[9px] text-dark-500 font-mono uppercase block">Proposed Code Updates</span>
                      <pre className="overflow-x-auto bg-[#03060c] border border-green-500/20 rounded-xl p-3 font-mono text-[9px] leading-normal max-h-[220px] scrollbar-thin text-green-300 select-text">
                        {approvalDiff.split('\n').filter(l => l.startsWith('+') && !l.startsWith('+++')).map(l => l.substring(1)).join('\n') || 'No lines added.'}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <pre className="overflow-x-auto bg-[#03060c] border border-border-primary rounded-xl p-3.5 font-mono text-[10px] leading-normal text-left max-h-[220px] scrollbar-thin text-dark-400 selection:bg-cyan-accent/25 select-text">
                    {approvalDiff}
                  </pre>
                )}
              </div>

            </CardContent>
            <CardFooter className="flex gap-4 border-t border-amber-500/20 pt-4 mt-4">
              <Button
                variant="primary"
                glow
                disabled={approvalSubmitting}
                onClick={() => handleApprovalDecision(true)}
                className="flex-1 flex items-center justify-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>APPROVE & APPLY MODIFICATIONS</span>
              </Button>
              <Button
                variant="danger"
                disabled={approvalSubmitting}
                onClick={() => handleApprovalDecision(false)}
                className="flex-1 flex items-center justify-center gap-2"
              >
                <XCircle className="w-4 h-4" />
                <span>REJECT & SKIP CHANGES</span>
              </Button>
            </CardFooter>
          </Card>
        )}

        {/* Final Report compiled panel */}
        {executionReport ? (
          <Card variant="soft" className="text-left animate-fade-in p-6">
            <CardHeader className="flex justify-between items-center border-b border-border-primary/30 pb-3.5 mb-4">
              <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                <ScrollText className="w-4 h-4 text-cyan-accent" />
                <span>Final Execution Summary Report</span>
              </h3>
              <Button variant="glass" size="sm" onClick={handleExportReport} className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider">
                <Download className="w-3.5 h-3.5" />
                <span>Export Report</span>
              </Button>
            </CardHeader>
            <CardContent className="space-y-6">
              
              <div className="prose prose-invert prose-xs text-xs font-sans text-dark-300 leading-relaxed max-w-none text-left bg-dark-950/20 border border-border-primary/50 rounded-xl p-5 select-text">
                <ReactMarkdown>{executionReport.executive_summary || 'No summary compiled.'}</ReactMarkdown>
              </div>

              {executionReport.recommendations && executionReport.recommendations.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-[10px] text-dark-500 font-mono font-bold uppercase tracking-wider">Recommendations Checklist</h4>
                  <div className="grid grid-cols-1 gap-2.5">
                    {executionReport.recommendations.map((rec: string, i: number) => (
                      <div key={i} className="flex gap-3 items-start p-3 bg-dark-900/40 border border-border-primary/60 rounded-xl">
                        <CheckCircle2 className="w-4 h-4 text-cyan-accent shrink-0 mt-0.5" />
                        <p className="text-xs text-dark-200 leading-normal">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </CardContent>
          </Card>
        ) : (
          executionStatus !== 'waiting_approval' && (
            <Card variant="soft" className="min-h-[140px] flex flex-col justify-center items-center text-center text-dark-500 italic p-6">
              <ScrollText className="w-8 h-8 text-dark-600 mb-2" />
              <span>Run an analysis to generate your first report.</span>
            </Card>
          )
        )}

        {/* 4. Filterable Workflow History list */}
        <Card variant="soft" className="text-left p-6">
          <CardHeader className="pb-3 border-b border-border-primary/30 flex flex-col gap-4 mb-4">
            <div className="flex justify-between items-center w-full">
              <div>
                <h3 className="text-xs font-bold text-dark-200 font-display uppercase tracking-wider flex items-center gap-2">
                  <History className="w-4 h-4 text-purple-accent" />
                  <span>Historical Executions Console</span>
                </h3>
                <p className="text-[10px] text-dark-500 font-mono mt-0.5">Track, filter, rerun, or delete past agent execution workflows</p>
              </div>
              <Button variant="glass" size="sm" onClick={() => fetchHistory()} className="font-mono text-[9px] uppercase tracking-wider">
                Refresh history
              </Button>
            </div>

            {/* Upgraded Filters and Search layout */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-2">
              <div className="relative">
                <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-dark-500" />
                <input
                  type="text"
                  placeholder="Search goals or repos..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                  className="w-full bg-[#0a0f1d] border border-border-primary text-dark-200 rounded-xl pl-9.5 pr-3 py-2 text-xs focus:border-cyan-accent/50 outline-none font-sans"
                />
              </div>
              
              <div className="flex items-center gap-2 bg-[#0a0f1d] border border-border-primary rounded-xl px-3 py-1.5">
                <SlidersHorizontal className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                <select
                  value={filterWorkflow}
                  onChange={(e) => setFilterWorkflow(e.target.value)}
                  className="w-full bg-transparent text-dark-200 text-xs outline-none cursor-pointer"
                >
                  <option value="ALL">All Workflows</option>
                  {TEMPLATE_PRESETS.map(t => (
                    <option key={t.name} value={t.name}>{t.name}</option>
                  ))}
                  <option value="Custom Goal">Custom Goal</option>
                </select>
              </div>

              <div className="flex items-center gap-2 bg-[#0a0f1d] border border-border-primary rounded-xl px-3 py-1.5">
                <Info className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="w-full bg-transparent text-dark-200 text-xs outline-none cursor-pointer"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="pending_approval">Pending Approval</option>
                </select>
              </div>

              <button
                onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
                className="flex items-center justify-center gap-2 bg-[#0a0f1d] border border-border-primary hover:border-cyan-accent/25 rounded-xl px-4 py-2 text-xs text-dark-300 font-mono transition cursor-pointer"
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
                <span>Sort: {sortOrder === 'desc' ? 'Newest' : 'Oldest'}</span>
              </button>
            </div>
          </CardHeader>

          <CardContent className="overflow-x-auto select-none">
            {isLoadingHistory ? (
              <LoaderSkeleton />
            ) : processedHistory.length === 0 ? (
              <EmptyState message="No executions found." />
            ) : (
              <table className="w-full text-xs text-left border-collapse min-w-[700px]">
                <thead>
                  <tr className="border-b border-border-primary text-dark-500 font-mono text-[9px] font-bold uppercase tracking-wider">
                    <th className="py-3 px-4">Repository</th>
                    <th className="py-3 px-4">Workflow</th>
                    <th className="py-3 px-4">Goal Description</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Created Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-primary/30">
                  {processedHistory.map((run) => (
                    <tr 
                      key={run.id}
                      onClick={() => handleLoadHistoryRun(run.id)}
                      className={`hover:bg-dark-900/30 cursor-pointer transition-all duration-150 ${
                        workflowId === run.id ? 'bg-purple-accent/5 border-l-2 border-l-cyan-accent' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-semibold text-dark-200 truncate max-w-[130px]" title={run.repository_name}>
                        {run.repository_name}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="font-display font-medium text-cyan-accent">{run.workflow_type}</span>
                      </td>
                      <td className="py-3.5 px-4 truncate max-w-[220px] text-dark-400 font-sans" title={run.goal}>
                        {run.goal}
                      </td>
                      <td className="py-3.5 px-4">
                        <Badge variant={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : run.status === 'pending_approval' ? 'warning' : 'primary'}>
                          {run.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-dark-300">
                        {run.duration ? `${run.duration.toFixed(1)}s` : '—'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-dark-500 text-[10px]">
                        {new Date(run.created_at).toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={(e) => handleRerunWorkflow(run, e)}
                            className="p-2 hover:bg-cyan-500/10 text-dark-400 hover:text-cyan-accent rounded-xl transition cursor-pointer"
                            title="Rerun workflow"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => handleDeleteRun(run.id, e)}
                            className="p-2 hover:bg-red-500/10 text-dark-500 hover:text-red-500 rounded-xl transition cursor-pointer"
                            title="Delete history"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AgentWorkspacePage;
