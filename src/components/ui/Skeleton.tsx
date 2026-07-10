import React from 'react';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rect',
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'circle':
        return 'rounded-full';
      case 'text':
        return 'rounded h-3 w-3/4 mb-2';
      case 'rect':
      default:
        return 'rounded-xl';
    }
  };

  return (
    <div
      className={`bg-border-primary/50 dark:bg-border-primary/20 relative overflow-hidden shimmer ${getVariantStyles()} ${className}`}
    >
      <div className="absolute inset-0 shimmer-mask" />
    </div>
  );
};
