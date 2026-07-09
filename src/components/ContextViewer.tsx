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

interface ContextViewerProps {
  chunks?: ContextChunk[];
}

export const ContextViewer: React.FC<ContextViewerProps> = ({ chunks }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!chunks || chunks.length === 0) return null;

  const stats = useMemo(() => {
    const uniqueFiles = new Set(chunks.map((c) => c.path)).size;
    const scores = chunks.filter((c) => c.score !== undefined).map((c) => c.score as number);
    const topScore = scores.length > 0 ? Math.max(...scores) : 0;
    const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    const totalLines = chunks.reduce((sum, c) => sum + (c.end_line - c.start_line + 1), 0);
    return { uniqueFiles, topScore, avgScore, totalLines };
  }, [chunks]);

  const statCards = [
    {
      label: 'Total Chunks',
      value: chunks.length.toString(),
      icon: <Layers className="w-4 h-4" />,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10 border-cyan-500/20',
    },
    {
      label: 'Files Covered',
      value: stats.uniqueFiles.toString(),
      icon: <FileCode className="w-4 h-4" />,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10 border-purple-500/20',
    },
    {
      label: 'Top Similarity',
      value: `${(stats.topScore * 100).toFixed(1)}%`,
      icon: <BarChart3 className="w-4 h-4" />,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      label: 'Total Lines',
      value: stats.totalLines.toLocaleString(),
      icon: <Hash className="w-4 h-4" />,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
    },
  ];

  return (
    <>
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-6">
        {/* Section header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
          <div>
            <h2 className="text-base font-semibold text-dark-100 font-mono flex items-center gap-2">
              <span>05.</span> RETRIEVED SEMANTIC CONTEXT
            </h2>
            <p className="text-xs text-dark-500 font-mono mt-1">
              Code snippets retrieved from the RAG pipeline and injected into the LLM prompt.
            </p>
          </div>
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-500/30 font-mono text-xs font-semibold uppercase tracking-wider cursor-pointer transition-all group shrink-0"
          >
            <span>View Context</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>

        {/* Compact stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {statCards.map((card) => (
            <div
              key={card.label}
              className="flex items-center gap-3 p-3.5 rounded-lg bg-dark-950/50 border border-dark-850 hover:border-dark-700 transition-colors"
            >
              <div className={`p-2 rounded-lg border ${card.bgColor}`}>
                <span className={card.color}>{card.icon}</span>
              </div>
              <div>
                <p className={`text-lg font-bold font-mono ${card.color}`}>{card.value}</p>
                <p className="text-[10px] text-dark-500 font-mono uppercase tracking-wide">{card.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Average score micro-bar */}
        <div className="mt-4 flex items-center gap-3">
          <span className="text-[10px] text-dark-500 font-mono uppercase tracking-wide shrink-0">
            Avg Similarity
          </span>
          <div className="flex-1 h-1.5 bg-dark-850 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
              style={{ width: `${stats.avgScore * 100}%` }}
            />
          </div>
          <span className="text-[10px] text-dark-400 font-mono font-bold shrink-0">
            {(stats.avgScore * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Drawer portal */}
      <ContextDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        chunks={chunks}
      />
    </>
  );
};
