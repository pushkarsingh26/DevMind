import httpx
import time
import asyncio
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logger import logger
from app.services.provider_health import provider_health_monitor

# --- Phase 7 API Status Constants ---
RETRYABLE_STATUS_CODES = [429, 500, 502, 503, 504]
NON_RETRYABLE_STATUS_CODES = [400, 401, 403, 404]

class ProviderRegistry:
    """
    Registry for managing and discovering provider model capabilities.
    Validates model settings against List Models API endpoints and supports fallbacks.
    """
    def __init__(self):
        # Initial status definitions
        self._provider_status: Dict[str, Dict[str, Any]] = {
            "google": {
                "status": "unavailable",
                "models": [],
                "selected_model": settings.GOOGLE_MODEL_NAME,
                "configured_model": settings.GOOGLE_MODEL_NAME,
                "latency": 0.0,
                "last_success": None,
                "fallback": False
            },
            "groq": {
                "status": "unavailable",
                "models": [],
                "selected_model": settings.GROQ_MODEL_NAME,
                "configured_model": settings.GROQ_MODEL_NAME,
                "latency": 0.0,
                "last_success": None,
                "fallback": False
            },
            "openrouter": {
                "status": "unavailable",
                "models": [],
                "selected_model": settings.OPENROUTER_MODEL_NAME,
                "configured_model": settings.OPENROUTER_MODEL_NAME,
                "latency": 0.0,
                "last_success": None,
                "fallback": False
            },
            "nvidia": {
                "status": "unavailable",
                "models": [],
                "selected_model": settings.NVIDIA_MODEL_NAME,
                "configured_model": settings.NVIDIA_MODEL_NAME,
                "latency": 0.0,
                "last_success": None,
                "fallback": False
            },
        }

        # Predefined fallback lists for each provider
        self.fallback_models = {
            "google": ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            "groq": ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192"],
            "openrouter": ["google/gemini-2.5-flash", "meta-llama/llama-3.3-70b-instruct", "deepseek/deepseek-chat"],
            "nvidia": ["meta/llama-3.3-70b-instruct", "nvidia/llama-3.1-nemotron-70b-instruct"],
        }

        # Tracks logged warnings to log each warning only once
        self._logged_warnings = set()

    def _log_warning_once(self, key: str, msg: str):
        if key not in self._logged_warnings:
            logger.warning(msg)
            self._logged_warnings.add(key)

    def get_status(self, provider: str) -> Dict[str, Any]:
        provider = provider.strip().lower()
        return self._provider_status.get(provider, {
            "status": "unavailable",
            "models": [],
            "selected_model": "",
            "configured_model": "",
            "latency": 0.0,
            "last_success": None,
            "fallback": False
        })

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        res = {}
        for provider, base_status in self._provider_status.items():
            health_stats = provider_health_monitor.get_stats(provider)
            status_str = base_status["status"]
            if not provider_health_monitor.is_healthy(provider):
                status_str = "offline"
            
            res[provider] = {
                "status": status_str,
                "selected_model": base_status["selected_model"],
                "configured_model": base_status["configured_model"],
                "models": base_status["models"],
                "latency": base_status["latency"] or (health_stats.get("latency_sum", 0) / max(health_stats.get("success_count", 0), 1)),
                "last_success": base_status["last_success"] or health_stats.get("last_success"),
                "fallback": base_status["fallback"]
            }
        return res

    def get_all_status(self) -> List[Dict[str, Any]]:
        res = []
        for provider, base_status in self._provider_status.items():
            health_stats = provider_health_monitor.get_stats(provider)
            status_str = base_status["status"]
            if not provider_health_monitor.is_healthy(provider):
                status_str = "offline"
            
            succ = health_stats.get("success_count", 0)
            fail = health_stats.get("failure_count", 0)
            total = succ + fail
            success_rate = (succ / total * 100.0) if total > 0 else 100.0
            
            avg_latency = base_status["latency"] or (health_stats.get("latency_sum", 0) / max(succ, 1))
            latency_ms = avg_latency * 1000.0
            
            healthy = status_str == "available"
            
            res.append({
                "provider": provider,
                "healthy": healthy,
                "configured_model": base_status["configured_model"],
                "active_model": base_status["selected_model"],
                "latency_ms": latency_ms,
                "success_rate": success_rate,
                "consecutive_failures": health_stats.get("consecutive_failures", 0),
                "last_error": None if healthy else f"Status: {status_str}",
                "last_success": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(health_stats["last_success"])) if health_stats.get("last_success") else None,
                "supports_streaming": True,
                "supports_tool_calling": provider in ["google", "groq", "openrouter", "nvidia"],
                "health_score": success_rate / 100.0
            })
        return res

    def mark_unavailable(self, provider: str, reason: str = ""):
        provider = provider.strip().lower()
        if provider in self._provider_status:
            self._provider_status[provider]["status"] = "unavailable"
            logger.warning(f"ProviderRegistry: Marked '{provider}' as unavailable. Reason: {reason}")

    async def validate_provider(self, provider: str) -> Dict[str, Any]:
        provider = provider.lower().strip()
        status_info = self._provider_status.get(provider)
        if not status_info:
            return {"status": "invalid_configuration", "models": [], "selected_model": "", "configured_model": "", "fallback": False}

        api_key = ""
        model_name = status_info["configured_model"]
        url = ""

        if provider == "google":
            api_key = settings.GOOGLE_API_KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        elif provider == "groq":
            api_key = settings.GROQ_API_KEY
            url = "https://api.groq.com/openai/v1/models"
        elif provider == "openrouter":
            api_key = settings.OPENROUTER_API_KEY
            url = "https://openrouter.ai/api/v1/models"
        elif provider == "nvidia":
            api_key = settings.NVIDIA_API_KEY
            url = "https://integrate.api.nvidia.com/v1/models"

        # Check configuration
        if not api_key or "api_key_here" in api_key:
            status_info["status"] = "invalid_configuration"
            return status_info

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                headers = {}
                if provider in ["groq", "openrouter", "nvidia"] and api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                response = await client.get(url, headers=headers)
                latency = time.time() - start_time
                status_info["latency"] = latency

                if response.status_code in [401, 403]:
                    status_info["status"] = "authentication_failed"
                    return status_info
                elif response.status_code != 200:
                    status_info["status"] = "unavailable"
                    return status_info
                
                data = response.json()
                models = []
                if provider == "google":
                    models = [m["name"].replace("models/", "") for m in data.get("models", [])]
                elif provider in ["groq", "openrouter", "nvidia"]:
                    models = [m["id"] for m in data.get("data", [])]
                
                status_info["models"] = list(set(models))
                
                # Check if configured model is available
                if model_name not in status_info["models"]:
                    # Attempt fallback resolution
                    status_info["fallback"] = True
                    resolved = None
                    for fb in self.fallback_models.get(provider, []):
                        if fb in status_info["models"]:
                            resolved = fb
                            break
                    
                    # If fallback not found in listed models, auto-resolve to the first model returned by provider API
                    if not resolved and status_info["models"]:
                        resolved = status_info["models"][0]
                    
                    if resolved:
                        status_info["selected_model"] = resolved
                        status_info["status"] = "available"
                        status_info["last_success"] = time.time()
                        self._log_warning_once(
                            f"{provider}_fallback_model",
                            f"ProviderRegistry: Configured model '{model_name}' for '{provider}' is unavailable. Auto-resolved to supported model: '{resolved}'."
                        )
                    else:
                        status_info["status"] = "invalid_configuration"
                        self._log_warning_once(
                            f"{provider}_invalid_model",
                            f"ProviderRegistry: Configured model '{model_name}' for '{provider}' is unavailable and no fallbacks found. Model validation failed."
                        )
                else:
                    status_info["selected_model"] = model_name
                    status_info["status"] = "available"
                    status_info["last_success"] = time.time()
                    status_info["fallback"] = False
                    
        except Exception as e:
            status_info["status"] = "unavailable"
            self._log_warning_once(
                f"{provider}_validation_failed",
                f"ProviderRegistry: Validation call failed for '{provider}': {e}"
            )
        
        return status_info

    async def validate_all(self):
        tasks = [self.validate_provider(p) for p in self._provider_status.keys()]
        await asyncio.gather(*tasks)

    def get_ordered_providers(self, agent_name: str = "") -> List[str]:
        """
        Returns a list of available providers ordered by preference for the given agent.
        Fast-task agents (Documentation, Testing, Summary) prefer google and groq first.
        All other agents use the standard priority order from the provider chain.
        Only providers with status == 'available' are included.
        """
        available = [
            p for p, s in self._provider_status.items()
            if s["status"] == "available"
        ]

        fast_tasks = ["Documentation Agent", "Testing Agent", "Summary Agent"]
        if agent_name in fast_tasks:
            preferred = ["google", "groq"]
            ordered = [p for p in preferred if p in available]
            ordered += [p for p in available if p not in preferred]
        else:
            # Standard priority: google > openrouter > nvidia > groq
            priority = ["google", "openrouter", "nvidia", "groq"]
            ordered = [p for p in priority if p in available]
            ordered += [p for p in available if p not in priority]

        return ordered

    def get_best_model(self, provider: str) -> Optional[str]:
        status_info = self.get_status(provider)
        if status_info["status"] != "available":
            return None
        return status_info["selected_model"]

    def get_runtime_stats(self, provider: str) -> Dict[str, Any]:
        """Exposes runtime stats for a provider from provider_health_monitor."""
        provider = provider.strip().lower()
        stats = provider_health_monitor.get_stats(provider)
        is_healthy = provider_health_monitor.is_healthy(provider)
        
        successes = stats.get("success_count", 0)
        failures = stats.get("failure_count", 0)
        total = successes + failures
        success_rate = (successes / total) if total > 0 else 1.0
        
        avg_latency = (stats.get("latency_sum", 0.0) / successes) if successes > 0 else 0.0
        
        return {
            "success_rate": round(success_rate, 2),
            "failure_rate": round(1.0 - success_rate, 2),
            "average_latency_sec": round(avg_latency, 2),
            "is_healthy": is_healthy,
            "disabled_until": stats.get("disabled_until")
        }

provider_registry = ProviderRegistry()

