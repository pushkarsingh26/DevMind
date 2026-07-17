import React from 'react';
import { Server, Zap } from 'lucide-react';
import { Card, CardContent } from './ui';

interface ReasoningMetrics {
  reasoning_build_ms: number;
  context_build_ms: number;
  dependency_reasoning_ms: number;
  impact_reasoning_ms: number;
  evidence_ranking_ms: number;
  historical_reasoning_ms: number;
  serialization_ms: number;
  cache_hit: boolean;
  cache_miss: boolean;
  reasoning_score: number;
  reasoning_confidence: number;
  critical_path_count: number;
  affected_files: number;
  affected_symbols: number;
}

interface ReasoningTimelineProps {
  metrics: ReasoningMetrics;
}

const TelemetryRow: React.FC<{ label: string; value: string | number; desc?: string }> = ({
  label, value, desc,
}) => (
  <div className="flex justify-between items-center py-2.5 border-b border-border-primary/40 last:border-0">
    <div className="space-y-0.5">
      <span className="text-[11px] font-mono text-dark-200">{label}</span>
      {desc && <p className="text-[9px] font-mono text-dark-500">{desc}</p>}
    </div>
    <span className="text-xs font-mono font-bold text-cyan-accent">{value}</span>
  </div>
);

const WaterfallBar: React.FC<{ label: string; durationMs: number; totalMs: number; color?: string }> = ({
  label, durationMs, totalMs, color = 'bg-cyan-accent',
}) => {
  const pct = Math.min(100, Math.max(1, Math.round((durationMs / Math.max(totalMs, 1)) * 100)));
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-[10px] font-mono text-dark-400">
        <span>{label}</span>
        <span className="font-bold text-dark-200">{durationMs.toFixed(1)} ms</span>
      </div>
      <div className="h-2 rounded bg-dark-900/60 overflow-hidden relative">
        <div
          className={`h-full rounded ${color} opacity-80`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export const ReasoningTimeline: React.FC<ReasoningTimelineProps> = ({ metrics }) => {
  const cacheHitLabel = metrics.cache_hit ? 'HIT' : 'MISS';
  const cacheHitColor = metrics.cache_hit
    ? 'border-green-500/40 text-green-400 bg-green-500/10'
    : 'border-red-500/40 text-red-400 bg-red-500/10';

  return (
    <div className="space-y-6">
      {/* Waterfall build timing chart */}
      <Card className="border-border-primary">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-accent animate-pulse" />
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Reasoning Build Timeline</h3>
            <span className={`ml-auto px-2 py-0.5 rounded-full text-[9px] font-mono border uppercase tracking-wider ${cacheHitColor}`}>
              Cache {cacheHitLabel}
            </span>
          </div>

          <div className="space-y-3">
            <WaterfallBar label="Subsystem Context Ingestion" durationMs={metrics.context_build_ms} totalMs={metrics.reasoning_build_ms} color="bg-cyan-accent" />
            <WaterfallBar label="Dependency Graph Traversal" durationMs={metrics.dependency_reasoning_ms} totalMs={metrics.reasoning_build_ms} color="bg-purple-accent" />
            <WaterfallBar label="Deterministic Impact Analysis" durationMs={metrics.impact_reasoning_ms} totalMs={metrics.reasoning_build_ms} color="bg-purple-accent/70" />
            <WaterfallBar label="Weighted Evidence Leaderboard" durationMs={metrics.evidence_ranking_ms} totalMs={metrics.reasoning_build_ms} color="bg-cyan-accent/70" />
            <WaterfallBar label="Historical Memory Reasoning" durationMs={metrics.historical_reasoning_ms} totalMs={metrics.reasoning_build_ms} color="bg-dark-400" />
            <WaterfallBar label="Artifact Serialisation & Writing" durationMs={metrics.serialization_ms} totalMs={metrics.reasoning_build_ms} color="bg-green-400" />
          </div>

          <div className="border-t border-border-primary/20 pt-4 flex justify-between items-center text-xs font-mono">
            <span className="text-dark-400 uppercase tracking-widest font-bold">Total Execution Latency</span>
            <span className="text-cyan-accent font-extrabold text-sm">{metrics.reasoning_build_ms.toFixed(0)} ms</span>
          </div>
        </CardContent>
      </Card>

      {/* Numerical values list */}
      <Card className="border-border-primary">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-purple-accent" />
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Telemetry Summary</h3>
          </div>
          <div className="divide-y divide-border-primary/30">
            <TelemetryRow label="Reasoning Score" value={metrics.reasoning_score.toFixed(3)} desc="Weighted pipeline score" />
            <TelemetryRow label="Reasoning Confidence" value={metrics.reasoning_confidence.toFixed(3)} desc="Normalized pipeline confidence" />
            <TelemetryRow label="Critical Path Count" value={metrics.critical_path_count} desc="Number of high-dependency bottleneck files" />
            <TelemetryRow label="Total Affected Files" value={metrics.affected_files} desc="Sum of direct and transitive impacted modules" />
            <TelemetryRow label="Total Affected Symbols" value={metrics.affected_symbols} desc="Symbols reachable from critical paths" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ReasoningTimeline;
