import React, { useState, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { Copy, Check, Info, Bot, User } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../types';
import { CitationCard } from './CitationCard';
import { FollowUpSuggestions } from './FollowUpSuggestions';
import { motion } from 'framer-motion';

import 'highlight.js/styles/github-dark.css';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
  onFollowUpClick?: (suggestion: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = React.memo(({
  message,
  isStreaming = false,
  onFollowUpClick,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const copyToClipboard = useCallback(() => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  const formattedTime = useMemo(() => new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  }), [message.created_at]);

  // Only animate new/streaming messages — historical messages use a plain div to
  // avoid Framer Motion overhead on every scroll repaint.
  const Wrapper = isStreaming ? motion.div : 'div' as any;
  const wrapperProps = isStreaming ? {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.25, ease: 'easeOut' },
  } : {};

  return (
    <Wrapper
      {...wrapperProps}
      className={`w-full flex flex-col gap-2.5 ${isUser ? 'items-end' : 'items-start'}`}
    >
      <div 
        className={`max-w-[85%] rounded-2xl p-4.5 border shadow-lg flex flex-col gap-3.5 relative overflow-hidden transition-all duration-200
          ${isUser 
            ? 'bg-purple-500/10 border-purple-500/25 text-dark-100 rounded-br-sm' 
            : 'bg-[#0f172a]/90 border-dark-800/80 text-dark-200 rounded-bl-sm'
          }`}
      >
        
        {/* Telemetry & Header Metadata Bar */}
        <div className="flex items-center justify-between border-b border-dark-850/60 pb-2.5 gap-6 font-mono text-[9px] tracking-wider font-bold">
          <div className="flex items-center gap-2">
            {isUser ? (
              <div className="p-1 rounded-md bg-purple-500/20 text-purple-400 border border-purple-500/20 shrink-0">
                <User className="w-3 h-3" />
              </div>
            ) : (
              <div className="p-1 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/20 shrink-0">
                <Bot className="w-3 h-3" />
              </div>
            )}
            <span className={isUser ? 'text-purple-400' : 'text-cyan-400'}>
              {isUser ? 'USER IDENTIFIER' : 'DEVMIND COGNITIVE CORE'}
            </span>
          </div>

          <div className="flex items-center gap-3 text-dark-500">
            {!isUser && message.model && (
              <span className="bg-[#070b14] border border-dark-800 text-dark-400 px-1.5 py-0.5 rounded-md font-semibold text-[8px]">
                {message.provider?.toUpperCase()} / {message.model.split('/').pop()?.toUpperCase()}
              </span>
            )}
            <span className="text-[8px]">{formattedTime}</span>
            <button
              onClick={copyToClipboard}
              className="text-dark-500 hover:text-dark-300 p-0.5 hover:bg-dark-800 rounded transition-colors cursor-pointer shrink-0"
              title="Copy message contents"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Message body with custom styling overrides for lists & code */}
        <div className="text-xs leading-relaxed break-words font-sans">
          {isUser ? (
            <p className="whitespace-pre-wrap font-sans text-xs text-dark-100">{message.content}</p>
          ) : (
            <div className="prose prose-invert max-w-none text-xs text-dark-200/90 font-sans space-y-1">
              <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Warning banner for fallbacks */}
        {message.is_fallback && !isUser && (
          <div className="flex items-center gap-2 bg-amber-950/15 border border-amber-500/20 text-amber-400 p-2.5 rounded-xl font-mono text-[9px] font-semibold mt-1">
            <Info className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>LLMs offline. Static analyzer resolved this query.</span>
          </div>
        )}

        {/* Citations section */}
        {message.citations && message.citations.length > 0 && (
          <div className="border-t border-dark-850/60 pt-3 mt-1 space-y-2">
            <span className="text-[9px] font-mono text-dark-500 font-bold uppercase tracking-wider block">Grounded File Sources:</span>
            <div className="grid grid-cols-1 gap-2">
              {message.citations.map((citation, idx) => (
                <CitationCard key={idx} citation={citation} index={idx} />
              ))}
            </div>
          </div>
        )}

        {/* Chunks latency telemetry */}
        {!isUser && !isStreaming && message.latency && (
          <div className="border-t border-dark-850/40 pt-2 mt-0.5 flex items-center justify-between text-[8px] font-mono text-dark-500 uppercase tracking-widest font-semibold">
            <span>Latency: {message.latency.toFixed(2)}s</span>
            <span>Tokens: {message.prompt_tokens || 0} prompt / {message.completion_tokens || 0} completion</span>
          </div>
        )}
      </div>

      {/* Follow-up query Suggestions (rendered directly underneath the bubble) */}
      {!isUser && !isStreaming && message.follow_up_questions && message.follow_up_questions.length > 0 && onFollowUpClick && (
        <div className="max-w-[85%] self-start mt-1">
          <FollowUpSuggestions
            suggestions={message.follow_up_questions}
            onClick={onFollowUpClick}
          />
        </div>
      )}
    </Wrapper>
  );
});
