import { useContext, useMemo, memo } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { useNavigate } from 'react-router-dom';
import { 
  Play, MessageSquare, ScrollText, Settings, History, 
  ShieldCheck, Heart, Sparkles, FolderGit2, AlertCircle, ArrowRight
} from 'lucide-react';
import { StatusCard } from '../components/StatusCard';
import { Card, CardHeader, CardContent, CardFooter, Button, Badge, Progress } from '../components/ui';

// Static action definitions — defined once at module scope, never recreated
const QUICK_ACTIONS = [
  {
    title: 'Analyze Repository',
    description: 'Audit GitHub URLs or ZIP file structures.',
    icon: <Play className="w-4 h-4 text-cyan-accent" />,
    path: '/repositories',
    glow: 'purple' as const,
  },
  {
    title: 'Grounded RAG Chat',
    description: 'Ask deep context-backed codebase questions.',
    icon: <MessageSquare className="w-4 h-4 text-purple-accent" />,
    path: '/chat',
    glow: 'cyan' as const,
  },
  {
    title: 'Code Audit Reports',
    description: 'Browse, export, or print generated reports.',
    icon: <ScrollText className="w-4 h-4 text-green-accent" />,
    path: '/reports',
    glow: 'purple' as const,
  },
  {
    title: 'Engine Settings',
    description: 'Adjust providers, temperatures, and timeouts.',
    icon: <Settings className="w-4 h-4 text-amber-accent" />,
    path: '/settings',
    glow: 'cyan' as const,
  },
];

export const DashboardPage = memo(() => {
  const context = useContext(AnalysisContext);
  const navigate = useNavigate();

  const history = context?.history || [];
  const parsedReport = context?.parsedReport || null;
  const status = context?.status || {
    planner: { status: 'waiting', message: 'Waiting...' },
    retriever: { status: 'waiting', message: 'Waiting...' },
    reviewer: { status: 'waiting', message: 'Waiting...' },
    critic: { status: 'waiting', message: 'Waiting...' }
  };

  // Active repo details
  const activeRepo = parsedReport?.repository;
  
  const healthScore = useMemo(() => {
    if (!parsedReport) return null;
    const bugIssues = parsedReport.aiOutput?.logical_issues?.length || 0;
    const riskIssues = parsedReport.aiOutput?.risk_areas?.length || 0;
    const securityIssues = parsedReport.aiOutput?.security_observations?.length || 0;
    return Math.max(25, 100 - (bugIssues * 12 + riskIssues * 8 + securityIssues * 10));
  }, [parsedReport]);

  const securityScore = useMemo(() => {
    if (!parsedReport) return null;
    const securityIssues = parsedReport.aiOutput?.security_observations?.length || 0;
    return securityIssues > 0 ? Math.max(30, 100 - securityIssues * 15) : 96;
  }, [parsedReport]);

  if (!context) return null;

  // Use static QUICK_ACTIONS from module scope
  const quickActions = QUICK_ACTIONS;

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* 1. Welcome Hero Header Banner */}
      <div className="relative overflow-hidden rounded-2xl glass-lvl2 p-6 md:p-8 shadow-premium border border-border-primary/80 bg-gradient-to-r from-purple-accent/5 to-cyan-accent/5">
        <div className="absolute top-[-10%] right-[-10%] w-60 h-60 bg-cyan-accent/8 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-[-10%] left-[-10%] w-60 h-60 bg-purple-accent/8 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-dark-50 font-display tracking-tight flex items-center gap-2">
              Welcome to DevMind, <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-accent to-purple-accent">Pushkar Chhokar</span>!
            </h2>
            <p className="text-xs text-dark-400 leading-relaxed font-sans max-w-xl">
              You are connected to the Phase 5 AI Code Intelligence cockpit. Audit structural defects, run grounded conversations, and retrieve index mappings across your developer projects.
            </p>
          </div>
          <div className="shrink-0">
            <Button
              variant="primary"
              glow
              size="md"
              onClick={() => navigate('/repositories')}
              className="flex items-center gap-4"
            >
              <span>AUDIT NEW PROJECT</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* 2. Visual Metric Cards Grid (24px gap) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Metric 1: Grounding Status Card */}
        <Card variant="soft" className="flex flex-col justify-between min-h-[150px] p-6">
          <div className="flex items-center justify-between gap-3 text-dark-500 font-mono text-[9px] font-bold uppercase tracking-wider">
            <span>Grounding Status</span>
            <FolderGit2 className="w-4 h-4 text-cyan-accent" />
          </div>
          <div className="my-2 truncate">
            {activeRepo ? (
              <>
                <span className="block text-sm font-semibold text-dark-100 truncate">
                  {activeRepo.owner}/{activeRepo.name}
                </span>
                <span className="text-[10px] text-dark-400 font-mono block mt-1">
                  Vector mapping active
                </span>
              </>
            ) : (
              <span className="block text-xs font-semibold text-dark-400">
                Select a repository to begin analysis.
              </span>
            )}
          </div>
          <div className="mt-2">
            {activeRepo ? (
              <Badge variant="success">READY FOR CHAT</Badge>
            ) : (
              <button 
                onClick={() => navigate('/repositories')}
                className="text-[9px] text-cyan-accent hover:text-cyan-400 font-mono font-bold text-left cursor-pointer p-0 bg-transparent border-none uppercase tracking-wider"
              >
                INDEX NOW →
              </button>
            )}
          </div>
        </Card>

        {/* Metric 2: Codebase Health Score */}
        <Card variant="soft" className="flex flex-col justify-between min-h-[150px] p-6">
          <div className="flex items-center justify-between gap-3 text-dark-500 font-mono text-[9px] font-bold uppercase tracking-wider">
            <span>Codebase Health</span>
            <Heart className="w-4 h-4 text-rose-500 animate-pulse" />
          </div>
          <div className="my-2 flex items-center justify-between gap-4">
            <div>
              <span className="text-2xl font-bold font-mono text-dark-100 leading-none">
                {healthScore !== null ? `${healthScore}%` : '—'}
              </span>
              <span className="text-[10px] text-dark-400 font-mono block mt-1">
                Refactoring & stability score
              </span>
            </div>
            {healthScore !== null && (
              <Progress type="circle" value={healthScore} size={42} strokeWidth={3} color="primary" />
            )}
          </div>
          <span className="text-[8px] font-mono text-dark-500 uppercase">
            {healthScore !== null ? 'Dynamic report calculation' : 'Awaiting analysis'}
          </span>
        </Card>

        {/* Metric 3: Security Index Score */}
        <Card variant="soft" className="flex flex-col justify-between min-h-[150px] p-6">
          <div className="flex items-center justify-between gap-3 text-dark-500 font-mono text-[9px] font-bold uppercase tracking-wider">
            <span>Security Index</span>
            <ShieldCheck className="w-4 h-4 text-green-accent" />
          </div>
          <div className="my-2 flex items-center justify-between gap-4">
            <div>
              <span className="text-2xl font-bold font-mono text-dark-100 leading-none">
                {securityScore !== null ? `${securityScore}%` : '—'}
              </span>
              <span className="text-[10px] text-dark-400 font-mono block mt-1">
                Observations vulnerabilities
              </span>
            </div>
            {securityScore !== null && (
              <Progress type="circle" value={securityScore} size={42} strokeWidth={3} color="success" />
            )}
          </div>
          <span className="text-[8px] font-mono text-dark-500 uppercase">
            {securityScore !== null ? 'OWASP ruleset check' : 'Awaiting analysis'}
          </span>
        </Card>

        {/* Metric 4: Total Audit History Sparkline Card */}
        <Card variant="soft" className="flex flex-col justify-between min-h-[150px] p-6">
          <div className="flex items-center justify-between gap-3 text-dark-500 font-mono text-[9px] font-bold uppercase tracking-wider">
            <span>Audit History</span>
            <History className="w-4 h-4 text-purple-accent" />
          </div>
          <div className="my-2 flex items-center justify-between gap-2.5">
            <div>
              <span className="text-2xl font-bold font-mono text-dark-100 leading-none">
                {history.length}
              </span>
              <span className="text-[10px] text-dark-400 font-mono block mt-1">
                Cached runs in workspace
              </span>
            </div>
            
            {/* Sparkline graphics */}
            <div className="w-16 h-10 shrink-0 select-none pointer-events-none">
              <svg viewBox="0 0 100 40" className="w-full h-full overflow-visible">
                <path
                  d="M0,35 Q20,10 40,25 T80,15 L100,5"
                  fill="none"
                  stroke="var(--secondary-accent)"
                  strokeWidth="3"
                  className="sparkline-path"
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>
          <button 
            onClick={() => navigate('/history')}
            className="text-[9px] text-[#a855f7] hover:text-purple-400 font-mono font-bold text-left cursor-pointer p-0 bg-transparent border-none uppercase tracking-wider"
          >
            VIEW LOGS →
          </button>
        </Card>
      </div>

      {/* 3. Main Dashboard Grid Layout (24px gap) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Quick Actions Grid */}
        <div className="lg:col-span-2">
          <Card variant="soft" className="h-full flex flex-col justify-between p-6">
            <CardHeader className="mb-4">
              <div>
                <h3 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-accent" />
                  <span>Quick Start Actions</span>
                </h3>
                <p className="text-xs text-dark-500 font-mono mt-0.5">Jump directly to specialized application workspaces</p>
              </div>
            </CardHeader>

            <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-6 py-2">
              {quickActions.map((act, idx) => (
                <Card
                  key={idx}
                  interactive
                  glowColor={act.glow}
                  onClick={() => navigate(act.path)}
                  className="p-6 cursor-pointer text-left flex gap-4 items-start"
                >
                  <div className="p-2.5 bg-dark-900/60 border border-border-primary rounded-xl shrink-0">
                    {act.icon}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-bold text-dark-200 font-display">{act.title}</h4>
                    <p className="text-[10px] text-dark-500 font-sans mt-1 leading-normal">{act.description}</p>
                  </div>
                </Card>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right: Recent Analyses List */}
        <div>
          <Card variant="soft" className="h-full flex flex-col justify-between p-6">
            <CardHeader className="mb-4">
              <div>
                <h3 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
                  <History className="w-4 h-4 text-purple-accent" />
                  <span>Recent Analyses</span>
                </h3>
                <p className="text-xs text-dark-500 font-mono mt-0.5">Last indexed runs in local storage</p>
              </div>
            </CardHeader>

            <CardContent className="flex-1 space-y-3.5 my-3">
              {context.isAnalyzing ? (
                // Shimmer Skeletons during active runs
                <div className="space-y-3">
                  <div className="h-12 w-full animate-shimmer rounded-xl" />
                  <div className="h-12 w-full animate-shimmer rounded-xl" />
                  <div className="h-12 w-full animate-shimmer rounded-xl" />
                </div>
              ) : history.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-dark-500 font-mono text-[10px] py-12 border border-dashed border-border-primary rounded-2xl">
                  <AlertCircle className="w-6 h-6 text-dark-600 mb-2" />
                  <span>No executions found.</span>
                </div>
              ) : (
                history.slice(0, 3).map((item) => (
                  <div 
                    key={item.id}
                    onClick={() => {
                      context.loadHistoryItem(item);
                      navigate('/repositories');
                    }}
                    className="flex items-center justify-between p-3.5 bg-dark-950/20 border border-border-primary/50 hover:border-cyan-accent/25 rounded-xl cursor-pointer transition duration-150"
                  >
                    <div className="truncate min-w-0 text-left">
                      <span className="text-xs font-semibold text-dark-200 block truncate leading-none mb-1">
                        {item.repositoryName}
                      </span>
                      <span className="text-[8px] font-mono text-dark-500 uppercase">
                        {item.taskType} · {item.provider}
                      </span>
                    </div>
                    <span className="text-[9px] font-mono text-cyan-accent font-semibold shrink-0 ml-2">
                      {item.duration.toFixed(1)}s
                    </span>
                  </div>
                ))
              )}
            </CardContent>

            <CardFooter className="mt-4">
              {history.length > 0 && (
                <Button
                  variant="glass"
                  size="md"
                  onClick={() => navigate('/history')}
                  className="w-full text-center"
                >
                  VIEW ALL RUN TIMELINES
                </Button>
              )}
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* 4. AI Agent Status Monitor Section */}
      <Card variant="soft" className="p-6">
        <CardHeader className="mb-4">
          <div>
            <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
              <span className="text-xs bg-purple-accent/10 text-purple-accent border border-purple-accent/20 px-2 py-0.5 rounded-lg font-mono">03</span>
              <span>AI AGENT STATUS MONITOR</span>
            </h2>
            <p className="text-xs text-dark-500 font-mono mt-0.5">Real-time failover diagnostic logs from LLM cognitive models</p>
          </div>
        </CardHeader>

        <CardContent>
          {context.isAnalyzing ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="h-24 animate-shimmer rounded-xl" />
              <div className="h-24 animate-shimmer rounded-xl" />
              <div className="h-24 animate-shimmer rounded-xl" />
              <div className="h-24 animate-shimmer rounded-xl" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatusCard
                agentName="Planner Agent"
                status={status.planner.status}
                message={status.planner.message}
              />
              <StatusCard
                agentName="Retriever Agent"
                status={status.retriever.status}
                message={status.retriever.message}
              />
              <StatusCard
                agentName="Reviewer Agent"
                status={status.reviewer.status}
                message={status.reviewer.message}
              />
              <StatusCard
                agentName="Critic Agent"
                status={status.critic.status}
                message={status.critic.message}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
});

export default DashboardPage;

