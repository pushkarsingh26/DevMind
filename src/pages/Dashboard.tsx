import React, { useMemo } from 'react';
import { RepositoryCard } from '../components/RepositoryCard';
import { TaskSelector } from '../components/TaskSelector';
import { StatusCard } from '../components/StatusCard';
import { OutputPanel } from '../components/OutputPanel';
import { PrimaryButton } from '../components/PrimaryButton';
import { Timeline } from '../components/Timeline';
import { AISessionPanel } from '../components/AISessionPanel';
import { IntelligenceDashboard } from '../components/IntelligenceDashboard';
import { ContextViewer } from '../components/ContextViewer';
import { AIConfiguration } from '../components/AIConfiguration';
import { useAnalysis } from '../hooks/useAnalysis';
import { motion } from 'framer-motion';
import { RefreshCw, Play, Loader2, Sparkles, Clock } from 'lucide-react';

export const Dashboard: React.FC = () => {
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
    // Linear approximation
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
    <div className="space-y-8 select-none">
      {/* 1. Repository Selector and Task Config Inputs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 print:hidden">
        <RepositoryCard />
        <TaskSelector />
      </div>

      {/* 2. Pipeline Execution Panel & Progress Bar */}
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 space-y-6 print:hidden">
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div className="text-left font-mono">
            <h3 className="text-sm font-semibold text-dark-200 uppercase flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>01. Execute Agent Pipeline</span>
            </h3>
            <p className="text-xs text-dark-500 mt-1">
              Start analysis to index chunks and query the provider failover chain.
            </p>
          </div>
          <div className="flex gap-3 w-full sm:w-auto">
            {analysisResult && (
              <button
                type="button"
                onClick={resetAnalysis}
                disabled={isAnalyzing}
                className="px-4 py-3 border border-dark-850 hover:border-dark-700 bg-dark-950 text-dark-300 hover:text-dark-100 rounded font-mono text-sm font-semibold uppercase flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <RefreshCw className="w-4 h-4" />
                <span>RESET</span>
              </button>
            )}
            <div className="flex-1 sm:flex-initial sm:w-64">
              <PrimaryButton onClick={startAnalysis} loading={isAnalyzing}>
                <span className="flex items-center justify-center gap-2">
                  <Play className="w-4 h-4 fill-white" />
                  <span>START ANALYSIS</span>
                </span>
              </PrimaryButton>
            </div>
          </div>
        </div>

        {/* Professional progress tracker shown during live audits */}
        {isAnalyzing && (
          <div className="border-t border-dark-850 pt-5 space-y-3 font-mono">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-2">
              <div className="flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                <span className="text-dark-300">STAGE: <span className="text-cyan-400 font-semibold">{currentStage}</span></span>
              </div>
              <div className="flex items-center gap-4 text-dark-500 text-[11px]">
                <span>TASK: <span className="text-dark-300 font-bold uppercase">{selectedTask}</span></span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-dark-400" />
                  <span>~{estimatedRemainingSeconds}s remaining</span>
                </span>
              </div>
            </div>

            {/* Pulsing progress bar */}
            <div className="w-full bg-dark-950 h-2.5 rounded-full overflow-hidden border border-dark-850 p-0.5">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-brand-500 to-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.3)]"
                initial={{ width: 0 }}
                animate={{ width: `${overallProgress}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
            <div className="flex justify-between text-[9px] text-dark-500 font-bold">
              <span>0% INDEPENDENT CLONER</span>
              <span>{overallProgress}% ACTIVE</span>
              <span>100% AUDIT REPORT</span>
            </div>
          </div>
        )}
      </div>

      {/* 3. AI Execution Stage Timeline */}
      <Timeline currentStage={currentStage} progress={overallProgress} status={timelineStatus} />

      {/* 4. Stage Status Monitor Cards */}
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 print:hidden">
        <h2 className="text-base font-semibold text-dark-100 font-mono mb-4 flex items-center gap-2">
          <span>03.</span> AGENT WORKSPACE MONITOR
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
        </div>
      </div>

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
