import os
import sys
import uuid
import pytest
from sqlalchemy.exc import IntegrityError

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.chat import ChatConversation, ChatMessage


def test_chat_models_lifecycle_and_cascade():
    """
    Verifies creation, relationship resolution, and cascading deletion for
    ChatConversation and ChatMessage ORM models.
    """
    db = SessionLocal()
    repo_id = f"repo_test_{uuid.uuid4().hex[:6]}"
    conv_id = str(uuid.uuid4())
    msg_id_1 = str(uuid.uuid4())
    msg_id_2 = str(uuid.uuid4())

    try:
        # 1. Create a parent Repository
        repo = Repository(
            id=repo_id,
            name="test-repo-models",
            owner="test-owner",
            source="github",
            status="READY"
        )
        db.add(repo)
        db.commit()

        # 2. Create ChatConversation linked to Repository
        conv = ChatConversation(
            id=conv_id,
            repository_id=repo_id,
            title="Model Test Chat",
            message_count=0
        )
        db.add(conv)
        db.commit()

        # 3. Create ChatMessages linked to ChatConversation
        msg_user = ChatMessage(
            id=msg_id_1,
            conversation_id=conv_id,
            role="user",
            content="Hello world"
        )
        msg_assistant = ChatMessage(
            id=msg_id_2,
            conversation_id=conv_id,
            role="assistant",
            content="Hello human",
            citations=[{"path": "main.py", "start_line": 1, "end_line": 10, "score": 0.95}],
            follow_up_questions=["How are you?"],
            provider="google",
            model="gemini-2.5-flash",
            latency=1.23,
            prompt_tokens=100,
            completion_tokens=20,
            is_fallback=False
        )
        db.add_all([msg_user, msg_assistant])
        db.commit()

        # 4. Verify fetch works and relationships are resolved
        db_conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
        assert db_conv is not None
        assert db_conv.repository_id == repo_id
        assert db_conv.title == "Model Test Chat"
        assert len(db_conv.messages) == 2
        
        # Verify message fields
        user_db = next(m for m in db_conv.messages if m.role == "user")
        assistant_db = next(m for m in db_conv.messages if m.role == "assistant")
        assert user_db.content == "Hello world"
        assert assistant_db.content == "Hello human"
        assert assistant_db.citations[0]["path"] == "main.py"
        assert assistant_db.follow_up_questions == ["How are you?"]
        assert assistant_db.provider == "google"
        assert assistant_db.latency == 1.23

        # 5. Delete Repository and check CASCADE DELETE on conversations and messages
        db.delete(repo)
        db.commit()

        deleted_conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
        deleted_msg_1 = db.query(ChatMessage).filter(ChatMessage.id == msg_id_1).first()
        deleted_msg_2 = db.query(ChatMessage).filter(ChatMessage.id == msg_id_2).first()

        assert deleted_conv is None
        assert deleted_msg_1 is None
        assert deleted_msg_2 is None

    finally:
        # Cleanup
        db.rollback()
        db.close()
