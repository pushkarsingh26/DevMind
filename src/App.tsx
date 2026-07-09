import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AnalysisProvider } from './context/AnalysisContext';
import { ChatProvider } from './chat/ChatContext';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { ChatPage } from './pages/ChatPage';

function App() {
  return (
    <BrowserRouter>
      <AnalysisProvider>
        <ChatProvider>
          <MainLayout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/chat" element={<ChatPage />} />
            </Routes>
          </MainLayout>
        </ChatProvider>
      </AnalysisProvider>
    </BrowserRouter>
  );
}

export default App;
