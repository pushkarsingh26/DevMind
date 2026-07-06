import type { TaskType, MultiAgentStatus } from '../types';

// Placeholder FastAPI configuration (uncomment when connecting backend in Phase 2)
// import axios from 'axios';
// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
// const api = axios.create({
//   baseURL: API_BASE_URL,
//   headers: {
//     'Content-Type': 'application/json',
//   },
// });

// In-memory store to simulate status progression based on elapsed time since trigger
interface MockProgress {
  startTime: number;
  taskType: TaskType;
  repoIdentifier: string;
}
const activeMockAnalyses = new Map<string, MockProgress>();

export const reviewRepository = async (repoUrl: string, task: TaskType): Promise<{ taskId: string }> => {
  try {
    // Placeholder FastAPI call:
    // const response = await api.post('/analyze/url', { repoUrl, task });
    // return response.data;
  } catch (error) {
    console.warn("Backend API not connected, falling back to mock behavior.", error);
  }

  const taskId = `task_${Math.random().toString(36).substring(2, 11)}`;
  activeMockAnalyses.set(taskId, {
    startTime: Date.now(),
    taskType: task,
    repoIdentifier: repoUrl,
  });
  return { taskId };
};

export const uploadRepository = async (file: File, task: TaskType): Promise<{ taskId: string }> => {
  try {
    // Placeholder FastAPI call:
    // const formData = new FormData();
    // formData.append('file', file);
    // formData.append('task', task);
    // const response = await api.post('/analyze/upload', formData, {
    //   headers: { 'Content-Type': 'multipart/form-data' }
    // });
    // return response.data;
  } catch (error) {
    console.warn("Backend API not connected, falling back to mock behavior.", error);
  }

  const taskId = `task_${Math.random().toString(36).substring(2, 11)}`;
  activeMockAnalyses.set(taskId, {
    startTime: Date.now(),
    taskType: task,
    repoIdentifier: file.name,
  });
  return { taskId };
};

export const getStatus = async (taskId: string): Promise<{
  status: MultiAgentStatus;
  resultText: string | null;
  isDone: boolean;
}> => {
  try {
    // Placeholder FastAPI call:
    // const response = await api.get(`/status/${taskId}`);
    // return response.data;
  } catch (error) {
    console.warn("Backend API not connected, falling back to mock behavior.", error);
  }

  const progress = activeMockAnalyses.get(taskId);
  if (!progress) {
    return {
      status: {
        planner: { status: 'waiting', message: 'Waiting...' },
        retriever: { status: 'waiting', message: 'Waiting...' },
        reviewer: { status: 'waiting', message: 'Waiting...' },
        critic: { status: 'waiting', message: 'Waiting...' },
      },
      resultText: null,
      isDone: false,
    };
  }

  // Progression timings:
  // Planner processing: 0-3s, Completed: >3s
  // Retriever processing: 3-6s, Completed: >6s
  // Reviewer processing: 6-9s, Completed: >9s
  // Critic processing: 9-12s, Completed: >12s
  const elapsed = (Date.now() - progress.startTime) / 1000;

  const status: MultiAgentStatus = {
    planner: { status: 'waiting', message: 'Waiting...' },
    retriever: { status: 'waiting', message: 'Waiting...' },
    reviewer: { status: 'waiting', message: 'Waiting...' },
    critic: { status: 'waiting', message: 'Waiting...' },
  };

  // Planner Agent
  if (elapsed < 3) {
    status.planner = { status: 'processing', message: 'Reviewing project structure...' };
  } else {
    status.planner = { status: 'completed', message: 'Completed: Analysis blueprint and goals generated.' };
  }

  // Retriever Agent
  if (elapsed < 3) {
    status.retriever = { status: 'waiting', message: 'Waiting for planner agent...' };
  } else if (elapsed < 6) {
    status.retriever = { status: 'processing', message: `Indexing directories and parsing syntax in ${progress.repoIdentifier}...` };
  } else {
    status.retriever = { status: 'completed', message: 'Completed: Indexed all files and cached code context.' };
  }

  // Reviewer Agent
  if (elapsed < 6) {
    status.reviewer = { status: 'waiting', message: 'Waiting for indexing to complete...' };
  } else if (elapsed < 9) {
    status.reviewer = { status: 'processing', message: `Running heuristics for task: '${progress.taskType}'...` };
  } else {
    status.reviewer = { status: 'completed', message: 'Completed: Evaluation finished and code problems recorded.' };
  }

  // Critic Agent
  if (elapsed < 9) {
    status.critic = { status: 'waiting', message: 'Waiting for reviewer evaluation...' };
  } else if (elapsed < 12) {
    status.critic = { status: 'processing', message: 'Auditing reviewer results and preparing markdown report...' };
  } else {
    status.critic = { status: 'completed', message: 'Completed: Audit report approved and signed off.' };
  }

  const isDone = elapsed >= 12;
  const resultText = isDone ? generateMockResultText(progress.taskType, progress.repoIdentifier) : null;

  return { status, resultText, isDone };
};

function generateMockResultText(task: TaskType, repoName: string): string {
  const dateStr = new Date().toLocaleString();
  const titleMap: Record<TaskType, string> = {
    review: 'Repository Structure & Security Audit',
    explain: 'Codebase Walkthrough & High-Level Design',
    tests: 'Automated Test Suite Proposals',
    bugs: 'Bug Finder & Quality Hotspots'
  };

  const overviewMap: Record<TaskType, string> = {
    review: 'Detailed architectural assessment and dependency scanning results.',
    explain: 'Summary of how modules are connected and flow patterns within the codebase.',
    tests: 'Outline of test specifications and sample Unit Tests generated for your components.',
    bugs: 'Static analysis audit reporting code concerns and logic improvements.'
  };

  const detailedReportMap: Record<TaskType, string> = {
    review: `
### Architecture Status
- **Standard Layout**: The codebase adheres to structured client separation. React hooks are isolated appropriately.
- **Dependency Scan**: 0 critical, 2 warning level out-of-date assets flagged.

### Security Scan
- **Hardcoded Secrets**: Not detected. Verified configuration schemas are clear.
- **Data Escapes**: Sanity checks verified in state binders.

### Improvement Roadmap
1. Refactor component context definitions to optimize re-renders.
2. Upgrade dependency bundler configuration for production optimizations.
`,
    explain: `
### Codebase Components
- \`src/main.tsx\`: Mounts the React component tree and hooks up styles.
- \`src/App.tsx\`: Acts as the central container manager.
- \`src/context/AnalysisContext.tsx\`: Serves as the state broker, tracking input, active task, status polling, and outputs.

### Architecture Flow
1. User provides a GitHub link or drops a zip file.
2. The context requests analysis status updates from the backend services.
3. The multi-agent pipeline resolves files step-by-step.
`,
    tests: `
### Sample Component Test

\`\`\`typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { PrimaryButton } from '../PrimaryButton';
import { vi } from 'vitest';

describe('PrimaryButton Component', () => {
  it('triggers action on user click', () => {
    const mockClick = vi.fn();
    render(<PrimaryButton onClick={mockClick}>Activate</PrimaryButton>);
    
    const element = screen.getByRole('button', { name: /activate/i });
    fireEvent.click(element);
    
    expect(mockClick).toHaveBeenCalledTimes(1);
  });
});
\`\`\`

### Recommended Scope
- Focus tests on state workflows in the context layer.
- Integrate unit verification on standard utility modules.
`,
    bugs: `
### Code Quality Hotspots

#### Hotspot 1: Missing Bounds Check
- **File**: \`src/components/TaskSelector.tsx\`
- **Details**: Optional selector accessing elements on index.
- **Recommendation**: Integrate fallback values.
\`\`\`diff
- const task = options[index];
+ const task = options?.[index] ?? 'review';
\`\`\`

#### Hotspot 2: Non-cleared Timer Interval
- **File**: \`src/context/AnalysisContext.tsx\`
- **Details**: Ensure polling clear handlers are called on system unmounting.
`
  };

  return `
# DevMind Agent Analysis: ${titleMap[task]}
- **Target Repository**: \`${repoName}\`
- **Execution Date**: \`${dateStr}\`
- **Analysis Status**: \`SUCCESS\`

---

## 1. Overview
${overviewMap[task]}

## 2. Multi-Agent Agent Activity Timeline
- **Planner Agent**: Generated blueprint and parsed requirements.
- **Retriever Agent**: Parsed workspace files and matched imports.
- **Reviewer Agent**: Conducted deep file scans and identified code characteristics.
- **Critic Agent**: Audited and compiled findings.

## 3. Findings & Reports
${detailedReportMap[task]}

---
*DevMind Agent Pipeline - Phase 1*
`;
}
