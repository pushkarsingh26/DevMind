"""Decision Engine storage manager.

Handles persistence of all decision outputs.
cache.json is written last as an atomic sentinel.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logger import logger
from app.services.decision.versions import (
    DECISION_VERSION,
    SCHEMA_VERSION,
    GENERATOR_VERSION,
)
from app.services.decision.decision_models import (
    DecisionSummary,
    DecisionHistoryRecord,
    DecisionMetrics,
    DecisionTelemetry,
)


def _decision_dir(repository_id: str) -> str:
    base = os.path.join(str(settings.WORKSPACE_ROOT), "repositories", repository_id, "decision")
    os.makedirs(base, exist_ok=True)
    return base


def _path(repository_id: str, filename: str) -> str:
    return os.path.join(_decision_dir(repository_id), filename)


def _write_json(filepath: str, data: Any) -> None:
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, filepath)


def _read_json(filepath: str) -> Optional[Any]:
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public Storage API
# ---------------------------------------------------------------------------

def save(
    repository_id: str,
    summary: DecisionSummary,
    history: List[DecisionHistoryRecord],
    metrics: DecisionMetrics,
    telemetry: DecisionTelemetry,
) -> None:
    """Save all decision files atomically. Writes cache.json last."""
    try:
        _write_json(_path(repository_id, "decision.json"), summary.to_dict())
        _write_json(
            _path(repository_id, "history.json"),
            [r.to_dict() for r in sorted(history, key=lambda x: x.completed_at, reverse=True)],
        )
        _write_json(_path(repository_id, "metrics.json"), metrics.to_dict())
        _write_json(_path(repository_id, "telemetry.json"), telemetry.to_dict())

        # Write cache.json last to guarantee valid write
        cache_data = {
            "repository_hash": summary.repository_hash,
            "decision_version": DECISION_VERSION,
            "schema_version": SCHEMA_VERSION,
            "generator_version": GENERATOR_VERSION,
            "generated_at": summary.generated_at,
            "decision_score": round(summary.decision_score, 4),
            "build_time_ms": round(summary.build_time_ms, 2),
        }
        _write_json(_path(repository_id, "cache.json"), cache_data)
        logger.debug(f"[DecisionStorage] Saved decision output for {repository_id}")
    except Exception as exc:
        logger.error(f"[DecisionStorage] Save failed for {repository_id}: {exc}")
        raise


def load(
    repository_id: str,
) -> Optional[Tuple[DecisionSummary, List[DecisionHistoryRecord], DecisionMetrics, DecisionTelemetry]]:
    """Load decision outputs from disk. Returns None if files are missing or broken."""
    try:
        sum_data = _read_json(_path(repository_id, "decision.json"))
        hist_data = _read_json(_path(repository_id, "history.json"))
        met_data = _read_json(_path(repository_id, "metrics.json"))
        tel_data = _read_json(_path(repository_id, "telemetry.json"))

        if sum_data is None or hist_data is None or met_data is None or tel_data is None:
            return None

        summary = DecisionSummary.from_dict(sum_data)
        history = [DecisionHistoryRecord.from_dict(r) for r in hist_data]
        metrics = DecisionMetrics.from_dict(met_data)
        telemetry = DecisionTelemetry.from_dict(tel_data)
        return summary, history, metrics, telemetry
    except Exception as exc:
        logger.warning(f"[DecisionStorage] Load failed for {repository_id}: {exc}")
        return None


def validate_cache(repository_id: str, repo_hash: str) -> bool:
    """Return True if cache.json exists and all versions + repository hash match."""
    cache = _read_json(_path(repository_id, "cache.json"))
    if not cache:
        return False
    try:
        return (
            cache.get("repository_hash") == repo_hash
            and cache.get("decision_version") == DECISION_VERSION
            and cache.get("schema_version") == SCHEMA_VERSION
            and cache.get("generator_version") == GENERATOR_VERSION
        )
    except Exception:
        return False


def invalidate(repository_id: str) -> None:
    """Invalidate cache by deleting cache.json."""
    c_path = _path(repository_id, "cache.json")
    if os.path.exists(c_path):
        try:
            os.remove(c_path)
            logger.debug(f"[DecisionStorage] Cache invalidated for {repository_id}")
        except Exception as exc:
            logger.warning(f"[DecisionStorage] Failed to remove cache.json: {exc}")


def add_history_record(repository_id: str, record: DecisionHistoryRecord) -> None:
    """Append a DecisionHistoryRecord to history.json without full engine rebuild."""
    try:
        hist_data = _read_json(_path(repository_id, "history.json")) or []
        history = [DecisionHistoryRecord.from_dict(r) for r in hist_data]
        # Avoid duplicate workflow records
        if not any(r.workflow_id == record.workflow_id for r in history):
            history.append(record)
            history.sort(key=lambda x: x.completed_at, reverse=True)
            _write_json(_path(repository_id, "history.json"), [r.to_dict() for r in history])
            logger.debug(f"[DecisionStorage] Appended history record to {repository_id}")
    except Exception as exc:
        logger.warning(f"[DecisionStorage] Failed to append history record: {exc}")


def load_raw_file(repository_id: str, filename: str) -> Optional[Any]:
    """Load a raw persisted JSON file (for read-only GET API performance)."""
    return _read_json(_path(repository_id, filename))
