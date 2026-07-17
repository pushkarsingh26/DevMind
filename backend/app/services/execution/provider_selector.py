"""Provider Selector with multi-factor scoring.
"""

from __future__ import annotations

from typing import Dict, Any, List

from app.core.logger import logger
from app.services.provider_health import provider_health_monitor


class ProviderSelector:
    """Deterministic, rule-based provider selector using latency, success, and cost."""

    def __init__(self):
        # Static cost profiles (1.0 = cheapest, 0.0 = most expensive)
        self.cost_ratings = {
            "groq": 1.0,
            "google": 0.9,
            "nvidia": 0.8,
            "openrouter": 0.6,
        }

    def score_provider(self, provider: str) -> float:
        """Computes score = 40% success rate + 30% latency + 20% availability + 10% cost."""
        provider = provider.strip().lower()
        stats = provider_health_monitor.get_stats(provider)
        
        # 1. Success Rate (40%)
        successes = stats.get("success_count", 0)
        failures = stats.get("failure_count", 0)
        total_runs = successes + failures
        success_rate = (successes / total_runs) if total_runs > 0 else 1.0  # Default to 1.0 if fresh
        
        # 2. Latency Rating (30%)
        # Calculate average latency. Lower is better.
        avg_latency = (stats.get("latency_sum", 0.0) / successes) if successes > 0 else 0.5  # Assume 500ms default
        # Rating = 1.0 / (1.0 + avg_latency)
        latency_rating = 1.0 / (1.0 + avg_latency)

        # 3. Availability (20%)
        # Healthy status checks
        is_healthy = provider_health_monitor.is_healthy(provider)
        availability_rating = 1.0 if is_healthy else 0.0

        # 4. Cost Rating (10%)
        cost_rating = self.cost_ratings.get(provider, 0.5)

        # Combine
        score = (
            (0.4 * success_rate) +
            (0.3 * latency_rating) +
            (0.2 * availability_rating) +
            (0.1 * cost_rating)
        )
        return round(score, 4)

    def select_best_provider(self, required_agent: str, current_provider: str = None) -> str:
        """Resolves the best available provider, optionally excluding current_provider on failover."""
        # Active providers list in the system
        providers = ["google", "groq", "openrouter", "nvidia"]
        
        scored_providers = []
        for p in providers:
            # Skip current provider if we are failing over
            if current_provider and p == current_provider.strip().lower():
                continue
                
            score = self.score_provider(p)
            scored_providers.append((p, score))

        # Sort by score descending
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        
        if scored_providers:
            best_provider, best_score = scored_providers[0]
            logger.info(f"[ProviderSelector] Selected '{best_provider}' with score {best_score} (excluding '{current_provider}')")
            return best_provider
            
        # Fallback to google if all are excluded or unavailable
        return "google"


provider_selector = ProviderSelector()
