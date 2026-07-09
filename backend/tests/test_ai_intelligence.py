import os
import sys
import pytest
import asyncio
from typing import AsyncIterator

# Ensure app is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.core.config import settings
from app.ai.token_manager import token_manager
from app.ai.prompt_builder import prompt_builder
from app.ai.response_parser import response_parser, AIResponseParsingError
from app.ai.schemas import ReviewSchema, TraceabilityRef
from app.ai.cache import ai_cache
from app.ai.ai_service import ai_service
from app.ai.client import LLMProviderClient, ProviderResponse
from app.ai.provider_factory import provider_factory

# Mock Client to isolate API dependency during testing
class MockLLMClient(LLMProviderClient):
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.call_idx = 0

    async def generate(self, system_prompt, user_prompt, model_name, api_key, temperature, max_tokens, timeout) -> ProviderResponse:
        self.call_idx += 1
        outcome = self.outcomes[self.call_idx - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def generate_stream(self, system_prompt, user_prompt, model_name, api_key, temperature, max_tokens, timeout) -> AsyncIterator[str]:
        raise NotImplementedError()


def test_ai_settings_parsing():
    """
    Verifies that AI Settings are parsed and populated correctly from environment.
    """
    assert settings.AI_PROVIDER in ("google", "groq", "openrouter", "nvidia")
    assert isinstance(settings.AI_PROVIDER_CHAIN, str)
    assert settings.MAX_TOKENS > 0
    assert settings.RETRIEVAL_LIMIT > 0
    assert 0.0 <= settings.TEMPERATURE <= 2.0


def test_token_manager_estimations():
    """
    Verifies token manager counts character bounds fallback correctly.
    """
    sample_text = "def hello():\n    return 'world'"
    tokens = token_manager.estimate_tokens(sample_text)
    assert tokens > 0
    # Empty string should be 0
    assert token_manager.estimate_tokens("") == 0


def test_token_manager_chunk_budgeting():
    """
    Verifies chunk truncation at boundary is enforced correctly.
    """
    chunks = [
        {"id": "ch1", "path": "a.py", "start_line": 1, "end_line": 5, "content": "hello_world_1"},
        {"id": "ch2", "path": "b.py", "start_line": 10, "end_line": 15, "content": "hello_world_2" * 50},
        {"id": "ch3", "path": "c.py", "start_line": 1, "end_line": 2, "content": "hello_world_3"}
    ]
    # Small budget to force truncation of second chunk
    budgeted, total = token_manager.budget_chunks(chunks, base_prompt_tokens=20, max_budget=80)
    assert len(budgeted) == 2
    assert total <= 80
    assert budgeted[0]["id"] == "ch1"
    assert "truncated" in budgeted[1]["content"]


def test_prompt_builder_optimizations():
    """
    Verifies that deduplication and line merging behave correctly.
    """
    # Create chunks: some duplicate, some overlapping, some contiguous
    raw_chunks = [
        {"id": "c1", "path": "math.py", "start_line": 1, "end_line": 5, "content": "line1\nline2\nline3\nline4\nline5"},
        # Duplicate
        {"id": "c1", "path": "math.py", "start_line": 1, "end_line": 5, "content": "line1\nline2\nline3\nline4\nline5"},
        # Overlapping math.py chunk
        {"id": "c2", "path": "math.py", "start_line": 4, "end_line": 8, "content": "line4\nline5\nline6\nline7\nline8"},
        # Contiguous app.py chunk
        {"id": "c3", "path": "app.py", "start_line": 1, "end_line": 10, "content": "app1"},
        {"id": "c4", "path": "app.py", "start_line": 11, "end_line": 20, "content": "app2"},
    ]

    optimized = prompt_builder.optimize_chunks(raw_chunks)
    # Deduplication and merging should reduce count from 5 to 2 (one for math.py, one for app.py)
    assert len(optimized) == 2
    
    math_chunk = next(x for x in optimized if x["path"] == "math.py")
    assert math_chunk["start_line"] == 1
    assert math_chunk["end_line"] == 8
    
    app_chunk = next(x for x in optimized if x["path"] == "app.py")
    assert app_chunk["start_line"] == 1
    assert app_chunk["end_line"] == 20


def test_response_parser_formatting():
    """
    Verifies that markdown sanitization and field repairing resolve missing attributes.
    """
    raw_json = "```json\n{\n  \"executive_summary\": \"FastAPI review\"\n}\n```"
    # Cleaner test
    cleaned = response_parser.clean_raw_output(raw_json)
    assert cleaned == '{\n  "executive_summary": "FastAPI review"\n}'

    # Repair test
    repaired_dict = {"executive_summary": "FastAPI review"}
    repaired = response_parser.repair_fields(repaired_dict, ReviewSchema)
    # Missing optional lists should be repaired to empty lists
    assert repaired["strengths"] == []
    assert repaired["improvements"] == []
    assert repaired["security_observations"] == []
    
    # Parse and validate
    model_obj = response_parser.parse_and_validate(raw_json, ReviewSchema)
    assert model_obj.executive_summary == "FastAPI review"
    assert model_obj.strengths == []


def test_ai_service_retry_and_failover():
    """
    Verifies failovers through chain sequence and retries backoffs.
    """
    # Temporarily disable caching for this run
    original_cache = settings.AI_CACHE_ENABLED
    original_provider = settings.AI_PROVIDER
    original_chain = settings.AI_PROVIDER_CHAIN
    original_retries = settings.MAX_RETRIES
    
    settings.AI_CACHE_ENABLED = False
    settings.AI_PROVIDER = "google"
    settings.AI_PROVIDER_CHAIN = "google,groq"
    settings.MAX_RETRIES = 2
    
    # Google will fail twice (timeout/outage), Groq will succeed on first try
    google_client = MockLLMClient([
        RuntimeError("Google Timeout"),
        RuntimeError("Google Outage")
    ])
    groq_client = MockLLMClient([
        ProviderResponse(text='{"executive_summary": "Failover success on Groq"}')
    ])
    
    provider_factory._clients["google"] = google_client
    provider_factory._clients["groq"] = groq_client
    
    # Mock parameters
    class MockDB:
        def query(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def first(self, *args, **kwargs):
            class MockRepo:
                repository_hash = "mock_hash"
            return MockRepo()

    class MockMetadata:
        repository_name = "test-repo"
        primary_language = "Python"
        framework = "FastAPI"
        total_files = 10
        directories = 2
        package_managers = ["pip"]
        dependencies = {}
        largest_files = []

    async def run_async_test():
        res = await ai_service.analyze_repository(MockDB(), "repo-999", "review", MockMetadata())
        assert res.executive_summary == "Failover success on Groq"
        assert res.is_fallback is False
        assert res.ai_metadata.provider_used_after_failover == "groq"
        
        # Test heuristic fallback if all providers fail
        google_client_fail = MockLLMClient([RuntimeError("Fail"), RuntimeError("Fail")])
        groq_client_fail = MockLLMClient([RuntimeError("Fail"), RuntimeError("Fail")])
        provider_factory._clients["google"] = google_client_fail
        provider_factory._clients["groq"] = groq_client_fail

        res_fallback = await ai_service.analyze_repository(MockDB(), "repo-999", "review", MockMetadata())
        assert res_fallback.is_fallback is True
        assert res_fallback.executive_summary == ""  # Default empty fallback value
        assert res_fallback.ai_metadata.fallback_flag is True

    try:
        asyncio.run(run_async_test())
    finally:
        # Restore configuration variables
        settings.AI_CACHE_ENABLED = original_cache
        settings.AI_PROVIDER = original_provider
        settings.AI_PROVIDER_CHAIN = original_chain
        settings.MAX_RETRIES = original_retries
