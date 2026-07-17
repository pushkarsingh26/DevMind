import React from 'react';
import { motion } from 'framer-motion';
import { 
  Cpu, Clock, Coins, ShieldAlert, AlertTriangle, 
  ChevronRight, Award, Info
} from 'lucide-react';
import { Card, CardHeader, CardContent, Progress } from './ui';

interface ExecutionStep {
  step_id: string;
  agent: string;
  title: string;
  description: string;
  execution_group: string;
  input_files: string[];
  estimated_duration: number;
  estimated_token_cost: number;
}

interface StepDependency {
  source_step_id: string;
  target_step_id: string;
  dependency_type: string;
}

interface PlanningMetrics {
  estimated_duration: number;
  estimated_tokens: number;
  estimated_cost: number;
  parallel_groups: string[];
  critical_path: string[];
  dependency_depth: number;
  affected_files: number;
  affected_modules: number;
}

interface ExecutionPlan {
  plan_id: string;
  plan_version: string;
  repository_hash: string;
  generated_at: string;
  planner_version: string;
  plan_schema_version: string;
  steps: ExecutionStep[];
  dependencies: StepDependency[];
  intent: string;
  priority_score: number;
  risk_level: 'low' | 'medium' | 'high';
  complexity_level: 'low' | 'medium' | 'high';
  rationale: string;
  metrics: PlanningMetrics;
  score: {
    confidence: number;
    completeness: number;
    estimated_success_probability: number;
  };
}

interface PlanningPanelProps {
  plan: ExecutionPlan;
}

export const PlanningPanel: React.FC<PlanningPanelProps> = ({ plan }) => {
  const steps = plan.steps || [];
  const dependencies = plan.dependencies || [];
  const metrics = plan.metrics || {
    estimated_duration: 0,
    estimated_tokens: 0,
    estimated_cost: 0.0,
    parallel_groups: [],
    critical_path: [],
    dependency_depth: 0,
    affected_files: 0,
    affected_modules: 0
  };

  const score = plan.score || { confidence: 0.0, completeness: 0.0, estimated_success_probability: 0.0 };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-red-400 bg-red-500/10 border-red-500/20';
      case 'medium': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'low':
      default:
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    }
  };

  // Convert duration in seconds to minute string
  const formatDuration = (sec: number) => {
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    const rem = sec % 60;
    return rem > 0 ? `${min}m ${rem}s` : `${min}m`;
  };

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Metadata Section */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl border border-border-primary bg-dark-900/20 backdrop-blur-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] bg-cyan-accent/10 text-cyan-accent border border-cyan-accent/20 px-2 py-0.5 rounded-lg font-mono font-bold uppercase">
              {plan.intent}
            </span>
            <span className="text-[10px] text-dark-500 font-mono">Plan ID: {plan.plan_id} (v{plan.plan_version})</span>
          </div>
          <p className="text-xs text-dark-300 font-mono italic max-w-2xl leading-relaxed mt-1">
            {plan.rationale}
          </p>
        </div>
        <div className="flex gap-3 text-xs font-mono text-dark-400">
          <div className="flex flex-col items-end">
            <span className="text-dark-500 font-bold uppercase text-[9px]">Priority Score</span>
            <span className="text-dark-100 font-bold mt-0.5">{plan.priority_score}/10</span>
          </div>
          <div className="h-6 w-px bg-border-primary self-center" />
          <div className="flex flex-col items-end">
            <span className="text-dark-500 font-bold uppercase text-[9px]">Success Rate</span>
            <span className="text-emerald-400 font-bold mt-0.5">{Math.round(score.estimated_success_probability * 100)}%</span>
          </div>
        </div>
      </div>

      {/* 2. Planning Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Estimated Duration</span>
            <div className="text-lg font-extrabold text-dark-100 font-mono">
              {formatDuration(metrics.estimated_duration)}
            </div>
          </div>
          <Clock className="w-4 h-4 text-cyan-accent" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Token Budget</span>
            <div className="text-lg font-extrabold text-dark-100 font-mono">
              {metrics.estimated_tokens.toLocaleString()}
            </div>
          </div>
          <Coins className="w-4 h-4 text-purple-accent" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Estimated Cost</span>
            <div className="text-lg font-extrabold text-dark-100 font-mono">
              ${metrics.estimated_cost.toFixed(3)}
            </div>
          </div>
          <Coins className="w-4 h-4 text-emerald-400" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Risk Level</span>
            <div className={`text-xs font-bold px-2 py-0.5 border rounded-lg uppercase mt-1 w-fit ${getRiskColor(plan.risk_level)}`}>
              {plan.risk_level}
            </div>
          </div>
          <ShieldAlert className="w-4 h-4 text-amber-accent" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Complexity</span>
            <div className={`text-xs font-bold px-2 py-0.5 border rounded-lg uppercase mt-1 w-fit ${getRiskColor(plan.complexity_level)}`}>
              {plan.complexity_level}
            </div>
          </div>
          <AlertTriangle className="w-4 h-4 text-purple-accent" />
        </Card>
      </div>

      {/* 3. Execution Parallel Flow Graph (Topological Tiers Lanes) */}
      <Card variant="soft" className="space-y-5 overflow-hidden">
        <CardHeader>
          <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-accent" />
            <span>Dependency-Ordered Execution Lanes</span>
          </h3>
          <p className="text-[11px] text-dark-400 font-mono mt-1">
            Steps sorted topologically. Columns represent parallelizable concurrency tiers.
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto pb-4">
          <div className="flex gap-6 min-w-[700px] items-stretch">
            {metrics.parallel_groups.map((group_str, level_idx) => {
              const step_ids = group_str.split(',');
              const tier_steps = steps.filter(s => step_ids.includes(s.step_id));

              return (
                <div key={level_idx} className="flex-1 flex flex-col space-y-4 border border-border-primary/50 bg-[#070b14]/20 p-4 rounded-2xl min-h-[300px]">
                  <div className="flex justify-between items-center border-b border-border-primary pb-2">
                    <span className="text-[10px] text-cyan-accent font-mono font-bold uppercase">Tier {level_idx + 1}</span>
                    <span className="text-[9px] text-dark-500 font-mono">{tier_steps.length} parallel</span>
                  </div>

                  <div className="flex-1 flex flex-col gap-3 justify-center">
                    {tier_steps.map((step) => {
                      const isCritical = metrics.critical_path.includes(step.step_id);
                      return (
                        <motion.div
                          key={step.step_id}
                          whileHover={{ scale: 1.02 }}
                          className={`p-4 rounded-xl border relative overflow-hidden transition-all duration-200 text-xs font-sans text-left space-y-2
                            ${isCritical 
                              ? 'bg-purple-accent/5 border-purple-accent/40 shadow-[0_0_15px_rgba(168,85,247,0.1)]' 
                              : 'bg-dark-900/35 border-border-primary hover:border-dark-700'
                            }`}
                        >
                          {/* Animated step heartbeat indicator */}
                          <div className="absolute top-3.5 right-3.5 flex items-center gap-1.5">
                            <span className="relative flex h-2 w-2">
                              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isCritical ? 'bg-purple-accent' : 'bg-cyan-accent'}`}></span>
                              <span className={`relative inline-flex rounded-full h-2 w-2 ${isCritical ? 'bg-purple-accent' : 'bg-cyan-accent'}`}></span>
                            </span>
                          </div>

                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] text-dark-400 font-mono font-bold uppercase">{step.agent}</span>
                              {isCritical && (
                                <span className="text-[8px] bg-purple-accent/10 border border-purple-accent/20 px-1 py-0.2 rounded text-purple-accent font-mono font-bold">CRITICAL</span>
                              )}
                            </div>
                            <h4 className="text-xs font-bold text-dark-100 font-display leading-tight">{step.title}</h4>
                          </div>

                          <p className="text-[10.5px] text-dark-400 leading-normal font-mono line-clamp-3">
                            {step.description}
                          </p>

                          <div className="flex justify-between items-center text-[9.5px] text-dark-500 font-mono border-t border-border-primary/50 pt-2 mt-1">
                            <span>ID: {step.step_id}</span>
                            <span className="text-dark-300 font-bold">{formatDuration(step.estimated_duration)}</span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 4. Dependency lists and confidence report */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card variant="soft" className="space-y-4">
          <CardHeader>
            <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
              <Award className="w-4 h-4 text-purple-accent" />
              <span>Orchestration Quality Audit</span>
            </h3>
          </CardHeader>
          <CardContent className="space-y-4 font-mono text-xs text-dark-300">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Plan Completeness Score</span>
                <span className="text-cyan-accent font-bold">{Math.round(score.completeness * 100)}%</span>
              </div>
              <Progress value={score.completeness * 100} color="secondary" />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Confidence Assessment</span>
                <span className="text-purple-accent font-bold">{Math.round(score.confidence * 100)}%</span>
              </div>
              <Progress value={score.confidence * 100} color="primary" />
            </div>

            <div className="border-t border-border-primary pt-4 space-y-2 text-[11px] text-dark-400">
              <div className="flex justify-between">
                <span className="text-dark-500 font-bold">AFFECTED MODULES count:</span>
                <span className="text-dark-200">{metrics.affected_modules} modules</span>
              </div>
              <div className="flex justify-between">
                <span className="text-dark-500 font-bold">ESTIMATED CRITICAL PATH depth:</span>
                <span className="text-dark-200">{metrics.dependency_depth} levels</span>
              </div>
              <div className="flex justify-between">
                <span className="text-dark-500 font-bold">PLANNER SCHEMA VERSION:</span>
                <span className="text-cyan-accent font-bold">{plan.plan_schema_version}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card variant="soft" className="space-y-4">
          <CardHeader>
            <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
              <Info className="w-4 h-4 text-cyan-accent" />
              <span>Step Execution Dependencies</span>
            </h3>
          </CardHeader>
          <CardContent className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
            {dependencies.length === 0 ? (
              <div className="p-8 text-center text-dark-500 font-mono text-xs">
                No dependencies registered. Steps can run completely concurrently.
              </div>
            ) : (
              dependencies.map((dep, idx) => {
                const srcStep = steps.find(s => s.step_id === dep.source_step_id);
                const tgtStep = steps.find(s => s.step_id === dep.target_step_id);
                return (
                  <div key={idx} className="p-3 rounded-xl border border-border-primary bg-dark-900/25 flex items-center justify-between text-xs font-mono">
                    <span className="text-dark-200 font-bold truncate max-w-[150px]">{srcStep?.title || dep.source_step_id}</span>
                    <span className="flex items-center text-dark-500 text-[10px] gap-2">
                      <ChevronRight className="w-3.5 h-3.5 text-cyan-accent" />
                      <span>{dep.dependency_type}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-cyan-accent" />
                    </span>
                    <span className="text-dark-200 font-bold truncate max-w-[150px]">{tgtStep?.title || dep.target_step_id}</span>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
