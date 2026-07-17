import React from 'react';
import { FileText, Layers, Terminal, Hash } from 'lucide-react';
import { Card, CardContent } from './ui';

export interface RepositoryMemory {
  repository_id: string;
  repository_hash: string;
  recurring_files: string[];
  frequently_modified_modules: string[];
  hotspot_history: Record<string, number>;
  dependency_history: string[];
  architecture_history: string[];
  language_history: Record<string, number>;
}

interface MemoryDashboardProps {
  memory: RepositoryMemory;
}

export const MemoryDashboard: React.FC<MemoryDashboardProps> = ({ memory }) => {
  return (
    <div className="space-y-6">
      {/* Structural overview grids */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Recurring files & Hotspots */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-cyan-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Recurring Affected Files</h3>
            </div>
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {memory.recurring_files.map(file => (
                <div key={file} className="flex justify-between items-center p-2 rounded-lg bg-dark-900/30 border border-border-primary/50 text-xs font-mono text-dark-300">
                  <span className="truncate mr-2">{file}</span>
                  <span className="text-[10px] text-cyan-accent bg-cyan-accent/10 px-1.5 py-0.5 rounded border border-cyan-accent/20">
                    {memory.hotspot_history[file] ?? 0}x
                  </span>
                </div>
              ))}
              {memory.recurring_files.length === 0 && (
                <p className="text-xs text-dark-500 font-mono text-center py-6">No files have qualified as recurring yet.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Frequently Modified Modules */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 text-purple-accent" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Frequently Modified Modules</h3>
            </div>
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {memory.frequently_modified_modules.map((module, idx) => (
                <div key={module} className="flex items-center gap-2.5 p-2 rounded-lg bg-dark-900/30 border border-border-primary/50 text-xs font-mono text-dark-300">
                  <span className="text-[9px] text-dark-500 font-bold w-4">{idx + 1}.</span>
                  <span className="truncate">{module}</span>
                </div>
              ))}
              {memory.frequently_modified_modules.length === 0 && (
                <p className="text-xs text-dark-500 font-mono text-center py-6">No modified module runs recorded.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Languages distribution */}
        <Card className="border-border-primary">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <Terminal className="w-4 h-4 text-yellow-400" />
              <h3 className="text-xs font-mono uppercase tracking-widest text-dark-400">Language Hotspot Counts</h3>
            </div>
            <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1">
              {Object.entries(memory.language_history).map(([lang, count]) => (
                <div key={lang} className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-dark-300 capitalize">{lang}</span>
                    <span className="text-dark-400">{count} parsed files</span>
                  </div>
                  <div className="h-1.5 w-full bg-dark-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-yellow-400 to-amber-500 rounded-full"
                      style={{ width: `${Math.min(100, (count / 15) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
              {Object.keys(memory.language_history).length === 0 && (
                <p className="text-xs text-dark-500 font-mono text-center py-6">No language stats registered.</p>
              )}
            </div>
          </CardContent>
        </Card>

      </div>

      {/* Dependency and Architecture history details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-border-primary">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center gap-2 text-dark-400">
              <Hash className="w-3.5 h-3.5 text-purple-accent" />
              <span className="text-[10px] uppercase tracking-widest font-mono">Dependency Scope Memory</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {memory.dependency_history.map(dep => (
                <span key={dep} className="px-2 py-0.5 rounded bg-purple-accent/10 border border-purple-accent/20 text-purple-accent text-[10px] font-mono">
                  {dep}
                </span>
              ))}
              {memory.dependency_history.length === 0 && (
                <span className="text-xs text-dark-500 font-mono">No parsed dependencies in memory database.</span>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border-primary">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center gap-2 text-dark-400">
              <Hash className="w-3.5 h-3.5 text-cyan-accent" />
              <span className="text-[10px] uppercase tracking-widest font-mono">Architecture Context List</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {memory.architecture_history.map(arch => (
                <span key={arch} className="px-2 py-0.5 rounded bg-cyan-accent/10 border border-cyan-accent/20 text-cyan-accent text-[10px] font-mono">
                  {arch}
                </span>
              ))}
              {memory.architecture_history.length === 0 && (
                <span className="text-xs text-dark-500 font-mono">No architecture records registered.</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
export default MemoryDashboard;
