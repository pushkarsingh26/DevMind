import type { AgentStatus } from '../types';
import { Circle, RotateCw, CheckCircle2, AlertTriangle } from 'lucide-react';

interface StatusCardProps {
  agentName: string;
  status: AgentStatus;
  message: string;
}

export const StatusCard: React.FC<StatusCardProps> = ({ agentName, status, message }) => {
  const getStatusStyles = () => {
    switch (status) {
      case 'processing':
        return {
          bg: 'bg-blue-950/20 border-blue-900/40',
          badge: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
          text: 'text-blue-300',
          icon: <RotateCw className="w-4 h-4 text-blue-400" />,
          label: 'PROCESSING',
        };
      case 'completed':
        return {
          bg: 'bg-emerald-950/20 border-emerald-900/40',
          badge: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          text: 'text-emerald-300',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
          label: 'COMPLETED',
        };
      case 'failed':
        return {
          bg: 'bg-rose-950/20 border-rose-900/40',
          badge: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          text: 'text-rose-300',
          icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
          label: 'FAILED',
        };
      case 'waiting':
      default:
        return {
          bg: 'bg-dark-900 border-dark-800',
          badge: 'bg-dark-950 border-dark-800 text-dark-500',
          text: 'text-dark-400',
          icon: <Circle className="w-4 h-4 text-dark-600" />,
          label: 'WAITING',
        };
    }
  };

  const styles = getStatusStyles();

  return (
    <div className={`border rounded-lg p-5 font-mono flex flex-col justify-between ${styles.bg}`}>
      <div className="flex items-center justify-between gap-4 mb-3">
        <span className="text-xs font-semibold text-dark-200 uppercase tracking-wider">
          {agentName}
        </span>
        <span className={`text-[10px] font-bold px-2 py-0.5 border rounded-full flex items-center gap-1.5 ${styles.badge}`}>
          {styles.icon}
          {styles.label}
        </span>
      </div>
      <p className={`text-xs leading-relaxed truncate ${styles.text}`}>
        {message}
      </p>
    </div>
  );
};
