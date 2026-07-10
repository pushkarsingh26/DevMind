import time
import random
import asyncio
from typing import List, Dict, Any, Type, Tuple, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.core.logger import logger
from app.ai.provider_factory import provider_factory
from app.ai.token_manager import token_manager
from app.ai.response_parser import response_parser

from app.ai.prompt_loader import prompt_loader

class BaseAgent:
    """
    Abstract/Base specialized agent class containing common LLM invocation
    failover, token budgeting, and parsing logic.
    """
    def __init__(self, agent_name: str, response_schema: Type[BaseModel]):
        self.agent_name = agent_name
        self.response_schema = response_schema

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

    def _get_provider_details(self, provider_name: str) -> Tuple[str, str]:
        key = provider_name.strip().lower()
        if key == "google":
            return settings.GOOGLE_MODEL_NAME, settings.GOOGLE_API_KEY
        elif key == "groq":
            return settings.GROQ_MODEL_NAME, settings.GROQ_API_KEY
        elif key == "openrouter":
            return settings.OPENROUTER_MODEL_NAME, settings.OPENROUTER_API_KEY
        elif key == "nvidia":
            return settings.NVIDIA_MODEL_NAME, settings.NVIDIA_API_KEY
        elif key == "ollama":
            return settings.OLLAMA_MODEL_NAME, ""
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Executes model query with failover routing and validates output against schema.
        """
        started_timestamp = time.time()
        active_provider = settings.AI_PROVIDER
        
        provider_chain = [p.strip().lower() for p in settings.AI_PROVIDER_CHAIN.split(",")]
        if active_provider.lower() not in provider_chain:
            provider_chain.insert(0, active_provider.lower())
        else:
            provider_chain.remove(active_provider.lower())
            provider_chain.insert(0, active_provider.lower())

        final_response_obj: Optional[BaseModel] = None
        telemetry = {}
        last_exception = None

        for current_provider in provider_chain:
            try:
                model_name, api_key = self._get_provider_details(current_provider)
            except ValueError:
                continue

            if current_provider != "ollama" and (not api_key or "api_key_here" in api_key):
                continue

            client = provider_factory.get_client(current_provider)
            
            for attempt in range(settings.MAX_RETRIES):
                try:
                    logger.info(f"[{self.agent_name}] Calling provider '{current_provider}' model '{model_name}' (Attempt {attempt+1})")
                    
                    response = await client.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_name=model_name,
                        api_key=api_key,
                        temperature=temperature,
                        max_tokens=settings.MAX_TOKENS,
                        timeout=settings.TIMEOUT
                    )
                    
                    # Parse and validate response text as JSON matching Pydantic schema
                    parsed_model = response_parser.parse_and_validate(response.text, self.response_schema)
                    
                    latency = time.time() - started_timestamp
                    telemetry = {
                        "provider": current_provider,
                        "model": model_name,
                        "latency": latency,
                        "prompt_tokens": response.prompt_tokens or token_manager.estimate_tokens(system_prompt + user_prompt),
                        "completion_tokens": response.completion_tokens or token_manager.estimate_tokens(response.text),
                        "is_fallback": False
                    }
                    telemetry["total_tokens"] = telemetry["prompt_tokens"] + telemetry["completion_tokens"]
                    
                    final_response_obj = parsed_model
                    break
                except Exception as err:
                    last_exception = err
                    logger.warning(f"[{self.agent_name}] Attempt {attempt+1} failed with {type(err).__name__}: {err}")
                    if attempt < settings.MAX_RETRIES - 1:
                        await asyncio.sleep(1.0 + random.random())

            if final_response_obj:
                break

        if final_response_obj:
            return final_response_obj, telemetry

        # Hard Fallback in case of all API failures: build mock model with empty defaults
        logger.error(f"[{self.agent_name}] Heuristic Fallback triggered. All LLM providers failed. Last exception: {last_exception}")
        
        # Get defaults or empty dict for schema
        fallback_data = {}
        for field_name, field_info in self.response_schema.model_fields.items():
            if field_info.annotation == list or str(field_info.annotation).startswith("typing.List"):
                fallback_data[field_name] = []
            elif field_info.annotation == dict or str(field_info.annotation).startswith("typing.Dict"):
                fallback_data[field_name] = {}
            elif field_info.annotation == str:
                fallback_data[field_name] = "Information unavailable due to provider downtime."
            elif field_info.annotation == float or field_info.annotation == int:
                fallback_data[field_name] = 0
            else:
                fallback_data[field_name] = None
        
        fallback_model = self.response_schema.model_validate(fallback_data)
        latency = time.time() - started_timestamp
        
        telemetry = {
            "provider": "fallback",
            "model": "heuristic",
            "latency": latency,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "is_fallback": True
        }
        return fallback_model, telemetry
