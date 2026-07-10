import React, { useState, useEffect } from 'react';
import { Plus, Search, Trash2, MessageSquare, Loader2 } from 'lucide-react';
import { useChatContext } from '../ChatContext';
import { RepositorySelector } from './RepositorySelector';
import { ChatExportMenu } from './ChatExportMenu';

interface ChatSidebarProps {
  isOpen?: boolean;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({ isOpen = false }) => {
  const {
    conversations,
    activeConversation,
    repositories,
    selectedRepositoryId,
    isLoadingConversations,
    selectRepository,
    startNewConversation,
    selectConversation,
    deleteConversation,
    searchConversations,
  } = useChatContext();

  const [search, setSearch] = useState('');

  // Debounced search trigger (300ms)
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      searchConversations(search);
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [search, searchConversations]);

  const handleNewChat = () => {
    if (!selectedRepositoryId) return;
    startNewConversation();
  };

  return (
    <aside className={`chat-sidebar h-full flex flex-col bg-[#0f172a]/95 border-r border-dark-800/80 shrink-0 ${isOpen ? 'chat-sidebar--open' : ''}`}>
      
      {/* Repository Grounding Selector */}
      <div className="p-4.5 space-y-4 shrink-0">
        <RepositorySelector
          repositories={repositories}
          selectedId={selectedRepositoryId}
          onSelect={selectRepository}
          disabled={activeConversation !== null && activeConversation.message_count > 0}
        />
      </div>

      {/* Control Actions & Search */}
      <div className="p-4.5 border-t border-dark-850/60 bg-[#070b14]/30 space-y-3 shrink-0">
        <div className="relative w-full">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-500 pointer-events-none" />
          <input
            type="text"
            className="w-full bg-[#070b14]/80 border border-dark-800 hover:border-dark-700/80 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/10 rounded-xl pl-10 pr-4 py-2.5 text-xs text-dark-200 outline-none transition-all duration-200 font-mono placeholder-dark-600"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <button
          onClick={handleNewChat}
          disabled={!selectedRepositoryId}
          className={`flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-400 hover:text-cyan-300 font-mono text-xs font-bold rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed select-none cursor-pointer
            ${!selectedRepositoryId ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <Plus className="w-3.5 h-3.5" />
          <span>NEW CONVERSATION</span>
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto flex flex-col py-2 border-t border-dark-850/60 scrollbar-thin">
        <div className="px-4 py-2 text-[9px] text-dark-500 font-mono tracking-widest uppercase font-bold">
          CONVERSATIONS ({conversations.length})
        </div>

        {isLoadingConversations ? (
          <div className="flex flex-col items-center justify-center py-12 text-cyan-400 gap-2 shrink-0">
            <Loader2 className="w-4.5 h-4.5 animate-spin" />
            <span className="text-[10px] font-mono tracking-wider">INDEXING CHATS...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-6 text-center text-xs text-dark-600 font-mono shrink-0">
            {selectedRepositoryId
              ? 'No sessions found. Create a new one.'
              : 'Select a codebase above.'}
          </div>
        ) : (
          <div className="flex flex-col">
            {conversations.map((conv) => {
              const isActive = activeConversation?.id === conv.id;
              const updatedTime = new Date(conv.updated_at).toLocaleDateString([], {
                month: 'short',
                day: 'numeric',
              });

              return (
                <div
                  key={conv.id}
                  onClick={() => selectConversation(conv.id)}
                  className={`flex items-center gap-3.5 px-4 py-3 border-b border-dark-850/20 last:border-b-0 cursor-pointer transition-all duration-150 group select-none relative
                    ${isActive ? 'bg-dark-900 border-l-2 border-cyan-500 text-cyan-400' : 'hover:bg-dark-900/40 text-dark-300 hover:text-dark-100'}
                  `}
                >
                  <div className="shrink-0">
                    <MessageSquare className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-dark-500'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className={`text-xs block truncate ${isActive ? 'font-semibold' : ''}`}>
                      {conv.title || 'Untitled Session'}
                    </span>
                    <div className="flex items-center gap-1.5 text-[9px] font-mono text-dark-500 mt-0.5">
                      <span>{updatedTime}</span>
                      <span>•</span>
                      <span>{conv.message_count} messages</span>
                    </div>
                  </div>
                  
                  {/* Delete Conversation action */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm('Are you sure you want to delete this chat session?')) {
                        deleteConversation(conv.id);
                      }
                    }}
                    className="p-1 rounded-lg hover:bg-rose-500/10 text-dark-500 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-opacity duration-150 bg-transparent border-none cursor-pointer shrink-0"
                    title="Delete chat session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Export menu footer */}
      <ChatExportMenu />
    </aside>
  );
};
