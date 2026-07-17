import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Clock, FileText, GitMerge, CheckCircle,
  AlertTriangle, Search, Filter,
} from 'lucide-react';
import { Card, CardContent } from './ui';

interface AgentEvent {
  timestamp: string;
  agent: string;
  step_id: string;
  event: string;
  finding_id?: string;
}

interface SharedFinding {
  finding_id: string;
  agent_name: string;
  severity: string;
  title: string;
  file_path: string;
  status: string;
  confidence: number;
}

interface CollaborationPanelProps {
  events: AgentEvent[];
  findings: SharedFinding[];
  contributions?: { agent_name: string; findings_count: number; evidence_count: number }[];
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  published: <FileText className="w-3.5 h-3.5 text-cyan-accent" />,
  reviewed: <CheckCircle className="w-3.5 h-3.5 text-green-400" />,
  conflict_detected: <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />,
  conflict_resolved: <GitMerge className="w-3.5 h-3.5 text-purple-accent" />,
  consensus_generated: <CheckCircle className="w-3.5 h-3.5 text-cyan-accent" />,
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

const STATUS_COLORS: Record<string, string> = {
  validated: 'bg-green-500/20 text-green-400',
  rejected: 'bg-red-500/20 text-red-400',
  pending: 'bg-yellow-500/20 text-yellow-400',
};

export const CollaborationPanel: React.FC<CollaborationPanelProps> = ({
  events, findings, contributions = [],
}) => {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => a.timestamp.localeCompare(b.timestamp)),
    [events],
  );

  const filteredFindings = useMemo(() => {
    return findings.filter(f => {
      if (severityFilter !== 'all' && f.severity !== severityFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return f.title.toLowerCase().includes(q) || f.file_path.toLowerCase().includes(q);
      }
      return true;
    });
  }, [findings, severityFilter, search]);

  const statusCounts = useMemo(() => ({
    pending: findings.filter(f => f.status === 'pending').length,
    validated: findings.filter(f => f.status === 'validated').length,
    rejected: findings.filter(f => f.status === 'rejected').length,
  }), [findings]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(['pending', 'validated', 'rejected'] as const).map(status => (
          <Card key={status} className="border-border-primary">
            <CardContent className="p-4 text-center">
              <div className={`text-2xl font-bold font-mono ${STATUS_COLORS[status]?.split(' ')[1] || 'text-dark-200'}`}>
                {statusCounts[status]}
              </div>
              <div className="text-[10px] uppercase tracking-widest text-dark-400 mt-1">{status}</div>
            </CardContent>
          </Card>
        ))}
        <Card className="border-border-primary">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold font-mono text-cyan-accent">{contributions.length}</div>
            <div className="text-[10px] uppercase tracking-widest text-dark-400 mt-1">Agents</div>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-dark-400" />
          <input
            type="text"
            placeholder="Search by title or file path..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-dark-900/50 border border-border-primary rounded-xl text-xs font-mono text-dark-200 focus:outline-none focus:border-cyan-accent/50"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-dark-400" />
          {['all', 'critical', 'high', 'medium', 'low'].map(sev => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase tracking-wider border transition-all cursor-pointer ${
                severityFilter === sev
                  ? 'border-cyan-accent/50 bg-cyan-accent/10 text-cyan-accent'
                  : 'border-border-primary text-dark-400 hover:text-dark-200'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Findings</h3>
        <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
          {filteredFindings.map(f => (
            <div key={f.finding_id} className="flex items-center gap-2 p-2.5 rounded-xl border border-border-primary bg-dark-900/30">
              <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase border ${SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.medium}`}>
                {f.severity}
              </span>
              <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase ${STATUS_COLORS[f.status] || STATUS_COLORS.pending}`}>
                {f.status}
              </span>
              <span className="text-xs text-dark-200 truncate flex-1">{f.title}</span>
              <span className="text-[10px] text-dark-500 font-mono">{(f.confidence * 100).toFixed(0)}%</span>
            </div>
          ))}
          {filteredFindings.length === 0 && (
            <p className="text-xs text-dark-500 font-mono text-center py-4">No findings match filters.</p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Agent Timeline</h3>
        <div className="space-y-2 max-h-80 overflow-y-auto scrollbar-thin">
          {sortedEvents.map((ev, idx) => (
            <motion.div
              key={`${ev.timestamp}-${idx}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.02 }}
              className="flex items-start gap-3 p-3 rounded-xl border border-border-primary bg-dark-900/20"
            >
              <div className="mt-0.5">{EVENT_ICONS[ev.event] || <Clock className="w-3.5 h-3.5 text-dark-400" />}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-mono text-dark-500">{ev.timestamp.slice(11, 19)}</span>
                  <span className="px-2 py-0.5 rounded bg-purple-accent/10 text-purple-accent text-[9px] font-mono">{ev.agent}</span>
                  <span className="text-[10px] font-mono uppercase text-dark-400">{ev.event.replace(/_/g, ' ')}</span>
                </div>
                {ev.finding_id && (
                  <span className="text-[10px] text-dark-500 font-mono mt-1 block truncate">
                    finding: {ev.finding_id}
                  </span>
                )}
              </div>
            </motion.div>
          ))}
          {sortedEvents.length === 0 && (
            <p className="text-xs text-dark-500 font-mono text-center py-8">No agent events recorded yet.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CollaborationPanel;
