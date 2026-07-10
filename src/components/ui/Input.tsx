import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label className="block text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full bg-[#070b14]/50 dark:bg-[#070b14]/80 border border-border-primary hover:border-dark-700/80 focus:border-cyan-accent focus:ring-1 focus:ring-cyan-accent/20 rounded-xl px-4 py-2.5 text-xs text-dark-200 outline-none transition-all duration-200 font-sans placeholder-dark-600 ${
            error ? 'border-rose-500/50 focus:border-rose-500 focus:ring-rose-500/20' : ''
          } ${className}`}
          {...props}
        />
        {error && (
          <span className="block text-[9px] font-mono text-rose-500 leading-none">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
