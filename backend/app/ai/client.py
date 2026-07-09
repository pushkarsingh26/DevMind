import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional
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
    """
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
        """
        Asynchronously executes text generation request.
        """
        pass

    @abstractmethod
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
        Asynchronously streams generated tokens.
        """
        pass


class GeminiProviderClient(LLMProviderClient):
    """
    Google AI Studio Gemini API Client.
    """
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        # Structure payload matching Gemini API contracts
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json"
            }
        }
        
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        # Parse text and usage statistics
        text = ""
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as err:
            logger.error(f"Failed to parse text from Gemini response: {err}. Response: {data}")
            raise ValueError("Malformed Gemini response payload")

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)

        # Free tier has 0.0 estimated cost
        return ProviderResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=0.0
        )

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
        # Placeholder for future streaming implementations
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={api_key}"
        raise NotImplementedError("Streaming is not implemented in this phase.")


class OpenAICompatibleClient(LLMProviderClient, ABC):
    """
    Base client implementation for OpenAI compatible APIs (Groq, OpenRouter, NVIDIA NIM).
    """
    def __init__(self, default_endpoint: str):
        self.default_endpoint = default_endpoint

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
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
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

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        text = ""
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            logger.error(f"Failed to parse text from OpenAI-compatible response: {err}. Response: {data}")
            raise ValueError("Malformed response payload")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        # Free tier models have 0.0 estimated cost
        return ProviderResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=0.0
        )

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
        raise NotImplementedError("Streaming is not implemented in this phase.")


class GroqProviderClient(OpenAICompatibleClient):
    """
    Groq API client implementation.
    """
    def __init__(self):
        super().__init__("https://api.groq.com/openai/v1/chat/completions")


class OpenRouterProviderClient(OpenAICompatibleClient):
    """
    OpenRouter API client implementation.
    """
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
        # Override to ensure it goes to the configured OpenRouter endpoint
        url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
        return await super().generate(
            system_prompt, user_prompt, model_name, api_key, temperature, max_tokens, timeout, custom_url=url
        )


class NvidiaNimProviderClient(OpenAICompatibleClient):
    """
    NVIDIA NIM API client implementation.
    """
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
        # Override to ensure it goes to the configured NVIDIA NIM endpoint
        url = f"{settings.NVIDIA_BASE_URL}/chat/completions"
        return await super().generate(
            system_prompt, user_prompt, model_name, api_key, temperature, max_tokens, timeout, custom_url=url
        )
