import React from 'react';
import { Boxes, Sparkles, Terminal, Code, Network, Share2, Rocket } from 'lucide-react';
import { Card, Badge } from '../components/ui';

export const FuturePage: React.FC = () => {
  const futureModules = [
    {
      title: 'Autonomous Multi-Agent Autopilot',
      description: 'Deploy groups of coordinator, review, and patch agents that collaboratively write commits, run tests, and publish pull requests autonomously.',
      icon: <Terminal className="w-5 h-5 text-cyan-accent" />,
      tag: 'PHASE 6',
      badgeVar: 'secondary' as const
    },
    {
      title: 'Interactive Codebase AST Visualizer',
      description: 'Explore live, responsive dependency trees, namespace hierarchy diagrams, and node structures computed directly from file parser indexes.',
      icon: <Network className="w-5 h-5 text-purple-accent" />,
      tag: 'PHASE 7',
      badgeVar: 'primary' as const
    },
    {
      title: 'Advanced CI/CD Pipeline Gateways',
      description: 'Automatically trigger security scans and code style audits on GitHub webhook pull requests, blocking merges on policy failures.',
      icon: <Code className="w-5 h-5 text-green-accent" />,
      tag: 'PHASE 8',
      badgeVar: 'success' as const
    },
    {
      title: 'Team Collaborative Shared Contexts',
      description: 'Host team-wide workspaces with pooled vector store cache models, shared audit logs, and parallel chat sessions.',
      icon: <Share2 className="w-5 h-5 text-amber-accent" />,
      tag: 'PHASE 9',
      badgeVar: 'warning' as const
    }
  ];

  return (
    <div className="space-y-8 select-none relative overflow-hidden min-h-[500px] text-left">
      <div className="absolute top-0 right-0 w-80 h-80 bg-[#a855f7]/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-dark-50 font-display flex items-center gap-2">
          <Boxes className="w-5 h-5 text-cyan-accent" />
          <span>Future Intelligence Modules</span>
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">Platform development blueprint & upcoming features</p>
      </div>

      {/* Hero Welcome banner */}
      <Card variant="soft" className="text-center space-y-4 max-w-2xl mx-auto">
        <div className="p-3 bg-purple-accent/10 w-14 h-14 rounded-2xl border border-purple-accent/20 text-purple-accent flex items-center justify-center mx-auto shadow-[0_0_15px_rgba(168,85,247,0.15)] animate-bounce">
          <Rocket className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-dark-100 font-display">DevMind Platform Expansion</h3>
          <p className="text-xs text-dark-400 leading-relaxed font-sans mt-2 max-w-md mx-auto">
            Our multi-agent pipeline is continuously evolving. Explore upcoming features planned for release in future phases of the code intelligence engine.
          </p>
        </div>
      </Card>

      {/* Grid of future modules */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 max-w-5xl mx-auto">
        {futureModules.map((mod, idx) => (
          <Card
            key={idx}
            interactive
            className="text-left flex flex-col justify-between h-full min-h-[160px]"
          >
            <div className="space-y-3">
              <div className="flex justify-between items-start gap-4">
                <div className="p-2.5 bg-[#070b14]/30 border border-border-primary rounded-xl shrink-0">
                  {mod.icon}
                </div>
                <Badge variant={mod.badgeVar}>
                  {mod.tag}
                </Badge>
              </div>

              <h4 className="text-sm font-semibold text-dark-200 font-display leading-tight">
                {mod.title}
              </h4>
              <p className="text-xs text-dark-400 leading-relaxed font-sans">
                {mod.description}
              </p>
            </div>

            <div className="border-t border-border-primary/50 pt-3 mt-4 text-[9px] font-mono text-dark-500 uppercase tracking-wider flex items-center gap-1.5 font-bold">
              <Sparkles className="w-3.5 h-3.5 text-cyan-accent animate-pulse" />
              <span>DEVELOPMENT STAGE — BLUEPRINT</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default FuturePage;
