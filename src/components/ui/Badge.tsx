import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'neutral';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  className = '',
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return 'border-purple-accent/25 text-purple-accent bg-purple-accent/10';
      case 'secondary':
        return 'border-cyan-accent/25 text-cyan-accent bg-cyan-accent/10';
      case 'success':
        return 'border-green-accent/25 text-green-accent bg-green-accent/10';
      case 'warning':
        return 'border-amber-accent/25 text-amber-accent bg-amber-accent/10';
      case 'danger':
        return 'border-red-accent/25 text-red-accent bg-red-accent/10';
      case 'neutral':
      default:
        return 'border-gray-accent/25 text-gray-accent bg-gray-accent/10';
    }
  };

  return (
    <span
      className={`inline-flex items-center justify-center border rounded-lg px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider ${getVariantStyles()} ${className}`}
    >
      {children}
    </span>
  );
};
