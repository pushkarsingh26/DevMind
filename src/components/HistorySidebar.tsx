import React, { useContext } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Trash2, Clock, Cpu, HardDrive, AlertCircle, Sparkles } from 'lucide-react';
import type { HistoryItem } from '../types';

interface HistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HistorySidebar: React.FC<HistorySidebarProps> = ({ isOpen, onClose }) => {
  const context = useContext(AnalysisContext);
  if (!context) return null;

  const { history, clearHistory, loadHistoryItem } = context;

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Dark blur overlay background */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black backdrop-blur-sm z-[80] cursor-pointer pointer-events-auto"
          />

          {/* Slide-out Sidebar container */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 220 }}
            className="fixed top-0 right-0 h-full w-full sm:w-[420px] bg-[#070b14]/98 border-l border-dark-850 shadow-2xl z-[85] flex flex-col pointer-events-auto"
          >
            {/* Sidebar Header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-850/60 bg-[#0f172a]/55">
              <div>
                <h3 className="text-base font-bold text-dark-100 font-display uppercase tracking-wider">Analysis History</h3>
                <p className="text-xs text-dark-500 mt-1 font-mono">Reopen previous report sessions</p>
              </div>
              <button
                onClick={onClose}
                className="text-dark-400 hover:text-dark-100 p-2 rounded-lg hover:bg-dark-850 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* List scroll container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
              {history.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-dark-500 font-mono text-xs py-20">
                  <Cpu className="w-8 h-8 stroke-[1.25] text-dark-600 mb-3 animate-pulse" />
                  <span>No previous analyses recorded.</span>
                </div>
              ) : (
                history.map((item: HistoryItem) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      loadHistoryItem(item);
                      onClose();
                    }}
                    className="group border border-dark-850 hover:border-cyan-500/20 bg-[#0f172a]/40 hover:bg-[#0f172a]/80 rounded-xl p-4 cursor-pointer transition-all duration-200"
                  >
                    {/* Timestamp & Header row */}
                    <div className="flex justify-between items-start mb-2.5 font-mono">
                      <div className="text-[9px] text-dark-500 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-dark-500" />
                        <span>{formatDate(item.timestamp)} @ {formatTimestamp(item.timestamp)}</span>
                      </div>
                      <span className="text-[9px] font-bold text-cyan-400 border border-cyan-500/25 px-2 py-0.5 rounded-lg bg-cyan-950/20 uppercase">
                        {item.taskType}
                      </span>
                    </div>

                    {/* Repository title */}
                    <h4 className="text-sm font-semibold text-dark-200 group-hover:text-cyan-400 truncate mb-1">
                      {item.repositoryName}
                    </h4>
                    <p className="text-xs text-dark-500 truncate mb-3">
                      Owner: {item.repositoryOwner}
                    </p>

                    {/* Meta specifics */}
                    <div className="grid grid-cols-2 gap-2 text-[9px] font-mono text-dark-500 border-t border-dark-850/60 pt-2.5">
                      <div className="flex items-center gap-1.5 truncate">
                        <Cpu className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                        <span className="truncate">{item.provider} ({item.model.split('/').pop()})</span>
                      </div>
                      <div className="flex items-center gap-1.5 justify-end">
                        <Clock className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span>{item.duration.toFixed(2)}s</span>
                      </div>
                    </div>

                    {/* Overlay indicators */}
                    <div className="flex gap-1.5 mt-3">
                      {item.cacheHit && (
                        <span className="text-[8px] font-mono font-bold flex items-center gap-0.5 text-emerald-400 border border-emerald-500/10 px-2 py-0.5 rounded-lg bg-emerald-950/15">
                          <HardDrive className="w-2.5 h-2.5" />
                          <span>CACHE HIT</span>
                        </span>
                      )}
                      {item.fallbackFlag && (
                        <span className="text-[8px] font-mono font-bold flex items-center gap-0.5 text-amber-400 border border-amber-500/10 px-2 py-0.5 rounded-lg bg-amber-950/15">
                          <AlertCircle className="w-2.5 h-2.5" />
                          <span>FALLBACK</span>
                        </span>
                      )}
                      {!item.cacheHit && !item.fallbackFlag && (
                        <span className="text-[8px] font-mono font-bold flex items-center gap-0.5 text-purple-400 border border-purple-500/10 px-2 py-0.5 rounded-lg bg-purple-950/15">
                          <Sparkles className="w-2.5 h-2.5" />
                          <span>LIVE AI</span>
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Sidebar Footer */}
            {history.length > 0 && (
              <div className="p-6 border-t border-dark-850 bg-[#0f172a]/55">
                <button
                  onClick={clearHistory}
                  className="w-full py-3 bg-dark-900 hover:bg-rose-950/20 text-dark-300 hover:text-rose-400 border border-dark-850 hover:border-rose-900/30 rounded-xl font-mono text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all duration-200"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>CLEAR SESSION HISTORY</span>
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
