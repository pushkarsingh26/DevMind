import React, { useContext } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const context = useContext(AnalysisContext);
  if (!context) return null;

  const { toasts, removeToast } = context;

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />,
    info: <Info className="w-5 h-5 text-cyan-400 shrink-0" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
    error: <XCircle className="w-5 h-5 text-rose-500 shrink-0" />,
  };

  const borderStyles = {
    success: 'border-emerald-500/25 bg-emerald-950/20 shadow-emerald-950/20 text-emerald-200',
    info: 'border-cyan-500/25 bg-cyan-950/20 shadow-cyan-950/20 text-cyan-200',
    warning: 'border-amber-500/25 bg-amber-950/20 shadow-amber-950/20 text-amber-200',
    error: 'border-rose-500/25 bg-rose-950/20 shadow-rose-950/20 text-rose-200',
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9, transition: { duration: 0.2 } }}
            className={`pointer-events-auto border rounded-lg p-4 shadow-xl backdrop-blur-md flex items-start gap-3 justify-between ${borderStyles[toast.type]}`}
          >
            <div className="flex items-start gap-3">
              {icons[toast.type]}
              <div className="text-xs font-mono font-medium pt-0.5">{toast.message}</div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-dark-500 hover:text-dark-300 p-0.5 rounded hover:bg-dark-850 shrink-0 cursor-pointer transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
