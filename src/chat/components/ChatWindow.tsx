import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Send, Loader2, ArrowDown, ChevronRight, Menu, MessageSquareCode, Sparkles } from 'lucide-react';
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

  const repoName = useMemo(() => {
    const activeRepo = repositories.find(r => r.id === selectedRepositoryId);
    return activeRepo ? `${activeRepo.owner}/${activeRepo.name}` : 'Grounding Codebase';
  }, [repositories, selectedRepositoryId]);

  const listContainerRef = useRef<HTMLDivElement>(null);
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

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (listContainerRef.current) {
      listContainerRef.current.scrollTop = listContainerRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const rafScrollRef = useRef<number | null>(null);

  // Register scroll listener as passive — must use imperative addEventListener
  useEffect(() => {
    const el = listContainerRef.current;
    if (!el) return;
    const onScroll = () => {
      if (rafScrollRef.current !== null) return; // throttle to one rAF per scroll burst
      rafScrollRef.current = requestAnimationFrame(() => {
        rafScrollRef.current = null;
        const container = listContainerRef.current;
        if (!container) return;
        const isScrolledUp = container.scrollHeight - container.scrollTop - container.clientHeight > 300;
        setShowScrollBottom(isScrolledUp);
        if (container.scrollTop === 0 && hasMoreMessages && !isLoadingMessages) {
          const prevHeight = container.scrollHeight;
          loadMoreMessages().then(() => {
            setTimeout(() => {
              if (container) container.scrollTop = container.scrollHeight - prevHeight;
            }, 50);
          });
        }
      });
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      el.removeEventListener('scroll', onScroll);
      if (rafScrollRef.current !== null) cancelAnimationFrame(rafScrollRef.current);
    };
  }, [hasMoreMessages, isLoadingMessages, loadMoreMessages]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return;
    const text = input.trim();
    setInput('');
    textareaRef.current?.focus();
    await sendMessage(text);
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming) handleSend();
    }
  }, [isStreaming, handleSend]);

  const scrollToBottom = useCallback(() => {
    if (listContainerRef.current) {
      listContainerRef.current.scrollTo({
        top: listContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, []);

  if (!activeConversation) {
    return (
      <div className="flex flex-col items-center justify-center text-center p-8 h-full relative bg-[#070b14] w-full">
        <div className="absolute top-4 left-4 md:hidden">
          <button 
            onClick={onToggleSidebar}
            className="flex items-center gap-2 px-3.5 py-2 border border-dark-850 hover:border-dark-750 bg-dark-900/60 text-dark-300 hover:text-dark-100 rounded-xl font-mono text-xs cursor-pointer"
          >
            <Menu className="w-4 h-4" />
            <span>Select Codebase</span>
          </button>
        </div>
        
        <div className="max-w-lg space-y-6">
          <div className="bg-purple-500/10 w-16 h-16 rounded-2xl border border-purple-500/25 text-purple-400 flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(168,85,247,0.15)] animate-pulse">
            <MessageSquareCode className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-dark-50 tracking-tight font-display">DevMind Grounded Chat</h3>
            <p className="text-xs text-dark-400 leading-relaxed font-sans mt-2 max-w-sm mx-auto">
              Ask deep questions grounded directly in your codebase's vector store indices.
            </p>
          </div>

          <div className="border border-dark-800/80 bg-dark-900/40 rounded-2xl p-5 text-left space-y-3.5 shadow-lg">
            <p className="font-semibold text-dark-200 font-display text-xs flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Grounded Chat Guide</span>
            </p>
            <ol className="list-decimal pl-4.5 space-y-2 text-dark-400 font-sans text-xs">
              <li>Select an indexed repository from the dropdown on the left.</li>
              <li>DevMind will verify index health and start a secure context-grounded session.</li>
              <li>Ask about architectural layering, component files, or query logic defects.</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }



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
    <div className="flex flex-col h-full bg-[#070b14] w-full relative">
      
      {/* Top Header Bar */}
      <div className="border-b border-dark-900 bg-[#070b14]/90 backdrop-blur-md px-5 py-4.5 flex items-center justify-between gap-4 shrink-0 z-10 shadow-sm">
        <div className="flex items-center gap-3 truncate min-w-0">
          <button 
            onClick={onToggleSidebar}
            className="md:hidden p-2 border border-dark-850 hover:border-dark-700 bg-dark-900/40 rounded-xl text-dark-300 hover:text-dark-100 cursor-pointer"
            title="Toggle chat sessions sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2 truncate text-xs font-mono">
            <span className="text-[10px] text-dark-500 uppercase tracking-widest font-bold">RAG CONTEXT:</span>
            <span className="text-cyan-400 font-semibold truncate">{repoName}</span>
            <span className="text-dark-600 font-semibold">/</span>
            <span className="text-dark-300 font-medium truncate max-w-[200px]">{activeConversation.title || 'Untitled Session'}</span>
          </div>
        </div>
      </div>

      {/* Scroll to Bottom Utility */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-28 right-6 bg-[#0f172a] border border-dark-800 hover:border-cyan-500/20 text-cyan-400 hover:text-cyan-300 p-2.5 rounded-full cursor-pointer z-20 shadow-[0_4px_15px_rgba(0,0,0,0.5)] transition-all"
          title="Scroll to bottom"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}

      {/* Message List area */}
      <div
        ref={listContainerRef}
        className="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin"
      >
        {hasMoreMessages && (
          <div className="flex items-center justify-center pb-6">
            {isLoadingMessages ? (
              <Loader2 className="w-4.5 h-4.5 text-cyan-400 animate-spin" />
            ) : (
              <button 
                onClick={loadMoreMessages}
                className="text-[9px] text-dark-500 hover:text-cyan-400 font-mono tracking-widest uppercase border border-dark-850 hover:border-cyan-500/20 px-3 py-1.5 rounded-xl bg-dark-900/30 transition-all cursor-pointer"
              >
                SCROLL UP OR CLICK TO LOAD OLDER
              </button>
            )}
          </div>
        )}

        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onFollowUpClick={setInput}
            />
          ))}

          {/* Render streaming delta */}
          {activeStreamMessage && (
            <ChatMessage
              message={activeStreamMessage}
              isStreaming={true}
            />
          )}

          {/* Streaming bounce animation */}
          {isStreaming && !streamingContent && (
            <div className="flex justify-start">
              <TypingIndicator />
            </div>
          )}
        </div>
      </div>

      {/* Bottom Input Area */}
      <div className="shrink-0 border-t border-dark-900/80 bg-[#070b14]/60 backdrop-blur-md p-4">
        <div className="max-w-4xl mx-auto space-y-2">
          
          {/* Custom Input box wrapper */}
          <div className="flex gap-3 items-end bg-[#0f172a]/80 border border-dark-800 focus-within:border-cyan-500/50 rounded-xl p-2.5 shadow-xl transition-all duration-200">
            <textarea
              ref={textareaRef}
              className="flex-1 min-h-[44px] max-h-[160px] bg-transparent text-xs font-mono text-dark-100 outline-none resize-none border-none p-1.5 focus:ring-0 leading-relaxed scrollbar-thin"
              placeholder={`Ask a question about ${activeConversation.title || 'the codebase'}... (Enter to send, Shift+Enter for new line)`}
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, 4000))}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              className={`p-2.5 rounded-lg flex items-center justify-center transition-all duration-150 shrink-0 select-none cursor-pointer
                ${(!input.trim() || isStreaming) 
                  ? 'bg-dark-850 text-dark-500 cursor-not-allowed' 
                  : 'bg-cyan-500 text-dark-950 font-bold hover:bg-cyan-400 hover:shadow-[0_0_12px_rgba(6,182,212,0.35)]'
                }`}
              title="Send message"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center justify-between px-1">
            <span className="font-mono text-[8px] text-dark-500 tracking-wider">
              CHARS: {input.length} / 4000
            </span>
            <span className="font-mono text-[8px] text-cyan-500 tracking-wider flex items-center gap-1">
              <ChevronRight className="w-3 h-3 text-cyan-400 animate-pulse" />
              GROUNDED VECTOR STORE INTERACTION
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
