import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  Code2, Folder, FileCode, Package, Shield, 
  CheckCircle2, AlertCircle, Layers, ShieldCheck, Heart, Sparkles 
} from 'lucide-react';
import type { ParsedReport } from '../types';

interface IntelligenceDashboardProps {
  report: ParsedReport | null;
}

export const IntelligenceDashboard: React.FC<IntelligenceDashboardProps> = React.memo(({ report }) => {
  // Calculate dynamic premium metrics
  const scores = useMemo(() => {
    if (!report) return { secScore: 96, health: 100, confidence: 95 };
    const aiOutput = report.aiOutput;
    const meta = aiOutput?.ai_metadata;
    const isFallback = aiOutput?.is_fallback || meta?.fallback_flag;
    const securityIssues = aiOutput?.security_observations?.length || 0;
    const bugIssues = aiOutput?.logical_issues?.length || 0;
    const riskIssues = aiOutput?.risk_areas?.length || 0;

    // 1. Security Score
    const secScore = securityIssues > 0 
      ? Math.max(30, 100 - securityIssues * 15) 
      : 96;
      
    // 2. Repository Health
    const health = Math.max(25, 100 - (bugIssues * 12 + riskIssues * 8 + securityIssues * 10));
    
    // 3. AI Confidence Score
    let confidence = 95;
    if (isFallback) {
      confidence = 60;
    } else {
      if (meta?.cache_hit) confidence = 99;
      if (meta?.retry_count && meta.retry_count > 0) confidence -= (meta.retry_count * 5);
    }

    return { secScore, health, confidence };
  }, [report]);

  if (!report) return null;

  const metadata = report.metadata;
  const stats = report.statistics;
  const repo = report.repository;
  const aiOutput = report.aiOutput;
  const meta = aiOutput?.ai_metadata;

  const dependencyCount = metadata?.dependencies ? Object.keys(metadata.dependencies).length : 0;
  const packageManagersStr = metadata?.package_managers?.join(', ') || 'npm';



  const statsCards = [
    {
      title: 'Primary Language',
      value: metadata?.primary_language || 'TypeScript',
      icon: <Code2 className="w-5 h-5 text-cyan-400" />,
      sub: 'Main codebase source',
      borderColor: 'border-cyan-500/10 hover:border-cyan-500/30'
    },
    {
      title: 'Framework Layout',
      value: metadata?.framework || 'React / Vite',
      icon: <Layers className="w-5 h-5 text-purple-400" />,
      sub: 'Web framework architecture',
      borderColor: 'border-purple-500/10 hover:border-purple-500/30'
    },
    {
      title: 'Total Files',
      value: stats?.total_files?.toLocaleString() || 0,
      icon: <FileCode className="w-5 h-5 text-blue-400" />,
      sub: 'Excluding node_modules',
      borderColor: 'border-blue-500/10 hover:border-blue-500/30'
    },
    {
      title: 'Directories',
      value: stats?.total_directories?.toLocaleString() || 0,
      icon: <Folder className="w-5 h-5 text-indigo-400" />,
      sub: 'Structure index tree',
      borderColor: 'border-indigo-500/10 hover:border-indigo-500/30'
    },
    {
      title: 'Dependencies',
      value: dependencyCount,
      icon: <Package className="w-5 h-5 text-amber-400" />,
      sub: `${packageManagersStr} registry`,
      borderColor: 'border-amber-500/10 hover:border-amber-500/30'
    },
    {
      title: 'License',
      value: metadata?.license || 'MIT License',
      icon: <Shield className="w-5 h-5 text-emerald-400" />,
      sub: 'Usage permission rights',
      borderColor: 'border-emerald-500/10 hover:border-emerald-500/30'
    }
  ];

  const scoreIndicators = [
    {
      label: 'Security Score',
      value: scores.secScore,
      icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
      barColor: 'from-emerald-500 to-teal-400',
      shadowColor: 'rgba(16, 185, 129, 0.2)'
    },
    {
      label: 'Repository Health',
      value: scores.health,
      icon: <Heart className="w-4 h-4 text-rose-400" />,
      barColor: 'from-rose-500 to-purple-500',
      shadowColor: 'rgba(244, 63, 94, 0.2)'
    },
    {
      label: 'AI Confidence Score',
      value: scores.confidence,
      icon: <Sparkles className="w-4 h-4 text-cyan-400" />,
      barColor: 'from-cyan-500 to-indigo-500',
      shadowColor: 'rgba(6, 182, 212, 0.2)'
    }
  ];

  const checklistBadges = [
    { label: 'Test Suite Coverage', active: !!metadata?.tests_present },
    { label: 'Docker Config', active: !!metadata?.docker_support },
    { label: 'CI/CD Pipelines', active: !!metadata?.cicd || !!metadata?.github_actions },
    { label: 'Repository Cache Hit', active: !!repo?.repository_hash },
    { label: 'AI Cache Restored', active: !!meta?.cache_hit }
  ];

  return (
    <div className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-6 shadow-xl space-y-6">
      
      {/* Header telemetry details */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-dark-850 pb-4 gap-2">
        <div>
          <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
            <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-lg font-mono">04</span>
            <span>REPOSITORY INTELLIGENCE DASHBOARD</span>
          </h2>
          <p className="text-xs text-dark-500 font-mono mt-1">Audit statistics for {repo?.owner || 'Unknown'}/{repo?.name || 'Unknown'}</p>
        </div>
        {repo?.repository_hash && (
          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/20 border border-cyan-500/20 px-2.5 py-1 rounded-lg select-all cursor-copy hover:border-cyan-400 transition-colors">
            INDEX HASH: {repo.repository_hash.slice(0, 12)}...
          </span>
        )}
      </div>

      {/* Grid of basic metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statsCards.map((card, idx) => (
          <motion.div
            key={idx}
            whileHover={{ y: -3, scale: 1.01 }}
            className={`bg-[#070b14]/50 border rounded-xl p-4 shadow-lg flex flex-col justify-between min-h-[110px] transition-all duration-200 ${card.borderColor}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[9px] font-mono font-bold text-dark-500 uppercase tracking-wider">{card.title}</span>
              {card.icon}
            </div>
            <div className="mt-3">
              <p className="text-sm font-bold text-dark-100 truncate">{card.value}</p>
              <p className="text-[9px] font-mono text-dark-500 mt-1 truncate leading-none">{card.sub}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Grid of progress score indicators */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 border-t border-dark-850/60 pt-5">
        {scoreIndicators.map((score, idx) => (
          <div key={idx} className="border border-dark-850 bg-[#070b14]/40 rounded-xl p-4.5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-dark-300 font-display flex items-center gap-2">
                {score.icon}
                {score.label}
              </span>
              <span className="text-sm font-bold font-mono text-dark-100">{score.value}%</span>
            </div>

            {/* Score Linear Progress Bar */}
            <div className="w-full bg-[#070b14] h-2 rounded-full overflow-hidden border border-dark-850 p-0.5">
              <motion.div
                className={`h-full rounded-full bg-gradient-to-r ${score.barColor}`}
                initial={{ width: 0 }}
                animate={{ width: `${score.value}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                style={{ boxShadow: `0 0 10px ${score.shadowColor}` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Integration Checklist Badges */}
      <div className="flex flex-wrap gap-2.5 border-t border-dark-850/60 pt-5">
        {checklistBadges.map((badge, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-mono transition-all duration-200 ${
              badge.active
                ? 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.02)]'
                : 'border-dark-800 bg-[#070b14]/30 text-dark-500'
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
});
