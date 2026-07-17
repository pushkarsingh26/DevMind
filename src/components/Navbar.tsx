import { useContext, useState, useRef, useEffect, useMemo, useCallback, memo } from 'react';
import { Menu, Sun, Moon, LogOut, KeyRound, Cpu, ChevronDown } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnalysisContext, AnalysisUIContext } from '../context/AnalysisContext';
import { useWorkflow } from '../context/WorkflowContext';
import { DevMindLogo } from '../layouts/MainLayout';
import { motion, AnimatePresence } from 'framer-motion';
import { Avatar, GlassPanel } from './ui';

interface NavbarProps {
  onOpenMobileSidebar?: () => void;
}

// Static map � no closure, computed once at module load
const PAGE_TITLES: Record<string, string> = {
  '/dashboard':    'Dashboard Overview',
  '/repositories': 'Repository Analysis',
  '/chat':         'Grounded Assistant',
  '/agents':       'Agent Workspace',
  '/graph':        'Knowledge Graph',
  '/reports':      'Interactive Audit Reports',
  '/history':      'Platform History Logs',
  '/settings':     'Intelligence Settings',
  '/future':       'Roadmap Blueprint',
};

const fallbackToggleTheme = () => {};
const fallbackAddToast = () => {};

export const Navbar = memo<NavbarProps>(({ onOpenMobileSidebar }) => {
  const dataContext = useContext(AnalysisContext);
  const uiContext   = useContext(AnalysisUIContext);
  const location    = useLocation();
  const navigate    = useNavigate();

  const { runningWorkflows, setActiveWorkflowId, setSelectedWorkflowId } = useWorkflow();
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);
  const widgetRef = useRef<HTMLDivElement>(null);

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close widget dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (widgetRef.current && !widgetRef.current.contains(e.target as Node)) {
        setIsWidgetOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside, { passive: true });
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleWidgetClick = useCallback((id: string) => {
    setActiveWorkflowId(id);
    setSelectedWorkflowId(id);
    setIsWidgetOpen(false);
    navigate('/agents');
  }, [setActiveWorkflowId, setSelectedWorkflowId, navigate]);

  // Close profile dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside, { passive: true });
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Read from UI context (theme)  isolated, doesn't trigger on data changes
  const theme       = uiContext?.theme       || 'dark';
  const toggleTheme = uiContext?.toggleTheme || fallbackToggleTheme;
  const addToast    = uiContext?.addToast    || fallbackAddToast;

  // Read only the fields we need from data context
  const parsedReport = dataContext?.parsedReport;
  const isAnalyzing  = dataContext?.isAnalyzing || false;

  // Memoized derived values  recompute only when dependencies change
  const pageTitle = useMemo(
    () => PAGE_TITLES[location.pathname] || 'DevMind Console',
    [location.pathname]
  );

  const activeProvider = useMemo(
    () => parsedReport?.aiOutput?.ai_metadata?.provider || 'GOOGLE AI',
    [parsedReport]
  );

  const activeModel = useMemo(
    () => (parsedReport?.aiOutput?.ai_metadata?.model?.split('/').pop() || 'gemini-2.5-flash'),
    [parsedReport]
  );

  const handleToggleProfile = useCallback(() => setIsProfileOpen(prev => !prev), []);

  const handleSessionLock = useCallback(() => {
    setIsProfileOpen(false);
    addToast('info', 'Developer security keys are locked.');
  }, [addToast]);

  return (
    <header className="sticky top-0 z-30 w-full px-5 py-3.5 border-b border-border-primary/80 bg-[#070b14]/50 dark:bg-[#070b14]/70 backdrop-blur-md select-none print:hidden">
      <div className="w-full flex items-center justify-between gap-4">

        {/* Left: Hamburger + Logo + Route Title */}
        <div className="flex items-center gap-3.5 truncate min-w-0">
          <button
            onClick={onOpenMobileSidebar}
            className="md:hidden p-2 border border-border-primary hover:border-dark-700 bg-dark-900/40 rounded-xl text-dark-300 hover:text-dark-100 cursor-pointer"
            title="Open navigation menu"
          >
            <Menu className="w-4 h-4" />
          </button>

          <div className="flex md:hidden items-center gap-2 shrink-0">
            <DevMindLogo className="w-6 h-6 shadow-[0_0_10px_rgba(6,182,212,0.1)]" />
          </div>

          <span className="hidden md:inline-block w-px h-4 bg-border-primary" />

          <h2 className="text-sm font-bold text-dark-100 font-display truncate leading-none">
            {pageTitle}
          </h2>
        </div>

        {/* Center: Telemetry */}
        <div className="hidden lg:flex items-center gap-4 text-[9px] font-mono border border-border-primary/80 bg-[#070b14]/30 px-3 py-1.5 rounded-xl shrink-0">
          <div className="flex items-center gap-1.5 text-dark-400">
            <Cpu className="w-3.5 h-3.5 text-cyan-accent shrink-0" />
            <span>AI CORE:</span>
            <span className="text-dark-200 font-bold">{activeProvider.toUpperCase()}</span>
          </div>
          <span className="w-px h-3 bg-border-primary" />
          <div className="flex items-center gap-1.5 text-dark-400">
            <KeyRound className="w-3.5 h-3.5 text-purple-accent shrink-0" />
            <span>MODEL:</span>
            <span className="text-dark-200 font-bold">{activeModel.toUpperCase()}</span>
          </div>
          {isAnalyzing && (
            <>
              <span className="w-px h-3 bg-border-primary" />
              <span className="w-2 h-2 rounded-full bg-cyan-accent animate-ping shrink-0" />
            </>
          )}
        </div>

        {/* Right: Theme + Profile */}
        <div className="flex items-center gap-3 shrink-0">
          {isAnalyzing && <span className="lg:hidden w-2 h-2 rounded-full bg-cyan-accent animate-ping" />}

          {/* Running Tasks Widget */}
          {runningWorkflows.length > 0 && (
            <div className="relative" ref={widgetRef}>
              <button
                onClick={() => setIsWidgetOpen(prev => !prev)}
                className="flex items-center gap-2 px-3 py-2 border border-emerald-500/30 hover:border-emerald-500/50 bg-emerald-500/5 hover:bg-emerald-500/10 text-emerald-400 font-mono text-[10px] font-bold rounded-xl transition cursor-pointer select-none"
                title="View running workflows"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                <span>RUNNING ({runningWorkflows.length})</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isWidgetOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {isWidgetOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 8, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 8, scale: 0.96 }}
                    transition={{ duration: 0.18 }}
                    className="absolute right-0 mt-2 z-50 w-72"
                  >
                    <GlassPanel variant="soft" elevation={3} className="overflow-hidden text-left border border-border-primary p-4 space-y-3">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-dark-400 block border-b border-border-primary pb-2">
                        Active Agent Flights
                      </span>
                      <div className="space-y-3 max-h-60 overflow-y-auto scrollbar-thin">
                        {runningWorkflows.map(w => {
                          const blocksCount = Math.round((w.progress || 0) / 10);
                          const filledBlock = '█'.repeat(blocksCount);
                          const emptyBlock = '░'.repeat(10 - blocksCount);
                          return (
                            <div
                              key={w.id}
                              onClick={() => handleWidgetClick(w.id)}
                              className="p-2.5 bg-dark-900/40 hover:bg-dark-900/80 border border-border-primary/60 hover:border-cyan-accent/30 rounded-xl transition cursor-pointer space-y-1.5"
                            >
                              <div className="flex justify-between items-center text-[10px] font-mono font-semibold">
                                <span className="text-dark-100 truncate max-w-[150px]">{w.workflow_type}</span>
                                <span className="text-cyan-accent">{w.progress}%</span>
                              </div>
                              <div className="flex items-center justify-between text-[8px] font-mono text-dark-500">
                                <span className="truncate max-w-[120px]">{w.current_step || 'Initializing'}</span>
                                <span className="capitalize text-purple-accent">{w.status}</span>
                              </div>
                              <div className="text-[10px] font-mono text-cyan-accent leading-none tracking-normal mt-1">
                                {filledBlock}
                                <span className="text-dark-800">{emptyBlock}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </GlassPanel>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          <button
            onClick={toggleTheme}
            className="p-2.5 border border-border-primary hover:border-dark-700 bg-dark-900/35 hover:bg-dark-900/60 text-dark-400 hover:text-dark-100 transition rounded-xl cursor-pointer"
            title="Toggle theme mode"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-accent" /> : <Moon className="w-4 h-4 text-purple-accent" />}
          </button>

          <div className="relative" ref={dropdownRef}>
            <button
              onClick={handleToggleProfile}
              className="cursor-pointer select-none"
              title="User Actions Profile Menu"
            >
              <Avatar initials="PC" size="md" />
            </button>

            <AnimatePresence>
              {isProfileOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.96 }}
                  transition={{ duration: 0.18 }}
                  className="absolute right-0 mt-2 z-50 w-64"
                >
                  <GlassPanel variant="soft" elevation={3} className="overflow-hidden text-left border border-border-primary">
                    <div className="p-4 border-b border-border-primary bg-dark-900/40">
                      <span className="text-xs font-bold text-dark-100 font-display block leading-tight">Pushkar Chhokar</span>
                    </div>

                    <div className="p-3.5 space-y-2 text-[9px] font-mono text-dark-400 border-b border-border-primary">
                      <div className="flex justify-between items-center bg-dark-950/20 border border-border-primary/50 p-2 rounded-xl">
                        <span className="text-dark-500">ENGINE ROLE:</span>
                        <span className="text-cyan-accent font-bold uppercase">System Admin</span>
                      </div>
                    </div>

                    <div className="p-2 bg-dark-900/20">
                      <button
                        onClick={handleSessionLock}
                        className="w-full flex items-center justify-between px-3 py-2 hover:bg-dark-900/50 text-[10px] font-mono text-rose-500 rounded-xl transition cursor-pointer bg-transparent border-none text-left"
                      >
                        <span>SESSION LOCK</span>
                        <LogOut className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </GlassPanel>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  );
});

