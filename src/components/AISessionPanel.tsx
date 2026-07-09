import React from 'react';
import { Cpu, HardDrive, Hourglass, Zap, ShieldAlert, FileSearch, RefreshCw, Calendar } from 'lucide-react';
import type { ParsedReport } from '../types';

interface AISessionPanelProps {
  report: ParsedReport | null;
}

export const AISessionPanel: React.FC<AISessionPanelProps> = ({ report }) => {
  if (!report) {
    return (
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 font-mono text-xs text-dark-500 text-center flex flex-col items-center justify-center gap-3">
        <ServerIcon className="w-8 h-8 text-dark-800 animate-pulse" />
        <span>No active session. Run analysis pipeline to establish AI reasoning context.</span>
      </div>
    );
  }

  const aiOutput = report.aiOutput;
  const meta = aiOutput?.ai_metadata;
  const isFallback = aiOutput?.is_fallback || meta?.fallback_flag;
  
  const formatDate = (timestamp?: number) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleString();
  };

  const sessionItems = [
    {
      label: 'Active Provider',
      value: isFallback ? 'None (Local Heuristics)' : meta?.provider_used_after_failover || meta?.provider || 'Unknown',
      icon: <Cpu className="w-4 h-4 text-cyan-400" />
    },
    {
      label: 'Active Model',
      value: isFallback ? 'Mock Heuristic Scanner' : meta?.model || 'Unknown',
      icon: <Zap className="w-4 h-4 text-purple-400" />
    },
    {
      label: 'Response Time',
      value: meta?.latency ? `${meta.latency.toFixed(2)} seconds` : 'N/A',
      icon: <Hourglass className="w-4 h-4 text-amber-400" />
    },
    {
      label: 'Context Chunks Used',
      value: report.chunks ? `${report.chunks.length} chunks` : '0 chunks',
      icon: <FileSearch className="w-4 h-4 text-blue-400" />
    },
    {
      label: 'Repository Cache',
      value: report.repository?.repository_hash ? 'Hit (Hash Indexed)' : 'Miss (Live Scan)',
      icon: <HardDrive className="w-4 h-4 text-indigo-400" />
    },
    {
      label: 'AI Cache Status',
      value: meta?.cache_hit ? 'Hit (JSON Restored)' : 'Miss (LLM Compiling)',
      icon: <RefreshCw className="w-4 h-4 text-emerald-400" />
    },
    {
      label: 'Prompt Version',
      value: '1.0.0 (Strict Types)',
      icon: <ShieldAlert className="w-4 h-4 text-rose-400" />
    },
    {
      label: 'Timestamp',
      value: formatDate(meta?.completed_timestamp),
      icon: <Calendar className="w-4 h-4 text-dark-400" />
    }
  ];

  return (
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-dark-850 pb-4">
        <div>
          <h2 className="text-base font-semibold text-dark-100 font-mono flex items-center gap-2">
            <span>02.</span> AI COGNITIVE SESSION DETAILS
          </h2>
          <p className="text-xs text-dark-500 font-mono mt-1">Real-time session monitoring metrics</p>
        </div>
        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
          isFallback 
            ? 'border-amber-500/20 bg-amber-950/15 text-amber-400' 
            : 'border-emerald-500/20 bg-emerald-950/15 text-emerald-400'
        }`}>
          {isFallback ? 'Fallback Mode' : 'AI Reasoning Active'}
        </span>
      </div>

      {/* Grid displaying indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {sessionItems.map((item, idx) => (
          <div key={idx} className="border border-dark-850 bg-dark-950/40 rounded-lg p-3.5 flex items-center gap-3">
            <div className="p-2 border border-dark-800 bg-dark-900 rounded shrink-0">
              {item.icon}
            </div>
            <div className="truncate min-w-0">
              <span className="text-[9px] font-mono text-dark-500 uppercase font-semibold block">{item.label}</span>
              <span className="text-xs font-semibold text-dark-200 mt-0.5 block truncate font-mono">{item.value}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Repository Hash Bar */}
      {report.repository?.repository_hash && (
        <div className="border border-dark-850 bg-dark-950/20 px-4 py-2.5 rounded font-mono text-[10px] text-dark-500 flex items-center justify-between gap-4">
          <span>REPOSITORY INDEX HASH</span>
          <span className="text-dark-300 font-semibold select-all truncate">{report.repository.repository_hash}</span>
        </div>
      )}
    </div>
  );
};

// Simple visual fallback icon
const ServerIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="20" height="8" x="2" y="2" rx="2" ry="2" />
    <rect width="20" height="8" x="2" y="14" rx="2" ry="2" />
    <line x1="6" x2="6.01" y1="6" y2="6" />
    <line x1="6" x2="6.01" y1="18" y2="18" />
    <line x1="10" x2="10.01" y1="6" y2="6" />
    <line x1="10" x2="10.01" y1="18" y2="18" />
  </svg>
);
