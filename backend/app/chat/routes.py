"""
Phase 5 — Chat API Routes

Endpoints:
  POST   /chat/conversations                → start a new conversation
  GET    /chat/conversations                → list conversations (with optional search)
  GET    /chat/conversations/{id}           → get one conversation
  DELETE /chat/conversations/{id}           → delete conversation + messages
  GET    /chat/conversations/{id}/messages  → paginated message history
  POST   /chat/message                      → synchronous chat turn
  GET    /chat/stream                       → streaming chat turn (SSE)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.chat.conversation_service import conversation_service
from app.chat.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ConversationListResponse,
    ConversationResponse,
    MessagesListResponse,
)
from app.core.logger import logger
from app.db.session import get_db

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


# ---------------------------------------------------------------------------
# Conversation endpoints
# ---------------------------------------------------------------------------

@chat_router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new repository chat conversation",
)
async def start_conversation(
    payload: ChatStartRequest,
    db: Session = Depends(get_db),
):
    try:
        return conversation_service.create_conversation(
            db=db,
            repository_id=payload.repository_id,
            title=payload.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"ChatRoutes: create_conversation error: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@chat_router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations (optionally filtered by repository or search query)",
)
async def list_conversations(
    repository_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return conversation_service.list_conversations(
        db=db,
        repository_id=repository_id,
        search_query=search,
        limit=limit,
        offset=offset,
    )


@chat_router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get a single conversation by ID",
)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    conv = conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return conv


@chat_router.delete(
    "/conversations/{conversation_id}",
    summary="Delete a conversation and all its messages",
)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    deleted = conversation_service.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return {"status": "deleted", "conversation_id": conversation_id}


@chat_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessagesListResponse,
    summary="Retrieve paginated message history for a conversation",
)
async def get_messages(
    conversation_id: str,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return conversation_service.get_messages(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Chat turn endpoints
# ---------------------------------------------------------------------------

@chat_router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Send a message and receive a synchronous (non-streaming) AI response",
)
async def send_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Synchronous chat turn. Use this for clients that do not support SSE.
    For streaming responses use GET /chat/stream.
    """
    # Validate conversation exists
    conv = conversation_service.get_conversation(db, payload.conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{payload.conversation_id}' not found.",
        )
    try:
        return await conversation_service.chat_turn(
            db=db,
            conversation_id=payload.conversation_id,
            user_message=payload.message,
        )
    except Exception as exc:
        logger.error(f"ChatRoutes: chat_turn error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the chat turn.",
        )


@chat_router.get(
    "/stream",
    summary="Stream an AI response via Server-Sent Events",
    response_class=StreamingResponse,
)
async def stream_message(
    conversation_id: str = Query(..., description="Conversation to continue"),
    message: str = Query(..., description="User message (max 4000 chars)", max_length=4000),
    db: Session = Depends(get_db),
):
    """
    Streaming chat turn using Server-Sent Events (SSE).

    Events emitted:
      {"type": "token",      "data": "...text chunk..."}
      {"type": "citations",  "data": [{path, start_line, end_line, score}]}
      {"type": "follow_ups", "data": ["q1", "q2"]}
      {"type": "done",       "data": {latency, prompt_tokens, ...}}
      {"type": "error",      "data": "error message"}

    The stream always terminates — there are no indefinitely open connections.
    """
    # Validate conversation exists synchronously before opening stream
    conv = conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    return StreamingResponse(
        content=conversation_service.chat_turn_stream(
            db=db,
            conversation_id=conversation_id,
            user_message=message,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )
