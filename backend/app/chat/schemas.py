"""
Phase 5 — Chat Pydantic Schemas

All request/response contracts for the /chat REST and SSE API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-model
# ---------------------------------------------------------------------------

class CitationRef(BaseModel):
    """
    A reference to a specific code span within the repository that the AI
    used when forming its answer.
    Field names intentionally mirror TraceabilityRef from Phase 4 for easy
    conversion.
    """
    path: str = Field(..., description="Relative path of the source file")
    start_line: int = Field(..., description="First line of the referenced span")
    end_line: int = Field(..., description="Last line of the referenced span")
    score: Optional[float] = Field(None, description="Semantic similarity score (0–1)")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ChatStartRequest(BaseModel):
    """Start a new conversation scoped to an indexed repository."""
    repository_id: str = Field(..., description="ID of the indexed repository to chat about")
    title: Optional[str] = Field(None, description="Optional title; auto-generated if omitted")


class ChatMessageRequest(BaseModel):
    """Send a message inside an existing conversation (non-streaming path)."""
    conversation_id: str = Field(..., description="ID of the conversation to continue")
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User's natural language question (max 4000 chars)"
    )
    stream: bool = Field(True, description="If True, prefer the SSE streaming endpoint")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ConversationSummary(BaseModel):
    """Lightweight representation for conversation list views."""
    id: str
    repository_id: str
    title: Optional[str]
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(ConversationSummary):
    """Full conversation record (same fields as summary for now; extensible)."""
    pass


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""
    conversations: List[ConversationSummary]
    total: int


class ChatMessageResponse(BaseModel):
    """Full representation of one chat turn (user or assistant)."""
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    citations: List[CitationRef] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    provider: Optional[str] = None
    model: Optional[str] = None
    latency: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    is_fallback: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessagesListResponse(BaseModel):
    """Paginated list of messages for a conversation."""
    messages: List[ChatMessageResponse]
    total: int
    has_more: bool


# ---------------------------------------------------------------------------
# SSE event schemas
# ---------------------------------------------------------------------------
# Every Server-Sent Event is a JSON-serialised SSEChatEvent line:
#   data: {"type": "token", "data": "Hello"}\n\n

class SSETokenEvent(BaseModel):
    type: Literal["token"] = "token"
    data: str  # Raw text chunk from LLM


class SSECitationsEvent(BaseModel):
    type: Literal["citations"] = "citations"
    data: List[CitationRef]


class SSEFollowUpsEvent(BaseModel):
    type: Literal["follow_ups"] = "follow_ups"
    data: List[str]


class SSEDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    data: SSEDonePayload


class SSEDonePayload(BaseModel):
    latency: float
    prompt_tokens: int
    completion_tokens: int
    provider: str
    model: str
    is_fallback: bool = False


class SSEErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    data: str  # Human-readable error description


SSEChatEvent = Union[
    SSETokenEvent,
    SSECitationsEvent,
    SSEFollowUpsEvent,
    SSEDoneEvent,
    SSEErrorEvent,
]
