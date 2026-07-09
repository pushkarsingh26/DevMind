import React, { useContext } from 'react';
import { Cpu, History } from 'lucide-react';
import { AnalysisContext } from '../context/AnalysisContext';

interface NavbarProps {
  onOpenHistory: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenHistory }) => {
  const context = useContext(AnalysisContext);
  
  // Safe fallback if context is not loaded yet
  const historyCount = context ? context.history.length : 0;
  const isAnalyzing = context ? context.isAnalyzing : false;
  const parsedReport = context ? context.parsedReport : null;

  const renderStatusBadge = () => {
    if (isAnalyzing) {
      return (
        <span className="px-2 py-0.5 rounded border border-cyan-500/30 bg-cyan-950/20 text-cyan-400 animate-pulse font-mono text-[10px]">
          RUNNING AUDIT...
        </span>
      );
    }

    if (parsedReport) {
      const meta = parsedReport.aiOutput?.ai_metadata;
      const isFallback = parsedReport.aiOutput?.is_fallback || meta?.fallback_flag;

      if (isFallback) {
        return (
          <span className="px-2 py-0.5 rounded border border-amber-500/30 bg-amber-950/20 text-amber-400 font-mono text-[10px]" title="LLMs offline. Static analyzer active.">
            HEURISTIC FALLBACK
          </span>
        );
      }

      return (
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span className="px-2 py-0.5 rounded border border-emerald-500/30 bg-emerald-950/20 text-emerald-400">
            AI MODE
          </span>
          <span className="text-dark-600">/</span>
          <span className="text-dark-300">
            {meta?.provider?.toUpperCase()} ({meta?.model?.split('/').pop()?.toUpperCase()})
          </span>
        </div>
      );
    }

    return (
      <span className="px-2 py-0.5 rounded border border-dark-800 bg-dark-950 text-dark-500 font-mono text-[10px]">
        AI ENGINE STANDBY
      </span>
    );
  };

  return (
    <header className="border-b border-dark-800 bg-dark-900/50 backdrop-blur-md px-6 py-4 z-30 relative">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-brand-600/10 p-2 rounded-lg border border-brand-500/20 text-brand-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-dark-50 tracking-tight flex items-center gap-2 m-0 p-0 leading-none">
              DevMind
              <span className="text-xs font-normal text-brand-400 px-2 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/25">
                Phase 4
              </span>
            </h1>
            <p className="text-xs text-dark-400 mt-1 font-mono">AI Code Intelligence Engine</p>
          </div>
        </div>
        
        <div className="flex items-center gap-5">
          {/* Dynamic AI status badge */}
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-dark-500 font-mono text-[10px]">SYSTEM STATUS:</span>
            {renderStatusBadge()}
          </div>

          <span className="text-dark-700 hidden sm:inline">|</span>

          {/* History drawer button */}
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-2 px-3.5 py-2 border border-dark-800 hover:border-dark-750 bg-dark-950 hover:bg-dark-900 rounded font-mono text-xs text-dark-300 hover:text-dark-100 transition-all cursor-pointer relative"
          >
            <History className="w-4 h-4 text-cyan-400" />
            <span>HISTORY</span>
            {historyCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-cyan-500 text-dark-950 font-bold rounded-full flex items-center justify-center text-[9px] scale-95 shadow-[0_0_6px_rgba(34,211,238,0.4)]">
                {historyCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
