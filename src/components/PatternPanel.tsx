import React, { useState } from 'react';
import { AlertCircle, ShieldAlert, Package, Flame, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent } from './ui';

export interface PatternRecord {
  pattern_id: string;
  category: string;
  key_signature: string;
  description: string;
  frequency: number;
  severity: string;
  confidence: number;
}

interface PatternPanelProps {
  patterns: PatternRecord[];
}

export const PatternPanel: React.FC<PatternPanelProps> = ({ patterns }) => {
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null);

  if (patterns.length === 0) {
    return (
      <p className="text-xs text-dark-500 font-mono text-center py-12">
        No recurring patterns recognized yet. Run more workflows to collect findings.
      </p>
    );
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'repeated_security_finding':
        return <ShieldAlert className="w-4 h-4 text-red-400" />;
      case 'repeated_dependency_problem':
        return <Package className="w-4 h-4 text-purple-400" />;
      case 'repeated_hotspot':
        return <Flame className="w-4 h-4 text-orange-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-cyan-accent" />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'repeated_security_finding':
        return 'Security Findings';
      case 'repeated_dependency_problem':
        return 'Dependency Risks';
      case 'repeated_hotspot':
        return 'Modularity Hotspots';
      case 'repeated_bug':
        return 'Repeated Bugs';
      default:
        return 'Other Patterns';
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'bg-red-500/10 text-red-400 border border-red-500/20';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
      default:
        return 'bg-green-500/10 text-green-400 border border-green-500/20';
    }
  };

  // Group patterns by category
  const groups: Record<string, PatternRecord[]> = {};
  patterns.forEach(pat => {
    groups[pat.category] = groups[pat.category] || [];
    groups[pat.category].push(pat);
  });

  return (
    <div className="space-y-4">
      {Object.entries(groups).map(([category, list]) => {
        const isExpanded = expandedGroupId === category;
        return (
          <Card key={category} className="border-border-primary overflow-hidden">
            <button
              onClick={() => setExpandedGroupId(isExpanded ? null : category)}
              className="w-full flex items-center justify-between p-4 bg-dark-900/10 hover:bg-dark-900/30 transition-all font-display text-left cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                {getCategoryIcon(category)}
                <span className="text-sm font-bold text-dark-100 uppercase tracking-wide">
                  {getCategoryLabel(category)} ({list.length})
                </span>
              </div>
              {isExpanded ? <ChevronUp className="w-4 h-4 text-dark-400" /> : <ChevronDown className="w-4 h-4 text-dark-400" />}
            </button>
            
            {isExpanded && (
              <CardContent className="p-4 border-t border-border-primary bg-dark-950/20 divide-y divide-border-primary/50">
                {list.map(pat => (
                  <div key={pat.pattern_id} className="py-3 first:pt-0 last:pb-0 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="text-sm text-dark-200 font-medium">{pat.description}</div>
                      <div className="text-[10px] font-mono text-dark-500">ID: {pat.pattern_id} · Signature: {pat.key_signature}</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 shrink-0">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${getSeverityStyle(pat.severity)}`}>
                        {pat.severity}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-dark-800 text-dark-300 text-[10px] font-mono">
                        Freq: {pat.frequency}x
                      </span>
                      <span className="px-2 py-0.5 rounded bg-cyan-accent/10 text-cyan-accent text-[10px] font-mono border border-cyan-accent/20">
                        Conf: {Math.round(pat.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
};
export default PatternPanel;
