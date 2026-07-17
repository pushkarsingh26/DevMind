"""Repository Intelligence Manager.

This is the ONLY authorised consumer of intelligence JSON files.

Architecture rule
-----------------
    WorkflowEngine
           │
           ▼
    IntelligenceManager   ← single entry point for ALL callers
           │
           ▼
    PromptBuilder
           │
           ▼
    LLM

No other component should read intelligence JSON files directly.

Public API
----------
    load(repo_id, intel_path, repo_hash)
    get(repo_id, section, repo_hash)
    exists(repo_id)
    validate(repo_id, repo_hash)
    invalidate(repo_id)
    rebuild(repo_id, repo_path, intel_path, repo_hash)
    refresh(repo_id, repo_path, intel_path, repo_hash)
    ensure_loaded(repo_id, repo_path, intel_path, repo_hash)   ← backward compat

Cache validity rules
--------------------
A cached entry is valid ONLY when ALL FOUR of the following match:
    1. repository_hash
    2. intelligence_version
    3. parser_version
    4. schema_version
    (format_version is not checked — it describes storage layout only)
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.logger import logger
from app.services.intelligence.intelligence_service import intelligence_service
from app.services.intelligence.parsers import PARSER_VERSION
from app.services.intelligence.versions import (
    FORMAT_VERSION,
    INTELLIGENCE_VERSION,
    REQUIRED_FILES,
    SCHEMA_VERSION,
)

# ---------------------------------------------------------------------------
# Section aliases for get()
# ---------------------------------------------------------------------------

_SECTION_ALIASES: Dict[str, str] = {
    "manifest":     "manifest",
    "file_tree":    "file_tree",
    "tree":         "file_tree",
    "modules":      "modules",
    "symbols":      "symbols",
    "imports":      "imports",
    "dependencies": "dependencies",
    "statistics":   "statistics",
    "stats":        "statistics",
    "errors":       "errors",
    "call_graph":   "call_graph",
    "graph":        "call_graph",
}


# ---------------------------------------------------------------------------
# RepositoryIntelligenceManager
# ---------------------------------------------------------------------------

class RepositoryIntelligenceManager:
    """Thread-safe, in-memory cache for repository intelligence data."""

    _lock: threading.Lock = threading.Lock()
    _cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # load
    # ------------------------------------------------------------------

    def load(
        self,
        repo_id: str,
        intelligence_path: str,
        repo_hash: Optional[str] = None,
    ) -> bool:
        """Load intelligence files for *repo_id* into the in-memory cache.

        Returns True if data was loaded (or already cached and valid).
        Returns False if loading failed.
        """
        with self._lock:
            if repo_id in self._cache and self._is_cache_valid(repo_id, repo_hash):
                return True
            if repo_id in self._cache:
                del self._cache[repo_id]
            return self._load_from_disk(repo_id, intelligence_path, repo_hash)

    # ------------------------------------------------------------------
    # get
    # ------------------------------------------------------------------

    def get(
        self,
        repo_id: str,
        section: Optional[str] = None,
        repo_hash: Optional[str] = None,
    ) -> Any:
        """Retrieve intelligence data for *repo_id*.

        Parameters
        ----------
        section:
            One of the aliases defined in ``_SECTION_ALIASES`` (e.g. "symbols",
            "statistics", "tree").  Pass ``None`` to receive the full dict.
        repo_hash:
            When provided the cache entry is validated against this hash
            before being returned.  Returns ``None`` on mismatch.
        """
        with self._lock:
            repo_data = self._cache.get(repo_id)
            if repo_data is None:
                return None
            if not self._is_cache_valid(repo_id, repo_hash):
                return None
            if section is None:
                return repo_data
            key = _SECTION_ALIASES.get(section, section)
            return repo_data.get(key)

    # ------------------------------------------------------------------
    # exists
    # ------------------------------------------------------------------

    def exists(self, repo_id: str) -> bool:
        """Return True if any cache entry exists for *repo_id* (regardless of validity)."""
        with self._lock:
            return repo_id in self._cache

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------

    def validate(self, repo_id: str, repo_hash: Optional[str] = None) -> bool:
        """Full validation: checks all 4 version strings plus repo hash.

        Returns True if the cached entry is completely valid.
        """
        with self._lock:
            return self._is_cache_valid(repo_id, repo_hash)

    # ------------------------------------------------------------------
    # invalidate
    # ------------------------------------------------------------------

    def invalidate(self, repo_id: str) -> None:
        """Evict *repo_id* from the in-memory cache."""
        with self._lock:
            self._cache.pop(repo_id, None)
        logger.debug(f"[IntelligenceManager] Evicted cache for {repo_id}")

    # ------------------------------------------------------------------
    # rebuild
    # ------------------------------------------------------------------

    def rebuild(
        self,
        repo_id: str,
        repo_path: str,
        intelligence_path: str,
        repo_hash: Optional[str] = None,
    ) -> bool:
        """Force rebuild intelligence (ignoring current cache state).

        Evicts any existing cache entry, runs IntelligenceService, then
        reloads the fresh artifacts into cache.

        Returns True on success, False on failure.
        """
        with self._lock:
            self._cache.pop(repo_id, None)

        logger.info(f"[IntelligenceManager] Forcing rebuild for {repo_id}")
        try:
            result = intelligence_service.build_intelligence(
                repo_path=repo_path,
                repo_id=repo_id,
                repo_hash=repo_hash,
            )
            with self._lock:
                return self._load_from_disk(repo_id, result["intelligence_path"], result["repo_hash"])
        except Exception as exc:
            logger.error(f"[IntelligenceManager] Rebuild failed for {repo_id}: {exc}")
            return False

    # ------------------------------------------------------------------
    # refresh
    # ------------------------------------------------------------------

    def refresh(
        self,
        repo_id: str,
        repo_path: str,
        intelligence_path: str,
        repo_hash: Optional[str] = None,
    ) -> bool:
        """Validate first; rebuild only if stale or missing.

        Returns True if valid intelligence is available after the call.
        """
        with self._lock:
            if repo_id in self._cache and self._is_cache_valid(repo_id, repo_hash):
                logger.debug(f"[IntelligenceManager] Cache still valid for {repo_id}, skipping refresh")
                return True

        # Need to refresh — release lock during potentially slow build
        intel_path = Path(intelligence_path)
        with self._lock:
            if self._files_complete(intel_path) and self._manifest_valid(intel_path, repo_hash):
                return self._load_from_disk(repo_id, intelligence_path, repo_hash)

        return self.rebuild(repo_id, repo_path, intelligence_path, repo_hash)

    # ------------------------------------------------------------------
    # ensure_loaded  (backward-compatible alias for refresh)
    # ------------------------------------------------------------------

    def ensure_loaded(
        self,
        repo_id: str,
        repo_path: str,
        intelligence_path: str,
        repo_hash: Optional[str] = None,
    ) -> bool:
        """Guarantee valid intelligence is in cache, rebuilding if necessary.

        Backward-compatible with Phase 8.1 callers.
        """
        return self.refresh(repo_id, repo_path, intelligence_path, repo_hash)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_cache_valid(self, repo_id: str, repo_hash: Optional[str]) -> bool:
        """Check all four version strings + repo hash against the cached manifest."""
        repo_data = self._cache.get(repo_id)
        if not repo_data:
            return False
        manifest = repo_data.get("manifest", {})

        if manifest.get("intelligence_version") != INTELLIGENCE_VERSION:
            return False
        if manifest.get("parser_version") != PARSER_VERSION:
            return False
        if manifest.get("schema_version") != SCHEMA_VERSION:
            return False
        if repo_hash and manifest.get("repository_hash") != repo_hash:
            return False
        return True

    def _files_complete(self, intel_path: Path) -> bool:
        return all((intel_path / f).is_file() for f in REQUIRED_FILES)

    def _manifest_valid(self, intel_path: Path, repo_hash: Optional[str]) -> bool:
        try:
            with (intel_path / "manifest.json").open("r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            if manifest.get("intelligence_version") != INTELLIGENCE_VERSION:
                return False
            if manifest.get("parser_version") != PARSER_VERSION:
                return False
            if manifest.get("schema_version") != SCHEMA_VERSION:
                return False
            if repo_hash and manifest.get("repository_hash") != repo_hash:
                return False
            return True
        except Exception:
            return False

    def _load_from_disk(
        self,
        repo_id: str,
        intelligence_path: str,
        repo_hash: Optional[str],
    ) -> bool:
        """Read all JSON files into cache.  Caller must hold ``_lock``."""
        path = Path(intelligence_path)
        if not path.is_dir():
            logger.warning(f"[IntelligenceManager] Intelligence dir missing: {path}")
            return False

        data: Dict[str, Any] = {}
        for file_name in REQUIRED_FILES:
            fp = path / file_name
            if not fp.is_file():
                logger.warning(f"[IntelligenceManager] Missing {file_name} for {repo_id}")
                continue
            try:
                with fp.open("r", encoding="utf-8") as fh:
                    key = file_name.replace(".json", "")
                    data[key] = json.load(fh)
            except Exception as exc:
                logger.error(f"[IntelligenceManager] Failed to parse {fp}: {exc}")

        if not data:
            return False

        self._cache[repo_id] = data
        manifest = data.get("manifest", {})
        logger.info(
            f"[IntelligenceManager] Loaded intelligence for {repo_id} "
            f"(iv={manifest.get('intelligence_version')} "
            f"pv={manifest.get('parser_version')} "
            f"sv={manifest.get('schema_version')})"
        )
        return True


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

intelligence_manager = RepositoryIntelligenceManager()
