import os
import sys

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.chat.prompt_builder import chat_prompt_builder
from app.core.config import settings


def test_chat_prompt_builder_basic():
    """
    Verifies that system prompt renders correctly and messages list is built
    in correct order.
    """
    metadata = {
        "repository_name": "owner/repo",
        "primary_language": "Python",
        "framework": "FastAPI",
        "total_files": 10,
        "directories": 2,
        "package_managers": ["pip"],
    }
    chunks = [
        {"id": "c1", "path": "main.py", "start_line": 1, "end_line": 10, "content": "print('hello')", "score": 0.9}
    ]
    history = [
        {"role": "user", "content": "Hi AI"},
        {"role": "assistant", "content": "Hi user"}
    ]
    user_message = "Show me the entrypoint"

    messages, total_tokens, budgeted = chat_prompt_builder.build_chat_messages(
        history=history,
        repo_metadata=metadata,
        chunks=chunks,
        user_message=user_message
    )

    # 1. Assert messages hierarchy
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"

    # 2. Check content rendering
    assert "owner/repo" in messages[0]["content"]
    assert "main.py" in messages[0]["content"]
    assert "print('hello')" in messages[0]["content"]
    assert messages[3]["content"] == user_message
    assert len(budgeted) == 1
    assert total_tokens > 0


def test_chat_prompt_builder_history_eviction():
    """
    Verifies that ChatPromptBuilder evicts oldest history turns when they exceed
    the history token budget.
    """
    metadata = {
        "repository_name": "owner/repo",
        "primary_language": "Python",
        "framework": "FastAPI",
    }
    chunks = []
    
    # Create a long history where each turn is ~200 tokens
    history = []
    for i in range(25):
        history.append({"role": "user", "content": f"User question number {i}: " + "bla " * 100})
        history.append({"role": "assistant", "content": f"Assistant response number {i}: " + "bla " * 100})

    user_message = "Current question"

    messages, total_tokens, budgeted = chat_prompt_builder.build_chat_messages(
        history=history,
        repo_metadata=metadata,
        chunks=chunks,
        user_message=user_message
    )

    # History budget is roughly: (4096 - 800 - 600) * 0.40 = 1078 tokens.
    # Each turn is ~230 tokens, so it should keep around 4-5 turns only.
    # Total messages should be system + kept_turns + current_user.
    assert len(messages) < len(history) + 2
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == user_message
    # Check that older items are evicted (e.g. index 0 is not in messages)
    assert "User question number 0" not in [m["content"] for m in messages]
