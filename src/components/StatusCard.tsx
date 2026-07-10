import React from 'react';
import type { AgentStatus } from '../types';
import { motion } from 'framer-motion';
import { Circle, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

interface StatusCardProps {
  agentName: string;
  status: AgentStatus;
  message: string;
}

export const StatusCard: React.FC<StatusCardProps> = React.memo(({ agentName, status, message }) => {
  const getStatusStyles = () => {
    switch (status) {
      case 'processing':
        return {
          bg: 'bg-cyan-950/15 border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.1)]',
          badge: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400',
          text: 'text-cyan-200/90',
          icon: <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />,
          label: 'PROCESSING',
        };
      case 'completed':
        return {
          bg: 'bg-emerald-950/10 border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.05)]',
          badge: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
          text: 'text-emerald-300/80',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
          label: 'COMPLETED',
        };
      case 'failed':
        return {
          bg: 'bg-rose-950/15 border-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.1)]',
          badge: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
          text: 'text-rose-300/80',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />,
          label: 'FAILED',
        };
      case 'waiting':
      default:
        return {
          bg: 'bg-dark-950/20 border-border-primary shadow-none',
          badge: 'bg-dark-900/30 border-border-primary text-dark-500',
          text: 'text-dark-500',
          icon: <Circle className="w-3 h-3 text-dark-600 fill-dark-950" />,
          label: 'STANDBY',
        };
    }
  };

  const styles = getStatusStyles();

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`border rounded-2xl p-5 flex flex-col justify-between h-32 relative overflow-hidden transition-all duration-300 ${styles.bg}`}
    >
      {/* Laser line animation for processing states */}
      {status === 'processing' && (
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-cyan-500/0 via-cyan-500/5 to-cyan-500/0"
          animate={{ x: ['-100%', '100%'] }}
          transition={{ repeat: Infinity, duration: 2.2, ease: 'linear' }}
        />
      )}

      <div className="flex items-start justify-between gap-4 mb-2 z-10">
        <span className="text-xs font-bold text-dark-200 font-display tracking-wider uppercase">
          {agentName}
        </span>
        <span className={`text-[9px] font-bold px-2 py-0.5 border rounded-lg flex items-center gap-1.5 shrink-0 font-mono ${styles.badge}`}>
          {styles.icon}
          {styles.label}
        </span>
      </div>
      
      <p className={`text-xs mt-auto z-10 leading-relaxed font-mono truncate max-w-full ${styles.text}`} title={message}>
        {message}
      </p>
    </motion.div>
  );
});
