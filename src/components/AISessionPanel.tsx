import React from 'react';
import { Cpu, HardDrive, Hourglass, Zap, ShieldCheck, FileSearch, RefreshCw, Calendar, Terminal } from 'lucide-react';
import type { ParsedReport } from '../types';
import { motion } from 'framer-motion';

interface AISessionPanelProps {
  report: ParsedReport | null;
}

export const AISessionPanel: React.FC<AISessionPanelProps> = React.memo(({ report }) => {
  if (!report) {
    return (
      <div className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-8 text-center flex flex-col items-center justify-center gap-4 min-h-[180px] shadow-lg">
        <div className="w-12 h-12 rounded-xl bg-dark-900 border border-dark-800 flex items-center justify-center text-dark-500 animate-pulse">
          <Terminal className="w-6 h-6" />
        </div>
        <div>
          <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold">SESSION TELEMETRY STANDBY</span>
          <p className="text-xs text-dark-500 mt-1 max-w-sm mx-auto font-sans leading-relaxed">
            Run the analysis agent pipeline to establish and stream live cognitive session metrics.
          </p>
        </div>
      </div>
    );
  }

  const aiOutput = report.aiOutput;
  const meta = aiOutput?.ai_metadata;
  const isFallback = aiOutput?.is_fallback || meta?.fallback_flag;
  
  const formatDate = (timestamp?: number) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + new Date(timestamp * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const sessionItems = [
    {
      label: 'Active Provider',
      value: isFallback ? 'Local Heuristics' : meta?.provider_used_after_failover || meta?.provider || 'Direct AI',
      icon: <Cpu className="w-4 h-4 text-cyan-400" />,
      borderGlow: 'hover:border-cyan-500/20'
    },
    {
      label: 'Active Model',
      value: isFallback ? 'Mock Scanner' : meta?.model?.split('/').pop() || 'Static Analyzer',
      icon: <Zap className="w-4 h-4 text-purple-400" />,
      borderGlow: 'hover:border-purple-500/20'
    },
    {
      label: 'Response Time',
      value: meta?.latency ? `${meta.latency.toFixed(2)}s` : 'N/A',
      icon: <Hourglass className="w-4 h-4 text-amber-400" />,
      borderGlow: 'hover:border-amber-500/20'
    },
    {
      label: 'Context Chunks',
      value: report.chunks ? `${report.chunks.length} chunks` : '0 chunks',
      icon: <FileSearch className="w-4 h-4 text-blue-400" />,
      borderGlow: 'hover:border-blue-500/20'
    },
    {
      label: 'Repository Cache',
      value: report.repository?.repository_hash ? 'Hit (Indexed)' : 'Miss (Live Scan)',
      icon: <HardDrive className="w-4 h-4 text-indigo-400" />,
      borderGlow: 'hover:border-indigo-500/20'
    },
    {
      label: 'AI Cache Status',
      value: meta?.cache_hit ? 'Hit (Restored)' : 'Miss (Compiling)',
      icon: <RefreshCw className="w-4 h-4 text-emerald-400" />,
      borderGlow: 'hover:border-emerald-500/20'
    },
    {
      label: 'Prompt Version',
      value: '1.0.0 (Strict)',
      icon: <ShieldCheck className="w-4 h-4 text-rose-400" />,
      borderGlow: 'hover:border-rose-500/20'
    },
    {
      label: 'Timestamp',
      value: formatDate(meta?.completed_timestamp),
      icon: <Calendar className="w-4 h-4 text-dark-400" />,
      borderGlow: 'hover:border-dark-700/40'
    }
  ];

  return (
    <div className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-6 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-dark-850 pb-4">
        <div>
          <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
            <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-lg font-mono">03</span>
            <span>AI COGNITIVE SESSION DETAILS</span>
          </h2>
          <p className="text-xs text-dark-500 font-mono mt-1">Real-time session monitoring metrics</p>
        </div>
        <span className={`text-[9px] font-mono font-bold px-2 py-1 rounded-lg border uppercase tracking-wider ${
          isFallback 
            ? 'border-amber-500/20 bg-amber-950/15 text-amber-400' 
            : 'border-emerald-500/20 bg-emerald-950/15 text-emerald-400'
        }`}>
          {isFallback ? 'Fallback Mode' : 'AI Reasoning Active'}
        </span>
      </div>

      {/* Grid of details */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {sessionItems.map((item, idx) => (
          <motion.div 
            key={idx}
            whileHover={{ y: -2, scale: 1.01 }}
            className={`border border-dark-850 bg-[#070b14]/50 rounded-xl p-3.5 flex items-center gap-3.5 transition-all duration-200 ${item.borderGlow}`}
          >
            <div className="p-2 border border-dark-800 bg-[#0f172a] rounded-lg shrink-0">
              {item.icon}
            </div>
            <div className="truncate min-w-0">
              <span className="text-[9px] font-mono text-dark-500 uppercase tracking-wider block">{item.label}</span>
              <span className="text-xs font-semibold text-dark-200 mt-0.5 block truncate font-mono">{item.value}</span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Repository Hash Bar */}
      {report.repository?.repository_hash && (
        <div className="border border-dark-850 bg-[#070b14]/40 px-4 py-2.5 rounded-xl font-mono text-[10px] text-dark-500 flex items-center justify-between gap-4">
          <span className="font-semibold tracking-wider text-[9px] uppercase">Repository Index Hash</span>
          <span className="text-dark-300 font-semibold select-all truncate">{report.repository.repository_hash}</span>
        </div>
      )}
    </div>
  );
});
