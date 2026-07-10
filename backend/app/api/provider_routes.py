"""
Provider Diagnostics API — Phase 7.5.2
GET /api/providers/status  →  live health snapshot for all configured providers
"""
from fastapi import APIRouter
from app.ai.provider_registry import provider_registry

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get(
    "/status",
    summary="Provider Health Status",
    description=(
        "Returns live health, model resolution, latency, and success-rate "
        "metrics for every configured AI provider."
    ),
)
async def get_provider_status():
    """
    Returns a list of provider status objects:

    ```json
    [
      {
        "provider": "google",
        "healthy": true,
        "configured_model": "gemini-2.5-flash",
        "active_model": "gemini-2.5-flash",
        "latency_ms": 342.0,
        "success_rate": 98.2,
        "consecutive_failures": 0,
        "last_error": null,
        "last_success": "2026-07-10T14:55:00Z",
        "supports_streaming": true,
        "supports_tool_calling": false,
        "health_score": 0.98
      },
      ...
    ]
    ```
    """
    return provider_registry.get_all_status()
