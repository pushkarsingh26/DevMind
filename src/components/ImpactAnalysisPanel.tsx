import React from 'react';
import { ShieldAlert, FileText, LayoutGrid, CheckSquare } from 'lucide-react';
import { Card, CardContent } from './ui';

interface ImpactReasoning {
  direct_impact: string[];
  indirect_impact: string[];
  repository_wide_impact: boolean;
  breaking_change_probability: number;
  refactor_impact_score: number;
  test_impact: string[];
  documentation_impact: string[];
}

interface ImpactAnalysisPanelProps {
  data: ImpactReasoning;
}

const ProgressBar: React.FC<{ label: string; value: number; color?: string }> = ({
  label, value, color = 'bg-cyan-accent',
}) => {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-xs font-mono">
        <span className="text-dark-400 uppercase tracking-widest">{label}</span>
        <span className="font-bold text-dark-200">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-dark-900/60 overflow-hidden border border-border-primary/30">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export const ImpactAnalysisPanel: React.FC<ImpactAnalysisPanelProps> = ({ data }) => {
  const allAffected = [...data.direct_impact, ...data.indirect_impact];

  return (
    <div className="space-y-6">
      {/* Alert banner if repository-wide impact */}
      {data.repository_wide_impact && (
        <div className="flex items-center gap-3 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400">
          <ShieldAlert className="w-5 h-5 shrink-0" />
          <div className="text-xs font-mono">
            <span className="font-extrabold uppercase tracking-widest">REPOSITORY-WIDE IMPACT DETECTED:</span>
            <p className="text-red-300 mt-1">Changes are projected to affect over 20% of modules. Exercise caution before merging.</p>
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Probability Gauges</h3>
            </div>
            <div className="space-y-4">
              <ProgressBar
                label="Breaking Change Probability"
                value={data.breaking_change_probability}
                color={data.breaking_change_probability > 0.7 ? 'bg-red-500 shadow-[0_0_8px_#ef4444]' : 'bg-cyan-accent'}
              />
              <ProgressBar
                label="Refactor Complexity Impact"
                value={data.refactor_impact_score}
                color={data.refactor_impact_score > 0.6 ? 'bg-purple-accent shadow-[0_0_8px_#a78bfa]' : 'bg-purple-accent/60'}
              />
            </div>
          </CardContent>
        </Card>

        {/* Heatmap summary */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <LayoutGrid className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Impact Heatmap</h3>
            </div>
            {allAffected.length > 0 ? (
              <div className="grid grid-cols-8 gap-1.5 p-2 rounded-lg bg-dark-950/40 border border-border-primary/40">
                {allAffected.slice(0, 48).map((file) => {
                  const isDirect = data.direct_impact.includes(file);
                  const color = isDirect ? 'bg-red-500/80 border-red-500' : 'bg-cyan-accent/60 border-cyan-accent/80';
                  return (
                    <div
                      key={file}
                      title={`${file} (${isDirect ? 'Direct' : 'Indirect'} Impact)`}
                      className={`aspect-square rounded border transition-all hover:scale-110 cursor-pointer ${color}`}
                    />
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-dark-500 font-mono text-center py-6">No files impacted.</p>
            )}
            <div className="flex gap-4 justify-center text-[9px] font-mono text-dark-500">
              <div className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded bg-red-500/80 border border-red-500" />
                <span>Direct ({data.direct_impact?.length ?? 0})</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded bg-cyan-accent/60 border border-cyan-accent/80" />
                <span>Indirect ({data.indirect_impact?.length ?? 0})</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Impact Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Test impact */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Test Impact</h3>
              <span className="ml-auto text-[10px] font-mono text-dark-500">{data.test_impact?.length ?? 0} files</span>
            </div>
            <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
              {(data.test_impact ?? []).map(f => (
                <div key={f} className="flex justify-between items-center p-2 rounded-lg bg-dark-900/30 border border-border-primary/50 text-xs font-mono text-dark-300">
                  <span className="truncate mr-2">{f}</span>
                  <span className="text-[9px] text-cyan-accent bg-cyan-accent/10 px-1.5 py-0.5 rounded border border-cyan-accent/20 uppercase tracking-widest">
                    Test
                  </span>
                </div>
              ))}
              {!data.test_impact?.length && (
                <p className="text-xs text-dark-500 font-mono text-center py-8">No test files impacted.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Documentation impact */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Doc Impact</h3>
              <span className="ml-auto text-[10px] font-mono text-dark-500">{data.documentation_impact?.length ?? 0} files</span>
            </div>
            <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
              {(data.documentation_impact ?? []).map(f => (
                <div key={f} className="flex justify-between items-center p-2 rounded-lg bg-dark-900/30 border border-border-primary/50 text-xs font-mono text-dark-300">
                  <span className="truncate mr-2">{f}</span>
                  <span className="text-[9px] text-purple-accent bg-purple-accent/10 px-1.5 py-0.5 rounded border border-purple-accent/20 uppercase tracking-widest">
                    Doc
                  </span>
                </div>
              ))}
              {!data.documentation_impact?.length && (
                <p className="text-xs text-dark-500 font-mono text-center py-8">No documentation files impacted.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ImpactAnalysisPanel;
