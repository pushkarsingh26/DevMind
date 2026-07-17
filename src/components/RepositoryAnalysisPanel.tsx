import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BarChart3, RefreshCw, AlertTriangle, ShieldAlert, Cpu, 
  GitFork, Eye, Code, ArrowRight, CheckCircle2, FileWarning
} from 'lucide-react';
import { Card, CardHeader, CardContent, Badge, Button, Progress, Spinner } from './ui';

interface RepositoryAnalysisPanelProps {
  repositoryId: string;
}

export const RepositoryAnalysisPanel: React.FC<RepositoryAnalysisPanelProps> = ({ repositoryId }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'dependencies' | 'dead_code' | 'hotspots'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [summary, setSummary] = useState<any>(null);
  const [deadCode, setDeadCode] = useState<any>(null);
  const [hotspots, setHotspots] = useState<any>(null);
  const [architecture, setArchitecture] = useState<any>(null);

  // Dependency Explorer states
  const [depSource, setDepSource] = useState('');
  const [depTarget, setDepTarget] = useState('');
  const [depPath, setDepPath] = useState<string[]>([]);
  const [depLoading, setDepLoading] = useState(false);
  const [depError, setDepError] = useState<string | null>(null);

  // Fetch analysis data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      const [summaryRes, deadRes, hotRes, archRes] = await Promise.all([
        axios.get(`${backendUrl}/api/analysis/${repositoryId}/summary`),
        axios.get(`${backendUrl}/api/analysis/${repositoryId}/dead-code`),
        axios.get(`${backendUrl}/api/analysis/${repositoryId}/hotspots`),
        axios.get(`${backendUrl}/api/analysis/${repositoryId}/architecture`)
      ]);

      setSummary(summaryRes.data);
      setDeadCode(deadRes.data);
      setHotspots(hotRes.data);
      setArchitecture(archRes.data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch repository analysis data.');
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    if (repositoryId) {
      fetchData();
    }
  }, [repositoryId, fetchData]);

  // Query dependency chain path
  const handleTraceDependencies = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!depSource || !depTarget) return;

    setDepLoading(true);
    setDepError(null);
    setDepPath([]);
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await axios.get(`${backendUrl}/api/analysis/${repositoryId}/dependencies`, {
        params: { source: depSource, target: depTarget }
      });
      if (res.data.path && res.data.path.length > 0) {
        setDepPath(res.data.path);
      } else {
        setDepError('No dependency path found between the selected nodes.');
      }
    } catch (err: any) {
      setDepError(err.response?.data?.detail || 'Trace execution failed.');
    } finally {
      setDepLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-4 font-mono text-cyan-accent">
        <Spinner size="lg" />
        <span className="text-xs uppercase tracking-widest">Running Repository Architecture Analysis...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="soft" className="border-red-500/20 bg-red-950/10 p-6 flex flex-col items-center justify-center text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-red-accent" />
        <div className="space-y-1">
          <h3 className="text-base font-bold text-dark-100 font-display">Analysis Engine Failed</h3>
          <p className="text-xs text-dark-400 max-w-lg leading-relaxed">{error}</p>
        </div>
        <Button variant="glass" onClick={fetchData} className="flex items-center gap-2">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>RETRY ANALYSIS</span>
        </Button>
      </Card>
    );
  }

  const issues = architecture?.issues || [];
  const healthColor = summary?.health_score > 80 ? 'text-emerald-400' : summary?.health_score > 50 ? 'text-amber-400' : 'text-red-400';

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card variant="soft" className="p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-dark-500 font-mono font-bold uppercase tracking-wider">Health Grade</span>
            <div className={`text-3xl font-extrabold font-display ${healthColor}`}>
              {summary?.health_score}%
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-accent/10 border border-purple-accent/20 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-purple-accent" />
          </div>
        </Card>

        <Card variant="soft" className="p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-dark-500 font-mono font-bold uppercase tracking-wider">Active Issues</span>
            <div className="text-3xl font-extrabold font-display text-amber-accent">
              {summary?.issues_count || 0}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-accent/10 border border-amber-accent/20 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-amber-accent" />
          </div>
        </Card>

        <Card variant="soft" className="p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-dark-500 font-mono font-bold uppercase tracking-wider">Graph Nodes</span>
            <div className="text-3xl font-extrabold font-display text-cyan-accent">
              {summary?.total_nodes || 0}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-cyan-accent/10 border border-cyan-accent/20 flex items-center justify-center">
            <GitFork className="w-5 h-5 text-cyan-accent" />
          </div>
        </Card>

        <Card variant="soft" className="p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-dark-500 font-mono font-bold uppercase tracking-wider">Dead Code Count</span>
            <div className="text-3xl font-extrabold font-display text-rose-400">
              {deadCode?.summary_count || 0}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <FileWarning className="w-5 h-5 text-rose-400" />
          </div>
        </Card>
      </div>

      {/* 2. Navigation Tabs */}
      <div className="flex bg-[#070b14]/35 p-1 rounded-xl border border-border-primary print:hidden">
        {(['overview', 'dependencies', 'dead_code', 'hotspots'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 text-center text-xs font-mono rounded-lg transition-all cursor-pointer capitalize
              ${activeTab === tab 
                ? 'bg-dark-900 border border-border-primary text-cyan-accent font-semibold shadow-sm' 
                : 'text-dark-400 hover:text-dark-200'
              }`}
          >
            {tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* 3. Dynamic Tab Content Panel */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.18 }}
        >
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Architecture issues listing */}
              <Card variant="soft" className="lg:col-span-2 space-y-4">
                <CardHeader>
                  <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-purple-accent" />
                    <span>Identified Structural Smells</span>
                  </h3>
                </CardHeader>
                <CardContent className="space-y-3.5 max-h-[420px] overflow-y-auto pr-1">
                  {issues.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-8 text-center text-dark-500 space-y-2 font-mono text-xs">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                      <span>Zero architectural issues identified. Solid codebase structures.</span>
                    </div>
                  ) : (
                    issues.map((issue: any) => (
                      <div key={issue.id} className="p-4 rounded-xl border border-border-primary bg-dark-900/30 flex items-start justify-between gap-3">
                        <div className="space-y-1.5 text-xs">
                          <div className="flex items-center gap-2">
                            <Badge variant={issue.severity === 'high' ? 'danger' : 'warning'}>
                              {issue.severity.toUpperCase()}
                            </Badge>
                            <span className="font-mono text-[10px] text-dark-500 uppercase">{issue.type.replace('_', ' ')}</span>
                          </div>
                          <p className="text-dark-200 leading-relaxed font-mono font-medium">{issue.message}</p>
                          {issue.affected_files && issue.affected_files.length > 0 && (
                            <div className="text-[10px] text-dark-400 font-mono flex flex-wrap gap-1 items-center mt-1">
                              <span className="text-dark-500">Files:</span>
                              {issue.affected_files.map((f: string) => (
                                <span key={f} className="bg-dark-900 px-1.5 py-0.5 rounded border border-border-primary">{f}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Health overview card */}
              <Card variant="soft" className="space-y-4">
                <CardHeader>
                  <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-cyan-accent" />
                    <span>Engine Health Overview</span>
                  </h3>
                </CardHeader>
                <CardContent className="space-y-5 text-xs font-mono text-dark-300">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Health Grade Value</span>
                      <span className={`font-bold ${healthColor}`}>{summary?.health_score}%</span>
                    </div>
                    <Progress value={summary?.health_score || 0} color="primary" />
                  </div>
                  
                  <div className="border-t border-border-primary pt-4 space-y-3 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-dark-500 font-bold">CIRCULAR IMPORTS:</span>
                      <span className="text-dark-200 font-bold">{issues.filter((i: any) => i.type === 'circular_dependency').length} detected</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-dark-500 font-bold">COMPLEX FILE HOTSPOTS:</span>
                      <span className="text-dark-200 font-bold">{issues.filter((i: any) => i.type === 'large_module').length} files</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-dark-500 font-bold">LAST ANALYZED TIME:</span>
                      <span className="text-dark-200 truncate max-w-[140px]" title={summary?.analysis_date}>
                        {summary?.analysis_date ? new Date(summary.analysis_date).toLocaleDateString() : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-dark-500 font-bold">ANALYSIS LATENCY:</span>
                      <span className="text-cyan-accent font-bold">{summary?.build_time_ms || 0} ms</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {activeTab === 'dependencies' && (
            <Card variant="soft" className="space-y-5">
              <CardHeader>
                <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-cyan-accent" />
                  <span>Interactive Dependency Path Explorer</span>
                </h3>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Form Inputs */}
                <form onSubmit={handleTraceDependencies} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-bold text-dark-400">Source Node ID</label>
                    <input
                      type="text"
                      placeholder="e.g. module:app/main.py"
                      value={depSource}
                      onChange={(e) => setDepSource(e.target.value)}
                      className="w-full bg-[#070b14]/40 border border-border-primary rounded-xl px-4 py-2 text-xs font-mono text-cyan-accent focus:outline-none focus:border-cyan-500/60"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-bold text-dark-400">Target Node ID</label>
                    <input
                      type="text"
                      placeholder="e.g. module:app/core/config.py"
                      value={depTarget}
                      onChange={(e) => setDepTarget(e.target.value)}
                      className="w-full bg-[#070b14]/40 border border-border-primary rounded-xl px-4 py-2 text-xs font-mono text-cyan-accent focus:outline-none focus:border-cyan-500/60"
                      required
                    />
                  </div>
                  <Button type="submit" variant="primary" glow loading={depLoading} className="w-full py-2.5">
                    TRACE PATH
                  </Button>
                </form>

                {/* Results Path Trace */}
                {depError && (
                  <div className="p-4 rounded-xl border border-red-500/20 bg-red-950/10 text-xs font-mono text-red-300">
                    {depError}
                  </div>
                )}

                {depPath.length > 0 && (
                  <div className="p-5 rounded-2xl border border-border-primary bg-dark-900/30 space-y-4">
                    <h4 className="text-xs font-bold font-mono text-dark-300 uppercase tracking-wider">Shortest Traced Path ({depPath.length - 1} hops)</h4>
                    <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
                      {depPath.map((node, index) => (
                        <React.Fragment key={node}>
                          {index > 0 && <ArrowRight className="w-3.5 h-3.5 text-cyan-accent" />}
                          <span className="bg-dark-950 border border-border-primary px-3 py-1.5 rounded-xl text-dark-100 font-medium">
                            {node}
                          </span>
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'dead_code' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Unused symbols */}
              <Card variant="soft" className="space-y-4">
                <CardHeader>
                  <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
                    <Code className="w-4 h-4 text-purple-accent" />
                    <span>Unused Symbol Declarations</span>
                  </h3>
                </CardHeader>
                <CardContent className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                  {deadCode?.unused_symbols?.length === 0 ? (
                    <div className="p-8 text-center text-dark-500 font-mono text-xs">
                      No unused symbols detected.
                    </div>
                  ) : (
                    deadCode?.unused_symbols?.map((sym: any, idx: number) => (
                      <div key={idx} className="p-3 rounded-xl border border-border-primary bg-dark-900/20 flex items-center justify-between text-xs font-mono">
                        <span className="text-dark-100 font-bold">{sym.name}</span>
                        <span className="text-dark-500 text-[10px] truncate max-w-[180px]">{sym.file}</span>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Unused modules */}
              <Card variant="soft" className="space-y-4">
                <CardHeader>
                  <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
                    <Eye className="w-4 h-4 text-cyan-accent" />
                    <span>Unimported Module/Files</span>
                  </h3>
                </CardHeader>
                <CardContent className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                  {deadCode?.unused_modules?.length === 0 ? (
                    <div className="p-8 text-center text-dark-500 font-mono text-xs">
                      No orphaned modules detected.
                    </div>
                  ) : (
                    deadCode?.unused_modules?.map((mod: string, idx: number) => (
                      <div key={idx} className="p-3 rounded-xl border border-border-primary bg-dark-900/20 text-xs font-mono text-dark-200 truncate" title={mod}>
                        {mod}
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {activeTab === 'hotspots' && (
            <Card variant="soft" className="space-y-4">
              <CardHeader>
                <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-cyan-accent" />
                  <span>High-Coupling Hotspots Ranking</span>
                </h3>
              </CardHeader>
              <CardContent className="overflow-x-auto pr-1">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border-primary text-dark-500 font-bold uppercase text-[10px]">
                      <th className="py-3 px-4">Node Name</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">File Path</th>
                      <th className="py-3 px-4 text-right">Coupling Degree</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hotspots?.hotspots?.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-dark-500">No hotspot nodes identified.</td>
                      </tr>
                    ) : (
                      hotspots?.hotspots?.map((hs: any, idx: number) => (
                        <tr key={idx} className="border-b border-border-primary/50 hover:bg-dark-900/20 transition-all">
                          <td className="py-3 px-4 font-bold text-cyan-accent">{hs.name}</td>
                          <td className="py-3 px-4 text-dark-400 capitalize">{hs.type.toLowerCase()}</td>
                          <td className="py-3 px-4 text-dark-400 truncate max-w-[200px]" title={hs.file}>{hs.file || 'N/A'}</td>
                          <td className="py-3 px-4 text-right font-bold text-dark-100">
                            {hs.coupling_degree} (In: {hs.in_degree}, Out: {hs.out_degree})
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
