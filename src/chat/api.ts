/**
 * Phase 5 — Chat API Service
 *
 * All HTTP and SSE communication functions for the /chat endpoints.
 * Streaming uses fetch() + ReadableStream (not EventSource) to support
 * POST-body messages and custom headers.
 */

import type {
  ChatMessage,
  Conversation,
  ConversationListResponse,
  MessagesListResponse,
  RepositoryListItem,
  SSEEvent,
  StreamCallbacks,
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export async function startConversation(
  repositoryId: string,
  title?: string
): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/chat/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repository_id: repositoryId, title }),
  });
  if (!res.ok) throw new Error(`Failed to start conversation: ${res.statusText}`);
  return res.json();
}

export async function listConversations(
  repositoryId?: string,
  search?: string,
  limit = 20,
  offset = 0
): Promise<ConversationListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (repositoryId) params.set('repository_id', repositoryId);
  if (search) params.set('search', search);
  const res = await fetch(`${API_BASE}/chat/conversations?${params}`);
  if (!res.ok) throw new Error(`Failed to list conversations: ${res.statusText}`);
  return res.json();
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}`);
  if (!res.ok) throw new Error(`Conversation not found: ${res.statusText}`);
  return res.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete conversation: ${res.statusText}`);
}

export async function getMessages(
  conversationId: string,
  limit = 30,
  offset = 0
): Promise<MessagesListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const res = await fetch(
    `${API_BASE}/chat/conversations/${conversationId}/messages?${params}`
  );
  if (!res.ok) throw new Error(`Failed to load messages: ${res.statusText}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Synchronous chat turn (non-streaming)
// ---------------------------------------------------------------------------

export async function sendMessage(
  conversationId: string,
  message: string
): Promise<ChatMessage> {
  const res = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, message, stream: false }),
  });
  if (!res.ok) throw new Error(`Failed to send message: ${res.statusText}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Streaming chat turn (SSE via fetch ReadableStream)
// ---------------------------------------------------------------------------

/**
 * Opens an SSE stream for a chat turn.
 *
 * Returns an AbortController — call `.abort()` to cancel the stream on
 * component unmount or when the user interrupts.
 *
 * Event parsing:
 *   data: {"type": "token",      "data": "..."}
 *   data: {"type": "citations",  "data": [...]}
 *   data: {"type": "follow_ups", "data": [...]}
 *   data: {"type": "done",       "data": {...}}
 *   data: {"type": "error",      "data": "..."}
 */
export function streamMessage(
  conversationId: string,
  message: string,
  callbacks: StreamCallbacks
): AbortController {
  const controller = new AbortController();

  const params = new URLSearchParams({
    conversation_id: conversationId,
    message,
  });

  // Run async in the background — caller does not await
  (async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/stream?${params}`, {
        signal: controller.signal,
        headers: { Accept: 'text/event-stream' },
      });

      if (!res.ok) {
        callbacks.onError(`HTTP ${res.status}: ${res.statusText}`);
        return;
      }

      if (!res.body) {
        callbacks.onError('Response body is null — SSE not supported by this browser.');
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double-newline SSE event boundaries
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? ''; // keep incomplete last part

        for (const part of parts) {
          const lines = part.trim().split('\n');
          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const raw = line.slice('data:'.length).trim();
            if (!raw || raw === '[DONE]') continue;

            try {
              const event = JSON.parse(raw) as SSEEvent;
              dispatchSSEEvent(event, callbacks);
            } catch {
              // Ignore malformed lines
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return; // clean abort
      callbacks.onError(err instanceof Error ? err.message : 'Unknown stream error');
    }
  })();

  return controller;
}

function dispatchSSEEvent(event: SSEEvent, callbacks: StreamCallbacks): void {
  switch (event.type) {
    case 'token':
      callbacks.onToken(event.data);
      break;
    case 'citations':
      callbacks.onCitations(event.data);
      break;
    case 'follow_ups':
      callbacks.onFollowUps(event.data);
      break;
    case 'done':
      callbacks.onDone(event.data);
      break;
    case 'error':
      callbacks.onError(event.data);
      break;
  }
}

// ---------------------------------------------------------------------------
// Repositories (reuses existing Phase 1-2 endpoint)
// ---------------------------------------------------------------------------

export async function listRepositories(): Promise<RepositoryListItem[]> {
  const res = await fetch(`${API_BASE}/repositories`);
  if (!res.ok) throw new Error(`Failed to list repositories: ${res.statusText}`);
  return res.json();
}

export async function deleteRepository(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/repositories/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to delete repository ${id}`);
  }
}

export async function deleteAllRepositories(): Promise<void> {
  const res = await fetch(`${API_BASE}/repositories`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to clear all repositories');
  }
}
