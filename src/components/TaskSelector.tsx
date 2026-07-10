import React, { useState, useRef, useEffect } from 'react';
import type { TaskType } from '../types';
import { useAnalysis } from '../hooks/useAnalysis';
import { ChevronDown, Sparkles, Check, Bug, Compass, FileCode2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, GlassPanel } from './ui';

interface TaskOption {
  value: TaskType;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const taskOptions: TaskOption[] = [
  {
    value: 'review',
    label: 'Review Repository',
    description: 'Structure review, style check, and security vulnerability analysis.',
    icon: <Compass className="w-4 h-4 text-cyan-400" />
  },
  {
    value: 'explain',
    label: 'Explain Code',
    description: 'High-level software architecture breakdown and layer mapping.',
    icon: <FileCode2 className="w-4 h-4 text-purple-400" />
  },
  {
    value: 'tests',
    label: 'Generate Tests',
    description: 'Generate automated robust unit test suites for primary components.',
    icon: <Sparkles className="w-4 h-4 text-emerald-400" />
  },
  {
    value: 'bugs',
    label: 'Find Bugs',
    description: 'Pinpoint logic defects, exception paths, and concurrency issues.',
    icon: <Bug className="w-4 h-4 text-rose-400" />
  },
];

export const TaskSelector: React.FC = () => {
  const { selectedTask, setSelectedTask, isAnalyzing } = useAnalysis();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentOption = taskOptions.find((o) => o.value === selectedTask) || taskOptions[0];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectTask = (value: TaskType) => {
    if (isAnalyzing) return;
    setSelectedTask(value);
    setIsOpen(false);
  };

  return (
    <Card variant="soft" className="flex flex-col justify-between relative space-y-4">
      <div className="relative" ref={dropdownRef}>
        <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2 mb-4">
          <span className="text-xs bg-purple-accent/10 text-purple-accent border border-purple-accent/20 px-2 py-0.5 rounded-lg font-mono font-bold">02</span>
          <span>ANALYSIS PIPELINE</span>
        </h2>
        
        <label className="block text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold mb-2">
          Select Agent Task
        </label>

        {/* Custom Premium Dropdown Button */}
        <button
          type="button"
          onClick={() => !isAnalyzing && setIsOpen(!isOpen)}
          disabled={isAnalyzing}
          className={`w-full bg-[#070b14]/30 dark:bg-[#070b14]/50 border border-border-primary hover:border-dark-700/80 focus:border-cyan-accent rounded-xl px-4 py-3 text-xs text-dark-100 font-sans flex items-center justify-between focus:outline-none transition-all duration-200 cursor-pointer select-none
            ${isAnalyzing ? 'opacity-50 cursor-not-allowed' : ''}
            ${isOpen ? 'border-cyan-accent/40 ring-1 ring-cyan-accent/10' : ''}
          `}
        >
          <div className="flex items-center gap-2.5">
            {currentOption.icon}
            <span className="font-sans font-semibold">{currentOption.label}</span>
          </div>
          <ChevronDown className={`w-4 h-4 text-dark-400 transition-transform duration-200 ${isOpen ? 'rotate-180 text-cyan-accent' : ''}`} />
        </button>

        {/* Dropdown Options Box */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute left-0 right-0 mt-2 z-50 min-w-48"
            >
              <GlassPanel variant="liquid" elevation={3} className="py-1.5 overflow-hidden border border-border-primary">
                {taskOptions.map((option) => {
                  const isSelected = option.value === selectedTask;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => selectTask(option.value)}
                      className={`w-full flex items-start gap-3 px-4 py-3 hover:bg-dark-900/60 transition-all text-left cursor-pointer
                        ${isSelected ? 'bg-dark-900/55' : ''}
                      `}
                    >
                      <div className="mt-0.5 shrink-0">{option.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className={`text-xs font-semibold font-sans ${isSelected ? 'text-cyan-accent font-bold' : 'text-dark-200'}`}>
                            {option.label}
                          </span>
                          {isSelected && <Check className="w-3.5 h-3.5 text-cyan-accent shrink-0" />}
                        </div>
                        <p className="text-[10px] text-dark-500 font-sans mt-1 leading-normal">
                          {option.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </GlassPanel>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Pipeline Objective Info block */}
      <div className="mt-2 pt-4 border-t border-border-primary">
        <span className="text-[9px] font-mono text-purple-accent uppercase tracking-widest font-bold block mb-1">
          Pipeline Objective
        </span>
        <p className="text-xs text-dark-400 font-sans leading-relaxed min-h-[40px]">
          {currentOption.description}
        </p>
      </div>
    </Card>
  );
};
