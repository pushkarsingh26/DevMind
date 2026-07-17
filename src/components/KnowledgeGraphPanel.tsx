import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GitBranch, Package, FileCode2, Layers, Search, X,
  ChevronRight, ChevronDown, ArrowUpRight, Network,
  AlertCircle, Loader2, Database, Code2, Zap
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GraphNode {
  id: string;
  type: 'file' | 'module' | 'symbol' | 'dependency' | 'entry_point';
  name: string;
  file?: string;
  language?: string;
  line?: number;
  visibility?: string;
  metadata?: Record<string, unknown>;
}

interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  edge_relationships: Record<string, number>;
}

interface GraphStatus {
  repository_id: string;
  cached: boolean;
  statistics: GraphStats;
}

interface KnowledgeGraphPanelProps {
  repositoryId: string | null;
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

const NODE_COLOR: Record<string, string> = {
  file:        'text-blue-400',
  module:      'text-purple-400',
  symbol:      'text-cyan-400',
  dependency:  'text-amber-400',
  entry_point: 'text-emerald-400',
};

const NODE_BG: Record<string, string> = {
  file:        'bg-blue-950/40 border-blue-500/20',
  module:      'bg-purple-950/40 border-purple-500/20',
  symbol:      'bg-cyan-950/40 border-cyan-500/20',
  dependency:  'bg-amber-950/40 border-amber-500/20',
  entry_point: 'bg-emerald-950/40 border-emerald-500/20',
};

const NODE_ICON: Record<string, React.ReactNode> = {
  file:        <FileCode2 className="w-3.5 h-3.5" />,
  module:      <Layers className="w-3.5 h-3.5" />,
  symbol:      <Code2 className="w-3.5 h-3.5" />,
  dependency:  <Package className="w-3.5 h-3.5" />,
  entry_point: <Zap className="w-3.5 h-3.5" />,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatBadge: React.FC<{ label: string; value: number | string; color?: string }> = ({
  label, value, color = 'text-cyan-400',
}) => (
  <div className="flex flex-col items-center gap-0.5 bg-[#070b14]/60 border border-dark-800/60 rounded-xl px-4 py-2.5">
    <span className={`text-lg font-bold font-mono ${color}`}>{value.toLocaleString()}</span>
    <span className="text-[9px] font-mono text-dark-500 uppercase tracking-wider">{label}</span>
  </div>
);

const NodeCard: React.FC<{
  node: GraphNode;
  onClick: (node: GraphNode) => void;
  selected: boolean;
}> = ({ node, onClick, selected }) => (
  <motion.button
    whileHover={{ x: 3 }}
    onClick={() => onClick(node)}
    className={`w-full text-left flex items-start gap-2.5 p-2.5 rounded-lg border transition-all duration-150 ${
      selected
        ? `${NODE_BG[node.type]} ring-1 ring-${node.type === 'symbol' ? 'cyan' : 'blue'}-500/40`
        : 'bg-transparent border-transparent hover:border-dark-800 hover:bg-[#070b14]/40'
    }`}
  >
    <span className={`mt-0.5 shrink-0 ${NODE_COLOR[node.type] ?? 'text-dark-400'}`}>
      {NODE_ICON[node.type]}
    </span>
    <div className="flex-1 min-w-0">
      <p className="text-xs font-bold text-dark-200 truncate font-mono">{node.name}</p>
      {node.file && (
        <p className="text-[9px] text-dark-500 font-mono truncate mt-0.5">{node.file}</p>
      )}
      {!!node.metadata?.symbol_type && (
        <span className="text-[8px] font-mono text-dark-600 bg-dark-850 rounded px-1 mt-0.5 inline-block">
          {String(node.metadata.symbol_type)}
        </span>
      )}
    </div>
    <span className={`text-[8px] font-mono shrink-0 mt-0.5 ${NODE_COLOR[node.type] ?? ''}`}>
      {node.type.toUpperCase()}
    </span>
  </motion.button>
);

const NodeDetail: React.FC<{ node: GraphNode; onClose: () => void }> = ({ node, onClose }) => (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: 8 }}
    className="bg-[#050910]/80 border border-dark-800 rounded-xl p-4 space-y-3"
  >
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={NODE_COLOR[node.type] ?? 'text-dark-400'}>
          {NODE_ICON[node.type]}
        </span>
        <span className="text-sm font-bold text-dark-100 font-mono">{node.name}</span>
      </div>
      <button onClick={onClose} className="text-dark-500 hover:text-dark-200 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>

    <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
      <div>
        <span className="text-dark-500">Type</span>
        <p className={`mt-0.5 font-semibold ${NODE_COLOR[node.type] ?? ''}`}>{node.type}</p>
      </div>
      {node.file && (
        <div>
          <span className="text-dark-500">File</span>
          <p className="mt-0.5 text-dark-300 truncate">{node.file}</p>
        </div>
      )}
      {node.language && (
        <div>
          <span className="text-dark-500">Language</span>
          <p className="mt-0.5 text-dark-300">{node.language}</p>
        </div>
      )}
      {node.visibility && node.visibility !== 'unknown' && (
        <div>
          <span className="text-dark-500">Visibility</span>
          <p className="mt-0.5 text-dark-300">{node.visibility}</p>
        </div>
      )}
      {node.line != null && node.line > 0 && (
        <div>
          <span className="text-dark-500">Line</span>
          <p className="mt-0.5 text-dark-300">{node.line}</p>
        </div>
      )}
    </div>

    {node.metadata && Object.keys(node.metadata).length > 0 && (
      <div className="border-t border-dark-850 pt-2 space-y-1">
        {Object.entries(node.metadata).map(([k, v]) =>
          v != null && v !== '' ? (
            <div key={k} className="flex gap-2 text-[9px] font-mono">
              <span className="text-dark-500 shrink-0">{k}:</span>
              <span className="text-dark-400 truncate">{String(v)}</span>
            </div>
          ) : null,
        )}
      </div>
    )}
  </motion.div>
);

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

type Tab = 'explorer' | 'symbols' | 'dependencies' | 'search';

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'explorer', label: 'Explorer', icon: <Network className="w-3.5 h-3.5" /> },
  { id: 'symbols',  label: 'Symbols',  icon: <Code2 className="w-3.5 h-3.5" /> },
  { id: 'dependencies', label: 'Deps', icon: <Package className="w-3.5 h-3.5" /> },
  { id: 'search',   label: 'Search',   icon: <Search className="w-3.5 h-3.5" /> },
];

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export const KnowledgeGraphPanel: React.FC<KnowledgeGraphPanelProps> = ({
  repositoryId,
  className = '',
}) => {
  const [status, setStatus] = useState<GraphStatus | null>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('explorer');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<GraphNode[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['file', 'symbol']));

  // ------------------------------------------------------------------
  // Lazy load — only when this panel mounts AND repositoryId is set
  // ------------------------------------------------------------------

  const loadGraph = useCallback(async (repoId: string) => {
    setLoading(true);
    setError(null);
    try {
      const st = await apiFetch<GraphStatus>(`/api/graph/${repoId}/status`);
      setStatus(st);
      if (st.cached) {
        const [syms, deps] = await Promise.all([
          apiFetch<GraphNode[]>(`/api/graph/${repoId}/symbols?pattern=.`),
          apiFetch<GraphNode[]>(`/api/graph/${repoId}/dependencies`),
        ]);
        setNodes([...syms, ...deps]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!repositoryId) return;
    // Reset state when repository changes
    setStatus(null);
    setNodes([]);
    setSelectedNode(null);
    setQuery('');
    setSearchResults([]);
    loadGraph(repositoryId);
  }, [repositoryId, loadGraph]);

  // ------------------------------------------------------------------
  // Search (debounced)
  // ------------------------------------------------------------------

  useEffect(() => {
    if (!repositoryId || activeTab !== 'search' || !query.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const results = await apiFetch<GraphNode[]>(`/api/graph/${repositoryId}/search?q=${encodeURIComponent(query)}`);
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, repositoryId, activeTab]);

  // ------------------------------------------------------------------
  // Derived data
  // ------------------------------------------------------------------

  const byType = useMemo<Record<string, GraphNode[]>>(() => {
    const out: Record<string, GraphNode[]> = {};
    for (const n of nodes) {
      (out[n.type] ||= []).push(n);
    }
    return out;
  }, [nodes]);

  const symbols   = byType['symbol'] ?? [];
  const deps      = byType['dependency'] ?? [];

  const toggleType = (t: string) => {
    setExpandedTypes(prev => {
      const next = new Set(prev);
      if (next.has(t)) {
        next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  };

  // ------------------------------------------------------------------
  // Render: no repo
  // ------------------------------------------------------------------

  if (!repositoryId) {
    return (
      <div className={`flex items-center justify-center min-h-[300px] ${className}`}>
        <div className="text-center space-y-2">
          <GitBranch className="w-10 h-10 text-dark-700 mx-auto" />
          <p className="text-sm text-dark-500 font-mono">No repository selected</p>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Render: loading
  // ------------------------------------------------------------------

  if (loading) {
    return (
      <div className={`flex items-center justify-center min-h-[300px] ${className}`}>
        <div className="text-center space-y-3">
          <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-sm text-dark-400 font-mono">Loading knowledge graph…</p>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Render: error
  // ------------------------------------------------------------------

  if (error) {
    return (
      <div className={`flex items-center justify-center min-h-[300px] ${className}`}>
        <div className="text-center space-y-2">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
          <p className="text-sm text-rose-400 font-mono">{error}</p>
          <button
            onClick={() => loadGraph(repositoryId)}
            className="text-xs text-cyan-400 hover:underline font-mono"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Render: graph not built yet
  // ------------------------------------------------------------------

  if (status && !status.cached) {
    return (
      <div className={`flex items-center justify-center min-h-[300px] ${className}`}>
        <div className="text-center space-y-3">
          <Database className="w-10 h-10 text-dark-600 mx-auto" />
          <p className="text-sm text-dark-400 font-mono">Knowledge graph not yet built</p>
          <p className="text-xs text-dark-600 font-mono">
            Run a repository analysis to generate the graph.
          </p>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Render: main panel
  // ------------------------------------------------------------------

  const stats = status?.statistics;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-dark-100 font-display uppercase tracking-wide">
            Knowledge Graph
          </h3>
        </div>
        {stats && (
          <span className="text-[9px] font-mono text-dark-500 bg-dark-900 border border-dark-800 px-2 py-0.5 rounded-lg">
            {stats.total_nodes.toLocaleString()} nodes · {stats.total_edges.toLocaleString()} edges
          </span>
        )}
      </div>

      {/* ── Stat badges ── */}
      {stats && (
        <div className="grid grid-cols-4 gap-2">
          <StatBadge label="Symbols"      value={stats.node_types['symbol'] ?? 0}      color="text-cyan-400" />
          <StatBadge label="Modules"      value={stats.node_types['module'] ?? 0}      color="text-purple-400" />
          <StatBadge label="Files"        value={stats.node_types['file'] ?? 0}        color="text-blue-400" />
          <StatBadge label="Dependencies" value={stats.node_types['dependency'] ?? 0}  color="text-amber-400" />
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="flex gap-1 bg-[#070b14]/60 border border-dark-850 rounded-xl p-1">
        {TABS.map(t => (
          <button
            key={t.id}
            id={`kg-tab-${t.id}`}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1.5 flex-1 justify-center py-1.5 rounded-lg text-[10px] font-mono font-semibold transition-all duration-150 ${
              activeTab === t.id
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'text-dark-500 hover:text-dark-300'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.15 }}
          className="space-y-2"
        >

          {/* ── Explorer tab: grouped by type ── */}
          {activeTab === 'explorer' && (
            <div className="space-y-2">
              {Object.entries(byType).map(([type, typeNodes]) => (
                <div key={type} className="border border-dark-850 rounded-xl overflow-hidden">
                  <button
                    id={`kg-explorer-${type}`}
                    onClick={() => toggleType(type)}
                    className="w-full flex items-center justify-between px-3 py-2 bg-[#070b14]/60 hover:bg-[#070b14]/80 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className={NODE_COLOR[type] ?? 'text-dark-400'}>{NODE_ICON[type]}</span>
                      <span className="text-[10px] font-mono font-bold text-dark-300 uppercase tracking-wider">
                        {type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono text-dark-600">{typeNodes.length}</span>
                      {expandedTypes.has(type)
                        ? <ChevronDown className="w-3.5 h-3.5 text-dark-500" />
                        : <ChevronRight className="w-3.5 h-3.5 text-dark-500" />}
                    </div>
                  </button>

                  <AnimatePresence>
                    {expandedTypes.has(type) && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="p-2 space-y-0.5 max-h-48 overflow-y-auto">
                          {typeNodes.slice(0, 60).map(n => (
                            <NodeCard
                              key={n.id}
                              node={n}
                              onClick={setSelectedNode}
                              selected={selectedNode?.id === n.id}
                            />
                          ))}
                          {typeNodes.length > 60 && (
                            <p className="text-[9px] text-dark-600 font-mono text-center py-1">
                              +{typeNodes.length - 60} more…
                            </p>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          )}

          {/* ── Symbols tab ── */}
          {activeTab === 'symbols' && (
            <div className="space-y-0.5 max-h-80 overflow-y-auto">
              {symbols.length === 0 ? (
                <p className="text-xs text-dark-500 font-mono text-center py-8">No symbols indexed</p>
              ) : symbols.map(n => (
                <NodeCard key={n.id} node={n} onClick={setSelectedNode} selected={selectedNode?.id === n.id} />
              ))}
            </div>
          )}

          {/* ── Dependencies tab ── */}
          {activeTab === 'dependencies' && (
            <div className="space-y-1.5 max-h-80 overflow-y-auto">
              {deps.length === 0 ? (
                <p className="text-xs text-dark-500 font-mono text-center py-8">No dependencies found</p>
              ) : deps.map(d => (
                <div
                  key={d.id}
                  className="flex items-center justify-between px-3 py-2 bg-amber-950/20 border border-amber-500/15 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <Package className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span className="text-xs font-mono font-bold text-dark-200">{d.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[9px] font-mono text-dark-500">
                    {!!d.metadata?.version && <span>{String(d.metadata.version)}</span>}
                    {d.language && <span className="text-amber-600">{d.language}</span>}
                    <ArrowUpRight className="w-3 h-3" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Search tab ── */}
          {activeTab === 'search' && (
            <div className="space-y-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-dark-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  id="kg-search-input"
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search nodes by name…"
                  className="w-full bg-[#070b14]/80 border border-dark-800 rounded-lg pl-8 pr-4 py-2 text-xs font-mono text-dark-200 placeholder-dark-600 focus:outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20 transition-all"
                />
                {searchLoading && (
                  <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin absolute right-3 top-1/2 -translate-y-1/2" />
                )}
              </div>

              <div className="space-y-0.5 max-h-64 overflow-y-auto">
                {searchResults.length === 0 && query.trim() && !searchLoading && (
                  <p className="text-xs text-dark-500 font-mono text-center py-6">No results for "{query}"</p>
                )}
                {searchResults.map(n => (
                  <NodeCard key={n.id} node={n} onClick={setSelectedNode} selected={selectedNode?.id === n.id} />
                ))}
              </div>
            </div>
          )}

        </motion.div>
      </AnimatePresence>

      {/* ── Selected node detail panel ── */}
      <AnimatePresence>
        {selectedNode && (
          <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
      </AnimatePresence>

    </div>
  );
};

export default KnowledgeGraphPanel;
