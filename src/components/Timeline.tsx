import React from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2, ShieldAlert } from 'lucide-react';
import { Card } from './ui';

interface TimelineProps {
  currentStage: string;
  progress: number;
  status: string;
}

export const Timeline: React.FC<TimelineProps> = React.memo(({ currentStage, progress, status }) => {
  const steps = [
    { label: 'Clone', match: ['cloning', 'clone', 'init', 'initializing'], minProgress: 8 },
    { label: 'Parse', match: ['parsing', 'parse', 'scan', 'scanning', 'indexer'], minProgress: 20 },
    { label: 'Chunk', match: ['chunk', 'chunking'], minProgress: 40 },
    { label: 'Embed', match: ['embed', 'embedding'], minProgress: 60 },
    { label: 'Retrieve', match: ['retrieve', 'retrieving', 'retrieval', 'querying', 'search'], minProgress: 75 },
    { label: 'AI Reasoning', match: ['critic', 'reasoning', 'llm', 'planner', 'reviewer', 'prompt'], minProgress: 88 },
    { label: 'Report Gen', match: ['report', 'markdown', 'serialize', 'generation', 'generate'], minProgress: 98 },
    { label: 'Complete', match: ['completed', 'success', 'complete'], minProgress: 100 }
  ];

  const getStepStatus = (index: number) => {
    if (status === 'failed') return 'failed';
    if (status === 'completed' || progress === 100) return 'completed';
    
    const stageLower = currentStage.toLowerCase();
    
    // Check if this step is currently running
    const isCurrentMatch = steps[index].match.some(m => stageLower.includes(m));
    
    if (isCurrentMatch) {
      return 'active';
    }

    // Determine past steps
    let maxMatchedIndex = -1;
    for (let i = 0; i < steps.length; i++) {
      if (steps[i].match.some(m => stageLower.includes(m)) || progress >= steps[i].minProgress) {
        maxMatchedIndex = i;
      }
    }

    if (index < maxMatchedIndex) return 'completed';
    if (index === maxMatchedIndex) return 'active';
    return 'waiting';
  };

  const icons = {
    waiting: <div className="w-2 h-2 rounded-full bg-dark-500" />,
    active: <Loader2 className="w-4 h-4 text-cyan-accent animate-spin" />,
    completed: <Check className="w-4 h-4 text-green-accent stroke-[3.5]" />,
    failed: <ShieldAlert className="w-4 h-4 text-rose-500" />
  };

  return (
    <Card variant="soft" className="w-full space-y-4">
      <h3 className="text-xs font-semibold font-mono text-purple-accent uppercase tracking-widest">
        AI PIPELINE EXECUTION MONITOR
      </h3>

      {/* Horizontal timeline container with scrolling support on small devices */}
      <div className="overflow-x-auto pb-3 md:pb-0 scrollbar-thin">
        <div className="min-w-[760px] relative flex justify-between items-center px-4 py-2">
          {steps.map((step, idx) => {
            const stepStatus = getStepStatus(idx);
            
            return (
              <div key={idx} className="flex flex-col items-center flex-1 relative">
                {/* Horizontal Line Connector */}
                {idx < steps.length - 1 && (
                  <div className="absolute top-5 left-[calc(50%+20px)] right-[calc(-50%+20px)] h-[2px] bg-border-primary/50 z-0">
                    <motion.div
                      className="h-full bg-gradient-to-r from-cyan-accent to-purple-accent"
                      initial={{ width: 0 }}
                      animate={{ width: stepStatus === 'completed' ? '100%' : '0%' }}
                      transition={{ duration: 0.4 }}
                    />
                  </div>
                )}

                {/* Circular Node */}
                <motion.div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border z-10 shrink-0 transition-all duration-200 ${
                    stepStatus === 'completed'
                      ? 'border-green-accent/40 bg-green-accent/15 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
                      : stepStatus === 'active'
                      ? 'border-cyan-accent/60 bg-cyan-accent/20 shadow-[0_0_15px_rgba(6,182,212,0.25)] ring-2 ring-cyan-accent/10'
                      : stepStatus === 'failed'
                      ? 'border-rose-500/40 bg-rose-500/10'
                      : 'border-border-primary bg-dark-950/20'
                  }`}
                  animate={stepStatus === 'active' ? { scale: [1, 1.04, 1] } : {}}
                  transition={stepStatus === 'active' ? { repeat: Infinity, duration: 2.2, ease: "easeInOut" } : {}}
                >
                  {icons[stepStatus]}
                </motion.div>

                {/* Title and Labels */}
                <div className="mt-3 text-center">
                  <p className={`text-[9px] font-mono font-bold uppercase tracking-wider ${
                    stepStatus === 'completed'
                      ? 'text-emerald-400'
                      : stepStatus === 'active'
                      ? 'text-cyan-400 animate-pulse'
                      : stepStatus === 'failed'
                      ? 'text-rose-400'
                      : 'text-dark-500'
                  }`}>
                    STAGE 0{idx + 1}
                  </p>
                  <p className={`text-xs font-semibold mt-0.5 font-display transition-colors ${
                    stepStatus === 'active' ? 'text-dark-100 font-bold' : 'text-dark-400'
                  }`}>
                    {step.label}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
});
