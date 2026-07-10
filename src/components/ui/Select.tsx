import React from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options?: Array<{ value: string; label: string }>;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options = [], className = '', children, ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5 text-left relative">
        {label && (
          <label className="block text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold">
            {label}
          </label>
        )}
        
        <div className="relative w-full">
          <select
            ref={ref}
            className={`w-full bg-[#070b14]/50 dark:bg-[#070b14]/80 border border-border-primary hover:border-dark-700/80 focus:border-cyan-accent rounded-xl px-4 py-2.5 text-xs text-dark-200 outline-none transition-all duration-200 font-sans cursor-pointer appearance-none ${
              error ? 'border-rose-500/50' : ''
            } ${className}`}
            {...props}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-panel-solid text-dark-200">
                {opt.label}
              </option>
            ))}
            {children}
          </select>
          <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400 pointer-events-none" />
        </div>

        {error && (
          <span className="block text-[9px] font-mono text-rose-500 leading-none">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';
