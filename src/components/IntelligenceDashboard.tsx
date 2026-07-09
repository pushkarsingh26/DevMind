import React from 'react';
import { motion } from 'framer-motion';
import { 
  Code2, Folder, FileCode, Package, Shield, 
  CheckCircle2, AlertCircle, Layers 
} from 'lucide-react';
import type { ParsedReport } from '../types';

interface IntelligenceDashboardProps {
  report: ParsedReport | null;
}

export const IntelligenceDashboard: React.FC<IntelligenceDashboardProps> = ({ report }) => {
  if (!report) return null;

  const metadata = report.metadata;
  const stats = report.statistics;
  const repo = report.repository;
  const aiOutput = report.aiOutput;
  const meta = aiOutput?.ai_metadata;

  const dependencyCount = metadata?.dependencies ? Object.keys(metadata.dependencies).length : 0;
  const packageManagersStr = metadata?.package_managers?.join(', ') || 'None';
  
  const cards = [
    {
      title: 'Primary Language',
      value: metadata?.primary_language || 'Unknown',
      icon: <Code2 className="w-5 h-5 text-cyan-400" />,
      glow: 'shadow-cyan-950/20 border-cyan-500/10'
    },
    {
      title: 'Framework Layout',
      value: metadata?.framework || 'None',
      icon: <Layers className="w-5 h-5 text-purple-400" />,
      glow: 'shadow-purple-950/20 border-purple-500/10'
    },
    {
      title: 'Total Files',
      value: stats?.total_files || 0,
      icon: <FileCode className="w-5 h-5 text-blue-400" />,
      glow: 'shadow-blue-950/20 border-blue-500/10'
    },
    {
      title: 'Total Directories',
      value: stats?.total_directories || 0,
      icon: <Folder className="w-5 h-5 text-indigo-400" />,
      glow: 'shadow-indigo-950/20 border-indigo-500/10'
    },
    {
      title: 'Dependencies Detected',
      value: dependencyCount,
      sub: `${packageManagersStr} manager`,
      icon: <Package className="w-5 h-5 text-amber-400" />,
      glow: 'shadow-amber-950/20 border-amber-500/10'
    },
    {
      title: 'License',
      value: metadata?.license || 'None',
      icon: <Shield className="w-5 h-5 text-emerald-400" />,
      glow: 'shadow-emerald-950/20 border-emerald-500/10'
    }
  ];

  const badges = [
    { label: 'Test Suite', active: !!metadata?.tests_present },
    { label: 'Docker Config', active: !!metadata?.docker_support },
    { label: 'CI/CD Pipelines', active: !!metadata?.cicd || !!metadata?.github_actions },
    { label: 'Repository Cache', active: !!repo?.repository_hash },
    { label: 'AI Cache Saved', active: !!meta?.cache_hit || (meta?.cache_hit === false && !aiOutput?.is_fallback) }
  ];

  return (
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-dark-850 pb-4">
        <div>
          <h2 className="text-base font-semibold text-dark-100 font-mono flex items-center gap-2">
            <span>04.</span> REPOSITORY INTELLIGENCE DASHBOARD
          </h2>
          <p className="text-xs text-dark-500 font-mono mt-1">Audit statistics for {repo?.owner || 'Unknown'}/{repo?.name || 'Unknown'}</p>
        </div>
        {repo?.repository_hash && (
          <span className="text-[10px] font-mono text-dark-500 bg-dark-950 border border-dark-850 px-2.5 py-1 rounded select-all cursor-copy hover:border-dark-700 transition-colors">
            HASH: {repo.repository_hash.slice(0, 12)}...
          </span>
        )}
      </div>

      {/* Grid of stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {cards.map((card, idx) => (
          <motion.div
            key={idx}
            whileHover={{ y: -3, scale: 1.01 }}
            className={`bg-dark-950/40 border rounded-lg p-4 shadow-lg flex flex-col justify-between ${card.glow}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono font-bold text-dark-500 uppercase">{card.title}</span>
              {card.icon}
            </div>
            <div className="mt-2">
              <p className="text-base font-bold text-dark-100 truncate">{card.value}</p>
              {card.sub && <p className="text-[9px] font-mono text-dark-500 mt-0.5 truncate">{card.sub}</p>}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Integration checklist badges */}
      <div className="flex flex-wrap gap-3 border-t border-dark-850/50 pt-5">
        {badges.map((badge, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[11px] font-mono ${
              badge.active
                ? 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400'
                : 'border-dark-800 bg-dark-950/20 text-dark-500'
            }`}
          >
            {badge.active ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
            <span>{badge.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
