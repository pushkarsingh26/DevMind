import React from 'react';

export interface ProgressProps {
  value: number; // 0 to 100
  type?: 'bar' | 'circle';
  size?: number; // for circle type
  strokeWidth?: number; // for circle type
  color?: 'primary' | 'secondary' | 'success';
  className?: string;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  type = 'bar',
  size = 48,
  strokeWidth = 4,
  color = 'primary',
  className = '',
}) => {
  const percentage = Math.min(100, Math.max(0, value));

  const getColorClass = () => {
    switch (color) {
      case 'secondary':
        return 'text-cyan-accent stroke-cyan-accent bg-cyan-accent';
      case 'success':
        return 'text-green-accent stroke-green-accent bg-green-accent';
      case 'primary':
      default:
        return 'text-purple-accent stroke-purple-accent bg-purple-accent';
    }
  };

  if (type === 'circle') {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className={`relative inline-flex items-center justify-center ${className}`}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="stroke-border-primary fill-transparent"
            strokeWidth={strokeWidth}
          />
          {/* Animated active circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className={`fill-transparent transition-all duration-300 ${getColorClass()}`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute text-[10px] font-mono font-bold text-dark-100">{percentage}%</span>
      </div>
    );
  }

  // Horizontal bar type
  const getBGColor = () => {
    switch (color) {
      case 'secondary':
        return 'bg-cyan-accent';
      case 'success':
        return 'bg-green-accent';
      case 'primary':
      default:
        return 'bg-purple-accent';
    }
  };

  return (
    <div className={`w-full bg-border-primary/50 dark:bg-border-primary/20 h-2 rounded-full overflow-hidden p-0.5 border border-border-primary ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-300 ${getBGColor()}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};
