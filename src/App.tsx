import { AnalysisProvider } from './context/AnalysisContext';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';

function App() {
  return (
    <AnalysisProvider>
      <MainLayout>
        <Dashboard />
      </MainLayout>
    </AnalysisProvider>
  );
}

export default App;
