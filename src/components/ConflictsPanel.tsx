import React from 'react';
import { GitMerge, Trophy, AlertTriangle } from 'lucide-react';
import { Card, CardContent } from './ui';

interface ConflictRecord {
  conflict_id: string;
  finding_id_a: string;
  finding_id_b: string;
  conflict_type: string;
  resolution: string;
  winning_finding_id: string;
  resolution_reason: string;
}

interface ConflictsPanelProps {
  conflicts: ConflictRecord[];
  findings?: { finding_id: string; title: string; severity: string; agent_name: string }[];
}

const CONFLICT_LABELS: Record<string, string> = {
  duplicate: 'Duplicate',
  contradiction: 'Contradiction',
  severity_mismatch: 'Severity Mismatch',
  recommendation_mismatch: 'Recommendation Mismatch',
};

export const ConflictsPanel: React.FC<ConflictsPanelProps> = ({ conflicts, findings = [] }) => {
  const findingMap = Object.fromEntries(findings.map(f => [f.finding_id, f]));

  return (
    <div className="space-y-4">
      {conflicts.map(conflict => {
        const fa = findingMap[conflict.finding_id_a];
        const fb = findingMap[conflict.finding_id_b];

        return (
          <Card key={conflict.conflict_id} className="border-border-primary">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <GitMerge className="w-4 h-4 text-yellow-400" />
                  <span className="text-xs font-mono text-dark-300">
                    {CONFLICT_LABELS[conflict.conflict_type] || conflict.conflict_type}
                  </span>
                </div>
                <span className={`px-2.5 py-0.5 rounded text-[9px] font-mono uppercase ${
                  conflict.resolution === 'resolved'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                }`}>
                  {conflict.resolution}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[fa, fb].filter(Boolean).map((f, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border ${
                      f?.finding_id === conflict.winning_finding_id
                        ? 'border-cyan-accent/50 bg-cyan-accent/5'
                        : 'border-border-primary bg-dark-900/30'
                    }`}
                  >
                    {f?.finding_id === conflict.winning_finding_id && (
                      <div className="flex items-center gap-1 mb-1.5">
                        <Trophy className="w-3 h-3 text-cyan-accent" />
                        <span className="text-[9px] font-mono uppercase text-cyan-accent">Winner</span>
                      </div>
                    )}
                    <div className="text-xs text-dark-200 font-medium truncate">{f?.title || 'Unknown'}</div>
                    <div className="text-[10px] text-dark-500 font-mono mt-1">
                      {f?.agent_name} · {f?.severity}
                    </div>
                  </div>
                ))}
              </div>

              {conflict.resolution_reason && (
                <p className="text-[11px] text-dark-400 font-mono flex items-start gap-1.5">
                  <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5 text-dark-500" />
                  {conflict.resolution_reason}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
      {conflicts.length === 0 && (
        <p className="text-xs text-dark-500 font-mono text-center py-12">No conflicts detected.</p>
      )}
    </div>
  );
};

export default ConflictsPanel;
