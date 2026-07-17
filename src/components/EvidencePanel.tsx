import React from 'react';
import { FileCode, Hash, GitBranch, Layers, User, Gauge } from 'lucide-react';
import { Card, CardContent } from './ui';

interface EvidenceRecord {
  evidence_id: string;
  finding_id: string;
  file_path: string;
  symbol: string;
  graph_node_id: string;
  chunk_id: string;
  workflow_step_id: string;
  source_agent: string;
  quality_score: number;
}

interface EvidencePanelProps {
  evidence: EvidenceRecord[];
  findings?: { finding_id: string; title: string }[];
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ evidence, findings = [] }) => {
  const findingMap = Object.fromEntries(findings.map(f => [f.finding_id, f.title]));

  const grouped = evidence.reduce<Record<string, EvidenceRecord[]>>((acc, ev) => {
    const key = ev.finding_id;
    if (!acc[key]) acc[key] = [];
    acc[key].push(ev);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([findingId, records]) => (
        <Card key={findingId} className="border-border-primary">
          <CardContent className="p-4 space-y-3">
            <h3 className="text-xs font-mono text-cyan-accent truncate">
              {findingMap[findingId] || findingId}
            </h3>
            {records.map(ev => (
              <div key={ev.evidence_id} className="p-3 rounded-xl border border-border-primary/60 bg-dark-900/30 space-y-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono">
                  <div className="flex items-center gap-2 text-dark-300">
                    <FileCode className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                    <span className="truncate">{ev.file_path || '—'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-dark-300">
                    <Hash className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                    <span>{ev.symbol || '—'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-dark-400">
                    <GitBranch className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                    <span className="truncate">{ev.graph_node_id || '—'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-dark-400">
                    <Layers className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                    <span>{ev.workflow_step_id}</span>
                  </div>
                  <div className="flex items-center gap-2 text-dark-400">
                    <User className="w-3.5 h-3.5 text-dark-500 shrink-0" />
                    <span>{ev.source_agent}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Gauge className="w-3.5 h-3.5 text-cyan-accent shrink-0" />
                  <div className="flex-1 h-2 bg-dark-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-accent/60 to-cyan-accent rounded-full transition-all"
                      style={{ width: `${Math.round(ev.quality_score * 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-cyan-accent w-10 text-right">
                    {Math.round(ev.quality_score * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
      {evidence.length === 0 && (
        <p className="text-xs text-dark-500 font-mono text-center py-12">No evidence records yet.</p>
      )}
    </div>
  );
};

export default EvidencePanel;
