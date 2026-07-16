import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAnalysis } from '../hooks/useAnalysis';
import type {
  ChatContextType, ChatMessage, CitationRef,
  Conversation, RepositoryListItem, SSEDonePayload,
} from './types';
import * as chatApi from './api';
import { ChatContext } from './ChatContext';

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [repositories, setRepositories] = useState<RepositoryListItem[]>([]);
  const [selectedRepositoryId, setSelectedRepositoryId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<CitationRef[]>([]);
  const [streamingFollowUps, setStreamingFollowUps] = useState<string[]>([]);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [messageOffset, setMessageOffset] = useState(0);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const rafRef = useRef<number | null>(null);
  const pendingTokenRef = useRef<string>('');
  const accumulatedContentRef = useRef<string>('');
  const analysis = useAnalysis();
  const wasAnalyzingRef = useRef(false);

  useEffect(() => {
    chatApi.listRepositories()
      .then(setRepositories)
      .catch((err) => console.warn('ChatContext: Failed to load repositories:', err));
  }, []);

  const selectRepository = useCallback((id: string) => {
    setSelectedRepositoryId(id);
    setActiveConversation(null);
    setMessages([]);
    setConversations([]);
    setIsLoadingConversations(true);
    chatApi.listConversations(id)
      .then(async (res) => {
        setConversations(res.conversations);
        if (res.conversations.length === 0) {
          try {
            const conv = await chatApi.startConversation(id, 'General Grounded Chat');
            setConversations([conv]);
            setActiveConversation(conv);
            setMessages([]);
            setMessageOffset(0);
            setHasMoreMessages(false);
          } catch (err: any) {
            setErrorMessage(err.message || 'Failed to start conversation');
          }
        } else {
          const latestConv = res.conversations[0];
          setActiveConversation(latestConv);
          setIsLoadingMessages(true);
          try {
            const result = await chatApi.getMessages(latestConv.id, 30, 0);
            setMessages(result.messages);
            setHasMoreMessages(result.has_more);
            setMessageOffset(result.messages.length);
          } catch (err: any) {
            setErrorMessage(err.message || 'Failed to load conversation messages');
          } finally {
            setIsLoadingMessages(false);
          }
        }
      })
      .catch((err) => setErrorMessage(err.message))
      .finally(() => setIsLoadingConversations(false));
  }, []);

  const selectRepositoryRef = useRef<(id: string) => void>(() => {});
  useEffect(() => { selectRepositoryRef.current = selectRepository; }, [selectRepository]);

  const readyRepositories = useMemo(
    () => repositories.filter((r) => r.status === 'READY'),
    [repositories]
  );

  useEffect(() => {
    if (wasAnalyzingRef.current && !analysis.isAnalyzing && analysis.parsedReport?.repository?.id) {
      const repoId = analysis.parsedReport.repository.id;
      chatApi.listRepositories()
        .then((repos) => { setRepositories(repos); selectRepositoryRef.current(repoId); })
        .catch((err) => console.warn('ChatContext: Failed to refresh repos after analysis:', err));
    }
    wasAnalyzingRef.current = analysis.isAnalyzing;
  }, [analysis.isAnalyzing, analysis.parsedReport]);

  const startNewConversation = useCallback(async (title?: string) => {
    if (!selectedRepositoryId) { setErrorMessage('Please select a repository first.'); return; }
    try {
      const conv = await chatApi.startConversation(selectedRepositoryId, title);
      setConversations((prev) => [conv, ...prev]);
      setActiveConversation(conv);
      setMessages([]);
      setMessageOffset(0);
      setHasMoreMessages(false);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to start conversation');
    }
  }, [selectedRepositoryId]);

  const selectConversation = useCallback(async (id: string) => {
    setIsLoadingMessages(true);
    setMessages([]);
    setMessageOffset(0);
    try {
      const conv = await chatApi.getConversation(id);
      setActiveConversation(conv);
      const result = await chatApi.getMessages(id, 30, 0);
      setMessages(result.messages);
      setHasMoreMessages(result.has_more);
      setMessageOffset(result.messages.length);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  const loadMoreMessages = useCallback(async () => {
    if (!activeConversation || isLoadingMessages || !hasMoreMessages) return;
    setIsLoadingMessages(true);
    try {
      const result = await chatApi.getMessages(activeConversation.id, 30, messageOffset);
      setMessages((prev) => [...result.messages, ...prev]);
      setHasMoreMessages(result.has_more);
      setMessageOffset((prev) => prev + result.messages.length);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setIsLoadingMessages(false);
    }
  }, [activeConversation, isLoadingMessages, hasMoreMessages, messageOffset]);

  const sendMessage = useCallback(async (text: string) => {
    if (!activeConversation || isStreaming) return;
    abortRef.current?.abort();
    if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }

    const tempUserId = 'temp_' + Date.now();
    const optimisticUser: ChatMessage = {
      id: tempUserId, conversation_id: activeConversation.id, role: 'user',
      content: text, citations: [], follow_up_questions: [], is_fallback: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);
    setIsStreaming(true);
    setStreamingContent('');
    setStreamingCitations([]);
    setStreamingFollowUps([]);
    accumulatedContentRef.current = '';
    pendingTokenRef.current = '';

    let finalCitations: CitationRef[] = [];
    let finalFollowUps: string[] = [];

    const flushPending = () => {
      if (pendingTokenRef.current) {
        accumulatedContentRef.current += pendingTokenRef.current;
        pendingTokenRef.current = '';
        setStreamingContent(accumulatedContentRef.current);
      }
      rafRef.current = null;
    };

    const controller = chatApi.streamMessage(activeConversation.id, text, {
      onToken: (token) => {
        pendingTokenRef.current += token;
        if (rafRef.current === null) {
          rafRef.current = requestAnimationFrame(flushPending);
        }
      },
      onCitations: (citations) => { finalCitations = citations; setStreamingCitations(citations); },
      onFollowUps: (questions) => { finalFollowUps = questions; setStreamingFollowUps(questions); },
      onDone: (payload: SSEDonePayload) => {
        if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
        if (pendingTokenRef.current) {
          accumulatedContentRef.current += pendingTokenRef.current;
          pendingTokenRef.current = '';
        }
        const assistantMsg: ChatMessage = {
          id: 'stream_' + Date.now(),
          conversation_id: activeConversation.id,
          role: 'assistant',
          content: accumulatedContentRef.current,
          citations: finalCitations,
          follow_up_questions: finalFollowUps,
          provider: payload.provider,
          model: payload.model,
          latency: payload.latency,
          prompt_tokens: payload.prompt_tokens,
          completion_tokens: payload.completion_tokens,
          is_fallback: payload.is_fallback,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setIsStreaming(false);
        setStreamingContent('');
        setStreamingCitations([]);
        setStreamingFollowUps([]);
        setActiveConversation((prev) =>
          prev ? { ...prev, message_count: prev.message_count + 2 } : prev
        );
        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeConversation.id
              ? { ...c, message_count: c.message_count + 2, updated_at: new Date().toISOString() }
              : c
          )
        );
      },
      onError: (msg) => {
        setErrorMessage(msg);
        setIsStreaming(false);
        setStreamingContent('');
        if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
      },
    });
    abortRef.current = controller;
  }, [activeConversation, isStreaming]);

  const deleteConversation = useCallback(async (id: string) => {
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversation?.id === id) { setActiveConversation(null); setMessages([]); }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to delete conversation');
    }
  }, [activeConversation]);

  const searchConversations = useCallback(async (query: string) => {
    setIsLoadingConversations(true);
    try {
      const res = await chatApi.listConversations(selectedRepositoryId ?? undefined, query);
      setConversations(res.conversations);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsLoadingConversations(false);
    }
  }, [selectedRepositoryId]);

  const deleteRepository = useCallback(async (id: string) => {
    try {
      await chatApi.deleteRepository(id);
      setRepositories((prev) => prev.filter((r) => r.id !== id));
      if (selectedRepositoryId === id) {
        setSelectedRepositoryId(null);
        setActiveConversation(null);
        setConversations([]);
        setMessages([]);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to delete repository');
    }
  }, [selectedRepositoryId]);

  const clearAll = useCallback(async () => {
    try {
      await chatApi.deleteAllRepositories();
      setRepositories([]);
      setSelectedRepositoryId(null);
      setActiveConversation(null);
      setConversations([]);
      setMessages([]);
      localStorage.removeItem('devmind_history');
      localStorage.clear();
      chatApi.listRepositories().then(setRepositories).catch(() => {});
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to clear repositories');
    }
  }, []);

  const clearError = useCallback(() => setErrorMessage(null), []);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const value = useMemo<ChatContextType>(() => ({
    conversations, activeConversation, messages,
    isStreaming, streamingContent, streamingCitations, streamingFollowUps,
    selectedRepositoryId, repositories, readyRepositories,
    isLoadingConversations, isLoadingMessages, hasMoreMessages, errorMessage,
    selectRepository, startNewConversation, selectConversation, sendMessage,
    loadMoreMessages, deleteConversation, searchConversations, clearError,
    deleteRepository, clearAll,
  }), [
    conversations, activeConversation, messages,
    isStreaming, streamingContent, streamingCitations, streamingFollowUps,
    selectedRepositoryId, repositories, readyRepositories,
    isLoadingConversations, isLoadingMessages, hasMoreMessages, errorMessage,
    selectRepository, startNewConversation, selectConversation, sendMessage,
    loadMoreMessages, deleteConversation, searchConversations, clearError,
    deleteRepository, clearAll,
  ]);

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};
