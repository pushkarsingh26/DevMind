import React from 'react';
import { Loader2 } from 'lucide-react';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  label,
  className = '',
}) => {
  const getSizeClass = () => {
    switch (size) {
      case 'sm':
        return 'w-4 h-4';
      case 'lg':
        return 'w-8 h-8';
      case 'md':
      default:
        return 'w-6 h-6';
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 text-cyan-accent ${className}`}>
      <Loader2 className={`animate-spin shrink-0 ${getSizeClass()}`} />
      {label && (
        <span className="text-[10px] font-mono uppercase tracking-widest font-bold text-dark-400">
          {label}
        </span>
      )}
    </div>
  );
};
