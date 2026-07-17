import React, { useState } from 'react';
import { GitBranch, ChevronDown, ChevronRight, ExternalLink, Globe, Layers } from 'lucide-react';
import { Card, CardContent } from './ui';

interface ReasoningChain {
  chain_id: string;
  source: string;
  steps: string[];
  depth: number;
  confidence: number;
  reasoning_type: string;
}

interface DependencyReasoning {
  critical_files: string[];
  dependency_chains: ReasoningChain[];
  affected_symbols: string[];
  architecture_influence: Record<string, number>;
  transitive_impact: string[];
  repository_boundaries: string[];
}

interface DependencyReasoningPanelProps {
  data: DependencyReasoning;
}

const ConfidencePill: React.FC<{ value: number }> = ({ value }) => {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? 'text-green-400 bg-green-400/10 border-green-400/30'
    : pct >= 40 ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30'
    : 'text-red-400 bg-red-400/10 border-red-400/30';
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${color}`}>
      {pct}%
    </span>
  );
};

const CollapsibleChain: React.FC<{ chain: ReasoningChain }> = ({ chain }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-border-primary/50 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between p-3 bg-dark-900/30 hover:bg-dark-900/60 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 min-w-0">
          {open ? <ChevronDown className="w-3.5 h-3.5 text-cyan-accent shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-dark-400 shrink-0" />}
          <span className="text-xs font-mono text-dark-200 truncate">{chain.source}</span>
          <span className="text-[10px] font-mono text-dark-500 shrink-0">depth {chain.depth}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span className="text-[10px] font-mono text-dark-500">{chain.steps.length} deps</span>
          <ConfidencePill value={chain.confidence} />
        </div>
      </button>

      {open && chain.steps.length > 0 && (
        <div className="p-3 space-y-1.5 border-t border-border-primary/30 bg-dark-950/30">
          {chain.steps.map((step, i) => (
            <div key={step} className="flex items-center gap-2 pl-3">
              <div className="flex flex-col items-center">
                <div className="w-px h-2 bg-border-primary/50" />
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-accent/40" />
                {i < chain.steps.length - 1 && <div className="w-px h-2 bg-border-primary/50" />}
              </div>
              <span className="text-[11px] font-mono text-dark-300">{step}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const DependencyReasoningPanel: React.FC<DependencyReasoningPanelProps> = ({ data }) => {
  const archEntries = Object.entries(data.architecture_influence ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  return (
    <div className="space-y-6">
      {/* Critical files */}
      <Card className="border-border-primary">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-accent" />
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Critical Files</h3>
            <span className="ml-auto text-[10px] font-mono text-dark-500">{data.critical_files?.length ?? 0} files</span>
          </div>
          <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
            {(data.critical_files ?? []).map((f, i) => (
              <div key={f} className="flex items-center gap-2 p-2 rounded-lg bg-dark-900/30 border border-border-primary/50 group">
                <span className="text-[10px] font-mono text-cyan-accent/50 w-5 shrink-0">#{i + 1}</span>
                <span className="text-xs font-mono text-dark-200 truncate flex-1">{f}</span>
                <ExternalLink className="w-3 h-3 text-dark-600 group-hover:text-cyan-accent transition-colors shrink-0" />
              </div>
            ))}
            {!data.critical_files?.length && (
              <p className="text-xs text-dark-500 font-mono text-center py-6">No critical files identified yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Dependency chains */}
      <Card className="border-border-primary">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-accent" />
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Dependency Chains</h3>
            <span className="ml-auto text-[10px] font-mono text-dark-500">{data.dependency_chains?.length ?? 0} chains</span>
          </div>
          <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
            {(data.dependency_chains ?? []).map(chain => (
              <CollapsibleChain key={chain.chain_id} chain={chain} />
            ))}
            {!data.dependency_chains?.length && (
              <p className="text-xs text-dark-500 font-mono text-center py-6">No dependency chains detected yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Architecture influence */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Architecture Influence</h3>
            </div>
            <div className="space-y-2">
              {archEntries.map(([mod, count]) => (
                <div key={mod} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono text-dark-300 truncate max-w-[180px]">{mod}</span>
                    <span className="text-[10px] font-mono text-cyan-accent shrink-0 ml-2">{count} dependents</span>
                  </div>
                  <div className="h-1 rounded-full bg-dark-900/60 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-cyan-accent/60 transition-all"
                      style={{ width: `${Math.min(100, (count / Math.max(...archEntries.map(e => e[1]), 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
              {!archEntries.length && (
                <p className="text-xs text-dark-500 font-mono text-center py-4">No module influence data available.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Repository boundaries */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Repository Boundaries</h3>
              <span className="ml-auto text-[10px] font-mono text-dark-500">external deps</span>
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-[180px] overflow-y-auto">
              {(data.repository_boundaries ?? []).map(b => (
                <span key={b} className="px-2 py-1 rounded-lg text-[10px] font-mono bg-purple-accent/10 border border-purple-accent/20 text-purple-accent">
                  {b}
                </span>
              ))}
              {!data.repository_boundaries?.length && (
                <p className="text-xs text-dark-500 font-mono text-center py-4 w-full">No external dependencies detected.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DependencyReasoningPanel;
