"""
BaseAgent — Phase 7.5.2
========================
Abstract base for all specialized agents.

Routing is now fully delegated to ProviderRegistry:
  - Task-aware provider ordering (fast vs heavy reasoning)
  - Dynamic model resolution (auto-fallback if configured model unavailable)
  - Smart retry: retryable errors (timeout/429/5xx) retry with backoff;
    non-retryable errors (400/401/403/404) skip provider immediately.
  - Health stats updated on every call via record_success() / record_failure().
"""
import time
import random
import asyncio
import httpx
from typing import List, Dict, Any, Type, Tuple, Optional, Callable
from pydantic import BaseModel
from app.core.config import settings
from app.core.logger import logger
from app.core.console import console
from app.ai.provider_factory import provider_factory
from app.ai.provider_registry import (
    provider_registry,
    RETRYABLE_STATUS_CODES,
    NON_RETRYABLE_STATUS_CODES,
)
from app.ai.token_manager import token_manager
from app.ai.response_parser import response_parser
from app.ai.prompt_loader import prompt_loader
from app.services.provider_health import provider_health_monitor


class BaseAgent:
    """
    Abstract/Base agent class containing LLM invocation with intelligent
    provider routing, failover, token budgeting, and streaming support.
    """

    def __init__(self, agent_name: str, response_schema: Type[BaseModel]):
        self.agent_name = agent_name
        self.response_schema = response_schema

    # ------------------------------------------------------------------
    # Prompt rendering
    # ------------------------------------------------------------------

    def render_prompts(self, context_vars: Dict[str, Any], version: str = "1.0.0") -> Tuple[str, str]:
        """
        Dynamically loads agent's versioned prompts from PromptLibrary and renders with Jinja2.
        """
        key = self.agent_name.lower().replace(" agent", "").strip()
        system_tmpl, user_tmpl, _ = prompt_loader.load_prompt(key, version)

        from jinja2 import Template
        system_prompt = Template(system_tmpl).render(context_vars)
        user_prompt = Template(user_tmpl).render(context_vars)
        return system_prompt, user_prompt

    # ------------------------------------------------------------------
    # API-key lookup (still needed for provider_factory calls)
    # ------------------------------------------------------------------

    def _get_api_key(self, provider_name: str) -> str:
        """Returns the configured API key for the given provider."""
        key = provider_name.strip().lower()
        if key == "google":
            return settings.GOOGLE_API_KEY or ""
        elif key == "groq":
            return settings.GROQ_API_KEY or ""
        elif key == "openrouter":
            return settings.OPENROUTER_API_KEY or ""
        elif key == "nvidia":
            return settings.NVIDIA_API_KEY or ""
        return ""

    def _get_provider_details(self, provider_name: str) -> Tuple[str, str]:
        """
        Returns a (model_name, api_key) tuple for the given provider.
        Uses provider_registry to resolve the best available model and
        _get_api_key to fetch the API credential.
        """
        model = provider_registry.get_best_model(provider_name) or ""
        api_key = self._get_api_key(provider_name)
        return model, api_key

    # ------------------------------------------------------------------
    # Core LLM invocation
    # ------------------------------------------------------------------

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Executes LLM query with intelligent provider routing, failover,
        smart retry logic, and optional streaming.

        Retry policy:
          - Retryable (timeout, 429, 500-504): retry with backoff on same provider
          - Non-retryable (400, 401, 403, 404): skip provider immediately (no retries)
        """
        started_timestamp = time.time()

        # Get task-aware ordered providers from registry
        ordered_providers = provider_registry.get_ordered_providers(self.agent_name)
        active_provider = settings.AI_PROVIDER
        
        provider_chain = [p.strip().lower() for p in settings.AI_PROVIDER_CHAIN.split(",")]
        if active_provider.lower() not in provider_chain:
            provider_chain.insert(0, active_provider.lower())
        else:
            provider_chain.remove(active_provider.lower())
            provider_chain.insert(0, active_provider.lower())

        # Prioritize fast providers for Documentation, Testing, and Summary agents
        is_fast_task = self.agent_name in ["Documentation Agent", "Testing Agent", "Summary Agent"]
        if is_fast_task:
            fast_providers = ["google", "groq"]
            for fp in reversed(fast_providers):
                if fp in provider_chain:
                    provider_chain.remove(fp)
                    provider_chain.insert(0, fp)

        final_response_obj: Optional[BaseModel] = None
        telemetry = {}
        last_exception = None

        for current_provider in provider_chain:
            # Task 7: Query ProviderRegistry & ProviderHealthMonitor first
            status_info = provider_registry.get_status(current_provider)
            is_healthy = provider_health_monitor.is_healthy(current_provider)
            
            if status_info["status"] != "available":
                console.ai(f"{current_provider.capitalize()}\nUnsupported model or disabled\n↓\nSkipped")
                continue
            if not is_healthy:
                console.ai(f"{current_provider.capitalize()}\nUnhealthy (Cooldown active)\n↓\nSkipped")
                continue

            # Task 3: Resolve dynamic model name through ProviderRegistry
            model_name = provider_registry.get_best_model(current_provider)
            if not model_name:
                console.ai(f"{current_provider.capitalize()}\nModel resolution failed\n↓\nSkipped")
                continue

            _, api_key = self._get_provider_details(current_provider)
            client = provider_factory.get_client(current_provider)
            
            # Task 8: Structured Log: AI REQUEST
            # Estimate tokens
            est_input_tokens = token_manager.estimate_tokens(system_prompt + user_prompt)
            console.display_ai_request(
                agent_name=self.agent_name,
                provider=current_provider,
                model=model_name,
                tokens=est_input_tokens,
                streaming="YES" if on_chunk else "NO",
                cache_status="MISS"  # Initially assumes miss, resolved later if cached is returned
            )

            # Task 4: Retry Policy implementation
            for attempt in range(settings.MAX_RETRIES):
                try:
                    response_text = ""
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    
                    if on_chunk:
                        # Throttled streaming: buffers chunks and flushes every 80ms
                        full_text_list = []
                        chunk_buffer = []
                        last_flush_time = time.time()
                        
                        async for chunk in client.generate_stream(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            model_name=model_name,
                            api_key=api_key,
                            temperature=temperature,
                            max_tokens=settings.MAX_TOKENS,
                            timeout=settings.TIMEOUT
                        ):
                            full_text_list.append(chunk)
                            chunk_buffer.append(chunk)
                            
                            now = time.time()
                            if now - last_flush_time >= 0.08:  # 80ms window
                                flushed_text = "".join(chunk_buffer)
                                chunk_buffer.clear()
                                last_flush_time = now
                                if flushed_text:
                                    on_chunk(flushed_text)
                                    
                        # Flush leftovers
                        if chunk_buffer:
                            flushed_text = "".join(chunk_buffer)
                            on_chunk(flushed_text)
                            
                        response_text = "".join(full_text_list)
                        prompt_tokens = token_manager.estimate_tokens(system_prompt + user_prompt)
                        completion_tokens = token_manager.estimate_tokens(response_text)
                        total_tokens = prompt_tokens + completion_tokens
                    else:
                        response = await client.generate(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            model_name=model_name,
                            api_key=api_key,
                            temperature=temperature,
                            max_tokens=settings.MAX_TOKENS,
                            timeout=settings.TIMEOUT
                        )
                        response_text = response.text
                        prompt_tokens = response.prompt_tokens or token_manager.estimate_tokens(system_prompt + user_prompt)
                        completion_tokens = response.completion_tokens or token_manager.estimate_tokens(response_text)
                        total_tokens = response.total_tokens or (prompt_tokens + completion_tokens)
                    
                    # Parse and validate response text as JSON matching Pydantic schema
                    parsed_model = response_parser.parse_and_validate(response_text, self.response_schema)
                    
                    # Task 5: Confidence Escalation without throwing exceptions
                    confidence_score = getattr(parsed_model, "confidence", 1.0)
                    if confidence_score < 0.70 and current_provider in ["google", "groq"]:
                        # Find next reasoning provider
                        next_provider = "Reasoning model"
                        try:
                            curr_idx = provider_chain.index(current_provider)
                            if curr_idx + 1 < len(provider_chain):
                                next_provider = provider_chain[curr_idx + 1].capitalize()
                        except ValueError:
                            pass
                        
                        console.ai(f"{current_provider.capitalize()}\nLow confidence ({confidence_score:.2f})\n↓\nEscalating -> {next_provider}")
                        provider_health_monitor.record_success(current_provider, time.time() - started_timestamp)
                        # Switch immediately by breaking retry loop
                        break

                    latency = time.time() - started_timestamp
                    provider_health_monitor.record_success(current_provider, latency)
                    
                    # Task 8: Success display log
                    console.display_ai_response(
                        latency=latency,
                        output_tokens=completion_tokens,
                        confidence=confidence_score
                    )

                    telemetry = {
                        "provider": current_provider,
                        "model": model_name,
                        "latency": latency,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "is_fallback": False
                    }
                    telemetry["total_tokens"] = total_tokens
                    final_response_obj = parsed_model
                    break
                except Exception as err:
                    last_exception = err
                    provider_health_monitor.record_failure(current_provider)
                    
                    # Determine if exception is retriable
                    should_retry = True
                    is_404 = False
                    
                    if isinstance(err, httpx.HTTPStatusError):
                        status_code = err.response.status_code
                        if status_code == 404:
                            is_404 = True
                            should_retry = False
                        elif status_code not in [429, 500, 502, 503, 504]:
                            should_retry = False
                    elif isinstance(err, (httpx.TimeoutException, asyncio.TimeoutError, httpx.ConnectError, httpx.ConnectTimeout)):
                        should_retry = True
                    else:
                        err_str = str(err).lower()
                        if "connection reset" in err_str or "connection refused" in err_str:
                            should_retry = True
                        else:
                            should_retry = False
                    
                    if is_404:
                        # Task 4: Mark provider unavailable and immediately switch
                        provider_registry.mark_unavailable(current_provider, reason="HTTP 404 Not Found")
                        console.error(f"Provider '{current_provider}' returned 404. Disabling and switching immediately.")
                        break  # Break retry loop, switch provider
                    
                    if not should_retry:
                        console.error(f"Attempt {attempt+1} failed with non-retriable {type(err).__name__}: {err}. Switching immediately.")
                        break  # Break retry loop, switch provider
                    
                    console.warning(f"Attempt {attempt+1} failed with retriable {type(err).__name__}: {err}. Retrying...")
                    if attempt < settings.MAX_RETRIES - 1:
                        await asyncio.sleep(1.0 + random.random())

            if final_response_obj:
                break

        if final_response_obj:
            return final_response_obj, telemetry

        # ---------------------------------------------------------------
        # Hard fallback: all providers exhausted — return empty schema
        # ---------------------------------------------------------------
        logger.error(
            f"[{self.agent_name}] All providers failed. "
            f"Activating heuristic fallback. Last error: {last_exception}"
        )

        fallback_data: Dict[str, Any] = {}
        for field_name, field_info in self.response_schema.model_fields.items():
            ann = field_info.annotation
            if ann == list or (isinstance(ann, type) and issubclass(ann, list)):
                fallback_data[field_name] = []
            elif ann == dict or (isinstance(ann, type) and issubclass(ann, dict)):
                fallback_data[field_name] = {}
            elif ann == str:
                fallback_data[field_name] = "Information unavailable due to provider downtime."
            elif ann in (float, int):
                fallback_data[field_name] = 0
            else:
                fallback_data[field_name] = None

        fallback_model = self.response_schema.model_validate(fallback_data)

        telemetry = {
            "provider": "fallback",
            "model": "heuristic",
            "latency": time.time() - started_timestamp,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "is_fallback": True,
        }
        return fallback_model, telemetry
