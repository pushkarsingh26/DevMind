import React from 'react';

export interface AvatarProps {
  initials: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  initials,
  size = 'md',
  className = '',
}) => {
  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return 'w-7 h-7 text-[10px] rounded-lg';
      case 'lg':
        return 'w-12 h-12 text-sm rounded-2xl';
      case 'md':
      default:
        return 'w-9 h-9 text-xs rounded-xl';
    }
  };

  return (
    <div
      className={`flex items-center justify-center border border-border-primary bg-gradient-to-r from-purple-accent/10 to-cyan-accent/10 hover:from-purple-accent/20 hover:to-cyan-accent/20 text-cyan-accent font-mono font-bold transition shadow-sm select-none ${getSizeStyles()} ${className}`}
    >
      {initials.toUpperCase()}
    </div>
  );
};
