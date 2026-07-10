import React, { useContext, useState, useMemo } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { OutputPanel } from '../components/OutputPanel';
import { Search, ScrollText, Calendar, AlertCircle } from 'lucide-react';
import type { HistoryItem, TaskType } from '../types';
import { Card, Badge } from '../components/ui';

export const ReportsPage: React.FC = () => {
  const context = useContext(AnalysisContext);
  const [search, setSearch] = useState('');
  const [taskFilter, setTaskFilter] = useState<TaskType | 'all'>('all');

  const history = context?.history;
  const parsedReport = context?.parsedReport || null;
  const loadHistoryItem = context?.loadHistoryItem || (() => {});

  // Filter reports
  const filteredReports = useMemo(() => {
    const list = history || [];
    return list.filter((item: HistoryItem) => {
      const matchSearch = `${item.repositoryOwner}/${item.repositoryName}`
        .toLowerCase()
        .includes(search.toLowerCase());
      const matchTask = taskFilter === 'all' || item.taskType === taskFilter;
      return matchSearch && matchTask;
    });
  }, [history, search, taskFilter]);

  if (!context) return null;

  const taskFilters: Array<{ label: string; value: TaskType | 'all' }> = [
    { label: 'All Tasks', value: 'all' },
    { label: 'Review', value: 'review' },
    { label: 'Bugs', value: 'bugs' },
    { label: 'Explain', value: 'explain' },
    { label: 'Tests', value: 'tests' }
  ];

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="space-y-8 select-none text-left">
      <div>
        <h2 className="text-xl font-bold text-dark-50 font-display flex items-center gap-2">
          <ScrollText className="w-5 h-5 text-cyan-accent" />
          <span>Audit Reports Workspace</span>
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">Browse, query, and export generated static analysis reports</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column: Filter and List Pane */}
        <div className="space-y-4">
          <Card variant="soft" className="space-y-4">
            {/* Search Input */}
            <div className="relative w-full">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-500 pointer-events-none" />
              <input
                type="text"
                placeholder="Search repository reports..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-[#070b14]/30 dark:bg-[#070b14]/50 border border-border-primary hover:border-dark-700/80 focus:border-cyan-accent focus:ring-1 focus:ring-cyan-accent/25 rounded-xl pl-10 pr-4 py-2.5 text-xs text-dark-200 outline-none transition-all duration-200 font-mono placeholder-dark-600"
              />
            </div>

            {/* Task filters */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono text-dark-500 font-bold uppercase tracking-wider block">Filter by Task Objective:</span>
              <div className="flex flex-wrap gap-2">
                {taskFilters.map((tf) => (
                  <button
                    key={tf.value}
                    onClick={() => setTaskFilter(tf.value)}
                    className={`px-3 py-1.5 rounded-lg border text-[10px] font-mono font-semibold uppercase transition cursor-pointer select-none
                      ${taskFilter === tf.value
                        ? 'bg-cyan-accent/15 border-cyan-accent/25 text-cyan-accent'
                        : 'border-border-primary bg-dark-900/10 hover:bg-dark-900/50 text-dark-400 hover:text-dark-200'
                      }`}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Reports scroll list */}
          <Card variant="soft" className="max-h-[480px] overflow-y-auto space-y-2.5 scrollbar-thin">
            <span className="text-[9px] font-mono text-dark-500 font-bold uppercase tracking-wider block px-1">Reports Available ({filteredReports.length})</span>
            {filteredReports.length === 0 ? (
              <div className="text-center py-12 text-dark-500 font-mono text-xs">
                <AlertCircle className="w-6 h-6 text-dark-600 mb-2.5 mx-auto" />
                <span>No audit reports match current filters.</span>
              </div>
            ) : (
              filteredReports.map((item) => {
                const isActive = parsedReport && (parsedReport.repository?.repository_hash === item.report.repository?.repository_hash && parsedReport.task_type === item.taskType);
                return (
                  <div
                    key={item.id}
                    onClick={() => loadHistoryItem(item)}
                    className={`p-3.5 border rounded-xl cursor-pointer text-left transition duration-150 flex flex-col gap-2.5 select-none
                      ${isActive
                        ? 'bg-dark-900/40 border-cyan-accent/30 shadow-[0_0_10px_rgba(6,182,212,0.05)]'
                        : 'bg-dark-950/20 border-border-primary hover:border-dark-800 hover:bg-[#070b14]/25'
                      }`}
                  >
                    <div className="flex justify-between items-start gap-3">
                      <div className="truncate min-w-0">
                        <span className={`text-xs font-semibold block truncate leading-none ${isActive ? 'text-cyan-accent' : 'text-dark-200'}`}>
                          {item.repositoryName}
                        </span>
                        <span className="text-[9px] font-mono text-dark-500 mt-1 block truncate">
                          {item.repositoryOwner}
                        </span>
                      </div>
                      <Badge variant="primary">
                        {item.taskType}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between text-[9px] font-mono text-dark-500 border-t border-border-primary/50 pt-2">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-dark-500" />
                        {formatDate(item.timestamp)}
                      </span>
                      <span className="text-dark-400 font-semibold">{item.duration.toFixed(1)}s run</span>
                    </div>
                  </div>
                );
              })
            )}
          </Card>
        </div>

        {/* Right Area: Report Detail Output panel */}
        <div className="lg:col-span-2 space-y-4">
          <OutputPanel />
        </div>
      </div>
    </div>
  );
};

export default ReportsPage;
