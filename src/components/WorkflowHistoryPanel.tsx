import React, { useState } from 'react';
import { Search, Clock, Cpu, CheckCircle2, XCircle, FileText } from 'lucide-react';
import { Card, CardContent, Input } from './ui';

export interface WorkflowMemory {
  workflow_id: string;
  goal: string;
  intent: string;
  execution_plan: Record<string, any>;
  execution_metrics: Record<string, any>;
  collaboration_summary: Record<string, any>;
  findings: any[];
  duration: number;
  provider_usage: string[];
  success: boolean;
  completed_at: string;
}

interface WorkflowHistoryPanelProps {
  history: WorkflowMemory[];
}

export const WorkflowHistoryPanel: React.FC<WorkflowHistoryPanelProps> = ({ history }) => {
  const [search, setSearch] = useState('');

  const filteredHistory = history.filter(run => 
    run.goal.toLowerCase().includes(search.toLowerCase()) ||
    run.intent.toLowerCase().includes(search.toLowerCase()) ||
    run.workflow_id.toLowerCase().includes(search.toLowerCase())
  );

  if (history.length === 0) {
    return (
      <p className="text-xs text-dark-500 font-mono text-center py-12">
        No workflow history recorded in the memory engine yet.
      </p>
    );
  }

  const getStatusIcon = (success: boolean) => {
    return success 
      ? <CheckCircle2 className="w-5 h-5 text-green-400" />
      : <XCircle className="w-5 h-5 text-red-400" />;
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3.5 top-3 w-4 h-4 text-dark-500" />
        <Input
          type="text"
          placeholder="Search by goal, workflow ID, or intent..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="relative border-l border-border-primary ml-3 pl-6 space-y-4">
        {filteredHistory.map(run => (
          <div key={run.workflow_id} className="relative">
            {/* Timeline Node Icon */}
            <div className="absolute -left-[37px] top-1.5 p-1 bg-dark-950 rounded-full border border-border-primary">
              {getStatusIcon(run.success)}
            </div>

            <Card className="border-border-primary">
              <CardContent className="p-4 flex flex-col md:flex-row justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-dark-800 text-dark-200 text-[10px] font-mono font-bold uppercase tracking-wider">
                      {run.intent}
                    </span>
                    <span className="text-[10px] text-dark-500 font-mono">
                      {run.workflow_id.slice(0, 12)}
                    </span>
                    <span className="text-[10px] text-dark-500 font-mono">
                      · {formatTimestamp(run.completed_at)}
                    </span>
                  </div>
                  
                  <p className="text-sm font-semibold text-dark-100 font-display">
                    {run.goal}
                  </p>

                  {/* Badges */}
                  <div className="flex flex-wrap items-center gap-3 text-[10px] text-dark-400 font-mono pt-1">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-cyan-accent" />
                      <span>{run.duration.toFixed(1)}s</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Cpu className="w-3.5 h-3.5 text-purple-accent" />
                      <span>{run.execution_metrics.tokens_used?.toLocaleString() ?? 0} tokens</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-yellow-400" />
                      <span>{run.findings.length} findings</span>
                    </div>
                  </div>
                </div>

                {/* Provider logs */}
                <div className="flex flex-wrap md:flex-col justify-end items-start md:items-end gap-1 shrink-0 font-mono text-[9px] text-dark-500">
                  <div className="uppercase tracking-widest text-[8px] text-dark-600 mb-1">Providers Used</div>
                  {run.provider_usage.map(prov => (
                    <span key={prov} className="px-2 py-0.5 rounded bg-dark-900 border border-border-primary">
                      {prov}
                    </span>
                  ))}
                  {run.provider_usage.length === 0 && <span>None</span>}
                </div>
              </CardContent>
            </Card>
          </div>
        ))}

        {filteredHistory.length === 0 && (
          <p className="text-xs text-dark-500 font-mono text-center py-6">
            No matching runs found.
          </p>
        )}
      </div>
    </div>
  );
};
export default WorkflowHistoryPanel;
