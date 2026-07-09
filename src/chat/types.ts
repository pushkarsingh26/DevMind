/**
 * Phase 5 — Chat TypeScript Types
 * All interfaces for the AI Repository Chat feature.
 */

// ---------------------------------------------------------------------------
// Core domain models (mirror backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface Conversation {
  id: string;
  repository_id: string;
  title: string | null;
  message_count: number;
  created_at: string;   // ISO datetime string
  updated_at: string;
}

export interface CitationRef {
  path: string;
  start_line: number;
  end_line: number;
  score?: number;
}

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  citations: CitationRef[];
  follow_up_questions: string[];
  provider?: string;
  model?: string;
  latency?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  is_fallback: boolean;
  created_at: string;
}

export interface RepositoryListItem {
  id: string;
  name: string;
  owner: string;
  source: string;
  framework?: string;
  language?: string;
  repository_hash?: string;
  status: string;
}

// ---------------------------------------------------------------------------
// API response wrappers
// ---------------------------------------------------------------------------

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
}

export interface MessagesListResponse {
  messages: ChatMessage[];
  total: number;
  has_more: boolean;
}

// ---------------------------------------------------------------------------
// SSE event types
// ---------------------------------------------------------------------------

export interface SSEDonePayload {
  latency: number;
  prompt_tokens: number;
  completion_tokens: number;
  provider: string;
  model: string;
  is_fallback: boolean;
}

export type SSEEvent =
  | { type: 'token';      data: string }
  | { type: 'citations';  data: CitationRef[] }
  | { type: 'follow_ups'; data: string[] }
  | { type: 'done';       data: SSEDonePayload }
  | { type: 'error';      data: string };

// ---------------------------------------------------------------------------
// Stream callback interface
// ---------------------------------------------------------------------------

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onCitations: (citations: CitationRef[]) => void;
  onFollowUps: (questions: string[]) => void;
  onDone: (payload: SSEDonePayload) => void;
  onError: (message: string) => void;
}

// ---------------------------------------------------------------------------
// ChatContext interface
// ---------------------------------------------------------------------------

export interface ChatContextType {
  // State
  conversations: Conversation[];
  activeConversation: Conversation | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  streamingCitations: CitationRef[];
  streamingFollowUps: string[];
  selectedRepositoryId: string | null;
  repositories: RepositoryListItem[];
  /** Memoized list of repositories with status === 'READY'. Use this instead of filtering repositories on every render. */
  readyRepositories: RepositoryListItem[];
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  hasMoreMessages: boolean;
  errorMessage: string | null;

  // Actions
  selectRepository: (id: string) => void;
  startNewConversation: (title?: string) => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  searchConversations: (query: string) => Promise<void>;
  clearError: () => void;
  deleteRepository: (id: string) => Promise<void>;
  clearAll: () => Promise<void>;
}
