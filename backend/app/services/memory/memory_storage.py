"""Memory JSON persistence service."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.memory.memory_models import (
    LearningMetrics,
    PatternRecord,
    Recommendation,
    RepositoryMemory,
    WorkflowMemory,
)
from app.services.memory.versions import (
    MEMORY_GENERATOR_VERSION,
    MEMORY_SCHEMA_VERSION,
    MEMORY_VERSION,
)


class MemoryStorage:
    """Manages reading and writing Memory Engine JSON files."""

    def get_memory_dir(self, repository_id: str) -> Path:
        # Resolve Workspace Data directory base
        base_dir = Path("data") / "repositories" / repository_id / "memory"
        return base_dir

    def save(
        self,
        repository_id: str,
        memory: RepositoryMemory,
        patterns: List[PatternRecord],
        recommendations: List[Recommendation],
        metrics: LearningMetrics,
        history: List[WorkflowMemory],
    ) -> bool:
        """Serialize memory engine structures to JSON files on disk."""
        try:
            memory_dir = self.get_memory_dir(repository_id)
            memory_dir.mkdir(parents=True, exist_ok=True)

            metadata = {
                "memory_version": MEMORY_VERSION,
                "schema_version": MEMORY_SCHEMA_VERSION,
                "generator_version": MEMORY_GENERATOR_VERSION,
                "repository_id": repository_id,
                "repository_hash": memory.repository_hash,
                "generated_at": memory_dir.stat().st_mtime if memory_dir.exists() else 0,
            }

            # Helper to save with standard metadata wrapper
            def _save_file(file_name: str, payload: Any):
                file_path = memory_dir / file_name
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {"metadata": metadata, "data": payload},
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

            _save_file("memory.json", memory.to_dict())
            _save_file("patterns.json", [p.to_dict() for p in patterns])
            _save_file("recommendations.json", [r.to_dict() for r in recommendations])
            _save_file("metrics.json", metrics.to_dict())
            _save_file("history.json", [h.to_dict() for h in history])

            logger.info(f"[MemoryStorage] Successfully saved memory state for {repository_id}")
            return True
        except Exception as exc:
            logger.error(f"[MemoryStorage] Failed to save memory state for {repository_id}: {exc}")
            return False

    def load(
        self, repository_id: str
    ) -> Optional[
        Tuple[
            RepositoryMemory,
            List[PatternRecord],
            List[Recommendation],
            LearningMetrics,
            List[WorkflowMemory],
        ]
    ]:
        """Loads and parses all memory engine JSON files from disk."""
        try:
            memory_dir = self.get_memory_dir(repository_id)
            if not memory_dir.is_dir():
                return None

            # Helper to read data section
            def _load_file(file_name: str) -> Optional[Any]:
                file_path = memory_dir / file_name
                if not file_path.is_file():
                    return None
                with open(file_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    return payload.get("data")

            raw_mem = _load_file("memory.json")
            if not raw_mem:
                return None

            memory = RepositoryMemory.from_dict(raw_mem)

            raw_patterns = _load_file("patterns.json") or []
            patterns = [PatternRecord.from_dict(p) for p in raw_patterns]

            raw_recs = _load_file("recommendations.json") or []
            recommendations = [Recommendation.from_dict(r) for r in raw_recs]

            raw_metrics = _load_file("metrics.json") or {}
            metrics = LearningMetrics.from_dict(raw_metrics)

            raw_history = _load_file("history.json") or []
            history = [WorkflowMemory.from_dict(h) for h in raw_history]

            return memory, patterns, recommendations, metrics, history
        except Exception as exc:
            logger.error(f"[MemoryStorage] Failed to load memory state for {repository_id}: {exc}")
            return None

    def validate_cache(self, repository_id: str, repo_hash: str) -> bool:
        """Verify cache metadata matches memory engine versions and repository hash."""
        try:
            memory_dir = self.get_memory_dir(repository_id)
            memory_file = memory_dir / "memory.json"
            if not memory_file.is_file():
                return False

            with open(memory_file, "r", encoding="utf-8") as f:
                payload = json.load(f)

            meta = payload.get("metadata", {})
            if meta.get("memory_version") != MEMORY_VERSION:
                return False
            if meta.get("schema_version") != MEMORY_SCHEMA_VERSION:
                return False
            if repo_hash and meta.get("repository_hash") != repo_hash:
                return False

            # Verify other essential files exist
            for f_name in ("patterns.json", "recommendations.json", "metrics.json", "history.json"):
                if not (memory_dir / f_name).is_file():
                    return False

            return True
        except Exception:
            return False

    def invalidate(self, repository_id: str) -> None:
        """Evict and delete memory engine directories from disk."""
        try:
            memory_dir = self.get_memory_dir(repository_id)
            if memory_dir.is_dir():
                for f in memory_dir.glob("*.json"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
                try:
                    memory_dir.rmdir()
                except Exception:
                    pass
                logger.info(f"[MemoryStorage] Invalidated and deleted memory directory for {repository_id}")
        except Exception as exc:
            logger.error(f"[MemoryStorage] Invalidation failed for {repository_id}: {exc}")


memory_storage = MemoryStorage()
