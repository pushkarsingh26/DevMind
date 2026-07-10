import React from 'react';
import { GlassPanel } from './GlassPanel';
import { motion } from 'framer-motion';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'liquid' | 'soft' | 'solid';
  elevation?: 1 | 2 | 3;
  interactive?: boolean;
  glowColor?: 'cyan' | 'purple' | 'none';
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'soft',
  elevation = 2,
  interactive = false,
  glowColor = 'none',
  className = '',
  ...props
}) => {
  const getGlowClass = () => {
    if (glowColor === 'cyan') {
      return 'border-cyan-glow/40 shadow-glow-cyan';
    }
    if (glowColor === 'purple') {
      return 'border-purple-glow/40 shadow-glow-purple';
    }
    return '';
  };

  const content = (
    <GlassPanel
      variant={variant}
      elevation={elevation}
      interactive={interactive}
      className={`p-6 ${getGlowClass()} ${className}`}
      {...props}
    >
      {children}
    </GlassPanel>
  );

  if (interactive) {
    return (
      <motion.div
        whileHover={{ scale: 1.01, y: -2 }}
        whileTap={{ scale: 0.99, y: 0.5 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
      >
        {content}
      </motion.div>
    );
  }

  return content;
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => (
  <div className={`mb-4 flex items-center justify-between gap-4 border-b border-border-primary pb-3.5 ${className}`} {...props}>
    {children}
  </div>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => (
  <div className={className} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => (
  <div className={`mt-4 pt-3.5 border-t border-border-primary flex items-center justify-between gap-4 ${className}`} {...props}>
    {children}
  </div>
);
