import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  GitBranch, Network, Activity, Heart, Clock, CheckCircle2,
  Database, RefreshCw, AlertTriangle
} from 'lucide-react';
import { KnowledgeGraphPanel } from '../components/KnowledgeGraphPanel';
import { useAnalysisData } from '../context/AnalysisContext';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GraphHealth {
  repository_id: string;
  status: 'healthy' | 'degraded';
  details: string[];
  node_count: number;
  edge_count: number;
  isolated_nodes: number;
  connected_components: number;
}

interface GraphStats {
  node_count: number;
  edge_count: number;
  average_degree: number;
  connected_components: number;
  isolated_nodes: number;
  build_time_ms: number;
  traversal_time_ms: number;
  cache_hits: number;
  cache_misses: number;
}

const API_BASE = (import.meta as unknown as Record<string, unknown> & { env?: Record<string, string> }).env?.VITE_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const MetricCard: React.FC<{
  label: string;
  value: string | number;
  sub: string;
  icon: React.ReactNode;
  color?: string;
}> = ({ label, value, sub, icon, color = 'text-cyan-400' }) => (
  <div className="bg-[#070b14]/50 border border-dark-850 hover:border-dark-800 rounded-xl p-4 shadow-lg flex flex-col justify-between transition-all duration-200">
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-mono font-bold text-dark-500 uppercase tracking-wider">{label}</span>
      <span className={color}>{icon}</span>
    </div>
    <div className="mt-3">
      <p className="text-base font-bold text-dark-100 font-mono">{value}</p>
      <p className="text-[9px] font-mono text-dark-500 mt-1 leading-none truncate">{sub}</p>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export const KnowledgeGraphPage: React.FC = () => {
  const { parsedReport } = useAnalysisData();

  // Lazily derive repo id
  const repositoryId = parsedReport?.repository?.id ?? null;

  const [health, setHealth] = useState<GraphHealth | null>(null);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchDetails = useCallback(async (repoId: string) => {
    setLoading(true);
    try {
      const [h, s] = await Promise.all([
        apiFetch<GraphHealth>(`/api/graph/${repoId}/health`),
        apiFetch<GraphStats>(`/api/graph/${repoId}/statistics`),
      ]);
      setHealth(h);
      setStats(s);
    } catch (e) {
      console.warn('Failed to load extra graph stats:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (repositoryId) {
      fetchDetails(repositoryId);
    } else {
      setHealth(null);
      setStats(null);
    }
  }, [repositoryId, fetchDetails]);

  return (
    <motion.div
      id="knowledge-graph-page"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="min-h-screen p-6 space-y-6"
    >
      {/* ── Page header ── */}
      <div className="flex items-center gap-3 border-b border-dark-850 pb-4">
        <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
          <GitBranch className="w-4.5 h-4.5 text-cyan-400" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-dark-100 font-display">Knowledge Graph</h1>
          <p className="text-xs text-dark-500 font-mono mt-0.5">
            Stabilized developer dashboard for intelligence health, cache status, and diagnostics.
          </p>
        </div>

        {repositoryId && (
          <button
            onClick={() => fetchDetails(repositoryId)}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 border border-dark-800 hover:border-dark-700 bg-dark-900/40 text-dark-300 hover:text-dark-100 rounded-lg text-[10px] font-mono transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Reload Diagnostics</span>
          </button>
        )}
      </div>

      {/* ── No analysis yet ── */}
      {!repositoryId ? (
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 text-center">
          <div className="w-16 h-16 rounded-2xl bg-[#070b14] border border-dark-800 flex items-center justify-center">
            <Network className="w-8 h-8 text-dark-700" />
          </div>
          <div>
            <h2 className="text-base font-bold text-dark-300 font-display">No Repository Analysed</h2>
            <p className="text-xs text-dark-600 font-mono mt-1">
              Run an analysis from the Dashboard to build the knowledge graph.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* ── Health & Diagnostics Banner ── */}
          {health && (
            <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              health.status === 'healthy'
                ? 'bg-emerald-950/10 border-emerald-500/20 text-emerald-400'
                : 'bg-amber-950/10 border-amber-500/20 text-amber-400'
            }`}>
              <div className="flex items-start gap-3">
                {health.status === 'healthy' ? (
                  <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                )}
                <div>
                  <h3 className="text-xs font-bold font-mono uppercase tracking-wider">
                    Graph Health Status: {health.status.toUpperCase()}
                  </h3>
                  {health.details.length === 0 ? (
                    <p className="text-[10px] font-mono text-dark-400 mt-1">
                      No structural issues found. Graph is clean and validated (0 orphan edges, 0 self loops).
                    </p>
                  ) : (
                    <ul className="text-[10px] font-mono text-dark-400 list-disc list-inside mt-1 space-y-0.5">
                      {health.details.map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  )}
                </div>
              </div>
              <div className="text-[9px] font-mono text-dark-500 text-right shrink-0">
                Connected components: {health.connected_components} · Isolated nodes: {health.isolated_nodes}
              </div>
            </div>
          )}

          {/* ── Advanced Stats Grid ── */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <MetricCard
                label="Average Degree"
                value={stats.average_degree.toFixed(2)}
                sub="Mean edges per node"
                icon={<Activity className="w-4 h-4" />}
                color="text-cyan-400"
              />
              <MetricCard
                label="Components"
                value={stats.connected_components}
                sub="Separated subgraphs"
                icon={<Network className="w-4 h-4" />}
                color="text-purple-400"
              />
              <MetricCard
                label="Isolated Nodes"
                value={stats.isolated_nodes}
                sub="0 connected edges"
                icon={<Heart className="w-4 h-4" />}
                color="text-rose-400"
              />
              <MetricCard
                label="Build Time"
                value={`${stats.build_time_ms} ms`}
                sub="Parsing overhead"
                icon={<Clock className="w-4 h-4" />}
                color="text-emerald-400"
              />
              <MetricCard
                label="Traversal Time"
                value={`${stats.traversal_time_ms} ms`}
                sub="BFS query latency"
                icon={<Clock className="w-4 h-4" />}
                color="text-blue-400"
              />
              <MetricCard
                label="Cache Hits/Misses"
                value={`${stats.cache_hits} / ${stats.cache_misses}`}
                sub="Memory resolution rate"
                icon={<Database className="w-4 h-4" />}
                color="text-amber-400"
              />
            </div>
          )}

          {/* ── Graph panel (lazy-loaded) ── */}
          <div className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-6 shadow-xl">
            <KnowledgeGraphPanel repositoryId={repositoryId} />
          </div>
        </>
      )}
    </motion.div>
  );
};

export default KnowledgeGraphPage;
