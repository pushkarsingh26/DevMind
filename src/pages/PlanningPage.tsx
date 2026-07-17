import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useAnalysisData } from '../context/AnalysisContext';
import { PlanningPanel } from '../components/PlanningPanel';
import { EmptyState, Button, Card, CardContent } from '../components/ui';
import { Cpu, Database, Play, RefreshCw, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export const PlanningPage: React.FC = () => {
  const { parsedReport, addToast } = useAnalysisData();
  const navigate = useNavigate();

  const repositoryId = parsedReport?.repository?.id ?? null;
  const repositoryName = parsedReport?.repository?.name ?? '';

  const [goal, setGoal] = useState('Perform a security audit scan on JWT authentication routes and verify package dependency vulnerabilities.');
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheClearing, setCacheClearing] = useState(false);

  // Preview custom plan
  const handlePreviewPlan = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repositoryId || !goal.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await axios.get(`${backendUrl}/api/planning/${repositoryId}/preview`, {
        params: { goal: goal }
      });
      setPlan(res.data);
      addToast('success', 'Execution plan formulated successfully!');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Plan generation failed.');
    } finally {
      setLoading(false);
    }
  }, [repositoryId, goal, addToast]);

  // Clear planning cache
  const handleClearCache = async () => {
    if (!repositoryId) return;
    setCacheClearing(true);
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      await axios.delete(`${backendUrl}/api/planning/cache/${repositoryId}`);
      addToast('success', 'Planning cache cleared successfully!');
      setPlan(null);
    } catch (err: any) {
      console.error(err);
      addToast('error', 'Failed to clear planning cache.');
    } finally {
      setCacheClearing(false);
    }
  };

  // Auto preview on mount if repo is selected
  useEffect(() => {
    if (repositoryId && goal) {
      // Create fake event to trigger preview
      const mockEvent = { preventDefault: () => {} } as React.FormEvent;
      handlePreviewPlan(mockEvent);
    }
  }, [repositoryId, goal, handlePreviewPlan]);

  return (
    <div className="space-y-6 text-left">
      {/* Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-dark-50 font-display tracking-tight flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-cyan-accent animate-pulse" />
            <span>Intelligent Planning Engine</span>
          </h1>
          <p className="text-xs text-dark-400 font-mono mt-1">
            {repositoryId ? `Active Codebase: ${repositoryName} (ID: ${repositoryId})` : 'Resolve goals to dependency-ordered concurrency graphs.'}
          </p>
        </div>
        {repositoryId && (
          <Button 
            variant="glass" 
            onClick={handleClearCache} 
            loading={cacheClearing}
            className="flex items-center gap-2 text-rose-400 border-rose-500/20 hover:bg-rose-500/10 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>CLEAR PLANNING CACHE</span>
          </Button>
        )}
      </div>

      {repositoryId ? (
        <div className="space-y-6">
          {/* Goal Input form */}
          <Card variant="soft">
            <CardContent className="pt-5">
              <form onSubmit={handlePreviewPlan} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-mono font-bold text-dark-400">Describe Your Workflow Goal</label>
                  <textarea
                    rows={3}
                    placeholder="e.g. Implement custom metrics logger module under backend/app/utils/ and write full unit tests."
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    className="w-full bg-[#070b14]/40 border border-border-primary rounded-2xl px-4 py-3 text-xs font-mono text-cyan-accent focus:outline-none focus:border-cyan-500/60 leading-relaxed"
                    required
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="submit" variant="primary" glow loading={loading} className="px-6 py-2">
                    FORMULATE PLAN
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Loader */}
          {loading && (
            <div className="flex flex-col items-center justify-center p-12 space-y-3 font-mono text-cyan-accent">
              <RefreshCw className="w-6 h-6 animate-spin" />
              <span className="text-xs uppercase tracking-wider">Topologically Sorting Graph Steps...</span>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-5 rounded-2xl border border-red-500/20 bg-red-950/10 text-xs font-mono text-red-300">
              {error}
            </div>
          )}

          {/* Render Plan */}
          {plan && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
            >
              <PlanningPanel plan={plan} />
            </motion.div>
          )}
        </div>
      ) : (
        <EmptyState
          title="No Active Repository Selected"
          description="You must select or upload a target repository first to preview execution graphs."
          icon={<Database className="w-8 h-8 text-cyan-accent animate-pulse" />}
          action={
            <Button variant="primary" glow onClick={() => navigate('/repositories')} className="flex items-center gap-2">
              <Play className="w-3.5 h-3.5 fill-dark-950 text-dark-950" />
              <span>SELECT REPOSITORY</span>
            </Button>
          }
        />
      )}
    </div>
  );
};

export default PlanningPage;
