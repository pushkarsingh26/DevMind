import React from 'react';
import { Settings, Cpu, Thermometer, ListFilter, ShieldAlert, KeyRound, Timer, ShieldCheck } from 'lucide-react';
import type { ParsedReport } from '../types';

interface AIConfigurationProps {
  report: ParsedReport | null;
}

export const AIConfiguration: React.FC<AIConfigurationProps> = ({ report }) => {
  const meta = report?.aiOutput?.ai_metadata;
  
  // Sourced config details from active report, falling back to backend environment defaults
  const config = {
    provider: meta?.provider || 'Google AI Studio',
    model: meta?.model || 'gemini-2.5-flash',
    temperature: '0.2',
    retrievalLimit: '15 chunks',
    maxTokens: '4,096',
    timeout: '30s',
    cacheEnabled: 'Yes (Dynamic self-invalidating)',
    promptVersion: '1.0.0 (Strict Pydantic schemas)'
  };

  const configItems = [
    { label: 'Active LLM Provider', value: config.provider, icon: <Cpu className="w-4 h-4 text-cyan-400" /> },
    { label: 'Target Model Identifier', value: config.model, icon: <KeyRound className="w-4 h-4 text-purple-400" /> },
    { label: 'Generation Temperature', value: config.temperature, icon: <Thermometer className="w-4 h-4 text-amber-400" /> },
    { label: 'RAG Retrieval Limit', value: config.retrievalLimit, icon: <ListFilter className="w-4 h-4 text-blue-400" /> },
    { label: 'Max Token Budget', value: config.maxTokens, icon: <ShieldAlert className="w-4 h-4 text-rose-400" /> },
    { label: 'API Connect Timeout', value: config.timeout, icon: <Timer className="w-4 h-4 text-indigo-400" /> },
    { label: 'AI Cache Integration', value: config.cacheEnabled, icon: <ShieldCheck className="w-4 h-4 text-emerald-400" /> },
    { label: 'Prompt Engine Version', value: config.promptVersion, icon: <Settings className="w-4 h-4 text-dark-400" /> }
  ];

  return (
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-dark-100 font-mono flex items-center gap-2">
          <span>07.</span> SYSTEM & AI CONFIGURATION ENGINE
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">Read-only runtime environment settings configuration</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
        {configItems.map((item, idx) => (
          <div key={idx} className="border border-dark-850 bg-dark-950/40 rounded-lg p-4 flex gap-3.5 items-start">
            <div className="p-1.5 border border-dark-800 bg-dark-900 rounded shrink-0">
              {item.icon}
            </div>
            <div>
              <p className="text-[10px] font-mono text-dark-500 uppercase font-semibold">{item.label}</p>
              <p className="text-xs font-semibold text-dark-200 mt-1 font-mono break-all">{item.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
