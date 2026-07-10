import React from 'react';
import { Settings, Cpu, Thermometer, ListFilter, ShieldAlert, KeyRound, Timer, ShieldCheck } from 'lucide-react';
import type { ParsedReport } from '../types';
import { motion } from 'framer-motion';

interface AIConfigurationProps {
  report: ParsedReport | null;
}

export const AIConfiguration: React.FC<AIConfigurationProps> = React.memo(({ report }) => {
  const meta = report?.aiOutput?.ai_metadata;
  
  const config = {
    provider: meta?.provider || 'Google AI Studio',
    model: meta?.model || 'gemini-2.5-flash',
    temperature: '0.2',
    retrievalLimit: '15 chunks',
    maxTokens: '4,096',
    timeout: '30s',
    cacheEnabled: 'Yes (Dynamic self-invalidating)',
    promptVersion: '1.0.0 (Strict Pydantic)'
  };

  const configItems = [
    { label: 'Active LLM Provider', value: config.provider, icon: <Cpu className="w-4 h-4 text-cyan-400" />, glowColor: 'hover:border-cyan-500/20' },
    { label: 'Target Model Identifier', value: config.model, icon: <KeyRound className="w-4 h-4 text-purple-400" />, glowColor: 'hover:border-purple-500/20' },
    { label: 'Generation Temperature', value: config.temperature, icon: <Thermometer className="w-4 h-4 text-amber-400" />, glowColor: 'hover:border-amber-500/20' },
    { label: 'RAG Retrieval Limit', value: config.retrievalLimit, icon: <ListFilter className="w-4 h-4 text-blue-400" />, glowColor: 'hover:border-blue-500/20' },
    { label: 'Max Token Budget', value: config.maxTokens, icon: <ShieldAlert className="w-4 h-4 text-rose-400" />, glowColor: 'hover:border-rose-500/20' },
    { label: 'API Connect Timeout', value: config.timeout, icon: <Timer className="w-4 h-4 text-indigo-400" />, glowColor: 'hover:border-indigo-500/20' },
    { label: 'AI Cache Integration', value: config.cacheEnabled, icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />, glowColor: 'hover:border-emerald-500/20' },
    { label: 'Prompt Engine Version', value: config.promptVersion, icon: <Settings className="w-4 h-4 text-dark-400" />, glowColor: 'hover:border-dark-700/40' }
  ];

  return (
    <div id="settings-config-section" className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-6 shadow-xl space-y-5">
      <div>
        <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
          <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-lg font-mono">06</span>
          <span>SYSTEM & AI CONFIGURATION ENGINE</span>
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">Read-only runtime environment settings configuration</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
        {configItems.map((item, idx) => (
          <motion.div 
            key={idx}
            whileHover={{ y: -2, scale: 1.01 }}
            className={`border border-dark-850 bg-[#070b14]/50 rounded-xl p-4 flex gap-3.5 items-start transition-all duration-200 ${item.glowColor}`}
          >
            <div className="p-2 border border-dark-800 bg-[#0f172a] rounded-lg shrink-0">
              {item.icon}
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-mono text-dark-500 uppercase tracking-wider font-semibold">{item.label}</p>
              <p className="text-xs font-semibold text-dark-200 mt-1 font-mono break-all">{item.value}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
});
