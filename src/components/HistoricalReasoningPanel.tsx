import React from 'react';
import { History, FileText, CheckCircle2, XCircle, AlertTriangle, Cpu } from 'lucide-react';
import { Card, CardContent } from './ui';

interface HistoricalReasoning {
  similar_workflows: string[];
  historical_failures: string[];
  historical_fixes: string[];
  common_risks: string[];
  success_probability: number;
  provider_history: Record<string, number>;
}

interface HistoricalReasoningPanelProps {
  data: HistoricalReasoning;
}

const ProviderReliabilityBar: React.FC<{ provider: string; reliability: number }> = ({
  provider, reliability,
}) => {
  const pct = Math.round(reliability * 100);
  const color = pct >= 80 ? 'bg-cyan-accent'
    : pct >= 50 ? 'bg-yellow-400'
    : 'bg-red-400';
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-[10px] font-mono text-dark-400">
        <span className="truncate mr-2">{provider}</span>
        <span className="font-bold">{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-dark-900/60 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

export const HistoricalReasoningPanel: React.FC<HistoricalReasoningPanelProps> = ({ data }) => {
  return (
    <div className="space-y-6">
      {/* Overview success metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-border-primary">
          <CardContent className="p-5 flex flex-col items-center justify-center gap-2">
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Historical Success Rate</h3>
            <span className="text-4xl font-extrabold font-mono text-cyan-accent">
              {Math.round((data.success_probability ?? 0.8) * 100)}%
            </span>
            <p className="text-[10px] text-dark-500 font-mono">Based on similar workflow intents</p>
          </CardContent>
        </Card>

        {/* Provider reliability */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Provider Reliability</h3>
            </div>
            <div className="space-y-2">
              {Object.entries(data.provider_history ?? {}).map(([provider, score]) => (
                <ProviderReliabilityBar key={provider} provider={provider} reliability={score} />
              ))}
              {!Object.keys(data.provider_history ?? {}).length && (
                <p className="text-xs text-dark-500 font-mono text-center py-4">No provider usage history available.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workflows checklist */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Similar Workflows</h3>
              <span className="ml-auto text-[10px] font-mono text-dark-500">{data.similar_workflows?.length ?? 0} runs</span>
            </div>
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {(data.similar_workflows ?? []).map(wf => {
                const isFail = data.historical_failures.includes(wf);
                return (
                  <div key={wf} className="flex justify-between items-center p-2.5 rounded-lg bg-dark-900/30 border border-border-primary/50 text-xs font-mono">
                    <span className="text-dark-200">{wf}</span>
                    {isFail ? (
                      <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                        <XCircle className="w-3 h-3" /> Failed
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                        <CheckCircle2 className="w-3 h-3" /> Success
                      </span>
                    )}
                  </div>
                );
              })}
              {!data.similar_workflows?.length && (
                <p className="text-xs text-dark-500 font-mono text-center py-8">No matching intent workflows in history.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Historical Fixes */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Historically Modified Files</h3>
              <span className="ml-auto text-[10px] font-mono text-dark-500">{data.historical_fixes?.length ?? 0} files</span>
            </div>
            <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
              {(data.historical_fixes ?? []).map(fix => (
                <div key={fix} className="p-2 rounded-lg bg-dark-900/30 border border-border-primary/50 text-xs font-mono text-dark-300 truncate">
                  {fix}
                </div>
              ))}
              {!data.historical_fixes?.length && (
                <p className="text-xs text-dark-500 font-mono text-center py-8">No prior files have fixes recorded.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Common risks cloud */}
      {(data.common_risks?.length ?? 0) > 0 && (
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">High-Severity Historical Risks</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.common_risks.map(risk => (
                <span key={risk} className="px-2.5 py-1.5 rounded-lg text-[10px] font-mono border border-yellow-400/20 text-yellow-400 bg-yellow-400/5">
                  {risk}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default HistoricalReasoningPanel;
