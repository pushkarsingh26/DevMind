from typing import Dict
from app.ai.client import (
    LLMProviderClient,
    GeminiProviderClient,
    GroqProviderClient,
    OpenRouterProviderClient,
    NvidiaNimProviderClient,
    OllamaProviderClient,  # Phase 5
)

class ProviderFactory:
    """
    Factory mapping provider strings to cached LLM client instances.
    """
    def __init__(self):
        self._clients: Dict[str, LLMProviderClient] = {}

    def get_client(self, provider_name: str) -> LLMProviderClient:
        """
        Retrieves a cached instance of the client matching the target provider name.
        """
        provider_key = provider_name.strip().lower()

        # Check cache dictionary first
        if provider_key in self._clients:
            return self._clients[provider_key]

        # Instantiate target client profile
        if provider_key == "google":
            client = GeminiProviderClient()
        elif provider_key == "groq":
            client = GroqProviderClient()
        elif provider_key == "openrouter":
            client = OpenRouterProviderClient()
        elif provider_key == "nvidia":
            client = NvidiaNimProviderClient()
        elif provider_key == "ollama":            # Phase 5 — local inference
            client = OllamaProviderClient()
        else:
            raise ValueError(
                f"Unsupported AI provider option: '{provider_name}'. "
                f"Supported profiles: google, groq, openrouter, nvidia, ollama."
            )

        # Cache initialized instance
        self._clients[provider_key] = client
        return client

provider_factory = ProviderFactory()
