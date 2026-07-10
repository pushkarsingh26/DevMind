import React from 'react';
import { XCircle } from 'lucide-react';
import { GlassPanel } from './GlassPanel';
import { Button } from './Button';

export interface ErrorStateProps {
  title: string;
  description: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  description,
  onRetry,
  className = '',
}) => {
  return (
    <GlassPanel
      variant="liquid"
      elevation={2}
      className={`flex flex-col items-center justify-center text-center p-8 border border-rose-500/20 bg-rose-500/5 rounded-2xl select-none ${className}`}
    >
      <div className="p-3.5 bg-rose-500/10 rounded-full border border-rose-500/20 text-rose-500 mb-4 shadow-sm">
        <XCircle className="w-8 h-8" />
      </div>
      <h3 className="text-sm font-bold text-rose-400 font-display uppercase tracking-wider">
        {title}
      </h3>
      <p className="text-xs text-dark-400 font-sans mt-2 max-w-sm leading-relaxed">
        {description}
      </p>
      {onRetry && (
        <div className="mt-5">
          <Button variant="secondary" className="border-rose-500/30 text-rose-400 bg-rose-500/10 hover:bg-rose-500/25" onClick={onRetry}>
            RETRY ACTION
          </Button>
        </div>
      )}
    </GlassPanel>
  );
};
