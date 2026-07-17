import React from 'react';
import { Award, Zap, RefreshCw, Layers } from 'lucide-react';
import { Card, CardContent } from './ui';

export interface LearningMetrics {
  workflow_success_rate: number;
  average_execution_time: number;
  average_retries: number;
  provider_reliability: Record<string, number>;
  recurring_findings_count: number;
  repository_health_trend: number[];
}

interface LearningMetricsPanelProps {
  metrics: LearningMetrics;
}

export const LearningMetricsPanel: React.FC<LearningMetricsPanelProps> = ({ metrics }) => {
  const successRatePct = Math.round(metrics.workflow_success_rate * 100);
  
  // Health score is the last value in health trend or default 100
  const currentHealthScore = metrics.repository_health_trend.length > 0 
    ? metrics.repository_health_trend[metrics.repository_health_trend.length - 1]
    : 100;

  return (
    <div className="space-y-6">
      {/* Upper key metrics grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Workflow Success Rate', value: `${successRatePct}%`, icon: Award, color: 'text-green-400' },
          { label: 'Avg Execution Duration', value: `${metrics.average_execution_time.toFixed(1)}s`, icon: Zap, color: 'text-cyan-accent' },
          { label: 'Avg Retries Per Run', value: metrics.average_retries.toFixed(2), icon: RefreshCw, color: 'text-purple-accent' },
          { label: 'Current Repository Health', value: `${currentHealthScore.toFixed(0)}/100`, icon: Layers, color: 'text-yellow-400' },
        ].map(m => {
          const Icon = m.icon;
          return (
            <Card key={m.label} className="border-border-primary bg-dark-900/10">
              <CardContent className="p-4 flex flex-col justify-between h-[96px]">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-dark-500">{m.label}</span>
                  <Icon className={`w-4 h-4 ${m.color}`} />
                </div>
                <div className="text-2xl font-bold font-mono text-dark-50">{m.value}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Provider Reliability */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-4">
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Provider Reliability</h3>
            <div className="space-y-3 pt-1">
              {Object.entries(metrics.provider_reliability).map(([provider, rate]) => (
                <div key={provider} className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-dark-300 capitalize">{provider}</span>
                    <span className="text-cyan-accent font-semibold">{(rate * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-dark-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-cyan-accent to-purple-accent rounded-full transition-all duration-500"
                      style={{ width: `${rate * 100}%` }}
                    />
                  </div>
                </div>
              ))}
              {Object.keys(metrics.provider_reliability).length === 0 && (
                <p className="text-xs text-dark-500 font-mono text-center py-6">No provider usage registered yet.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Health Trend Chart (Sparkline representation) */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-4">
            <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Health Trend</h3>
            {metrics.repository_health_trend.length > 0 ? (
              <div className="space-y-4 pt-1">
                {/* Visual bar graph representation */}
                <div className="flex items-end justify-between gap-1.5 h-20 px-2 border-b border-border-primary/50">
                  {metrics.repository_health_trend.map((score, idx) => (
                    <div 
                      key={idx} 
                      className="flex-1 bg-gradient-to-t from-cyan-accent/20 to-cyan-accent rounded-t hover:opacity-80 transition-all duration-300 relative group"
                      style={{ height: `${score}%` }}
                    >
                      {/* Tooltip */}
                      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block px-1.5 py-0.5 rounded bg-dark-950 border border-border-primary text-[8px] font-mono text-cyan-accent whitespace-nowrap z-10 shadow-lg">
                        Run {idx + 1}: {score}%
                      </span>
                    </div>
                  ))}
                </div>
                <div className="flex justify-between text-[9px] font-mono text-dark-500 uppercase tracking-widest">
                  <span>Earliest Run</span>
                  <span>Latest Run</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-dark-500 font-mono text-center py-6">No runs to map trend.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
export default LearningMetricsPanel;
