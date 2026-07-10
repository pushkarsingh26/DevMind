"""
Phase 5 — ConversationService

Orchestrates the full lifecycle of a chat conversation:
  - CRUD for ChatConversation records
  - Loading and paginating ChatMessage records
  - Executing a chat turn (retrieval → prompt → LLM → parse → persist)
  - Streaming chat turns via async generator (for SSE)
  - Provider failover chain (identical logic to Phase 4 AIService)
  - Graceful fallback when all providers fail

The DB session is released before the LLM streaming call to ensure no
PostgreSQL connections are held open during token generation.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.chat.prompt_builder import chat_prompt_builder
from app.chat.response_parser import chat_response_parser
from app.chat.schemas import (
    ChatMessageResponse,
    CitationRef,
    ConversationListResponse,
    ConversationResponse,
    ConversationSummary,
    MessagesListResponse,
    SSECitationsEvent,
    SSEDoneEvent,
    SSEDonePayload,
    SSEErrorEvent,
    SSEFollowUpsEvent,
    SSETokenEvent,
)
import re
from app.core.config import settings
from app.core.logger import logger

class StreamingAnswerExtractor:
    """
    State machine that processes tokens streamed from the LLM,
    and extracts only the content inside the "answer" (or "text") JSON string.
    Unescapes JSON escape sequences (like \n, \t) in real-time.
    """
    def __init__(self) -> None:
        self.state = "FIND_KEY"  # FIND_KEY, STREAM, FALLBACK, DONE
        self.buffer = ""
        self.escape = False

    def feed(self, token: str) -> str:
        if self.state == "DONE":
            return ""

        if self.state == "FIND_KEY":
            self.buffer += token
            match = re.search(r'"(answer|text)"\s*:\s*"', self.buffer)
            if match:
                start_of_value_idx = match.end()
                answer_prefix = self.buffer[start_of_value_idx:]
                self.state = "STREAM"
                self.buffer = ""
                return self._feed_stream(answer_prefix)
            else:
                if len(self.buffer) > 1000:
                    self.state = "FALLBACK"
                    return self.buffer
                return ""

        elif self.state == "STREAM":
            return self._feed_stream(token)

        elif self.state == "FALLBACK":
            return token

        return ""

    def _feed_stream(self, text: str) -> str:
        yielded = []
        for char in text:
            if self.escape:
                self.escape = False
                if char == 'n':
                    yielded.append('\n')
                elif char == 't':
                    yielded.append('\t')
                elif char == 'r':
                    yielded.append('\r')
                elif char == 'b':
                    yielded.append('\b')
                elif char == 'f':
                    yielded.append('\f')
                elif char == '"':
                    yielded.append('"')
                elif char == '\\':
                    yielded.append('\\')
                elif char == '/':
                    yielded.append('/')
                else:
                    yielded.append('\\' + char)
                continue

            if char == '\\':
                self.escape = True
                continue

            if char == '"':
                self.state = "DONE"
                break

            yielded.append(char)

        return "".join(yielded)
from app.models.chat import ChatConversation, ChatMessage
from app.models.repository import Repository
from app.ai.provider_factory import provider_factory
from app.services.retrieval_service import retrieval_service


def _new_id() -> str:
    return str(uuid.uuid4())


class ConversationService:
    """
    Stateless service — safe for horizontal scaling.
    Each method receives a db Session; no session is stored as instance state.
    """

    # -----------------------------------------------------------------------
    # Conversation CRUD
    # -----------------------------------------------------------------------

    def create_conversation(
        self,
        db: Session,
        repository_id: str,
        title: Optional[str] = None,
    ) -> ConversationResponse:
        """Create a new conversation scoped to an indexed repository."""
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise ValueError(f"Repository '{repository_id}' not found.")

        auto_title = title or "New Chat"
        conv = ChatConversation(
            id=_new_id(),
            repository_id=repository_id,
            title=auto_title,
            message_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        logger.info(f"ConversationService: Created conversation {conv.id} for repo {repository_id}")
        return ConversationResponse.model_validate(conv)

    def get_conversation(self, db: Session, conversation_id: str) -> Optional[ConversationResponse]:
        conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conv:
            return None
        return ConversationResponse.model_validate(conv)

    def list_conversations(
        self,
        db: Session,
        repository_id: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ConversationListResponse:
        q = db.query(ChatConversation)
        if repository_id:
            q = q.filter(ChatConversation.repository_id == repository_id)
        if search_query and search_query.strip():
            pattern = f"%{search_query.strip()}%"
            q = q.filter(ChatConversation.title.ilike(pattern))
        total = q.count()
        convs = q.order_by(ChatConversation.updated_at.desc()).offset(offset).limit(limit).all()
        return ConversationListResponse(
            conversations=[ConversationSummary.model_validate(c) for c in convs],
            total=total,
        )

    def delete_conversation(self, db: Session, conversation_id: str) -> bool:
        conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        logger.info(f"ConversationService: Deleted conversation {conversation_id}")
        return True

    def get_messages(
        self,
        db: Session,
        conversation_id: str,
        limit: int = 30,
        offset: int = 0,
    ) -> MessagesListResponse:
        q = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id)
        total = q.count()
        msgs = q.order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()
        return MessagesListResponse(
            messages=[self._orm_to_response(m) for m in msgs],
            total=total,
            has_more=(offset + limit) < total,
        )

    # -----------------------------------------------------------------------
    # Non-streaming chat turn
    # -----------------------------------------------------------------------

    async def chat_turn(
        self,
        db: Session,
        conversation_id: str,
        user_message: str,
    ) -> ChatMessageResponse:
        """
        Execute one full chat turn and return the assistant's response.
        DB session is held throughout (safe for non-streaming path).
        """
        conv, repo, history, chunks, messages, budgeted_chunks = \
            await self._prepare_turn(db, conversation_id, user_message)

        # Persist user message
        user_msg = self._save_message(db, conversation_id, "user", user_message)

        started = time.time()
        raw_text, provider_used, model_used, prompt_tokens, completion_tokens = \
            await self._run_provider_chain(messages)

        latency = time.time() - started
        parsed = chat_response_parser.parse(raw_text)

        assistant_msg = self._save_assistant_message(
            db, conversation_id, parsed, provider_used, model_used,
            latency, prompt_tokens, completion_tokens, not parsed.parse_ok
        )
        self._update_conversation(db, conv, count_delta=2)

        return self._orm_to_response(assistant_msg)

    # -----------------------------------------------------------------------
    # Streaming chat turn (SSE generator)
    # -----------------------------------------------------------------------

    async def chat_turn_stream(
        self,
        db: Session,
        conversation_id: str,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """
        Execute a streaming chat turn.
        Yields JSON-encoded SSE event lines (data: {...}\\n\\n).

        IMPORTANT: The DB session is used only during preparation and finalization.
        No DB connection is held while the LLM is streaming tokens.
        """
        try:
            conv, repo, history, chunks, messages, budgeted_chunks = \
                await self._prepare_turn(db, conversation_id, user_message)
        except Exception as prep_err:
            logger.error(f"ConversationService: Preparation failed: {prep_err}")
            yield self._sse_line(SSEErrorEvent(data=str(prep_err)))
            return

        # Persist user message before LLM call
        self._save_message(db, conversation_id, "user", user_message)
        self._update_conversation(db, conv, count_delta=1)

        # --- DB session work done; release before streaming ---

        started = time.time()
        accumulated_text = ""
        provider_used = "unknown"
        model_used = "unknown"
        prompt_tokens = 0
        completion_tokens = 0
        extractor = StreamingAnswerExtractor()

        try:
            provider_used, model_used, api_key = self._resolve_first_available_provider()
            client = provider_factory.get_client(provider_used)

            async for token in client.generate_chat_stream(
                messages=messages,
                model_name=model_used,
                api_key=api_key,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                timeout=settings.TIMEOUT,
            ):
                accumulated_text += token
                completion_tokens += 1
                clean_token = extractor.feed(token)
                if clean_token:
                    yield self._sse_line(SSETokenEvent(data=clean_token))

        except Exception as stream_err:
            logger.warning(
                f"ConversationService: Streaming failed for provider '{provider_used}': {stream_err}. "
                f"Falling back to non-streaming chain."
            )
            # Fallback: try remaining providers non-streaming
            try:
                raw_text, provider_used, model_used, prompt_tokens, completion_tokens = \
                    await self._run_provider_chain(messages)
                accumulated_text = raw_text
                clean_text = extractor.feed(raw_text)
                if clean_text:
                    yield self._sse_line(SSETokenEvent(data=clean_text))
                else:
                    parsed_fallback = chat_response_parser.parse(raw_text)
                    yield self._sse_line(SSETokenEvent(data=parsed_fallback.answer))
            except Exception as fallback_err:
                logger.error(f"ConversationService: All providers failed in streaming turn: {fallback_err}")
                fallback_answer = (
                    "I'm sorry, I was unable to reach any AI provider at this time. "
                    "Please check your API keys in the `.env` file and try again."
                )
                yield self._sse_line(SSETokenEvent(data=fallback_answer))
                accumulated_text = fallback_answer
                provider_used = settings.AI_PROVIDER
                model_used = "fallback"

        # Parse accumulated response
        parsed = chat_response_parser.parse(accumulated_text)
        latency = time.time() - started

        # Emit structured events
        if parsed.citations:
            yield self._sse_line(
                SSECitationsEvent(data=[CitationRef(**c) for c in parsed.citations])
            )
        if parsed.follow_up_questions:
            yield self._sse_line(SSEFollowUpsEvent(data=parsed.follow_up_questions))

        # Persist assistant message
        assistant_msg = self._save_assistant_message(
            db, conversation_id, parsed, provider_used, model_used,
            latency, prompt_tokens, completion_tokens, not parsed.parse_ok
        )
        self._update_conversation(db, conv, count_delta=1)

        # Emit done event
        yield self._sse_line(
            SSEDoneEvent(data=SSEDonePayload(
                latency=round(latency, 3),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                provider=provider_used,
                model=model_used,
                is_fallback=not parsed.parse_ok,
            ))
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _prepare_turn(
        self,
        db: Session,
        conversation_id: str,
        user_message: str,
    ) -> Tuple[ChatConversation, Repository, List[Dict], List[Dict], List[Dict], List[Dict]]:
        """
        Load conversation, history, repository metadata, and retrieved chunks,
        then build the messages[] list. Returns all artifacts needed for the turn.
        """
        conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found.")

        repo = db.query(Repository).filter(Repository.id == conv.repository_id).first()
        if not repo:
            raise ValueError(f"Repository '{conv.repository_id}' no longer exists.")

        # Load last N messages as history
        window = settings.CHAT_HISTORY_WINDOW
        history_orm = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(window)
            .all()
        )
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history_orm)
        ]

        # Retrieve relevant context chunks
        top_k = settings.CHAT_RETRIEVAL_LIMIT
        retrieved_pairs = retrieval_service.retrieve_chunks(
            db=db,
            repository_id=conv.repository_id,
            query=user_message,
            top_k=top_k,
        )
        chunks = [
            {
                "id": str(chunk.id),
                "path": chunk.path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
                "score": float(score),
            }
            for chunk, score in retrieved_pairs
        ]

        # Build repository metadata dict
        repo_metadata = {
            "repository_name": f"{repo.owner}/{repo.name}",
            "primary_language": repo.language or "Unknown",
            "framework": repo.framework or "None",
            "total_files": repo.total_files or 0,
            "directories": repo.directories or 0,
            "package_managers": repo.package_managers or [],
        }

        # Build messages list via ChatPromptBuilder
        messages, estimated_tokens, budgeted_chunks = chat_prompt_builder.build_chat_messages(
            history=history,
            repo_metadata=repo_metadata,
            chunks=chunks,
            user_message=user_message,
        )

        logger.info(
            f"ConversationService: Turn prepared. conv={conversation_id} "
            f"history={len(history)} chunks={len(budgeted_chunks)} tokens≈{estimated_tokens}"
        )
        return conv, repo, history, chunks, messages, budgeted_chunks

    def _resolve_first_available_provider(self) -> Tuple[str, str, str]:
        """
        Returns (provider_name, model_name, api_key) for the first provider
        in the chain that has a non-empty API key configured.
        """
        chain = [p.strip().lower() for p in settings.AI_PROVIDER_CHAIN.split(",")]
        # Ensure configured default is first
        default = settings.AI_PROVIDER.strip().lower()
        if default in chain:
            chain.remove(default)
        chain.insert(0, default)

        for provider in chain:
            try:
                model, key = self._provider_credentials(provider)
                if key and "api_key_here" not in key:
                    return provider, model, key
            except ValueError:
                continue

        raise RuntimeError("No AI provider with valid credentials found in the chain.")

    async def _run_provider_chain(
        self,
        messages: List[Dict[str, str]],
    ) -> Tuple[str, str, str, int, int]:
        """
        Non-streaming provider failover. Returns:
          (raw_text, provider_used, model_used, prompt_tokens, completion_tokens)

        Retry policy:
          - Retryable (timeout, 429, 5xx): retry with exponential backoff
          - Non-retryable (400, 401, 403, 404): skip to next provider immediately
        """
        import httpx as _httpx
        from app.ai.provider_registry import RETRYABLE_STATUS_CODES, NON_RETRYABLE_STATUS_CODES

        chain = [p.strip().lower() for p in settings.AI_PROVIDER_CHAIN.split(",")]
        default = settings.AI_PROVIDER.strip().lower()
        if default in chain:
            chain.remove(default)
        chain.insert(0, default)

        last_err: Optional[Exception] = None

        for provider in chain:
            try:
                model, key = self._provider_credentials(provider)
            except ValueError:
                continue

            if not key or "api_key_here" in key:
                # Not configured — skip silently (not a failure)
                logger.info(f"ConversationService: Provider '{provider}' has no API key configured. Skipping.")
                continue

            client = provider_factory.get_client(provider)

            for attempt in range(settings.MAX_RETRIES):
                try:
                    resp = await client.generate_chat(
                        messages=messages,
                        model_name=model,
                        api_key=key,
                        temperature=settings.TEMPERATURE,
                        max_tokens=settings.MAX_TOKENS,
                        timeout=settings.TIMEOUT,
                    )
                    return resp.text, provider, model, resp.prompt_tokens, resp.completion_tokens

                except _httpx.HTTPStatusError as http_err:
                    status_code = http_err.response.status_code
                    last_err = http_err
                    if status_code in NON_RETRYABLE_STATUS_CODES:
                        logger.warning(
                            f"ConversationService: Provider '{provider}' returned non-retryable "
                            f"HTTP {status_code}. Skipping to next provider."
                        )
                        break  # Skip to next provider immediately
                    # Retryable (429, 5xx)
                    logger.warning(
                        f"ConversationService: Provider '{provider}' attempt {attempt + 1} "
                        f"retryable HTTP {status_code}."
                    )
                    if attempt < settings.MAX_RETRIES - 1:
                        await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 0.5))

                except (_httpx.TimeoutException, _httpx.ConnectError) as net_err:
                    last_err = net_err
                    logger.warning(
                        f"ConversationService: Provider '{provider}' attempt {attempt + 1} "
                        f"network error: {type(net_err).__name__}: {net_err}"
                    )
                    if attempt < settings.MAX_RETRIES - 1:
                        await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 0.5))

                except Exception as err:
                    last_err = err
                    logger.warning(
                        f"ConversationService: Provider '{provider}' attempt {attempt + 1}/{settings.MAX_RETRIES} "
                        f"failed: {type(err).__name__}: {err}"
                    )
                    if attempt < settings.MAX_RETRIES - 1:
                        await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 0.5))

        raise RuntimeError(
            f"All providers in the failover chain failed. Last error: {last_err}"
        )

    def _provider_credentials(self, provider: str) -> Tuple[str, str]:
        """Returns (model_name, api_key) for the given cloud provider name."""
        p = provider.strip().lower()
        if p == "google":
            return settings.GOOGLE_MODEL_NAME, settings.GOOGLE_API_KEY or ""
        elif p == "groq":
            return settings.GROQ_MODEL_NAME, settings.GROQ_API_KEY or ""
        elif p == "openrouter":
            return settings.OPENROUTER_MODEL_NAME, settings.OPENROUTER_API_KEY or ""
        elif p == "nvidia":
            return settings.NVIDIA_MODEL_NAME, settings.NVIDIA_API_KEY or ""
        raise ValueError(f"Unknown provider: {provider}")

    def _save_message(
        self,
        db: Session,
        conversation_id: str,
        role: str,
        content: str,
    ) -> ChatMessage:
        msg = ChatMessage(
            id=_new_id(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def _save_assistant_message(
        self,
        db: Session,
        conversation_id: str,
        parsed: Any,
        provider: str,
        model: str,
        latency: float,
        prompt_tokens: int,
        completion_tokens: int,
        is_fallback: bool,
    ) -> ChatMessage:
        from app.chat.response_parser import ParsedChatResponse
        msg = ChatMessage(
            id=_new_id(),
            conversation_id=conversation_id,
            role="assistant",
            content=parsed.answer,
            citations=parsed.citations or [],
            follow_up_questions=parsed.follow_up_questions or [],
            provider=provider,
            model=model,
            latency=round(latency, 3),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            is_fallback=is_fallback,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def _update_conversation(
        self, db: Session, conv: ChatConversation, count_delta: int
    ) -> None:
        conv.message_count = (conv.message_count or 0) + count_delta
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()

    def _orm_to_response(self, msg: ChatMessage) -> ChatMessageResponse:
        citations = [CitationRef(**c) for c in (msg.citations or [])]
        follow_ups = list(msg.follow_up_questions or [])
        return ChatMessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            citations=citations,
            follow_up_questions=follow_ups,
            provider=msg.provider,
            model=msg.model,
            latency=msg.latency,
            prompt_tokens=msg.prompt_tokens,
            completion_tokens=msg.completion_tokens,
            is_fallback=msg.is_fallback,
            created_at=msg.created_at,
        )

    @staticmethod
    def _sse_line(event: Any) -> str:
        """Serialise a Pydantic SSE event model to a data: ...\\n\\n line."""
        return f"data: {event.model_dump_json()}\n\n"


conversation_service = ConversationService()
