import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CitationRef } from '../types';
import { ChevronDown, FileText } from 'lucide-react';

interface CitationCardProps {
  citation: CitationRef;
  index: number;
}

export const CitationCard = React.memo(({ citation, index }: CitationCardProps) => {
  const [expanded, setExpanded] = useState(false);

  const filename = citation.path.split('/').pop() ?? citation.path;
  const scoreLabel = citation.score != null ? `${(citation.score * 100).toFixed(0)}%` : null;

  const getScoreBadgeClass = (score?: number) => {
    if (!score) return 'border-dark-800 text-dark-500 bg-dark-900/40';
    if (score >= 0.85) return 'border-emerald-500/20 text-emerald-400 bg-emerald-950/25 shadow-[0_0_8px_rgba(16,185,129,0.15)]';
    if (score >= 0.65) return 'border-cyan-500/20 text-cyan-400 bg-cyan-950/25 shadow-[0_0_8px_rgba(6,182,212,0.15)]';
    return 'border-amber-500/20 text-amber-400 bg-amber-950/25';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.2 }}
      className={`border rounded-xl bg-[#070b14]/70 overflow-hidden transition-all duration-200 ${
        expanded ? 'border-dark-800/80 shadow-md' : 'border-dark-850/60 hover:border-dark-800'
      }`}
    >
      <button
        type="button"
        className="w-full flex items-center justify-between px-3.5 py-2.5 cursor-pointer text-left focus:outline-none bg-transparent"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2.5 truncate min-w-0">
          <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="text-xs font-sans font-medium text-dark-200 truncate" title={citation.path}>
            {filename}
          </span>
          <span className="text-[9px] font-mono text-dark-500 shrink-0 bg-dark-900 border border-dark-850 px-1.5 py-0.5 rounded">
            L{citation.start_line}–{citation.end_line}
          </span>
        </div>
        
        <div className="flex items-center gap-2 shrink-0">
          {scoreLabel && (
            <span className={`text-[8px] font-mono font-bold border rounded px-1.5 py-0.5 ${getScoreBadgeClass(citation.score)}`}>
              {scoreLabel} Match
            </span>
          )}
          <ChevronDown className={`w-3.5 h-3.5 text-dark-400 transition-transform duration-200 ${expanded ? 'rotate-180 text-cyan-400' : ''}`} />
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="border-t border-dark-850/60 bg-[#070b14]/90 px-3.5 py-2"
          >
            <code className="text-[9px] font-mono text-dark-400 break-all select-all leading-normal">
              {citation.path}
            </code>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
});
