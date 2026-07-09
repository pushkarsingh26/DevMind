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
    <aside className={`chat-sidebar ${isOpen ? 'chat-sidebar--open' : ''}`}>
      {/* Repository Grounding Selector */}
      <div className="chat-sidebar-section">
        <RepositorySelector
          repositories={repositories}
          selectedId={selectedRepositoryId}
          onSelect={selectRepository}
          disabled={activeConversation !== null}
        />
      </div>

      {/* Control Actions & Search */}
      <div className="chat-sidebar-section border-t border-dark-800">
        <div className="search-input-wrapper">
          <Search className="search-input-icon" />
          <input
            type="text"
            className="search-input-field"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <button
          onClick={handleNewChat}
          disabled={!selectedRepositoryId}
          className={`new-chat-btn ${!selectedRepositoryId ? 'new-chat-btn--disabled' : ''}`}
        >
          <Plus className="w-4 h-4" />
          <span>NEW CONVERSATION</span>
        </button>
      </div>

      {/* Conversation List */}
      <div className="chat-conversations-list flex-1 overflow-y-auto">
        <div className="px-4 py-2 text-[10px] text-dark-500 font-mono tracking-wider uppercase">
          CHATS ({conversations.length})
        </div>

        {isLoadingConversations ? (
          <div className="flex items-center justify-center p-8 text-cyan-400 gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-xs font-mono">LOADING CHATS...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-6 text-center text-xs text-dark-600 font-mono">
            {selectedRepositoryId
              ? 'No conversations found. Click "New Conversation" above.'
              : 'Select a repository above to browse conversations.'}
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = activeConversation?.id === conv.id;
            const updatedTime = new Date(conv.updated_at).toLocaleDateString([], {
              month: 'short',
              day: 'numeric',
            });

            return (
              <div
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`conversation-item ${isActive ? 'conversation-item--active' : ''}`}
              >
                <div className="conversation-item-icon">
                  <MessageSquare className="w-4 h-4 text-cyan-500/80" />
                </div>
                <div className="conversation-item-content">
                  <span className="conversation-item-title">
                    {conv.title || 'Untitled Session'}
                  </span>
                  <div className="conversation-item-meta">
                    <span>{updatedTime}</span>
                    <span>•</span>
                    <span>{conv.message_count} messages</span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Are you sure you want to delete this chat session?')) {
                      deleteConversation(conv.id);
                    }
                  }}
                  className="conversation-item-delete"
                  title="Delete chat session"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>
      <ChatExportMenu />
    </aside>
  );
};
