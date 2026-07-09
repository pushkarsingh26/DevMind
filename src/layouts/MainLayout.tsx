import React, { useState } from 'react';
import { Navbar } from '../components/Navbar';
import { HistorySidebar } from '../components/HistorySidebar';
import { ToastContainer } from '../components/ToastContainer';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  return (
    <div className="min-h-screen bg-dark-950 text-dark-100 flex flex-col font-mono selection:bg-brand-500/30 selection:text-white">
      {/* Top Navbar with drawer triggers */}
      <Navbar onOpenHistory={() => setIsHistoryOpen(true)} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8">
        {children}
      </main>

      {/* Dynamic Toast notifications overlay */}
      <ToastContainer />

      {/* History Slide-out Panel Drawer */}
      <HistorySidebar isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />

      {/* Developer Footer */}
      <footer className="border-t border-dark-900 bg-dark-950 px-6 py-4 text-center text-[10px] text-dark-600 font-mono print:hidden">
        DevMind © {new Date().getFullYear()} — Phase 5 AI Code Intelligence Engine. Built By Pushkar Chhokar.
      </footer>
    </div>
  );
};
