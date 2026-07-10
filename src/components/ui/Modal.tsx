import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { GlassPanel } from './GlassPanel';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  className = '',
}) => {
  const getSizeClass = () => {
    switch (size) {
      case 'sm':
        return 'max-w-md';
      case 'lg':
        return 'max-w-2xl';
      case 'xl':
        return 'max-w-4xl';
      case 'md':
      default:
        return 'max-w-lg';
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop Blur overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black cursor-pointer"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 15 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className={`w-full ${getSizeClass()} z-10`}
          >
            <GlassPanel variant="liquid" elevation={3} className={`p-6 overflow-hidden ${className}`}>
              {/* Header */}
              <div className="flex items-center justify-between border-b border-border-primary pb-3.5 mb-4">
                {title ? (
                  <h3 className="text-sm font-bold text-dark-100 font-display uppercase tracking-wider">{title}</h3>
                ) : (
                  <div />
                )}
                <button
                  onClick={onClose}
                  className="p-1 rounded-lg hover:bg-dark-900/60 text-dark-400 hover:text-dark-100 transition cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Body */}
              <div className="text-left">{children}</div>
            </GlassPanel>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
