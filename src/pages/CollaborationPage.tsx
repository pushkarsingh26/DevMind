import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Network, ArrowLeft, RefreshCw, FileText, Shield, GitMerge, Award, Activity } from 'lucide-react';
import { useWorkflow } from '../context/WorkflowContext';
import { CollaborationPanel } from '../components/CollaborationPanel';
import { EvidencePanel } from '../components/EvidencePanel';
import { ConflictsPanel } from '../components/ConflictsPanel';
import { ConsensusPanel } from '../components/ConsensusPanel';
import { EmptyState, Button, Card, CardContent } from '../components/ui';

type TabId = 'workspace' | 'findings' | 'evidence' | 'reviews' | 'conflicts' | 'consensus';

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'workspace', label: 'Workspace', icon: Activity },
  { id: 'findings', label: 'Findings', icon: FileText },
  { id: 'evidence', label: 'Evidence', icon: Shield },
  { id: 'reviews', label: 'Reviews', icon: FileText },
  { id: 'conflicts', label: 'Conflicts', icon: GitMerge },
  { id: 'consensus', label: 'Consensus', icon: Award },
];

const backendUrl = () => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const CollaborationPage: React.FC = () => {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();
  const { workflows } = useWorkflow();

  const [activeTab, setActiveTab] = useState<TabId>('workspace');
  const [loading, setLoading] = useState(true);
  const [findings, setFindings] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [consensus, setConsensus] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);

  const liveCollab = workflowId && workflowId !== 'active'
    ? workflows[workflowId]?.collaboration
    : undefined;

  const fetchTabData = useCallback(async (tab: TabId) => {
    if (!workflowId || workflowId === 'active') return;
    setLoading(true);
    try {
      const base = `${backendUrl()}/api/collaboration/${workflowId}`;
      if (tab === 'workspace') {
        const [evRes, healthRes] = await Promise.all([
          axios.get(`${base}/events`),
          axios.get(`${base}/health`),
        ]);
        setEvents(evRes.data);
        setHealth(healthRes.data);
      }
      if (tab === 'findings' || tab === 'workspace') {
        const res = await axios.get(`${base}/findings`);
        setFindings(res.data);
      }
      if (tab === 'evidence') {
        const res = await axios.get(`${base}/evidence`);
        setEvidence(res.data);
      }
      if (tab === 'reviews') {
        const res = await axios.get(`${base}/reviews`);
        setReviews(res.data);
      }
      if (tab === 'conflicts') {
        const res = await axios.get(`${base}/conflicts`);
        setConflicts(res.data);
      }
      if (tab === 'consensus') {
        try {
          const res = await axios.get(`${base}/consensus`);
          setConsensus(res.data);
        } catch {
          setConsensus(null);
        }
      }
    } catch (err) {
      console.error('[CollaborationPage] fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchTabData(activeTab);
  }, [activeTab, fetchTabData]);

  useEffect(() => {
    fetchTabData('workspace');
  }, [workflowId, fetchTabData]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    fetchTabData(tab);
  };

  if (workflowId === 'active' || !workflowId) {
    return (
      <EmptyState
        title="No Workflow Selected"
        description="Select a workflow run to view multi-agent collaboration data."
        icon={<Network className="w-8 h-8 text-cyan-accent animate-pulse" />}
        action={
          <Button variant="primary" glow onClick={() => navigate('/history')}>
            VIEW WORKFLOW HISTORY
          </Button>
        }
      />
    );
  }

  const counters = liveCollab || {
    findings_count: findings.length,
    validated_count: findings.filter(f => f.status === 'validated').length,
    conflicts_count: conflicts.filter(c => c.resolution === 'pending').length,
    confidence: consensus?.overall_confidence ?? 0,
  };

  return (
    <div className="space-y-6 text-left">
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
            <Network className="w-6 h-6 text-cyan-accent" />
            <span>Multi-Agent Collaboration</span>
          </h1>
          <p className="text-xs text-dark-400 font-mono">
            Workflow: <span className="text-cyan-accent">{workflowId}</span>
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            { label: 'Findings', value: counters.findings_count },
            { label: 'Validated', value: counters.validated_count },
            { label: 'Conflicts', value: counters.conflicts_count },
            { label: 'Confidence', value: `${Math.round((counters.confidence ?? 0) * 100)}%` },
          ].map(c => (
            <div key={c.label} className="px-3 py-2 rounded-xl border border-border-primary bg-dark-900/40 text-center min-w-[80px]">
              <div className="text-lg font-bold font-mono text-cyan-accent">{c.value}</div>
              <div className="text-[9px] uppercase tracking-widest text-dark-500">{c.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-border-primary pb-3">
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
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
          onClick={() => fetchTabData(activeTab)}
          className="ml-auto flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-mono text-dark-400 hover:text-cyan-accent cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Tab content */}
      {loading && activeTab !== 'workspace' ? (
        <p className="text-xs text-dark-500 font-mono text-center py-12">Loading...</p>
      ) : (
        <>
          {activeTab === 'workspace' && (
            <CollaborationPanel events={events} findings={findings} />
          )}
          {activeTab === 'findings' && (
            <div className="space-y-2">
              {findings.map(f => (
                <Card key={f.finding_id} className="border-border-primary">
                  <CardContent className="p-4 flex items-start gap-3">
                    <span className="px-2 py-0.5 rounded text-[9px] font-mono uppercase bg-purple-accent/10 text-purple-accent">{f.severity}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-dark-100 font-medium">{f.title}</div>
                      <div className="text-[11px] text-dark-400 font-mono mt-1">{f.description}</div>
                      <div className="text-[10px] text-dark-500 font-mono mt-1">{f.agent_name} · {f.file_path}</div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase ${
                      f.status === 'validated' ? 'bg-green-500/20 text-green-400'
                        : f.status === 'rejected' ? 'bg-red-500/20 text-red-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}>{f.status}</span>
                  </CardContent>
                </Card>
              ))}
              {findings.length === 0 && (
                <p className="text-xs text-dark-500 font-mono text-center py-12">No findings yet.</p>
              )}
            </div>
          )}
          {activeTab === 'evidence' && (
            <EvidencePanel evidence={evidence} findings={findings.map(f => ({ finding_id: f.finding_id, title: f.title }))} />
          )}
          {activeTab === 'reviews' && (
            <div className="space-y-2">
              {reviews.map(r => (
                <Card key={r.review_id} className="border-border-primary">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-dark-200 font-mono">{r.reviewer_agent}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase ${
                        r.decision === 'approved' ? 'bg-green-500/20 text-green-400'
                          : r.decision === 'rejected' ? 'bg-red-500/20 text-red-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}>{r.decision}</span>
                    </div>
                    <p className="text-[11px] text-dark-400 font-mono mt-2">{r.reason}</p>
                    <p className="text-[10px] text-dark-500 font-mono mt-1">finding: {r.finding_id} · confidence: {(r.confidence * 100).toFixed(0)}%</p>
                  </CardContent>
                </Card>
              ))}
              {reviews.length === 0 && (
                <p className="text-xs text-dark-500 font-mono text-center py-12">No reviews yet.</p>
              )}
            </div>
          )}
          {activeTab === 'conflicts' && (
            <ConflictsPanel conflicts={conflicts} findings={findings} />
          )}
          {activeTab === 'consensus' && (
            <ConsensusPanel consensus={consensus} findings={findings} />
          )}
        </>
      )}

      {health && activeTab === 'workspace' && (
        <div className="text-[10px] text-dark-500 font-mono text-center">
          Evidence coverage: {Math.round((health.evidence_coverage ?? 0) * 100)}% · Version: {health.collaboration_version}
        </div>
      )}
    </div>
  );
};

export default CollaborationPage;
