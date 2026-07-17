import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Cpu, Clock, Shield, Coins, RefreshCw, Layers, Calendar
} from 'lucide-react';
import { Card, CardHeader, CardContent, Progress } from './ui';
import axios from 'axios';

interface ExecutionStep {
  step_id: string;
  agent: string;
  title: string;
  description: string;
  execution_group: string;
}

interface ExecutionEvent {
  timestamp: string;
  step_id: string;
  event: 'started' | 'completed' | 'failed' | 'retry' | 'failover';
  provider: string;
  duration_ms: number;
  retry: number;
}

interface ExecutionState {
  workflow_id: string;
  repository_id: string;
  current_step_id: string | null;
  current_tier_index: number;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'failed';
  start_time: string;
  last_updated_at: string;
  last_completed_step: string | null;
  failed_step: string | null;
  resume_from_step: string | null;
}

interface ExecutionMetrics {
  total_duration_sec: number;
  remaining_duration_sec_eta: number;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  retry_count: number;
  active_provider: string;
}

interface ExecutionBudget {
  max_tokens: number;
  max_cost_usd: number;
  used_tokens: number;
  used_cost_usd: number;
  remaining_tokens: number;
  remaining_cost: number;
}

interface ExecutionDashboardProps {
  workflowId: string;
  steps: ExecutionStep[];
}

export const ExecutionDashboard: React.FC<ExecutionDashboardProps> = ({ workflowId, steps = [] }) => {
  const [state, setState] = useState<ExecutionState | null>(null);
  const [metrics, setMetrics] = useState<ExecutionMetrics | null>(null);
  const [budget, setBudget] = useState<ExecutionBudget | null>(null);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const workflowIdRef = React.useRef(workflowId);
  workflowIdRef.current = workflowId;

  // Poll state and events — stable reference via useCallback
  const fetchStatus = React.useCallback(async () => {
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const statusRes = await axios.get(`${backendUrl}/api/execution/${workflowId}/status`);
      const eventsRes = await axios.get(`${backendUrl}/api/execution/${workflowId}/events`);

      if (statusRes.data.state) {
        setState(statusRes.data.state);
        setMetrics(statusRes.data.metrics);
        setBudget(statusRes.data.budget);
      } else {
        // Mock fallback if state is not initialized in file yet (queued)
        setState({
          workflow_id: workflowId,
          repository_id: '',
          current_step_id: null,
          current_tier_index: 0,
          status: statusRes.data.status || 'queued',
          start_time: new Date().toISOString(),
          last_updated_at: new Date().toISOString(),
          last_completed_step: null,
          failed_step: null,
          resume_from_step: null,
        });
        setMetrics({
          total_duration_sec: 0,
          remaining_duration_sec_eta: steps.length * 15,
          total_steps: steps.length,
          completed_steps: 0,
          failed_steps: 0,
          retry_count: 0,
          active_provider: 'google',
        });
        setBudget({
          max_tokens: 1000000,
          max_cost_usd: 5.0,
          used_tokens: 0,
          used_cost_usd: 0.0,
          remaining_tokens: 1000000,
          remaining_cost: 5.0,
        });
      }
      setEvents(eventsRes.data);
    } catch (err) {
      console.error('Failed to poll execution details:', err);
    } finally {
      setLoading(false);
    }
  }, [workflowId, steps.length]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      if (state?.status === 'running' || state?.status === 'queued') {
        fetchStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [workflowId, state?.status, fetchStatus]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3 font-mono text-cyan-accent">
        <RefreshCw className="w-6 h-6 animate-spin" />
        <span className="text-xs uppercase tracking-wider">RESOLVING EXECUTION STATE...</span>
      </div>
    );
  }

  const progressPct = metrics ? Math.round((metrics.completed_steps / metrics.total_steps) * 100) : 0;

  const getStepStatus = (stepId: string) => {
    if (state?.failed_step === stepId) return 'failed';
    if (state?.current_step_id === stepId) return 'running';
    
    // Check events log to see if completed
    const isCompleted = events.some(e => e.step_id === stepId && e.event === 'completed');
    if (isCompleted) return 'completed';
    
    const isStarted = events.some(e => e.step_id === stepId && e.event === 'started');
    if (isStarted) return 'running';

    return 'waiting';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'running': return 'text-cyan-accent bg-cyan-500/10 border-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.1)]';
      case 'failed': return 'text-red-400 bg-red-500/10 border-red-500/20';
      case 'waiting':
      default:
        return 'text-dark-500 bg-[#070b14]/20 border-border-primary';
    }
  };

  const formatDuration = (sec: number) => {
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    const rem = sec % 60;
    return rem > 0 ? `${min}m ${rem}s` : `${min}m`;
  };

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Estimated ETA</span>
            <div className="text-lg font-extrabold text-dark-100 font-mono animate-pulse">
              {metrics ? formatDuration(metrics.remaining_duration_sec_eta) : 'Estimating...'}
            </div>
          </div>
          <Clock className="w-4 h-4 text-cyan-accent" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Active Provider</span>
            <div className="text-xs font-bold text-purple-accent font-mono uppercase bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-lg w-fit mt-1">
              {metrics?.active_provider || 'google'}
            </div>
          </div>
          <Shield className="w-4 h-4 text-purple-accent" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Token Pool Remaining</span>
            <div className="text-lg font-extrabold text-dark-100 font-mono">
              {budget?.remaining_tokens.toLocaleString() || '1,000,000'}
            </div>
          </div>
          <Coins className="w-4 h-4 text-emerald-400" />
        </Card>

        <Card variant="soft" className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[9px] text-dark-500 font-mono font-bold uppercase">Cost Pool Remaining</span>
            <div className="text-lg font-extrabold text-dark-100 font-mono">
              ${budget?.remaining_cost.toFixed(3) || '5.000'}
            </div>
          </div>
          <Coins className="w-4 h-4 text-rose-400" />
        </Card>
      </div>

      {/* 2. Progress Indicator */}
      <Card variant="soft" className="p-5 space-y-3">
        <div className="flex justify-between items-center text-xs font-mono">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-accent animate-spin" />
            <span className="text-dark-200 font-bold uppercase">Progress: {metrics?.completed_steps || 0} / {metrics?.total_steps || 0} steps</span>
          </div>
          <span className="text-cyan-accent font-bold">{progressPct}%</span>
        </div>
        <Progress value={progressPct} color="secondary" />
      </Card>

      {/* 3. Concurrency step slots indicating status */}
      <Card variant="soft" className="space-y-4">
        <CardHeader>
          <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-accent" />
            <span>Execution Tiers Pipeline</span>
          </h3>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map((step) => {
            const stepStatus = getStepStatus(step.step_id);
            return (
              <div 
                key={step.step_id} 
                className={`p-4 rounded-xl border flex flex-col justify-between text-xs font-sans transition-all duration-200 min-h-[140px]
                  ${getStatusColor(stepStatus)}`}
              >
                <div className="space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-[9px] font-mono font-bold uppercase text-dark-400">{step.agent}</span>
                    <span className="text-[8px] font-mono uppercase font-bold">{stepStatus}</span>
                  </div>
                  <h4 className="font-bold text-dark-100 leading-tight">{step.title}</h4>
                  <p className="text-[10px] text-dark-400 font-mono line-clamp-2 mt-1">{step.description}</p>
                </div>
                <div className="flex justify-between items-center text-[9px] text-dark-500 font-mono border-t border-border-primary/50 pt-2 mt-2">
                  <span>ID: {step.step_id}</span>
                  <span>{step.execution_group}</span>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* 4. Event timeline list */}
      <Card variant="soft" className="space-y-4">
        <CardHeader>
          <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
            <Calendar className="w-4 h-4 text-purple-accent" />
            <span>Live Timeline Events Log</span>
          </h3>
        </CardHeader>
        <CardContent className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
          {events.length === 0 ? (
            <div className="p-12 text-center text-dark-500 font-mono text-xs">
              Waiting for workflow to begin... Queued execution log.
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {events.map((event, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="p-3 rounded-xl border border-border-primary bg-dark-900/35 flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-dark-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
                    <span className="text-dark-200 font-bold uppercase">{event.event}</span>
                    <span className="text-dark-400">Step: {event.step_id}</span>
                  </div>
                  <div className="flex items-center gap-4 text-dark-400">
                    <span>Provider: <strong className="text-purple-accent">{event.provider}</strong></span>
                    {event.retry > 0 && <span>Retry: <strong className="text-amber-accent">{event.retry}</strong></span>}
                    {event.duration_ms > 0 && <span>Duration: <strong>{formatDuration(Math.round(event.duration_ms / 1000))}</strong></span>}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
