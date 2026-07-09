import React, { useState } from 'react';
import { ChatSidebar } from './ChatSidebar';
import { ChatWindow } from './ChatWindow';

export const ChatWorkspace: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  return (
    <div className="chat-workspace relative flex w-full h-full overflow-hidden">
      {/* Backdrop overlay for mobile when sidebar is open */}
      {isSidebarOpen && (
        <div 
          className="chat-sidebar-backdrop md:hidden absolute inset-0 bg-black/60 z-40 transition-opacity"
          onClick={closeSidebar}
        />
      )}
      
      {/* Sidebar with open state class passed directly */}
      <ChatSidebar isOpen={isSidebarOpen} />

      {/* Main chat window, pass down toggle control */}
      <div className="chat-window-wrapper flex-1 h-full min-w-0">
        <ChatWindow onToggleSidebar={toggleSidebar} />
      </div>
    </div>
  );
};
