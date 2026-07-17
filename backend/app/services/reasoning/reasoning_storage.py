"""Reasoning Engine storage layer.

Persists under:
    backend/data/repositories/{repository_id}/reasoning/

Files:
    cache.json     — version manifest (written LAST for atomic validity)
    reasoning.json — full ReasoningSummary
    chains.json    — List[ReasoningChain] sorted by chain_id
    metrics.json   — ReasoningMetrics (13 telemetry fields)
    telemetry.json — raw per-stage timing dict
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logger import logger
from app.services.reasoning.versions import (
    REASONING_VERSION,
    SCHEMA_VERSION,
    GENERATOR_VERSION,
)
from app.services.reasoning.reasoning_models import (
    ReasoningSummary,
    ReasoningChain,
    ReasoningMetrics,
)


def _reasoning_dir(repository_id: str) -> str:
    base = os.path.join(str(settings.WORKSPACE_ROOT), "repositories", repository_id, "reasoning")
    os.makedirs(base, exist_ok=True)
    return base


def _path(repository_id: str, filename: str) -> str:
    return os.path.join(_reasoning_dir(repository_id), filename)


def _write_json(filepath: str, data: Any) -> None:
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, filepath)  # atomic on most OSes


def _read_json(filepath: str) -> Optional[Any]:
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save(
    repository_id: str,
    summary: ReasoningSummary,
    chains: List[ReasoningChain],
    metrics: ReasoningMetrics,
    telemetry: Dict[str, Any],
) -> None:
    """Persist all reasoning artefacts. cache.json is written LAST.

    If a crash occurs before cache.json is written the old cache entry
    (if any) remains valid, preventing a corrupted partial state from
    being treated as a cache hit.
    """
    t0 = time.time()
    try:
        _write_json(_path(repository_id, "reasoning.json"), summary.to_dict())
        _write_json(
            _path(repository_id, "chains.json"),
            sorted([c.to_dict() for c in chains], key=lambda x: x["chain_id"]),
        )
        _write_json(_path(repository_id, "metrics.json"), metrics.to_dict())
        _write_json(_path(repository_id, "telemetry.json"), telemetry)

        serialization_ms = (time.time() - t0) * 1000

        # Write cache manifest last — this is the atomicity sentinel
        cache_manifest = {
            "repository_hash": summary.repository_hash,
            "reasoning_version": REASONING_VERSION,
            "schema_version": SCHEMA_VERSION,
            "generator_version": GENERATOR_VERSION,
            "generated_at": summary.generated_at,
            "reasoning_score": round(summary.reasoning_score, 4),
            "build_time_ms": round(summary.build_time_ms, 2),
            "serialization_ms": round(serialization_ms, 2),
        }
        _write_json(_path(repository_id, "cache.json"), cache_manifest)
        logger.debug(f"[ReasoningStorage] Saved reasoning for {repository_id}")
    except Exception as exc:
        logger.error(f"[ReasoningStorage] Save failed for {repository_id}: {exc}")
        raise


def load(
    repository_id: str,
) -> Optional[Tuple[ReasoningSummary, List[ReasoningChain], ReasoningMetrics]]:
    """Load all reasoning artefacts from disk. Returns None if any are missing."""
    try:
        r_data = _read_json(_path(repository_id, "reasoning.json"))
        c_data = _read_json(_path(repository_id, "chains.json"))
        m_data = _read_json(_path(repository_id, "metrics.json"))
        if r_data is None or c_data is None or m_data is None:
            return None
        summary = ReasoningSummary.from_dict(r_data)
        chains = [ReasoningChain.from_dict(c) for c in c_data]
        metrics = ReasoningMetrics.from_dict(m_data)
        return summary, chains, metrics
    except Exception as exc:
        logger.warning(f"[ReasoningStorage] Load failed for {repository_id}: {exc}")
        return None


def validate_cache(repository_id: str, repo_hash: str) -> bool:
    """Return True iff cache.json exists and all version fields + hash match.

    Any parse error or missing field is treated as a cache miss (False).
    This prevents corrupted cache.json from blocking reasoning.
    """
    cache_data = _read_json(_path(repository_id, "cache.json"))
    if not cache_data:
        return False
    try:
        return (
            cache_data.get("repository_hash") == repo_hash
            and cache_data.get("reasoning_version") == REASONING_VERSION
            and cache_data.get("schema_version") == SCHEMA_VERSION
            and cache_data.get("generator_version") == GENERATOR_VERSION
        )
    except Exception:
        return False


def invalidate(repository_id: str) -> None:
    """Remove cache.json only. Other files are kept for replay/debugging."""
    cache_path = _path(repository_id, "cache.json")
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            logger.debug(f"[ReasoningStorage] Cache invalidated for {repository_id}")
        except Exception as exc:
            logger.warning(f"[ReasoningStorage] Failed to invalidate cache for {repository_id}: {exc}")


def load_section(repository_id: str, section: str) -> Optional[Dict[str, Any]]:
    """Load a specific section from reasoning.json for API GET performance.

    section must be one of: 'dependency_reasoning', 'impact_reasoning',
    'evidence_ranking', 'historical_reasoning', 'reasoning_context'
    """
    r_data = _read_json(_path(repository_id, "reasoning.json"))
    if r_data is None:
        return None
    return r_data.get(section)


def load_metrics_dict(repository_id: str) -> Optional[Dict[str, Any]]:
    """Load raw metrics.json as a dict (for API serialization)."""
    return _read_json(_path(repository_id, "metrics.json"))


def load_chains_list(repository_id: str) -> Optional[List[Dict[str, Any]]]:
    """Load raw chains.json as a list (for API serialization)."""
    return _read_json(_path(repository_id, "chains.json"))


def load_full_dict(repository_id: str) -> Optional[Dict[str, Any]]:
    """Load the full reasoning.json as a raw dict (for API serialization)."""
    return _read_json(_path(repository_id, "reasoning.json"))


def get_cache_manifest(repository_id: str) -> Optional[Dict[str, Any]]:
    """Return cache.json as a dict for status checks."""
    return _read_json(_path(repository_id, "cache.json"))
