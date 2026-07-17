import React from 'react';
import { HelpCircle, Terminal, FileCode, AlertTriangle, Play } from 'lucide-react';
import { Card, CardContent } from './ui';

export interface Recommendation {
  recommendation_id: string;
  type: string;
  title: string;
  description: string;
  confidence: number;
  details: Record<string, any>;
}

interface RecommendationPanelProps {
  recommendations: Recommendation[];
}

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({ recommendations }) => {
  if (recommendations.length === 0) {
    return (
      <p className="text-xs text-dark-500 font-mono text-center py-12">
        No active recommendations computed yet. Complete more workflow tasks to seed engine data.
      </p>
    );
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'suggested_workflow':
        return <Play className="w-5 h-5 text-cyan-accent" />;
      case 'likely_affected_files':
        return <FileCode className="w-5 h-5 text-purple-accent" />;
      case 'common_failure_locations':
        return <AlertTriangle className="w-5 h-5 text-red-400" />;
      case 'repeated_dependency_issues':
        return <Terminal className="w-5 h-5 text-yellow-400" />;
      default:
        return <HelpCircle className="w-5 h-5 text-dark-400" />;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {recommendations.map(rec => (
        <Card key={rec.recommendation_id} className="border-border-primary hover:border-cyan-accent/30 transition-all flex flex-col justify-between">
          <CardContent className="p-5 space-y-4 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-dark-900/50 border border-border-primary">
                  {getTypeIcon(rec.type)}
                </div>
                <h3 className="text-sm font-bold text-dark-100 font-display uppercase tracking-wide">
                  {rec.title}
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-cyan-accent/10 text-cyan-accent text-[10px] font-mono border border-cyan-accent/20 shrink-0">
                {(rec.confidence * 100).toFixed(0)}% Conf
              </span>
            </div>
            
            <p className="text-xs text-dark-300 font-mono leading-relaxed">
              {rec.description}
            </p>

            {rec.details && Object.keys(rec.details).length > 0 && (
              <div className="p-3 rounded-lg bg-dark-950/40 border border-border-primary/50 text-[11px] font-mono text-dark-400 space-y-1">
                {Object.entries(rec.details).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-dark-500 uppercase tracking-widest text-[9px]">{key.replace('_', ' ')}:</span>
                    <span className="text-dark-300 truncate max-w-[200px]">
                      {Array.isArray(val) ? val.join(', ') : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
export default RecommendationPanel;
