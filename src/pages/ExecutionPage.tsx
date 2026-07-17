import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAnalysisData } from '../context/AnalysisContext';
import { ExecutionDashboard } from '../components/ExecutionDashboard';
import { EmptyState, Button } from '../components/ui';
import { 
  Play, Pause, RefreshCw, Trash2, Cpu, ArrowLeft, RotateCcw
} from 'lucide-react';
import axios from 'axios';

export const ExecutionPage: React.FC = () => {
  const { workflowId } = useParams<{ workflowId: string }>();
  const { addToast } = useAnalysisData();
  const navigate = useNavigate();

  const [steps, setSteps] = useState<any[]>([]);
  const [status, setStatus] = useState<string>('queued');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchSteps = useCallback(async () => {
    if (!workflowId || workflowId === 'active') return;
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await axios.get(`${backendUrl}/api/execution/${workflowId}/status`);
      setSteps(res.data.steps || []);
      setStatus(res.data.state?.status || res.data.status || 'queued');
    } catch (err) {
      console.error('Failed to fetch plan steps:', err);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    if (workflowId && workflowId !== 'active') {
      fetchSteps();
      const interval = setInterval(fetchSteps, 3000);
      return () => clearInterval(interval);
    } else {
      setLoading(false);
    }
  }, [workflowId, fetchSteps]);

  const handleAction = async (action: 'pause' | 'resume' | 'cancel' | 'retry') => {
    if (!workflowId) return;
    setActionLoading(action);
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await axios.post(`${backendUrl}/api/execution/${workflowId}/${action}`);
      addToast('success', res.data.message || `Action ${action} executed successfully.`);
      fetchSteps();
    } catch (err: any) {
      console.error(err);
      addToast('error', err.response?.data?.detail || `Failed to execute ${action}.`);
    } finally {
      setActionLoading(null);
    }
  };

  if (workflowId === 'active' || !workflowId) {
    return (
      <EmptyState
        title="No Active Execution Selected"
        description="Select a workflow run from history or launch a new execution from the planner to monitor it here."
        icon={<Cpu className="w-8 h-8 text-cyan-accent animate-pulse" />}
        action={
          <Button variant="primary" glow onClick={() => navigate('/history')} className="flex items-center gap-2">
            <Play className="w-3.5 h-3.5 fill-dark-950 text-dark-950" />
            <span>VIEW WORKFLOW HISTORY</span>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6 text-left">
      {/* Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border-primary pb-4">
        <div className="space-y-1">
          <button 
            onClick={() => navigate(-1)} 
            className="flex items-center gap-1.5 text-xs text-dark-400 font-mono hover:text-cyan-accent cursor-pointer mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>BACK</span>
          </button>
          <h1 className="text-xl font-extrabold text-dark-5 font-display tracking-tight flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-cyan-accent" />
            <span>Adaptive Execution Panel</span>
          </h1>
          <p className="text-xs text-dark-400 font-mono">
            Workflow Run ID: <span className="text-cyan-accent">{workflowId}</span> | State: <span className="text-dark-200 uppercase font-bold">{status}</span>
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap gap-2.5">
          {status === 'running' && (
            <Button 
              variant="glass" 
              onClick={() => handleAction('pause')} 
              loading={actionLoading === 'pause'}
              className="flex items-center gap-2 border-amber-500/20 text-amber-400 hover:bg-amber-500/10 cursor-pointer"
            >
              <Pause className="w-3.5 h-3.5" />
              <span>PAUSE RUN</span>
            </Button>
          )}

          {status === 'paused' && (
            <Button 
              variant="primary" 
              glow
              onClick={() => handleAction('resume')} 
              loading={actionLoading === 'resume'}
              className="flex items-center gap-2 cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-dark-950 text-dark-950" />
              <span>RESUME RUN</span>
            </Button>
          )}

          {status === 'failed' && (
            <>
              <Button 
                variant="primary" 
                glow
                onClick={() => handleAction('retry')} 
                loading={actionLoading === 'retry'}
                className="flex items-center gap-2 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5 text-dark-950" />
                <span>RETRY LAST STEP</span>
              </Button>
              <Button 
                variant="glass" 
                onClick={() => handleAction('resume')} 
                loading={actionLoading === 'resume'}
                className="flex items-center gap-2 border-cyan-500/20 text-cyan-accent hover:bg-cyan-500/10 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 text-cyan-accent" />
                <span>RESTART ENTIRE FLOW</span>
              </Button>
            </>
          )}

          {(status === 'running' || status === 'paused' || status === 'queued') && (
            <Button 
              variant="glass" 
              onClick={() => handleAction('cancel')} 
              loading={actionLoading === 'cancel'}
              className="flex items-center gap-2 border-rose-500/20 text-rose-400 hover:bg-rose-500/10 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>CANCEL RUN</span>
            </Button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 space-y-3 font-mono text-cyan-accent">
          <RefreshCw className="w-6 h-6 animate-spin" />
          <span className="text-xs uppercase tracking-wider">RESOLVING DYNAMIC GRAPH...</span>
        </div>
      ) : (
        <ExecutionDashboard workflowId={workflowId} steps={steps} />
      )}
    </div>
  );
};

export default ExecutionPage;
