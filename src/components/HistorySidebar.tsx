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
          {/* Dark overlay background */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black z-40 cursor-pointer pointer-events-auto"
          />

          {/* Slide-out Sidebar container */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full sm:w-[420px] bg-dark-950 border-l border-dark-850 shadow-2xl z-50 flex flex-col pointer-events-auto"
          >
            {/* Sidebar Header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-850">
              <div>
                <h3 className="text-base font-semibold text-dark-100 font-mono">ANALYSIS HISTORY</h3>
                <p className="text-xs text-dark-500 mt-1 font-mono">Reopen previous report sessions</p>
              </div>
              <button
                onClick={onClose}
                className="text-dark-400 hover:text-dark-200 p-1.5 rounded hover:bg-dark-900 cursor-pointer transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* List scroll container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {history.length === 0 ? (
                <div className="h-48 flex flex-col items-center justify-center text-center text-dark-500 font-mono text-xs">
                  <Cpu className="w-8 h-8 stroke-[1.25] text-dark-700 mb-3" />
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
                    className="group relative border border-dark-850 hover:border-cyan-500/30 bg-dark-900/60 hover:bg-dark-900 rounded-lg p-4 cursor-pointer transition-all duration-200"
                  >
                    {/* Timestamp & Header row */}
                    <div className="flex justify-between items-start mb-2 font-mono">
                      <div className="text-[10px] text-dark-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(item.timestamp)} @ {formatTimestamp(item.timestamp)}</span>
                      </div>
                      <span className="text-[10px] uppercase font-bold text-cyan-400 border border-cyan-500/20 px-1.5 py-0.5 rounded bg-cyan-950/20">
                        {item.taskType}
                      </span>
                    </div>

                    {/* Repository title */}
                    <h4 className="text-sm font-semibold text-dark-200 group-hover:text-cyan-400 truncate mb-1">
                      {item.repositoryName}
                    </h4>
                    <p className="text-xs text-dark-400 truncate mb-3">
                      Owner: {item.repositoryOwner}
                    </p>

                    {/* Meta specifics */}
                    <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-dark-500 border-t border-dark-850/50 pt-2.5">
                      <div className="flex items-center gap-1.5 truncate">
                        <Cpu className="w-3.5 h-3.5 text-dark-400" />
                        <span>{item.provider} ({item.model.split('/').pop()})</span>
                      </div>
                      <div className="flex items-center gap-1.5 justify-end">
                        <Clock className="w-3.5 h-3.5 text-dark-400" />
                        <span>{item.duration.toFixed(2)}s</span>
                      </div>
                    </div>

                    {/* Overlay indicators */}
                    <div className="flex gap-1.5 mt-2.5">
                      {item.cacheHit && (
                        <span className="text-[9px] font-mono flex items-center gap-0.5 text-emerald-400 border border-emerald-500/10 px-1.5 py-0.5 rounded bg-emerald-950/10">
                          <HardDrive className="w-2.5 h-2.5" />
                          <span>CACHE HIT</span>
                        </span>
                      )}
                      {item.fallbackFlag && (
                        <span className="text-[9px] font-mono flex items-center gap-0.5 text-amber-400 border border-amber-500/10 px-1.5 py-0.5 rounded bg-amber-950/10">
                          <AlertCircle className="w-2.5 h-2.5" />
                          <span>FALLBACK</span>
                        </span>
                      )}
                      {!item.cacheHit && !item.fallbackFlag && (
                        <span className="text-[9px] font-mono flex items-center gap-0.5 text-purple-400 border border-purple-500/10 px-1.5 py-0.5 rounded bg-purple-950/10">
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
              <div className="p-6 border-t border-dark-850">
                <button
                  onClick={clearHistory}
                  className="w-full py-3 bg-dark-900 hover:bg-rose-950/20 text-dark-300 hover:text-rose-400 border border-dark-800 hover:border-rose-900/30 rounded font-mono text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all duration-200"
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
