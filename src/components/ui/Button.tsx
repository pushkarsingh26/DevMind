import React from 'react';
import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import type { HTMLMotionProps } from 'framer-motion';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  children?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'glass' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  glow?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'glass',
  size = 'md',
  loading = false,
  glow = false,
  disabled = false,
  className = '',
  type = 'button',
  ...props
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return 'bg-gradient-to-r from-purple-accent to-cyan-accent text-dark-950 font-bold border-none hover:brightness-110';
      case 'secondary':
        return 'bg-cyan-accent/15 border border-cyan-accent/20 text-cyan-accent hover:bg-cyan-accent/25';
      case 'danger':
        return 'bg-rose-500/10 border border-rose-500/20 text-rose-500 hover:bg-rose-500 hover:text-white';
      case 'ghost':
        return 'bg-transparent hover:bg-dark-900/40 text-dark-300 hover:text-dark-100 border-none';
      case 'glass':
      default:
        return 'glass-lvl2 bg-panel hover:bg-panel-solid text-dark-200 border-border-primary hover:text-dark-50';
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return 'px-3 py-1.5 text-[10px] font-mono rounded-lg';
      case 'lg':
        return 'px-6 py-3.5 text-sm font-semibold rounded-xl';
      case 'md':
      default:
        return 'px-4.5 py-2.5 text-xs font-semibold rounded-xl';
    }
  };

  const getGlowStyles = () => {
    if (!glow || disabled || loading) return '';
    if (variant === 'primary') {
      return 'shadow-[0_0_20px_rgba(168,85,247,0.3)] hover:shadow-[0_0_25px_rgba(168,85,247,0.45)]';
    }
    return 'shadow-glow-cyan';
  };

  return (
    <motion.button
      type={type}
      disabled={disabled || loading}
      whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
      transition={{ duration: 0.15 }}
      className={`liquid-btn font-sans uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer select-none transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed ${getVariantStyles()} ${getSizeStyles()} ${getGlowStyles()} ${className}`}
      {...props}
    >
      {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
      <span>{children}</span>
    </motion.button>
  );
};
