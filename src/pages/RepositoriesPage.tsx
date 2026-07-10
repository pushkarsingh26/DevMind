import React, { useMemo } from 'react';
import { RepositoryCard } from '../components/RepositoryCard';
import { TaskSelector } from '../components/TaskSelector';
import { StatusCard } from '../components/StatusCard';
import { OutputPanel } from '../components/OutputPanel';
import { Timeline } from '../components/Timeline';
import { AISessionPanel } from '../components/AISessionPanel';
import { IntelligenceDashboard } from '../components/IntelligenceDashboard';
import { ContextViewer } from '../components/ContextViewer';
import { AIConfiguration } from '../components/AIConfiguration';
import { useAnalysis } from '../hooks/useAnalysis';
import { RefreshCw, Play, Loader2, Sparkles, Clock } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, Progress } from '../components/ui';

export const RepositoriesPage: React.FC = () => {
  const {
    status,
    isAnalyzing,
    startAnalysis,
    resetAnalysis,
    analysisResult,
    parsedReport,
    overallProgress,
    currentStage,
    selectedTask
  } = useAnalysis();

  // Estimate remaining duration in seconds based on typical 20-30s runs
  const estimatedRemainingSeconds = useMemo(() => {
    if (!isAnalyzing) return 0;
    if (overallProgress <= 5) return 25;
    if (overallProgress >= 95) return 2;
    return Math.max(2, Math.ceil((100 - overallProgress) * 0.25));
  }, [isAnalyzing, overallProgress]);

  // Determine timeline operational status
  const timelineStatus = useMemo(() => {
    if (isAnalyzing) return 'active';
    if (parsedReport) {
      return parsedReport.aiOutput?.is_fallback ? 'failed' : 'completed';
    }
    return 'waiting';
  }, [isAnalyzing, parsedReport]);

  return (
    <div className="space-y-8 select-none text-left">
      {/* 1. Repository Selector and Task Config Inputs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 print:hidden relative z-10">
        <RepositoryCard />
        <TaskSelector />
      </div>

      {/* 2. Pipeline Execution Panel & Progress Bar */}
      <Card variant="soft" className="print:hidden">
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div className="text-left font-mono">
            <h3 className="text-sm font-bold text-dark-100 uppercase flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-accent" />
              <span>01. Execute Agent Pipeline</span>
            </h3>
            <p className="text-xs text-dark-500 mt-1">
              Start analysis to index chunks and query the failover engine chain.
            </p>
          </div>
          <div className="flex gap-3 w-full sm:w-auto">
            {analysisResult && (
              <Button
                variant="glass"
                onClick={resetAnalysis}
                disabled={isAnalyzing}
                className="flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>RESET</span>
              </Button>
            )}
            <div className="flex-1 sm:flex-initial sm:w-64">
              <Button
                variant="primary"
                glow
                onClick={startAnalysis}
                loading={isAnalyzing}
                className="w-full flex items-center justify-center gap-2"
              >
                <Play className="w-3.5 h-3.5 fill-dark-950 text-dark-950" />
                <span>START ANALYSIS</span>
              </Button>
            </div>
          </div>
        </div>

        {/* Professional progress tracker shown during live audits */}
        {isAnalyzing && (
          <div className="border-t border-border-primary pt-5 mt-5 space-y-3 font-mono">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-2">
              <div className="flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 text-cyan-accent animate-spin" />
                <span className="text-dark-300">STAGE: <span className="text-cyan-accent font-semibold">{currentStage}</span></span>
              </div>
              <div className="flex items-center gap-4 text-dark-500 text-[11px]">
                <span>TASK: <span className="text-dark-300 font-bold uppercase">{selectedTask}</span></span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-dark-400" />
                  <span>~{estimatedRemainingSeconds}s remaining</span>
                </span>
              </div>
            </div>

            {/* Premium progress bar primitive */}
            <Progress value={overallProgress} color="primary" />

            <div className="flex justify-between text-[9px] text-dark-500 font-bold">
              <span>0% INITIALIZING</span>
              <span>{overallProgress}% ACTIVE PROGRESS</span>
              <span>100% COMPLETE</span>
            </div>
          </div>
        )}
      </Card>

      {/* 3. AI Execution Stage Timeline */}
      <Timeline currentStage={currentStage} progress={overallProgress} status={timelineStatus} />

      {/* 4. Stage Status Monitor Cards */}
      <Card variant="soft" className="print:hidden">
        <CardHeader>
          <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
            <span className="text-xs bg-purple-accent/10 text-purple-accent border border-purple-accent/20 px-2 py-0.5 rounded-lg font-mono">03</span>
            <span>AGENT WORKSPACE MONITOR</span>
          </h2>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard
            agentName="Planner Agent"
            status={status.planner.status}
            message={status.planner.message}
          />
          <StatusCard
            agentName="Retriever Agent"
            status={status.retriever.status}
            message={status.retriever.message}
          />
          <StatusCard
            agentName="Reviewer Agent"
            status={status.reviewer.status}
            message={status.reviewer.message}
          />
          <StatusCard
            agentName="Critic Agent"
            status={status.critic.status}
            message={status.critic.message}
          />
        </CardContent>
      </Card>

      {/* 5. Cognitive Session Details */}
      <AISessionPanel report={parsedReport} />

      {/* 6. Repository Intelligence Dashboard */}
      {parsedReport && <IntelligenceDashboard report={parsedReport} />}

      {/* 7. Retrieved Context Viewer */}
      {parsedReport && parsedReport.chunks && (
        <ContextViewer chunks={parsedReport.chunks} />
      )}

      {/* 8. Main Collapsible Sectioned Report Output */}
      <OutputPanel />

      {/* 9. Read-only configuration panel */}
      <AIConfiguration report={parsedReport} />
    </div>
  );
};

export default RepositoriesPage;
