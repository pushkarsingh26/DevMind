import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.main import app
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.chat import ChatConversation

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_repo(db):
    repo_id = f"repo_rt_{uuid.uuid4().hex[:6]}"
    repo = Repository(
        id=repo_id,
        name="routes-test-repo",
        owner="owner",
        source="local",
        status="READY"
    )
    db.add(repo)
    db.commit()
    yield repo
    db.delete(repo)
    db.commit()


def test_routes_conversation_lifecycle(db, test_repo):
    # 1. Start conversation (POST)
    payload = {"repository_id": test_repo.id, "title": "Route test"}
    res = client.post("/chat/conversations", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["title"] == "Route test"
    conv_id = data["id"]

    # 2. List conversations (GET)
    res_list = client.get(f"/chat/conversations?repository_id={test_repo.id}")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] == 1
    assert list_data["conversations"][0]["id"] == conv_id

    # 3. Get individual conversation (GET)
    res_get = client.get(f"/chat/conversations/{conv_id}")
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "Route test"

    # 4. Get messages (GET)
    res_msgs = client.get(f"/chat/conversations/{conv_id}/messages")
    assert res_msgs.status_code == 200
    assert res_msgs.json()["total"] == 0

    # 5. Delete conversation (DELETE)
    res_del = client.delete(f"/chat/conversations/{conv_id}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # Verify deleted
    res_get_deleted = client.get(f"/chat/conversations/{conv_id}")
    assert res_get_deleted.status_code == 404


def test_routes_invalid_repository():
    payload = {"repository_id": "nonexistent_repo"}
    res = client.post("/chat/conversations", json=payload)
    assert res.status_code == 404


def test_routes_message_sse_streaming(db, test_repo):
    """
    Verifies that the /chat/stream SSE endpoint responds with a text/event-stream
    and yields lines of event payloads correctly.
    """
    # Create conversation
    conv = ChatConversation(
        id=f"conv_stream_{uuid.uuid4().hex[:6]}",
        repository_id=test_repo.id,
        title="Streaming test"
    )
    db.add(conv)
    db.commit()

    # Async generator stream mocker
    async def mock_stream(*args, **kwargs):
        yield 'data: {"type": "token", "data": "Hello"}\n\n'
        yield 'data: {"type": "token", "data": " world"}\n\n'
        yield 'data: {"type": "done", "data": {"latency": 0.5, "prompt_tokens": 10, "completion_tokens": 2, "provider": "google", "model": "gemini", "is_fallback": false}}\n\n'

    with patch("app.chat.conversation_service.conversation_service.chat_turn_stream", side_effect=mock_stream):
        # We query the SSE stream endpoint
        # EventSource / SSE works via GET in our endpoints
        response = client.get(
            f"/chat/stream?conversation_id={conv.id}&message=Say%20hello"
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("text/event-stream")
        
        # Verify content lines
        lines = [line for line in response.iter_lines() if line]
        joined = "".join(lines)
        assert "Hello" in joined
        assert "world" in joined
        assert "done" in joined
