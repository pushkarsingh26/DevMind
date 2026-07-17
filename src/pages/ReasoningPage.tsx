import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Brain, ArrowLeft, RefreshCw, Layers, Award, FileText, ShieldAlert, Sparkles, Database } from 'lucide-react';

import { ReasoningDashboard } from '../components/ReasoningDashboard';
import { DependencyReasoningPanel } from '../components/DependencyReasoningPanel';
import { ImpactAnalysisPanel } from '../components/ImpactAnalysisPanel';
import { EvidenceRankingPanel } from '../components/EvidenceRankingPanel';
import { HistoricalReasoningPanel } from '../components/HistoricalReasoningPanel';
import { ReasoningTimeline } from '../components/ReasoningTimeline';
import { EmptyState, Button } from '../components/ui';

type TabId = 'overview' | 'dependencies' | 'impact' | 'evidence' | 'historical' | 'telemetry';

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: Brain },
  { id: 'dependencies', label: 'Dependencies', icon: Layers },
  { id: 'impact', label: 'Impact Analysis', icon: ShieldAlert },
  { id: 'evidence', label: 'Evidence Leaderboard', icon: Award },
  { id: 'historical', label: 'Historical Fixes', icon: FileText },
  { id: 'telemetry', label: 'Telemetry Summary', icon: Sparkles },
];

const backendUrl = () => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const ReasoningPage: React.FC = () => {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [dependencies, setDependencies] = useState<any>(null);
  const [impact, setImpact] = useState<any>(null);
  const [evidence, setEvidence] = useState<any>(null);
  const [historical, setHistorical] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);

  const fetchReasoningData = useCallback(async (tab: TabId) => {
    if (!repositoryId) return;
    setLoading(true);
    try {
      const base = `${backendUrl()}/api/reasoning/${repositoryId}`;
      if (tab === 'overview') {
        const res = await axios.get(base);
        setSummary(res.data);
      } else if (tab === 'dependencies') {
        const res = await axios.get(`${base}/dependencies`);
        setDependencies(res.data);
      } else if (tab === 'impact') {
        const res = await axios.get(`${base}/impact`);
        setImpact(res.data);
      } else if (tab === 'evidence') {
        const res = await axios.get(`${base}/evidence`);
        setEvidence(res.data);
      } else if (tab === 'historical') {
        const res = await axios.get(`${base}/history`);
        setHistorical(res.data);
      } else if (tab === 'telemetry') {
        const res = await axios.get(`${base}/metrics`);
        setMetrics(res.data);
      }
    } catch (err: any) {
      console.error('[ReasoningPage] Fetch failed:', err);
      // Clean states on failure
      if (tab === 'overview') setSummary(null);
      if (tab === 'dependencies') setDependencies(null);
      if (tab === 'impact') setImpact(null);
      if (tab === 'evidence') setEvidence(null);
      if (tab === 'historical') setHistorical(null);
      if (tab === 'telemetry') setMetrics(null);
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    fetchReasoningData(activeTab);
  }, [activeTab, fetchReasoningData]);

  const handleRebuild = async () => {
    if (!repositoryId) return;
    setRebuilding(true);
    try {
      await axios.post(`${backendUrl()}/api/reasoning/${repositoryId}/rebuild`);
      // Wait slightly for thread build to begin
      await new Promise(resolve => setTimeout(resolve, 800));
      await fetchReasoningData(activeTab);
    } catch (err) {
      console.error('[ReasoningPage] Rebuild failed:', err);
    } finally {
      setRebuilding(false);
    }
  };

  if (!repositoryId) {
    return (
      <EmptyState
        title="No Repository Selected"
        description="Select a repository to explore its autonomous reasoning outputs."
        icon={<Brain className="w-8 h-8 text-cyan-accent animate-pulse" />}
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
            <Brain className="w-6 h-6 text-cyan-accent" />
            <span>Autonomous Reasoning Engine</span>
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
            REBUILD REASONING
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
          onClick={() => fetchReasoningData(activeTab)}
          className="ml-auto flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-mono text-dark-400 hover:text-cyan-accent cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-6 h-6 text-cyan-accent animate-spin" />
          <p className="text-xs text-dark-500 font-mono">Loading Reasoning Analytics...</p>
        </div>
      ) : (
        <div className="space-y-4">
          {activeTab === 'overview' && (
            summary ? <ReasoningDashboard summary={summary} /> : (
              <EmptyState
                title="No Reasoning Summary"
                description="No active reasoning model exists for this repository yet. Trigger a rebuild or complete a workflow to instantiate it."
                icon={<Database className="w-8 h-8 text-dark-600" />}
                action={
                  <Button variant="primary" glow onClick={handleRebuild} disabled={rebuilding}>
                    TRIGGER BUILD
                  </Button>
                }
              />
            )
          )}
          {activeTab === 'dependencies' && (
            dependencies ? <DependencyReasoningPanel data={dependencies} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">No dependency analysis available.</p>
            )
          )}
          {activeTab === 'impact' && (
            impact ? <ImpactAnalysisPanel data={impact} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">No impact analysis available.</p>
            )
          )}
          {activeTab === 'evidence' && (
            evidence ? <EvidenceRankingPanel data={evidence} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">No evidence leaderboard available.</p>
            )
          )}
          {activeTab === 'historical' && (
            historical ? <HistoricalReasoningPanel data={historical} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">No historical fix data available.</p>
            )
          )}
          {activeTab === 'telemetry' && (
            metrics ? <ReasoningTimeline metrics={metrics} /> : (
              <p className="text-xs text-dark-500 font-mono text-center py-12">No telemetry metrics available.</p>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default ReasoningPage;
