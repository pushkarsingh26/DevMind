import React from 'react';
import { Users, FileCheck, Clock, Hash, Award } from 'lucide-react';
import { Card, CardContent } from './ui';

interface ConsensusResult {
  consensus_id: string;
  supporting_agents: string[];
  conflicting_agents: string[];
  validated_findings: string[];
  overall_confidence: number;
  evidence_count: number;
  recommendation: string;
  generated_at: string;
  consensus_version: string;
  generated_from_workspace_hash: string;
  generated_duration_ms: number;
  validated_findings_count: number;
}

interface ConsensusPanelProps {
  consensus: ConsensusResult | null;
  findings?: { finding_id: string; title: string; severity: string }[];
}

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export const ConsensusPanel: React.FC<ConsensusPanelProps> = ({ consensus, findings = [] }) => {
  if (!consensus) {
    return (
      <p className="text-xs text-dark-500 font-mono text-center py-12">
        Consensus not yet generated. Run workflow steps to build validated findings.
      </p>
    );
  }

  const confidencePct = Math.round(consensus.overall_confidence * 100);
  const circumference = 2 * Math.PI * 54;
  const strokeDashoffset = circumference - (consensus.overall_confidence * circumference);

  const validatedFindingsList = findings
    .filter(f => consensus.validated_findings.includes(f.finding_id))
    .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3));

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row items-center gap-8">
        {/* Confidence gauge */}
        <div className="relative w-36 h-36 shrink-0">
          <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
            <circle cx="60" cy="60" r="54" fill="none" stroke="currentColor" strokeWidth="8" className="text-dark-800" />
            <circle
              cx="60" cy="60" r="54" fill="none"
              stroke="url(#consensusGrad)" strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-700"
            />
            <defs>
              <linearGradient id="consensusGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="var(--secondary-accent)" />
                <stop offset="100%" stopColor="var(--primary-accent)" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold font-mono text-cyan-accent">{confidencePct}%</span>
            <span className="text-[9px] uppercase tracking-widest text-dark-400">Confidence</span>
          </div>
        </div>

        <div className="flex-1 space-y-3">
          <div className="flex flex-wrap gap-2">
            <span className="px-2.5 py-1 rounded-lg bg-purple-accent/10 text-purple-accent text-[10px] font-mono uppercase border border-purple-accent/20">
              {consensus.consensus_version}
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-cyan-accent/10 text-cyan-accent text-[10px] font-mono border border-cyan-accent/20">
              {consensus.validated_findings_count} validated
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-dark-800 text-dark-300 text-[10px] font-mono flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Generated in {consensus.generated_duration_ms}ms
            </span>
          </div>
          <p className="text-sm text-dark-200">
            Recommendation: <span className="text-cyan-accent font-semibold uppercase">{consensus.recommendation}</span>
          </p>
          <div className="flex items-center gap-2 text-[10px] text-dark-500 font-mono" title={consensus.generated_from_workspace_hash}>
            <Hash className="w-3 h-3" />
            workspace hash: {consensus.generated_from_workspace_hash.slice(0, 12)}…
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card className="border-border-primary">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-green-400" />
              <span className="text-[10px] uppercase tracking-widest text-dark-400">Supporting Agents</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {consensus.supporting_agents.map(a => (
                <span key={a} className="px-2 py-0.5 rounded bg-green-500/10 text-green-400 text-[10px] font-mono">{a}</span>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="border-border-primary">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Award className="w-4 h-4 text-cyan-accent" />
              <span className="text-[10px] uppercase tracking-widest text-dark-400">Evidence Count</span>
            </div>
            <span className="text-2xl font-bold font-mono text-cyan-accent">{consensus.evidence_count}</span>
          </CardContent>
        </Card>
        <Card className="border-border-primary">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileCheck className="w-4 h-4 text-purple-accent" />
              <span className="text-[10px] uppercase tracking-widest text-dark-400">Conflicting Agents</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {consensus.conflicting_agents.length > 0
                ? consensus.conflicting_agents.map(a => (
                    <span key={a} className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 text-[10px] font-mono">{a}</span>
                  ))
                : <span className="text-[10px] text-dark-500 font-mono">None</span>}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-2">
        <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Validated Findings</h3>
        <div className="space-y-2">
          {validatedFindingsList.map(f => (
            <div key={f.finding_id} className="flex items-center gap-2 p-2.5 rounded-xl border border-border-primary bg-dark-900/30">
              <span className="px-2 py-0.5 rounded text-[9px] font-mono uppercase bg-cyan-accent/10 text-cyan-accent">{f.severity}</span>
              <span className="text-xs text-dark-200 truncate">{f.title}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ConsensusPanel;
