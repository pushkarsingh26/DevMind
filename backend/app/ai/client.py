"""
AI Provider Clients — Phase 7.5

Cloud-only providers: Google AI Studio (Gemini), Groq, OpenRouter, NVIDIA NIM.

Phase 4 interface (unchanged):
  generate(system_prompt, user_prompt, ...)  → ProviderResponse

Phase 5 additions (non-breaking):
  generate_chat(messages, ...)               → ProviderResponse
  generate_chat_stream(messages, ...)        → AsyncIterator[str]

generate_chat / generate_chat_stream accept the standard OpenAI-compatible
messages[] list (list of {"role": ..., "content": ...} dicts), enabling
multi-turn conversation without restructuring Phase 4 code paths.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.logger import logger


class ProviderResponse:
    """
    Unified response wrapper returned by all LLM clients.
    """
    def __init__(
        self,
        text: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost: float = 0.0
    ):
        self.text = text
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.estimated_cost = estimated_cost


class LLMProviderClient(ABC):
    """
    Abstract interface for LLM service providers.
    All concrete clients must implement generate() and generate_chat().
    generate_stream() and generate_chat_stream() have default implementations
    that fall back to non-streaming for providers that do not support it.
    """

    # ------------------------------------------------------------------
    # Phase 4 API (one-shot, system + user prompt)
    # ------------------------------------------------------------------

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        """Synchronous (non-streaming) single-turn generation."""
        pass

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> AsyncIterator[str]:
        """
        Streaming single-turn generation.
        Delegates to generate_chat_stream to leverage native streaming.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        async for chunk in self.generate_chat_stream(
            messages=messages,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        ):
            yield chunk

    # ------------------------------------------------------------------
    # Phase 5 API (multi-turn messages[] list)
    # ------------------------------------------------------------------

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        """
        Non-streaming multi-turn generation.
        Default: extracts system + last user message and delegates to generate().
        Concrete clients should override for native messages[] support.
        """
        system_prompt = ""
        user_parts = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_parts.append(f"[{msg['role'].upper()}]: {msg['content']}")
        user_prompt = "\n".join(user_parts)
        return await self.generate(
            system_prompt, user_prompt, model_name, api_key,
            temperature, max_tokens, timeout
        )

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> AsyncIterator[str]:
        """
        Streaming multi-turn generation.
        Default: delegates to generate_chat() and yields full text as one chunk.
        Concrete clients should override with true streaming.
        """
        resp = await self.generate_chat(
            messages, model_name, api_key, temperature, max_tokens, timeout
        )
        yield resp.text


# ---------------------------------------------------------------------------
# Google AI Studio — Gemini
# ---------------------------------------------------------------------------

class GeminiProviderClient(LLMProviderClient):
    """Google AI Studio Gemini API Client."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json"
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as err:
            logger.error(f"GeminiClient: Failed to parse text: {err}. Response: {data}")
            raise ValueError("Malformed Gemini response payload")

        usage = data.get("usageMetadata", {})
        return ProviderResponse(
            text=text,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            total_tokens=usage.get("totalTokenCount", 0),
            estimated_cost=0.0
        )

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        """
        Gemini uses a 'contents' array with alternating user/model turns
        plus a separate 'systemInstruction' field.
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )

        system_prompt = ""
        contents = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_prompt = content
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:  # user
                contents.append({"role": "user", "parts": [{"text": content}]})

        if not contents:
            raise ValueError("GeminiClient: No user/assistant messages in history.")

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json"
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as err:
            logger.error(f"GeminiClient: Failed to parse chat text: {err}. Response: {data}")
            raise ValueError("Malformed Gemini chat response payload")

        usage = data.get("usageMetadata", {})
        return ProviderResponse(
            text=text,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            total_tokens=usage.get("totalTokenCount", 0),
            estimated_cost=0.0
        )

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> AsyncIterator[str]:
        """
        Gemini streaming via streamGenerateContent (SSE-like NDJSON).
        Yields text chunks as they arrive.
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:streamGenerateContent?alt=sse&key={api_key}"
        )

        system_prompt = ""
        contents = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_prompt = content
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                        text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                        if text:
                            yield text
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue


# ---------------------------------------------------------------------------
# OpenAI-Compatible Base (Groq, OpenRouter, NVIDIA NIM)
# ---------------------------------------------------------------------------

class OpenAICompatibleClient(LLMProviderClient, ABC):
    """
    Base client for providers with an OpenAI-compatible /chat/completions API.
    Subclasses only need to set the endpoint URL.
    """

    def __init__(self, default_endpoint: str):
        self.default_endpoint = default_endpoint

    # Phase 4 method — unchanged
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        custom_url: Optional[str] = None
    ) -> ProviderResponse:
        endpoint = custom_url or self.default_endpoint
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
        return await self._post(endpoint, api_key, payload, timeout)

    # Phase 5 — native multi-turn support
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
        return await self._post(self.default_endpoint, api_key, payload, timeout)

    # Phase 5 — streaming multi-turn
    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> AsyncIterator[str]:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", self.default_endpoint, json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue

    # ------------------------------------------------------------------
    # Shared HTTP helper
    # ------------------------------------------------------------------

    async def _post(
        self,
        endpoint: str,
        api_key: str,
        payload: Dict[str, Any],
        timeout: float
    ) -> ProviderResponse:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            logger.error(f"OpenAICompatibleClient: Parse error: {err}. Response: {data}")
            raise ValueError("Malformed OpenAI-compatible response payload")

        usage = data.get("usage", {})
        return ProviderResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            estimated_cost=0.0
        )


# ---------------------------------------------------------------------------
# Concrete OpenAI-compatible clients
# ---------------------------------------------------------------------------

class GroqProviderClient(OpenAICompatibleClient):
    def __init__(self):
        super().__init__("https://api.groq.com/openai/v1/chat/completions")


class OpenRouterProviderClient(OpenAICompatibleClient):
    def __init__(self):
        super().__init__(f"{settings.OPENROUTER_BASE_URL}/chat/completions")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
        return await super().generate(
            system_prompt, user_prompt, model_name, api_key,
            temperature, max_tokens, timeout, custom_url=url
        )


class NvidiaNimProviderClient(OpenAICompatibleClient):
    def __init__(self):
        super().__init__(f"{settings.NVIDIA_BASE_URL}/chat/completions")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ProviderResponse:
        url = f"{settings.NVIDIA_BASE_URL}/chat/completions"
        return await super().generate(
            system_prompt, user_prompt, model_name, api_key,
            temperature, max_tokens, timeout, custom_url=url
        )

