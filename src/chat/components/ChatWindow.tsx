import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Terminal, Loader2, ArrowDown, ChevronRight, Menu } from 'lucide-react';
import { useChatContext } from '../ChatContext';
import { ChatMessage } from './ChatMessage';
import { TypingIndicator } from './TypingIndicator';

interface ChatWindowProps {
  onToggleSidebar?: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ onToggleSidebar }) => {
  const {
    activeConversation,
    messages,
    isStreaming,
    streamingContent,
    streamingCitations,
    streamingFollowUps,
    isLoadingMessages,
    hasMoreMessages,
    loadMoreMessages,
    sendMessage,
    selectedRepositoryId,
    repositories,
  } = useChatContext();

  const [input, setInput] = useState('');
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  const listContainerRef = useRef<HTMLDivElement>(null);
  const scrollSentinelRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus input on activeConversation mount or after isStreaming becomes false
  useEffect(() => {
    if (!isStreaming && activeConversation) {
      const timer = setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [activeConversation, isStreaming]);

  // 1. Auto-scroll to bottom on new messages
  useEffect(() => {
    if (listContainerRef.current) {
      listContainerRef.current.scrollTop = listContainerRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  // 2. Detect scroll positions for loading older messages (pagination)
  const handleScroll = () => {
    const el = listContainerRef.current;
    if (!el) return;

    const isScrolledUp = el.scrollHeight - el.scrollTop - el.clientHeight > 300;
    setShowScrollBottom(isScrolledUp);

    if (el.scrollTop === 0 && hasMoreMessages && !isLoadingMessages) {
      const prevHeight = el.scrollHeight;
      loadMoreMessages().then(() => {
        setTimeout(() => {
          if (el) {
            el.scrollTop = el.scrollHeight - prevHeight;
          }
        }, 50);
      });
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    const text = input.trim();
    setInput('');
    textareaRef.current?.focus();
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming) {
        handleSend();
      }
    }
  };

  const scrollToBottom = () => {
    if (listContainerRef.current) {
      listContainerRef.current.scrollTo({
        top: listContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  };

  if (!activeConversation) {
    return (
      <div className="chat-window flex flex-col items-center justify-center text-center p-8 h-full relative bg-[#0b111e]">
        <div className="absolute top-4 left-4 md:hidden">
          <button 
            onClick={onToggleSidebar}
            className="chat-sidebar-toggle-btn"
          >
            <Menu className="w-4 h-4" />
            <span>Select Repository</span>
          </button>
        </div>
        <div className="max-w-md space-y-5">
          <div className="bg-brand-600/10 w-14 h-14 rounded-lg border border-brand-500/25 text-brand-400 flex items-center justify-center mx-auto shadow-[0_0_15px_rgba(14,165,233,0.15)]">
            <Terminal className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-dark-100 font-bold text-base mb-2 font-mono">DevMind Grounded Chat</h3>
            <p className="text-xs text-dark-400 leading-relaxed font-mono">
              Ask questions directly grounded in your codebase's vector store index.
            </p>
          </div>
          <div className="border border-dark-850 bg-dark-900/30 rounded-lg p-4 text-[11px] font-mono text-dark-500 text-left space-y-2 leading-relaxed">
            <p className="font-semibold text-dark-300">💡 Quick Start Guide:</p>
            <ol className="list-decimal pl-4 space-y-1">
              <li>Open the sidebar to select an indexed repository.</li>
              <li>DevMind will automatically initialize a secure context-grounded chat session.</li>
              <li>Ask about architecture, routing, database models, or find code bugs.</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  // Construct active repository name — memoized to avoid re-running find() on every render
  const repoName = useMemo(() => {
    const activeRepo = repositories.find(r => r.id === selectedRepositoryId);
    return activeRepo ? `${activeRepo.owner}/${activeRepo.name}` : 'Grounding Standby';
  }, [repositories, selectedRepositoryId]);

  // Construct streaming message object if isStreaming is active
  const activeStreamMessage = isStreaming && streamingContent ? {
    id: 'streaming_msg',
    conversation_id: activeConversation.id,
    role: 'assistant' as const,
    content: streamingContent,
    citations: streamingCitations,
    follow_up_questions: streamingFollowUps,
    is_fallback: false,
    created_at: new Date().toISOString(),
  } : null;

  return (
    <div className="chat-window relative flex flex-col h-full bg-[#0b111e]">
      {/* Top Header Bar */}
      <div className="chat-window-header border-b border-dark-900 bg-dark-950/60 backdrop-blur-md px-4 py-3 flex items-center gap-3 shrink-0">
        <button 
          onClick={onToggleSidebar}
          className="chat-sidebar-toggle-btn md:hidden"
          title="Toggle chat sessions sidebar"
        >
          <Menu className="w-4 h-4" />
        </button>
        <div className="chat-header-info flex items-center gap-2 truncate">
          <span className="text-[10px] font-mono text-dark-500 uppercase tracking-wider">GROUNDED:</span>
          <span className="text-xs font-semibold text-cyan-400 font-mono truncate">{repoName}</span>
          <span className="text-dark-600 font-mono">/</span>
          <span className="text-xs font-medium text-dark-300 truncate">{activeConversation.title || 'Untitled Session'}</span>
        </div>
      </div>

      {/* Scroll to Bottom Utility */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="chat-scroll-bottom-btn"
          title="Scroll to bottom"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}

      {/* Message List area */}
      <div
        ref={listContainerRef}
        onScroll={handleScroll}
        className="chat-messages-container flex-1 overflow-y-auto"
      >
        {/* Load older messages sentinel */}
        {hasMoreMessages && (
          <div className="flex items-center justify-center p-4 border-b border-dark-900 bg-dark-950/40">
            {isLoadingMessages ? (
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
            ) : (
              <span className="text-[10px] text-dark-500 font-mono">SCROLL UP TO LOAD OLDER MESSAGES</span>
            )}
          </div>
        )}

        <div className="chat-messages-inner">
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onFollowUpClick={setInput}
            />
          ))}

          {/* Render streaming delta in real time */}
          {activeStreamMessage && (
            <ChatMessage
              message={activeStreamMessage}
              isStreaming={true}
            />
          )}

          {/* Streaming bounce animation */}
          {isStreaming && !streamingContent && (
            <TypingIndicator />
          )}

          <div ref={scrollSentinelRef} />
        </div>
      </div>

      {/* Bottom Input Area */}
      <div className="chat-input-container shrink-0 border-t border-dark-900 bg-dark-950/40 p-4">
        <div className="chat-input-wrapper max-w-4xl mx-auto flex gap-3 items-end bg-[#090d16] border border-dark-800 rounded-lg p-2">
          <textarea
            ref={textareaRef}
            className="chat-input-textarea flex-1 min-h-[44px] max-h-[200px] bg-transparent text-xs font-mono text-dark-100 outline-none resize-none border-none p-2 focus:ring-0 leading-relaxed"
            placeholder={`Ask a question about ${activeConversation.title || 'the repository'}... (Enter to send, Shift+Enter for new lines)`}
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, 4000))}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className={`chat-send-btn ${(!input.trim() || isStreaming) ? 'chat-send-btn--disabled' : ''}`}
            title="Send message"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="chat-input-footer max-w-4xl mx-auto flex items-center justify-between mt-2 px-1">
          <span className="font-mono text-[9px] text-dark-600">
            MAX MESSAGE: {input.length} / 4000 CHARS
          </span>
          <span className="font-mono text-[9px] text-dark-600 flex items-center gap-1">
            <ChevronRight className="w-2.5 h-2.5 text-cyan-500" />
            CONTEXT: GROUNDED RAG PIPELINE
          </span>
        </div>
      </div>
    </div>
  );
};
