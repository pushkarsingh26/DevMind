import os
import sys
import pytest
from pydantic import ValidationError

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.chat.schemas import (
    ChatStartRequest,
    ChatMessageRequest,
    CitationRef,
    SSETokenEvent,
    SSECitationsEvent,
    SSEFollowUpsEvent,
    SSEDoneEvent,
)


def test_request_validation():
    # ChatStartRequest
    req = ChatStartRequest(repository_id="repo_123")
    assert req.repository_id == "repo_123"
    assert req.title is None

    # ChatMessageRequest
    msg = ChatMessageRequest(conversation_id="conv_123", message="How does X work?")
    assert msg.conversation_id == "conv_123"
    assert msg.message == "How does X work?"
    assert msg.stream is True

    # Empty message rejection
    with pytest.raises(ValidationError):
        ChatMessageRequest(conversation_id="conv_123", message="")

    # Message exceeding 4000 chars rejection
    with pytest.raises(ValidationError):
        ChatMessageRequest(conversation_id="conv_123", message="A" * 4001)


def test_citation_schema():
    citation = CitationRef(path="app/main.py", start_line=5, end_line=10, score=0.875)
    assert citation.path == "app/main.py"
    assert citation.start_line == 5
    assert citation.end_line == 10
    assert citation.score == 0.875


def test_sse_event_serialization():
    # Token event
    tok = SSETokenEvent(data="Hello")
    assert tok.type == "token"
    assert tok.data == "Hello"
    assert tok.model_dump() == {"type": "token", "data": "Hello"}

    # Citations event
    cit_ref = CitationRef(path="utils.py", start_line=1, end_line=5, score=0.99)
    cit_event = SSECitationsEvent(data=[cit_ref])
    assert cit_event.type == "citations"
    assert cit_event.data[0].path == "utils.py"

    # Done event
    done = SSEDoneEvent(
        data={
            "latency": 1.5,
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "provider": "google",
            "model": "gemini-2.5-flash",
            "is_fallback": False,
        }
    )
    assert done.type == "done"
    assert done.data.provider == "google"
    assert done.data.is_fallback is False
