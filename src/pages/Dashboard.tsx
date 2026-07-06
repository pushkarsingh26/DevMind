import React from 'react';
import { RepositoryCard } from '../components/RepositoryCard';
import { TaskSelector } from '../components/TaskSelector';
import { StatusCard } from '../components/StatusCard';
import { OutputPanel } from '../components/OutputPanel';
import { PrimaryButton } from '../components/PrimaryButton';
import { useAnalysis } from '../hooks/useAnalysis';
import { RefreshCw, Play } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const {
    status,
    isAnalyzing,
    startAnalysis,
    resetAnalysis,
    analysisResult,
  } = useAnalysis();

  return (
    <div className="space-y-8">
      {/* 2-Column Inputs Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RepositoryCard />
        <TaskSelector />
      </div>

      {/* Action Buttons Panel */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-dark-900 border border-dark-800 rounded-lg p-6">
        <div className="text-left font-mono mb-4 sm:mb-0">
          <h3 className="text-sm font-semibold text-dark-200 uppercase">Execute Agent Pipeline</h3>
          <p className="text-xs text-dark-500 mt-1">
            Running in local sandbox. Agent results will appear sequentially below.
          </p>
        </div>
        <div className="flex gap-3 w-full sm:w-auto">
          {analysisResult && (
            <button
              type="button"
              onClick={resetAnalysis}
              disabled={isAnalyzing}
              className="px-4 py-3 border border-dark-850 hover:border-dark-700 bg-dark-950 text-dark-300 hover:text-dark-100 rounded-md font-mono text-sm font-semibold uppercase flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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

      {/* Status Panel */}
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-6">
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

      {/* Output Panel */}
      <OutputPanel />
    </div>
  );
};
