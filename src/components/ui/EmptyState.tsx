import React from 'react';
import { AlertCircle } from 'lucide-react';
import { GlassPanel } from './GlassPanel';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon = <AlertCircle className="w-8 h-8 text-dark-500" />,
  action,
  className = '',
}) => {
  return (
    <GlassPanel
      variant="soft"
      elevation={2}
      className={`flex flex-col items-center justify-center text-center p-8 border border-border-primary rounded-2xl select-none ${className}`}
    >
      <div className="p-4 bg-border-primary/20 rounded-full border border-border-primary/50 text-dark-400 mb-4 shadow-inner">
        {icon}
      </div>
      <h3 className="text-sm font-bold text-dark-200 font-display uppercase tracking-wider">
        {title}
      </h3>
      <p className="text-xs text-dark-400 font-sans mt-2 max-w-sm leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </GlassPanel>
  );
};
