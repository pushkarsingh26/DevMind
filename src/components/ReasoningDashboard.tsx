import React from 'react';
import { Brain, ShieldAlert, Layers, Activity, GitBranch, AlertTriangle } from 'lucide-react';
import { Card, CardContent } from './ui';

interface ReasoningSummary {
  repository_id: string;
  reasoning_score: number;
  confidence: number;
  critical_paths: string[];
  affected_modules: string[];
  risk_indicators: string[];
  generated_at: string;
  build_time_ms: number;
}

interface ReasoningDashboardProps {
  summary: ReasoningSummary;
}

const RISK_COLORS: Record<string, string> = {
  HIGH_BREAKING_CHANGE_RISK: 'border-red-500/40 text-red-400 bg-red-500/10',
  REPOSITORY_WIDE_IMPACT: 'border-orange-500/40 text-orange-400 bg-orange-500/10',
  LOW_HISTORICAL_SUCCESS: 'border-yellow-500/40 text-yellow-400 bg-yellow-500/10',
  PREVIOUS_FAILURES_DETECTED: 'border-red-400/40 text-red-300 bg-red-400/10',
  HIGH_REFACTOR_COMPLEXITY: 'border-purple-accent/40 text-purple-accent bg-purple-accent/10',
};

const GaugeArc: React.FC<{ value: number; size?: number; label: string; color?: string }> = ({
  value,
  size = 120,
  label,
  color = '#22d3ee',
}) => {
  const r = (size - 16) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = Math.PI;
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(startAngle + Math.PI);
  const y2 = cy + r * Math.sin(startAngle + Math.PI);
  const filled = cx + r * Math.cos(startAngle + Math.PI * value);
  const filledY = cy + r * Math.sin(startAngle + Math.PI * value);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size / 2 + 8} viewBox={`0 0 ${size} ${size / 2 + 8}`}>
        {/* Track */}
        <path
          d={`M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d={`M ${x1} ${y1} A ${r} ${r} 0 0 1 ${filled} ${filledY}`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
        {/* Value text */}
        <text x={cx} y={cy / 2 + 28} textAnchor="middle" fontSize="20" fontWeight="700" fill={color} fontFamily="monospace">
          {Math.round(value * 100)}
        </text>
      </svg>
      <span className="text-[10px] font-mono uppercase tracking-widest text-dark-400">{label}</span>
    </div>
  );
};

const MetricCard: React.FC<{ icon: React.ReactNode; label: string; value: string | number; sub?: string; color?: string }> = ({
  icon, label, value, sub, color = 'text-cyan-accent',
}) => (
  <Card className="border-border-primary">
    <CardContent className="p-4 flex items-start gap-3">
      <div className={`mt-0.5 ${color}`}>{icon}</div>
      <div>
        <p className="text-[10px] font-mono uppercase tracking-widest text-dark-400">{label}</p>
        <p className={`text-2xl font-extrabold font-display tracking-tight ${color}`}>{value}</p>
        {sub && <p className="text-[10px] font-mono text-dark-500 mt-0.5">{sub}</p>}
      </div>
    </CardContent>
  </Card>
);

export const ReasoningDashboard: React.FC<ReasoningDashboardProps> = ({ summary }) => {
  const builtAt = summary.generated_at
    ? new Date(summary.generated_at).toLocaleString()
    : '—';

  return (
    <div className="space-y-6">
      {/* Gauges row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-border-primary">
          <CardContent className="p-6 flex flex-col items-center gap-1">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Reasoning Score</h3>
            </div>
            <GaugeArc value={summary.reasoning_score} size={160} label="Score / 100" color="#22d3ee" />
            <p className="text-[10px] text-dark-500 font-mono mt-2">Built in {summary.build_time_ms?.toFixed(0) ?? 0}ms · {builtAt}</p>
          </CardContent>
        </Card>

        <Card className="border-border-primary">
          <CardContent className="p-6 flex flex-col items-center gap-1">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Confidence</h3>
            </div>
            <GaugeArc value={summary.confidence} size={160} label="Confidence / 100" color="#a78bfa" />
            <p className="text-[10px] text-dark-500 font-mono mt-2">
              {summary.risk_indicators?.length ?? 0} active risk indicator{(summary.risk_indicators?.length ?? 0) !== 1 ? 's' : ''}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<GitBranch className="w-5 h-5" />}
          label="Critical Paths"
          value={summary.critical_paths?.length ?? 0}
          sub="High-dependency files"
          color="text-cyan-accent"
        />
        <MetricCard
          icon={<Layers className="w-5 h-5" />}
          label="Affected Modules"
          value={summary.affected_modules?.length ?? 0}
          sub="In dependency graph"
          color="text-purple-accent"
        />
        <MetricCard
          icon={<ShieldAlert className="w-5 h-5" />}
          label="Risk Indicators"
          value={summary.risk_indicators?.length ?? 0}
          sub="Active risks detected"
          color="text-yellow-400"
        />
        <MetricCard
          icon={<Brain className="w-5 h-5" />}
          label="Build Time"
          value={`${Math.round(summary.build_time_ms ?? 0)}ms`}
          sub="Last reasoning build"
          color="text-green-400"
        />
      </div>

      {/* Risk indicator badges */}
      {(summary.risk_indicators?.length ?? 0) > 0 && (
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Active Risk Indicators</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {summary.risk_indicators.map(ri => (
                <span
                  key={ri}
                  className={`px-3 py-1.5 rounded-full text-[10px] font-mono font-semibold border ${RISK_COLORS[ri] ?? 'border-border-primary text-dark-400 bg-dark-900/30'}`}
                >
                  {ri.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Critical paths list */}
      {(summary.critical_paths?.length ?? 0) > 0 && (
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Critical Paths</h3>
              <span className="ml-auto text-[10px] font-mono text-dark-500">{summary.critical_paths.length} files</span>
            </div>
            <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
              {summary.critical_paths.map((p, i) => (
                <div key={p} className="flex items-center gap-2 p-2 rounded-lg bg-dark-900/30 border border-border-primary/50">
                  <span className="text-[10px] font-mono text-cyan-accent/60 w-5 text-right shrink-0">#{i + 1}</span>
                  <span className="text-xs font-mono text-dark-200 truncate">{p}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ReasoningDashboard;
