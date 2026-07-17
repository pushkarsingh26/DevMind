import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Database, ArrowLeft, RefreshCw, Layers, Award, FileText, ShieldAlert, Sparkles } from 'lucide-react';

import { MemoryDashboard } from '../components/MemoryDashboard';
import { PatternPanel } from '../components/PatternPanel';
import { RecommendationPanel } from '../components/RecommendationPanel';
import { WorkflowHistoryPanel } from '../components/WorkflowHistoryPanel';
import { LearningMetricsPanel } from '../components/LearningMetricsPanel';
import { EmptyState, Button } from '../components/ui';

type TabId = 'dashboard' | 'patterns' | 'recommendations' | 'history' | 'metrics';

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'dashboard', label: 'Repository Memory', icon: Layers },
  { id: 'patterns', label: 'Patterns', icon: ShieldAlert },
  { id: 'recommendations', label: 'Recommendations', icon: Sparkles },
  { id: 'history', label: 'Execution History', icon: FileText },
  { id: 'metrics', label: 'Learning Metrics', icon: Award },
];

const backendUrl = () => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const MemoryPage: React.FC = () => {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [memory, setMemory] = useState<any>(null);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);

  const fetchMemoryData = useCallback(async (tab: TabId) => {
    if (!repositoryId) return;
    setLoading(true);
    try {
      const base = `${backendUrl()}/api/memory/${repositoryId}`;
      if (tab === 'dashboard') {
        const res = await axios.get(base);
        setMemory(res.data);
      } else if (tab === 'patterns') {
        const res = await axios.get(`${base}/patterns`);
        setPatterns(res.data);
      } else if (tab === 'recommendations') {
        const res = await axios.get(`${base}/recommendations`);
        setRecommendations(res.data);
      } else if (tab === 'history') {
        const res = await axios.get(`${base}/history`);
        setHistory(res.data);
      } else if (tab === 'metrics') {
        const res = await axios.get(`${base}/metrics`);
        setMetrics(res.data);
      }
    } catch (err) {
      console.error('[MemoryPage] Fetch failed:', err);
      if (tab === 'dashboard') setMemory(null);
      if (tab === 'metrics') setMetrics(null);
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    fetchMemoryData(activeTab);
  }, [activeTab, fetchMemoryData]);

  const handleRebuild = async () => {
    if (!repositoryId) return;
    setRebuilding(true);
    try {
      await axios.post(`${backendUrl()}/api/memory/${repositoryId}/rebuild`);
      await fetchMemoryData(activeTab);
    } catch (err) {
      console.error('[MemoryPage] Rebuild failed:', err);
    } finally {
      setRebuilding(false);
    }
  };

  if (!repositoryId) {
    return (
      <EmptyState
        title="No Repository Selected"
        description="Select a repository to explore its memory and execution insights."
        icon={<Database className="w-8 h-8 text-cyan-accent animate-pulse" />}
        action={
          <Button variant="primary" glow onClick={() => navigate('/repositories')}>
            VIEW REPOSITORIES
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border-primary pb-4">
        <div className="space-y-1">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-xs text-dark-400 font-mono hover:text-cyan-accent cursor-pointer mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>BACK</span>
          </button>
          <h1 className="text-xl font-extrabold text-dark-50 font-display tracking-tight flex items-center gap-2.5">
            <Database className="w-6 h-6 text-cyan-accent" />
            <span>Memory & Learning Dashboard</span>
          </h1>
          <p className="text-xs text-dark-400 font-mono">
            Repository: <span className="text-cyan-accent">{repositoryId}</span>
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="secondary"
            className="flex items-center gap-1.5 text-[11px] font-mono"
            onClick={handleRebuild}
            disabled={rebuilding}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            REBUILD MEMORY
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-border-primary pb-3">
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-mono uppercase tracking-wider transition-all cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-cyan-accent/10 text-cyan-accent border border-cyan-accent/30'
                  : 'text-dark-400 hover:text-dark-200 border border-transparent'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
        <button
          onClick={() => fetchMemoryData(activeTab)}
          className="ml-auto flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-mono text-dark-400 hover:text-cyan-accent cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <p className="text-xs text-dark-500 font-mono text-center py-12">Loading Memory Data...</p>
      ) : (
        <div className="space-y-4">
          {activeTab === 'dashboard' && (
            memory ? <MemoryDashboard memory={memory} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">
                No active memory model exists for this repository yet. Complete your first workflow to instantiate it.
              </p>
            )
          )}
          {activeTab === 'patterns' && <PatternPanel patterns={patterns} />}
          {activeTab === 'recommendations' && <RecommendationPanel recommendations={recommendations} />}
          {activeTab === 'history' && <WorkflowHistoryPanel history={history} />}
          {activeTab === 'metrics' && (
            metrics ? <LearningMetricsPanel metrics={metrics} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">
                No performance metrics available yet.
              </p>
            )
          )}
        </div>
      )}
    </div>
  );
};
export default MemoryPage;
