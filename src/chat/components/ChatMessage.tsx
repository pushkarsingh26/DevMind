import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { Copy, Check, Info } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../types';
import { CitationCard } from './CitationCard';
import { FollowUpSuggestions } from './FollowUpSuggestions';

// Import CSS for code syntax highlighting if available
import 'highlight.js/styles/github-dark.css';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
  onFollowUpClick?: (suggestion: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isStreaming = false,
  onFollowUpClick,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedTime = new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--assistant'}`}>
      <div className={`message-bubble ${isUser ? 'message-bubble--user' : 'message-bubble--assistant'}`}>
        {/* Top Info Bar */}
        <div className="message-meta-bar">
          <span className="message-role-label">
            {isUser ? 'USER' : 'DEVMIND AI'}
          </span>
          <div className="message-meta-right">
            {!isUser && message.model && (
              <span className="message-model-badge">
                {message.provider?.toUpperCase()} / {message.model.split('/').pop()?.toUpperCase()}
              </span>
            )}
            <span className="message-time">{formattedTime}</span>
            <button
              onClick={copyToClipboard}
              className="message-action-btn"
              title="Copy message"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Message Content */}
        <div className="message-body">
          {isUser ? (
            <p className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed">{message.content}</p>
          ) : (
            <div className="markdown-body font-sans text-[13px] leading-relaxed">
              <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Heuristic Fallback Warning */}
        {message.is_fallback && !isUser && (
          <div className="message-warning-banner">
            <Info className="w-4 h-4 text-amber-500 shrink-0" />
            <span>LLMs offline. Static heuristics resolved this request.</span>
          </div>
        )}

        {/* Citations section */}
        {message.citations && message.citations.length > 0 && (
          <div className="message-citations-section">
            <span className="citations-label">Sources Cited:</span>
            <div className="citations-grid">
              {message.citations.map((citation, idx) => (
                <CitationCard key={idx} citation={citation} index={idx} />
              ))}
            </div>
          </div>
        )}

        {/* Telemetry Footer */}
        {!isUser && !isStreaming && message.latency && (
          <div className="message-telemetry-bar">
            <span>Latency: {message.latency.toFixed(2)}s</span>
            <span>•</span>
            <span>Tokens: {message.prompt_tokens || 0} prompt / {message.completion_tokens || 0} completion</span>
          </div>
        )}
      </div>

      {/* Follow-up question suggestion pills (rendered below the bubble in the same row context) */}
      {!isUser && !isStreaming && message.follow_up_questions && message.follow_up_questions.length > 0 && onFollowUpClick && (
        <FollowUpSuggestions
          suggestions={message.follow_up_questions}
          onClick={onFollowUpClick}
        />
      )}
    </div>
  );
};
