import React from 'react';
import { Navbar } from '../components/Navbar';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-dark-950 text-dark-100 flex flex-col font-mono selection:bg-brand-500/30 selection:text-white">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8">
        {children}
      </main>

      {/* Developer Footer */}
      <footer className="border-t border-dark-900 bg-dark-950 px-6 py-4 text-center text-[10px] text-dark-600 font-mono">
        DevMind © {new Date().getFullYear()} — Phase 1 Base Infrastructure. Built for Pushkar Chhokar.
      </footer>
    </div>
  );
};
