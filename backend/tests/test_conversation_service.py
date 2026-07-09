import os
import sys
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.chat import ChatConversation, ChatMessage
from app.chat.conversation_service import conversation_service


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_repo(db):
    repo_id = f"repo_srv_{uuid.uuid4().hex[:6]}"
    repo = Repository(
        id=repo_id,
        name="service-test-repo",
        owner="owner",
        source="zip",
        status="READY",
        language="Python",
        framework="Django"
    )
    db.add(repo)
    db.commit()
    yield repo
    # Cleanup will happen via transaction rollback or DB cleanup
    db.delete(repo)
    db.commit()


def test_create_and_get_conversation(db, test_repo):
    # 1. Create conversation
    conv = conversation_service.create_conversation(db, test_repo.id, title="django review")
    assert conv.id is not None
    assert conv.repository_id == test_repo.id
    assert conv.title == "django review"
    assert conv.message_count == 0

    # 2. Get conversation
    fetched = conversation_service.get_conversation(db, conv.id)
    assert fetched is not None
    assert fetched.title == "django review"

    # 3. List conversations
    listing = conversation_service.list_conversations(db, repository_id=test_repo.id)
    assert len(listing.conversations) == 1
    assert listing.conversations[0].id == conv.id


@pytest.mark.anyio
async def test_chat_turn_mocked_llm(db, test_repo):
    """
    Verifies that chat_turn runs retrieval, prompt builder, mocks provider call,
    parses response, and commits messages to the database.
    """
    conv = conversation_service.create_conversation(db, test_repo.id, title="review chat")

    mock_response_json = {
        "answer": "Django models are in models.py.",
        "citations": [{"path": "models.py", "start_line": 1, "end_line": 10, "score": 0.9}],
        "follow_up_questions": ["Where are the views?"]
    }
    
    import json
    mock_provider_response = MagicMock()
    mock_provider_response.text = (
        f"```json\n"
        f"{json.dumps(mock_response_json)}\n"
        f"```"
    )
    mock_provider_response.prompt_tokens = 50
    mock_provider_response.completion_tokens = 20

    mock_client = MagicMock()
    async def mock_generate_chat(*args, **kwargs):
        return mock_provider_response
    mock_client.generate_chat = mock_generate_chat

    # Patch ProviderFactory and RetrievalService
    with patch("app.chat.conversation_service.provider_factory.get_client", return_value=mock_client), \
         patch("app.chat.conversation_service.retrieval_service.retrieve_chunks", return_value=[]), \
         patch("app.chat.conversation_service.ConversationService._resolve_first_available_provider", return_value=("google", "gemini-2.5-flash", "mock_key")):

        # Run chat turn
        resp = await conversation_service.chat_turn(db, conv.id, "Explain django models")
        
        # Assert response Pydantic model
        assert resp.role == "assistant"
        assert resp.content == "Django models are in models.py."
        assert len(resp.citations) == 1
        assert resp.citations[0].path == "models.py"
        assert resp.follow_up_questions == ["Where are the views?"]
        assert resp.provider == "google"
        assert resp.is_fallback is False

        # Assert database contains both user message and assistant message
        msgs = conversation_service.get_messages(db, conv.id)
        assert msgs.total == 2
        assert msgs.messages[0].role == "user"
        assert msgs.messages[0].content == "Explain django models"
        assert msgs.messages[1].role == "assistant"
        assert msgs.messages[1].content == "Django models are in models.py."
        
        # Verify conversation updated counts
        db_conv = db.query(ChatConversation).filter(ChatConversation.id == conv.id).first()
        assert db_conv.message_count == 2
