import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AnalysisProvider } from './context/AnalysisProvider';
import { WorkflowProvider } from './context/WorkflowProvider';
import { ChatProvider } from './chat/ChatProvider';
import { MainLayout } from './layouts/MainLayout';
import { Loader2 } from 'lucide-react';
import ErrorBoundary from './components/ErrorBoundary';

// Lazy-load page components
const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const RepositoriesPage = React.lazy(() => import('./pages/RepositoriesPage'));
const ChatPage = React.lazy(() => import('./pages/ChatPage').then(m => ({ default: m.ChatPage })));
const ReportsPage = React.lazy(() => import('./pages/ReportsPage'));
const HistoryPage = React.lazy(() => import('./pages/HistoryPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));
const FuturePage = React.lazy(() => import('./pages/FuturePage'));
const AgentWorkspacePage = React.lazy(() => import('./pages/AgentWorkspacePage'));
const KnowledgeGraphPage = React.lazy(() => import('./pages/KnowledgeGraphPage'));
const RepositoryAnalysisPage = React.lazy(() => import('./pages/RepositoryAnalysisPage'));
const PlanningPage = React.lazy(() => import('./pages/PlanningPage'));
const ExecutionPage = React.lazy(() => import('./pages/ExecutionPage'));
const CollaborationPage = React.lazy(() => import('./pages/CollaborationPage'));
const MemoryPage = React.lazy(() => import('./pages/MemoryPage').then(m => ({ default: m.MemoryPage })));
const ReasoningPage = React.lazy(() => import('./pages/ReasoningPage').then(m => ({ default: m.ReasoningPage })));

// Dynamic loading spinner fallback
const LoadingFallback = () => (
  <div className="flex flex-col items-center justify-center min-h-[400px] text-cyan-400 gap-3 font-mono">
    <Loader2 className="w-8 h-8 animate-spin" />
    <span className="text-xs uppercase tracking-widest font-semibold">Loading Page Workspace...</span>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <AnalysisProvider>
        <WorkflowProvider>
          <ChatProvider>
            <MainLayout>
              <Suspense fallback={<LoadingFallback />}>
                <ErrorBoundary>
                  <Routes>
                    {/* Redirect root to dashboard */}
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/repositories" element={<RepositoriesPage />} />
                    <Route path="/analysis" element={<RepositoryAnalysisPage />} />
                    <Route path="/planning" element={<PlanningPage />} />
                    <Route path="/execution/:workflowId" element={<ExecutionPage />} />
                    <Route path="/collaboration/:workflowId" element={<CollaborationPage />} />
                    <Route path="/memory/:repositoryId" element={<MemoryPage />} />
                    <Route path="/reasoning/:repositoryId" element={<ReasoningPage />} />
                    <Route path="/chat" element={<ChatPage />} />
                    <Route path="/agents" element={<AgentWorkspacePage />} />
                    <Route path="/graph" element={<KnowledgeGraphPage />} />
                    <Route path="/reports" element={<ReportsPage />} />
                    <Route path="/history" element={<HistoryPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/future" element={<FuturePage />} />
                    
                    {/* Fallback redirect */}
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </ErrorBoundary>
              </Suspense>
            </MainLayout>
          </ChatProvider>
        </WorkflowProvider>
      </AnalysisProvider>
    </BrowserRouter>
  );
}

export default App;
