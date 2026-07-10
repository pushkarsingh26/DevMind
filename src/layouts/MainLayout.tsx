import React, { useState, useEffect, useCallback, useMemo, useContext, memo, useRef } from 'react';
import { Navbar } from '../components/Navbar';
import { ToastContainer } from '../components/ToastContainer';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { SVGRefractionFilter } from '../components/ui';
import {
  LayoutDashboard, Code2, MessageSquare, ScrollText,
  History, Settings, Boxes, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { AnalysisUIContext } from '../context/AnalysisContext';

interface MainLayoutProps { children: React.ReactNode; }

// -----------------------------------------------------------------------------
// Static logo — stable across all renders
// -----------------------------------------------------------------------------
export const DevMindLogo: React.FC<{ className?: string }> = memo(({ className = 'w-7 h-7' }) => (
  <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%"   stopColor="var(--secondary-accent)" />
        <stop offset="100%" stopColor="var(--primary-accent)" />
      </linearGradient>
    </defs>
    <path d="M16 2L28 9V23L16 30L4 23V9L16 2Z"       stroke="url(#logoGrad)" strokeWidth="2" strokeLinejoin="round" />
    <path d="M16 8L23 12V20L16 24L9 20V12L16 8Z"    fill="url(#logoGrad)" fillOpacity="0.25" stroke="url(#logoGrad)" strokeWidth="1.5" />
    <circle cx="16" cy="16" r="3.5" fill="var(--secondary-accent)" className="animate-pulse" />
  </svg>
));

// -----------------------------------------------------------------------------
// Static nav item definitions — defined once, never recreated
// -----------------------------------------------------------------------------
const NAV_ITEMS = [
  { label: 'Dashboard',           icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Repository Analysis', icon: Code2,           path: '/repositories' },
  { label: 'Grounded Chat',       icon: MessageSquare,   path: '/chat' },
  { label: 'Agent Workspace',     icon: Boxes,           path: '/agents' },
  { label: 'Reports',             icon: ScrollText,      path: '/reports' },
  { label: 'History',             icon: History,         path: '/history' },
  { label: 'Settings',            icon: Settings,        path: '/settings' },
  { label: 'Future Modules',      icon: Boxes,           path: '/future' },
] as const;

// -----------------------------------------------------------------------------
// Sidebar — memo-ized standalone component, only re-renders on its own props
// -----------------------------------------------------------------------------
interface SidebarProps {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
  onToggleCollapse: () => void;
}

const SidebarContent = memo<SidebarProps>(({
  isCollapsed, isMobileOpen, currentPath, onNavigate, onToggleCollapse,
}) => (
  <div className="flex flex-col h-full bg-[#090d16]/30 backdrop-blur-xl">
    {/* Brand header */}
    <div className="flex items-center gap-3.5 px-5 py-6 border-b border-border-primary">
      <DevMindLogo className="w-8 h-8 shrink-0 shadow-[0_0_20px_rgba(6,182,212,0.15)]" />
      {(!isCollapsed || isMobileOpen) && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.15 }}
          className="truncate"
        >
          <h1 className="text-base font-bold text-dark-50 tracking-tight leading-none font-display">DevMind</h1>
          <span className="text-[9px] text-cyan-accent font-mono mt-1.5 block font-bold tracking-wider uppercase">Phase 5 Engine</span>
        </motion.div>
      )}
    </div>

    {/* Navigation */}
    <nav className="flex-1 px-3.5 py-5 space-y-1.5 overflow-y-auto scrollbar-thin">
      {NAV_ITEMS.map((item) => {
        const Icon   = item.icon;
        const active = currentPath === item.path;
        return (
          <button
            key={item.path}
            onClick={() => onNavigate(item.path)}
            className={`w-full flex items-center gap-4.5 px-3.5 py-3 rounded-xl transition-all duration-200 text-left font-sans text-xs relative group cursor-pointer ${
              active
                ? 'bg-purple-accent/10 border border-purple-accent/20 text-cyan-accent font-semibold'
                : 'text-dark-300 hover:text-dark-100 hover:bg-dark-900/40 border border-transparent'
            }`}
          >
            <div className={`shrink-0 transition-transform duration-200 ${active ? 'scale-110 text-cyan-accent' : 'group-hover:scale-110'}`}>
              <Icon className="w-4.5 h-4.5" />
            </div>

            {(!isCollapsed || isMobileOpen) && (
              <motion.span
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
                className="truncate tracking-wide"
              >
                {item.label}
              </motion.span>
            )}

            {/* Active micro-dot for collapsed state */}
            {isCollapsed && !isMobileOpen && active && (
              <span className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-cyan-accent rounded-full shadow-[0_0_8px_rgba(6,182,212,0.6)]" />
            )}

            {/* Hover tooltip for collapsed state */}
            {isCollapsed && !isMobileOpen && (
              <div className="absolute left-22 bg-panel-solid border border-border-primary text-dark-100 px-3 py-2 rounded-xl text-[10px] font-mono opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap shadow-lg z-50">
                {item.label.toUpperCase()}
              </div>
            )}
          </button>
        );
      })}
    </nav>

    {/* Collapse toggle */}
    <div className="p-3.5 border-t border-border-primary hidden md:block">
      <button
        onClick={onToggleCollapse}
        className="w-full flex items-center justify-center p-2.5 rounded-xl border border-border-primary hover:border-dark-700 bg-dark-900/30 text-dark-400 hover:text-dark-200 transition-all cursor-pointer"
      >
        {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </div>
  </div>
));

// -----------------------------------------------------------------------------
// Sidebar animation variants (stable outside component)
// -----------------------------------------------------------------------------
const sidebarVariants = {
  expanded:  { width: 256, transition: { duration: 0.25, ease: 'easeOut' as const } },
  collapsed: { width: 88,  transition: { duration: 0.25, ease: 'easeOut' as const } },
};

// Page transition — opacity-only, no y-shift (avoids layout recalculation)
const pageVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit:    { opacity: 0 },
};
const pageTransition = { duration: 0.18, ease: 'easeOut' as const };

// -----------------------------------------------------------------------------
// Main Layout
// -----------------------------------------------------------------------------
export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('devmind_sidebar_collapsed');
    return saved === 'true';
  });
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [animationsPaused,    setAnimationsPaused]    = useState(false);

  const location = useLocation();
  const navigate = useNavigate();

  // Subscribe only to UI context (theme) — not the heavy data context
  const uiContext = useContext(AnalysisUIContext);
  const theme     = uiContext?.theme || 'dark';

  // Debounced localStorage write — no need to write on every toggle during rapid clicks
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      localStorage.setItem('devmind_sidebar_collapsed', String(isSidebarCollapsed));
    }, 300);
    return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); };
  }, [isSidebarCollapsed]);

  // Scroll restoration on route change
  useEffect(() => {
    const workspaceEl = document.querySelector('main');
    if (workspaceEl) { workspaceEl.scrollTop = 0; workspaceEl.scrollLeft = 0; }
  }, [location.pathname]);

  // Pause background animations when tab is hidden — saves GPU cycles
  useEffect(() => {
    const handleVisibility = () => setAnimationsPaused(document.hidden);
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  const handleNavigation = useCallback((path: string) => {
    setIsMobileSidebarOpen(false);
    navigate(path);
  }, [navigate]);

  const handleToggleCollapse = useCallback(() => {
    setIsSidebarCollapsed(prev => !prev);
  }, []);

  const handleOpenMobileSidebar = useCallback(() => setIsMobileSidebarOpen(true),  []);
  const handleCloseMobileSidebar= useCallback(() => setIsMobileSidebarOpen(false), []);

  // Stable rainbow lines — generated once, never change
  const rainbowLines = useMemo(() => {
    const colorsList = [
      ['rgb(232, 121, 249)', 'rgb(96, 165, 250)',  'rgb(94, 234, 212)'],
      ['rgb(232, 121, 249)', 'rgb(94, 234, 212)',  'rgb(96, 165, 250)'],
      ['rgb(94, 234, 212)',  'rgb(232, 121, 249)', 'rgb(96, 165, 250)'],
      ['rgb(94, 234, 212)',  'rgb(96, 165, 250)',  'rgb(232, 121, 249)'],
      ['rgb(96, 165, 250)',  'rgb(94, 234, 212)',  'rgb(232, 121, 249)'],
      ['rgb(96, 165, 250)',  'rgb(232, 121, 249)', 'rgb(94, 234, 212)'],
    ];
    const length   = 25;
    const baseTime = 55;
    return Array.from({ length }).map((_, idx) => {
      const i        = idx + 1;
      const r        = Math.floor((i * 7) % 6);
      const colors   = colorsList[r];
      const duration = baseTime - (baseTime / length / 2) * i;
      const delay    = -(i / length) * baseTime;
      const background = `linear-gradient(90deg, rgba(255,255,255,0) 0%, ${colors[0]} 20%, ${colors[1]} 50%, ${colors[2]} 80%, rgba(255,255,255,0) 100%)`;
      return (
        <div
          key={i}
          className="rainbow"
          style={{
            background,
            animation: `${duration}s linear infinite slide`,
            animationDelay: `${delay}s`,
            animationPlayState: animationsPaused ? 'paused' : 'running',
          }}
        />
      );
    });
  }, [animationsPaused]);

  // Stable particle elements — positions seeded once
  const particleElements = useMemo(() => {
    // Use deterministic values to avoid hydration differences
    const configs = [
      { size: 8,  left: 15, top: 22, dur: 22, del: -3, purple: true  },
      { size: 6,  left: 42, top: 67, dur: 18, del: -7, purple: false },
      { size: 10, left: 73, top: 15, dur: 28, del: -2, purple: true  },
      { size: 5,  left: 88, top: 45, dur: 20, del: -9, purple: false },
      { size: 9,  left: 30, top: 80, dur: 25, del: -4, purple: true  },
      { size: 7,  left: 58, top: 35, dur: 16, del: -6, purple: false },
      { size: 6,  left: 5,  top: 55, dur: 30, del: -1, purple: true  },
      { size: 8,  left: 95, top: 72, dur: 19, del: -8, purple: false },
      { size: 5,  left: 65, top: 90, dur: 23, del: -5, purple: true  },
      { size: 10, left: 20, top: 10, dur: 27, del: -2, purple: false },
      { size: 7,  left: 80, top: 28, dur: 21, del: -7, purple: true  },
      { size: 6,  left: 48, top: 50, dur: 17, del: -3, purple: false },
    ];
    return configs.map((c, idx) => (
      <div
        key={idx}
        className={`absolute rounded-full pointer-events-none opacity-20 blur-[1px] ${c.purple ? 'bg-purple-accent/30' : 'bg-cyan-accent/30'}`}
        style={{
          width: `${c.size}px`, height: `${c.size}px`,
          left: `${c.left}%`, top: `${c.top}%`,
          animation: `float-aurora ${c.dur}s infinite ease-in-out alternate`,
          animationDelay: `${c.del}s`,
          animationPlayState: animationsPaused ? 'paused' : 'running',
          willChange: 'transform, opacity',
        }}
      />
    ));
  }, [animationsPaused]);

  const isChat = location.pathname === '/chat';

  return (
    <div className="h-screen w-screen bg-canvas text-dark-300 flex font-sans selection:bg-purple-accent/20 selection:text-cyan-accent relative overflow-hidden">

      {/* SVG Filter Definition */}
      <SVGRefractionFilter />

      {/* Dynamic Theme Background */}
      {theme === 'light' ? (
        <div
          className="rainbow-container"
          style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }}
        >
          {rainbowLines}
          <div className="rainbow-h" />
          <div className="rainbow-v" />
        </div>
      ) : (
        <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none select-none">
          <div className="stars" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="shooting-star" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="shooting-star" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="shooting-star" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="shooting-star" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="shooting-star" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="absolute top-[-15%] left-[-15%] w-[60vw] h-[60vw] rounded-full bg-purple-accent/5 dark:bg-purple-accent/4 blur-[130px] animate-aurora-1" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="absolute bottom-[-15%] right-[-15%] w-[60vw] h-[60vw] rounded-full bg-cyan-accent/5 dark:bg-cyan-accent/4 blur-[130px] animate-aurora-2" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          <div className="absolute top-[35%] left-[30%] w-[40vw] h-[40vw] rounded-full bg-purple-accent/3 dark:bg-purple-accent/2 blur-[110px] animate-aurora-3" style={{ animationPlayState: animationsPaused ? 'paused' : 'running' }} />
          {particleElements}
        </div>
      )}

      {/* Desktop Pinned Sidebar */}
      <motion.aside
        initial={isSidebarCollapsed ? 'collapsed' : 'expanded'}
        animate={isSidebarCollapsed ? 'collapsed' : 'expanded'}
        variants={sidebarVariants}
        className="hidden md:flex flex-col shrink-0 h-screen z-40 overflow-hidden border-r border-border-primary/80"
      >
        <div className="h-full overflow-hidden glass-lvl2 bg-panel-1 shrink-0 flex flex-col">
          <SidebarContent
            isCollapsed={isSidebarCollapsed}
            isMobileOpen={false}
            currentPath={location.pathname}
            onNavigate={handleNavigation}
            onToggleCollapse={handleToggleCollapse}
          />
        </div>
      </motion.aside>

      {/* Mobile Sidebar Overlay Drawer */}
      <AnimatePresence>
        {isMobileSidebarOpen && (
          <div className="fixed inset-0 z-50 md:hidden flex">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.6 }}
              exit={{ opacity: 0 }}
              onClick={handleCloseMobileSidebar}
              className="fixed inset-0 bg-black cursor-pointer"
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="relative w-64 h-full z-10 flex flex-col"
            >
              <SidebarContent
                isCollapsed={false}
                isMobileOpen={true}
                currentPath={location.pathname}
                onNavigate={handleNavigation}
                onToggleCollapse={handleToggleCollapse}
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen relative z-10 overflow-hidden">

        <Navbar onOpenMobileSidebar={handleOpenMobileSidebar} />

        {/* Scrollable Workspace */}
        <main className={`flex-1 min-h-0 relative w-full ${isChat ? 'overflow-hidden' : 'overflow-y-auto'}`}>
          <div className={`max-w-7xl mx-auto flex flex-col justify-between ${isChat ? 'h-full p-0' : 'p-6 md:p-8 min-h-full'}`}>
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 w-full flex flex-col justify-between h-full min-h-0"
              >
                {children}
              </motion.div>
            </AnimatePresence>

            {!isChat && (
              <footer className="border-t border-border-primary/60 bg-transparent px-6 py-6 text-center text-[10px] text-dark-500 font-mono print:hidden mt-8">
                DevMind © {new Date().getFullYear()} — Phase 7 AI Code Intelligence Engine. Built By Pushkar Chhokar.
              </footer>
            )}
          </div>
        </main>

        <ToastContainer />
      </div>
    </div>
  );
};

