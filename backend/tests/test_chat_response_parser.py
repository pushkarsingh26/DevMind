import os
import sys

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.chat.response_parser import chat_response_parser


def test_chat_response_parser_valid_json():
    raw = """
    ```json
    {
      "answer": "This is the answer.",
      "citations": [{"path": "main.py", "start_line": 5, "end_line": 15, "score": 0.99}],
      "follow_up_questions": ["q1", "q2"]
    }
    ```
    """
    parsed = chat_response_parser.parse(raw)
    assert parsed.parse_ok is True
    assert parsed.answer == "This is the answer."
    assert len(parsed.citations) == 1
    assert parsed.citations[0]["path"] == "main.py"
    assert parsed.citations[0]["start_line"] == 5
    assert parsed.citations[0]["end_line"] == 15
    assert parsed.citations[0]["score"] == 0.99
    assert parsed.follow_up_questions == ["q1", "q2"]


def test_chat_response_parser_embedded_json():
    # prose prefix + JSON inside
    raw = """
    Here is your requested answer:
    {
      "answer": "Embedded answer here.",
      "citations": []
    }
    Hope this helps!
    """
    parsed = chat_response_parser.parse(raw)
    assert parsed.parse_ok is True
    assert parsed.answer == "Embedded answer here."
    assert parsed.citations == []
    assert parsed.follow_up_questions == []


def test_chat_response_parser_invalid_fallback():
    # Plain text only
    raw = "This is a purely text-based response without JSON formatting."
    parsed = chat_response_parser.parse(raw)
    assert parsed.parse_ok is False
    assert parsed.answer == raw
    assert parsed.citations == []
    assert parsed.follow_up_questions == []


def test_chat_response_parser_empty():
    parsed = chat_response_parser.parse("")
    assert parsed.parse_ok is False
    assert "empty response" in parsed.answer
    assert parsed.citations == []
