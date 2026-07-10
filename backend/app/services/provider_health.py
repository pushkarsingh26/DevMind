import time
from typing import Dict, Any

class ProviderHealthMonitor:
    """
    Maintains runtime health statistics for each AI provider.
    Tracks success rates, failures, latencies, and enforces a 5-minute cooldown
    after 3 consecutive failures.
    """
    def __init__(self):
        self._stats: Dict[str, Dict[str, Any]] = {}
        self.cooldown_seconds = 300  # 5 minutes

    def get_stats(self, provider: str) -> Dict[str, Any]:
        provider = provider.strip().lower()
        if provider not in self._stats:
            self._stats[provider] = {
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "latency_sum": 0.0,
                "last_success": None,
                "disabled_until": None,
            }
        return self._stats[provider]

    def record_success(self, provider: str, latency: float):
        stats = self.get_stats(provider)
        stats["success_count"] += 1
        stats["consecutive_failures"] = 0
        stats["latency_sum"] += latency
        stats["last_success"] = time.time()
        stats["disabled_until"] = None

    def record_failure(self, provider: str):
        stats = self.get_stats(provider)
        stats["failure_count"] += 1
        stats["consecutive_failures"] += 1
        if stats["consecutive_failures"] >= 3:
            stats["disabled_until"] = time.time() + self.cooldown_seconds
            # Log warning about temporary disable
            from app.core.logger import logger
            logger.warning(
                f"Provider '{provider}' has failed 3 consecutive times. "
                f"Temporarily disabling for 5 minutes."
            )

    def is_healthy(self, provider: str) -> bool:
        stats = self.get_stats(provider)
        disabled_until = stats.get("disabled_until")
        if disabled_until and time.time() < disabled_until:
            return False
        return True

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        return self._stats

provider_health_monitor = ProviderHealthMonitor()
