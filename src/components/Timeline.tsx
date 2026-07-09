import React from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2, ShieldAlert } from 'lucide-react';

interface TimelineProps {
  currentStage: string;
  progress: number;
  status: string;
}

export const Timeline: React.FC<TimelineProps> = ({ currentStage, progress, status }) => {
  const steps = [
    { label: 'Repository Indexed', match: ['scanner', 'scanning', 'cloning', 'index', 'chunk', 'init'], minProgress: 10 },
    { label: 'Semantic Retrieval', match: ['retrieval', 'querying', 'search'], minProgress: 30 },
    { label: 'Context Optimization', match: ['deduplicator', 'merging', 'optimize'], minProgress: 50 },
    { label: 'Prompt Building', match: ['prompt', 'templates'], minProgress: 70 },
    { label: 'AI Reasoning', match: ['critic', 'reasoning', 'llm'], minProgress: 85 },
    { label: 'JSON Validation', match: ['validation', 'parser', 'pydantic', 'repair'], minProgress: 95 },
    { label: 'Report Generation', match: ['report', 'markdown', 'serialize'], minProgress: 98 },
    { label: 'Completed', match: ['completed', 'success'], minProgress: 100 }
  ];

  const getStepStatus = (index: number) => {
    if (status === 'failed') return 'failed';
    if (status === 'completed' || progress === 100) return 'completed';
    
    const stageLower = currentStage.toLowerCase();
    
    // Check if this step is currently running
    const isCurrentMatch = steps[index].match.some(m => stageLower.includes(m));
    
    // If not matching directly, estimate based on minProgress bounds
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
    waiting: <div className="w-2.5 h-2.5 rounded-full bg-dark-700" />,
    active: <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />,
    completed: <Check className="w-4 h-4 text-emerald-400 stroke-[3]" />,
    failed: <ShieldAlert className="w-4 h-4 text-rose-500" />
  };

  return (
    <div className="w-full bg-dark-900 border border-dark-800 rounded-lg p-6">
      <h3 className="text-xs font-semibold font-mono text-dark-400 uppercase mb-5 tracking-wider">
        AI Execution Timeline
      </h3>

      {/* Horizontal timeline grid */}
      <div className="relative flex flex-col md:flex-row justify-between items-start md:items-center gap-6 md:gap-2">
        {steps.map((step, idx) => {
          const stepStatus = getStepStatus(idx);
          
          return (
            <div key={idx} className="flex md:flex-col items-center flex-1 w-full relative">
              {/* Connector Line */}
              {idx < steps.length - 1 && (
                <div className="hidden md:block absolute top-5 left-[calc(50%+16px)] right-[calc(-50%+16px)] h-[1px] bg-dark-800 z-0">
                  <motion.div
                    className="h-full bg-cyan-500/50"
                    initial={{ width: 0 }}
                    animate={{ width: stepStatus === 'completed' ? '100%' : '0%' }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              )}

              {/* Node Indicator */}
              <motion.div
                className={`w-10 h-10 rounded-full flex items-center justify-center border z-10 shrink-0 ${
                  stepStatus === 'completed'
                    ? 'border-emerald-500/30 bg-emerald-950/20 shadow-[0_0_12px_rgba(16,185,129,0.1)]'
                    : stepStatus === 'active'
                    ? 'border-cyan-500/50 bg-cyan-950/25 shadow-[0_0_12px_rgba(34,211,238,0.15)] ring-2 ring-cyan-500/10'
                    : stepStatus === 'failed'
                    ? 'border-rose-500/40 bg-rose-950/20'
                    : 'border-dark-800 bg-dark-950'
                }`}
                animate={stepStatus === 'active' ? { scale: [1, 1.05, 1] } : {}}
                transition={stepStatus === 'active' ? { repeat: Infinity, duration: 2 } : {}}
              >
                {icons[stepStatus]}
              </motion.div>

              {/* Step Title Label */}
              <div className="ml-4 md:ml-0 md:mt-3 text-left md:text-center">
                <p className={`text-[10px] font-mono font-bold uppercase ${
                  stepStatus === 'completed'
                    ? 'text-emerald-400'
                    : stepStatus === 'active'
                    ? 'text-cyan-400'
                    : stepStatus === 'failed'
                    ? 'text-rose-400'
                    : 'text-dark-500'
                }`}>
                  STEP 0{idx + 1}
                </p>
                <p className={`text-xs font-semibold mt-0.5 whitespace-nowrap ${
                  stepStatus === 'active' ? 'text-dark-100 font-medium' : 'text-dark-400'
                }`}>
                  {step.label}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
