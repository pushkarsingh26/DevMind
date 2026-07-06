import type { TaskType } from '../types';
import { useAnalysis } from '../hooks/useAnalysis';

interface TaskOption {
  value: TaskType;
  label: string;
  description: string;
}

const taskOptions: TaskOption[] = [
  {
    value: 'review',
    label: 'Review Repository',
    description: 'Structure review, style check, and security analysis.',
  },
  {
    value: 'explain',
    label: 'Explain Code',
    description: 'High-level structure and architecture breakdown.',
  },
  {
    value: 'tests',
    label: 'Generate Tests',
    description: 'Generate automated unit test suites for components.',
  },
  {
    value: 'bugs',
    label: 'Find Bugs',
    description: 'Find logic defects, error paths, and code hotspots.',
  },
];

export const TaskSelector: React.FC = () => {
  const { selectedTask, setSelectedTask, isAnalyzing } = useAnalysis();

  const currentOption = taskOptions.find((o) => o.value === selectedTask) || taskOptions[0];

  return (
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 flex flex-col justify-between">
      <div>
        <h2 className="text-base font-semibold text-dark-100 font-mono mb-4 flex items-center gap-2">
          <span>02.</span> ANALYSIS PIPELINE
        </h2>
        <label htmlFor="task-select" className="block text-xs font-mono text-dark-400 mb-2">
          SELECT AGENT TASK
        </label>
        <select
          id="task-select"
          disabled={isAnalyzing}
          value={selectedTask}
          onChange={(e) => setSelectedTask(e.target.value as TaskType)}
          className="w-full bg-dark-950 border border-dark-800 rounded px-4 py-3 text-sm text-dark-100 font-mono focus:outline-none focus:border-brand-500 disabled:opacity-50 cursor-pointer"
        >
          {taskOptions.map((option) => (
            <option key={option.value} value={option.value} className="bg-dark-900 text-dark-100 font-mono">
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-6 pt-4 border-t border-dark-800">
        <span className="text-[10px] font-mono text-brand-400 uppercase tracking-widest block mb-1">
          Pipeline Objective
        </span>
        <p className="text-xs text-dark-400 font-mono leading-relaxed min-h-[40px]">
          {currentOption.description}
        </p>
      </div>
    </div>
  );
};
