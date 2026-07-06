import React from 'react';
import { Cpu } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="border-b border-dark-800 bg-dark-900/50 backdrop-blur-md px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-brand-600/10 p-2 rounded-lg border border-brand-500/20 text-brand-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-dark-50 tracking-tight flex items-center gap-2 m-0 p-0 leading-none">
              DevMind
              <span className="text-xs font-normal text-brand-400 px-2 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/25">
                Phase 1
              </span>
            </h1>
            <p className="text-xs text-dark-400 mt-1 font-mono">Multi-Agent Developer Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-dark-400">
          <span>Environment: <span className="text-emerald-400">Mock Mode</span></span>
          <span className="text-dark-700">|</span>
          <span>v0.1.0</span>
        </div>
      </div>
    </header>
  );
};
