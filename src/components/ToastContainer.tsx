import { useContext, memo } from 'react';
import { AnalysisUIContext } from '../context/AnalysisContext';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react';

export const ToastContainer = memo(() => {
  const context = useContext(AnalysisUIContext);
  if (!context) return null;

  const { toasts, removeToast } = context;

  const icons = {
    success: <CheckCircle2 className="w-4.5 h-4.5 text-emerald-400 shrink-0 mt-0.5" />,
    info: <Info className="w-4.5 h-4.5 text-cyan-400 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-4.5 h-4.5 text-amber-400 shrink-0 mt-0.5" />,
    error: <XCircle className="w-4.5 h-4.5 text-rose-500 shrink-0 mt-0.5" />,
  };

  const titles = {
    success: 'Success Response',
    info: 'System Telemetry',
    warning: 'Action Warning',
    error: 'Execution Error',
  };

  const borderStyles = {
    success: 'border-emerald-500/20 bg-[#0f172a]/90 shadow-[0_4px_20px_rgba(16,185,129,0.08)] text-dark-100',
    info: 'border-cyan-500/20 bg-[#0f172a]/90 shadow-[0_4px_20px_rgba(6,182,212,0.08)] text-dark-100',
    warning: 'border-amber-500/20 bg-[#0f172a]/90 shadow-[0_4px_20px_rgba(245,158,11,0.08)] text-dark-100',
    error: 'border-rose-500/20 bg-[#0f172a]/90 shadow-[0_4px_20px_rgba(244,63,94,0.08)] text-dark-100',
  };

  return (
    <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-3.5 max-w-sm w-full pointer-events-none select-none">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 40, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9, transition: { duration: 0.15 } }}
            className={`pointer-events-auto border rounded-2xl p-4 shadow-2xl backdrop-blur-xl flex items-start gap-3.5 justify-between ${borderStyles[toast.type]}`}
          >
            <div className="flex items-start gap-3">
              {icons[toast.type]}
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-dark-400 block leading-none mb-1">
                  {titles[toast.type]}
                </span>
                <div className="text-xs font-sans leading-relaxed text-dark-200">{toast.message}</div>
              </div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-dark-500 hover:text-dark-200 p-1 rounded-lg hover:bg-dark-850 shrink-0 cursor-pointer transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
});
