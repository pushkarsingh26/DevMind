from typing import Dict
from app.ai.client import (
    LLMProviderClient,
    GeminiProviderClient,
    GroqProviderClient,
    OpenRouterProviderClient,
    NvidiaNimProviderClient,
)


class ProviderFactory:
    """
    Factory mapping provider name strings to cached LLM client instances.
    Supported providers: google, groq, openrouter, nvidia.
    """
    def __init__(self):
        self._clients: Dict[str, LLMProviderClient] = {}

    def get_client(self, provider_name: str) -> LLMProviderClient:
        """
        Retrieves (or lazily instantiates) the client for the given provider name.
        """
        provider_key = provider_name.strip().lower()

        if provider_key in self._clients:
            return self._clients[provider_key]

        if provider_key == "google":
            client: LLMProviderClient = GeminiProviderClient()
        elif provider_key == "groq":
            client = GroqProviderClient()
        elif provider_key == "openrouter":
            client = OpenRouterProviderClient()
        elif provider_key == "nvidia":
            client = NvidiaNimProviderClient()
        else:
            raise ValueError(
                f"Unsupported AI provider: '{provider_name}'. "
                f"Supported providers: google, groq, openrouter, nvidia."
            )

        self._clients[provider_key] = client
        return client


provider_factory = ProviderFactory()
