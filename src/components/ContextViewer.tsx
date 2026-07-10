import React, { useState, useMemo } from 'react';
import {
  Layers,
  FileCode,
  BarChart3,
  Hash,
  ArrowRight,
} from 'lucide-react';
import { ContextDrawer } from './ContextDrawer';
import type { ContextChunk } from '../types';
import { motion } from 'framer-motion';

interface ContextViewerProps {
  chunks?: ContextChunk[];
}

export const ContextViewer: React.FC<ContextViewerProps> = React.memo(({ chunks }) => {
  const stats = useMemo(() => {
    if (!chunks || chunks.length === 0) {
      return { uniqueFiles: 0, topScore: 0, avgScore: 0, totalLines: 0 };
    }
    const uniqueFiles = new Set(chunks.map((c) => c.path)).size;
    const scores = chunks.filter((c) => c.score !== undefined).map((c) => c.score as number);
    const topScore = scores.length > 0 ? Math.max(...scores) : 0;
    const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    const totalLines = chunks.reduce((sum, c) => sum + (c.end_line - c.start_line + 1), 0);
    return { uniqueFiles, topScore, avgScore, totalLines };
  }, [chunks]);

  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!chunks || chunks.length === 0) return null;

  const statCards = [
    {
      label: 'Total Chunks',
      value: chunks.length.toString(),
      icon: <Layers className="w-4 h-4 text-cyan-400" />,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10 border-cyan-500/20',
      hoverBorder: 'hover:border-cyan-500/30'
    },
    {
      label: 'Files Covered',
      value: stats.uniqueFiles.toString(),
      icon: <FileCode className="w-4 h-4 text-purple-400" />,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10 border-purple-500/20',
      hoverBorder: 'hover:border-purple-500/30'
    },
    {
      label: 'Top Similarity',
      value: `${(stats.topScore * 100).toFixed(1)}%`,
      icon: <BarChart3 className="w-4 h-4 text-emerald-400" />,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
      hoverBorder: 'hover:border-emerald-500/30'
    },
    {
      label: 'Total Lines',
      value: stats.totalLines.toLocaleString(),
      icon: <Hash className="w-4 h-4 text-amber-400" />,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
      hoverBorder: 'hover:border-amber-500/30'
    },
  ];

  return (
    <>
      <div className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-6 shadow-xl space-y-5">
        
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-dark-850 pb-4">
          <div>
            <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
              <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-lg font-mono">05</span>
              <span>RETRIEVED SEMANTIC CONTEXT</span>
            </h2>
            <p className="text-xs text-dark-500 font-mono mt-1">
              Code snippets retrieved from RAG pipeline and injected into LLM context.
            </p>
          </div>
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500/15 border border-cyan-500/25 text-cyan-400 hover:bg-cyan-500/25 hover:border-cyan-500/40 font-mono text-[11px] font-bold uppercase tracking-wider cursor-pointer transition-all group shrink-0 shadow-lg"
          >
            <span>View Code Context</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>

        {/* Compact stats grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card) => (
            <motion.div
              key={card.label}
              whileHover={{ y: -2, scale: 1.01 }}
              className={`flex items-center gap-3.5 p-4 rounded-xl bg-[#070b14]/50 border border-dark-850 transition-all duration-200 ${card.hoverBorder}`}
            >
              <div className={`p-2.5 rounded-lg border ${card.bgColor} shrink-0`}>
                {card.icon}
              </div>
              <div className="min-w-0">
                <p className={`text-lg font-bold font-mono leading-none ${card.color}`}>{card.value}</p>
                <p className="text-[10px] text-dark-500 font-mono uppercase tracking-wider mt-1 truncate">{card.label}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Average score micro-bar */}
        <div className="mt-2 flex items-center gap-4 border-t border-dark-850/50 pt-4">
          <span className="text-[9px] text-dark-500 font-mono uppercase tracking-widest shrink-0 font-semibold">
            Avg Similarity
          </span>
          <div className="flex-1 h-2 bg-[#070b14] rounded-full overflow-hidden border border-dark-850 p-0.5">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 shadow-[0_0_8px_rgba(6,182,212,0.3)]"
              initial={{ width: 0 }}
              animate={{ width: `${stats.avgScore * 100}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>
          <span className="text-[10px] text-cyan-400 font-mono font-bold shrink-0">
            {(stats.avgScore * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Drawer overlay panel */}
      <ContextDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        chunks={chunks}
      />
    </>
  );
});
