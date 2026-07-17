import React, { useState } from 'react';
import { Award, ShieldAlert, Sparkles, Database, Search } from 'lucide-react';
import { Card, CardContent } from './ui';

interface EvidenceItem {
  evidence_id: string;
  source: string;
  title: string;
  score: number;
  confidence: number;
  factors: Record<string, number>;
}

interface EvidenceRanking {
  ranked_items: EvidenceItem[];
  total_sources: number;
  top_confidence: number;
}

interface EvidenceRankingPanelProps {
  data: EvidenceRanking;
}

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  dependency_reasoning: <Award className="w-3.5 h-3.5 text-cyan-accent" />,
  repository_analysis: <ShieldAlert className="w-3.5 h-3.5 text-yellow-400" />,
  memory_hotspot: <Database className="w-3.5 h-3.5 text-purple-accent" />,
};

const FactorBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="space-y-0.5">
    <div className="flex justify-between items-center text-[9px] font-mono text-dark-500">
      <span>{label}</span>
      <span>{Math.round(value * 100)}%</span>
    </div>
    <div className="h-1 rounded-full bg-dark-900/40 overflow-hidden">
      <div
        className="h-full rounded-full bg-dark-400 transition-all"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  </div>
);

export const EvidenceRankingPanel: React.FC<EvidenceRankingPanelProps> = ({ data }) => {
  const [query, setQuery] = useState('');

  const filtered = (data.ranked_items ?? []).filter(item =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.source.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Overview statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-border-primary">
          <CardContent className="p-4 flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-cyan-accent" />
            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-dark-400">Canonical Sources</p>
              <p className="text-xl font-bold font-mono text-dark-200">{data.total_sources ?? 0} active</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border-primary">
          <CardContent className="p-4 flex items-center gap-3">
            <Award className="w-5 h-5 text-purple-accent" />
            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-dark-400">Peak Confidence</p>
              <p className="text-xl font-bold font-mono text-purple-accent">{Math.round((data.top_confidence ?? 0) * 100)}%</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter and leaderboard */}
      <Card className="border-border-primary">
        <CardContent className="p-5 space-y-4">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Evidence Leaderboard</h3>
            </div>
            {/* Search Input */}
            <div className="relative w-full md:w-72">
              <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-dark-500" />
              <input
                type="text"
                placeholder="Filter evidence items..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 rounded-xl border border-border-primary/60 bg-dark-950/40 text-xs font-mono text-dark-200 focus:outline-none focus:border-cyan-accent/50 focus:ring-1 focus:ring-cyan-accent/20"
              />
            </div>
          </div>

          <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
            {filtered.map((item, idx) => (
              <div
                key={item.evidence_id}
                className="p-4 rounded-xl border border-border-primary/50 bg-dark-900/20 hover:border-cyan-accent/30 transition-all flex flex-col md:flex-row justify-between gap-4"
              >
                <div className="space-y-2 flex-1 min-w-0">
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-bold font-mono text-cyan-accent/60 mt-0.5 shrink-0">
                      #{idx + 1}
                    </span>
                    <span className="text-xs font-semibold text-dark-100 font-mono truncate max-w-full block">
                      {item.title}
                    </span>
                  </div>
                  {/* Factor breakdown */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 pt-1.5 border-t border-border-primary/20">
                    {Object.entries(item.factors ?? {}).map(([factor, val]) => (
                      <FactorBar key={factor} label={factor.replace(/_/g, ' ')} value={val} />
                    ))}
                  </div>
                </div>

                <div className="flex md:flex-col justify-between items-end shrink-0 gap-2">
                  <div className="flex items-center gap-1.5 bg-dark-950/60 border border-border-primary/60 px-2 py-1 rounded-lg">
                    {SOURCE_ICONS[item.source] ?? <Sparkles className="w-3.5 h-3.5 text-dark-400" />}
                    <span className="text-[9px] font-mono text-dark-300 uppercase tracking-wider">
                      {item.source.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-dark-500">score</span>
                    <span className="text-xs font-bold font-mono text-cyan-accent">
                      {item.score.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="text-xs text-dark-500 font-mono text-center py-12">No evidence items match your filter query.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EvidenceRankingPanel;
