/**
 * Phase 5 - ChatContext (Performance Optimized)
 * Key optimizations:
 * - Context value memoized - no identity churn
 * - Streaming token updates batched via requestAnimationFrame
 * - All callbacks wrapped in useCallback
 * - Abort controller + rAF cleaned on unmount
 */
import { createContext, useContext } from 'react';
import type { ChatContextType } from './types';

export const ChatContext = createContext<ChatContextType | null>(null);

export function useChatContext(): ChatContextType {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChatContext must be used within <ChatProvider>');
  return ctx;
}
