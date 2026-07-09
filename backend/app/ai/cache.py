import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logger import logger

class AICache:
    """
    Manages a persistent, self-invalidating file-based cache for AI analyses.
    Gracefully invalidates whenever repos, models, retrieval limits, or prompt templates change.
    """
    def __init__(self):
        self.cache_dir = settings.AI_CACHE_DIR
        if settings.AI_CACHE_ENABLED:
            try:
                # Ensure directory exists relative to backend execution path
                os.makedirs(self.cache_dir, exist_ok=True)
                logger.info(f"AICache: File caching directory is ready at '{self.cache_dir}'")
            except Exception as err:
                logger.error(f"AICache: Failed to establish cache directory: {err}")

    def compute_retrieval_hash(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Computes a stable sha256 hash representing chunk IDs, contents, and scores.
        """
        hasher = hashlib.sha256()
        # Sort chunks by ID to guarantee hash stability
        sorted_chunks = sorted(
            chunks,
            key=lambda x: str(x.get("id") or x.get("chunk_id") or "")
        )

        for c in sorted_chunks:
            chunk_id = str(c.get("id") or c.get("chunk_id") or "")
            content = str(c.get("content", ""))
            score = str(c.get("score", ""))
            
            hasher.update(chunk_id.encode("utf-8"))
            hasher.update(content.encode("utf-8"))
            hasher.update(score.encode("utf-8"))

        return hasher.hexdigest()

    def generate_cache_key(
        self,
        repository_hash: str,
        retrieval_hash: str,
        task_type: str,
        provider: str,
        selected_model: str,
        prompt_version: str,
        retrieval_limit: int,
        temperature: float
    ) -> str:
        """
        Creates a sha256 cache key using the full operational parameters of the AI request.
        """
        payload = (
            f"{repository_hash}:{retrieval_hash}:{task_type.strip().lower()}:"
            f"{provider.strip().lower()}:{selected_model}:{prompt_version}:"
            f"{retrieval_limit}:{temperature:.4f}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached JSON analysis if it exists. Handles corrupted files gracefully by deleting them.
        """
        if not settings.AI_CACHE_ENABLED:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not os.path.exists(cache_file):
            return None

        logger.info(f"AICache: Found cache file for key '{cache_key}'")
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as err:
            logger.error(
                f"AICache: Cache corruption detected in '{cache_file.name}': {err}. "
                f"Invalidating cache entry."
            )
            # Corruption recovery: discard and delete corrupted file
            try:
                os.remove(cache_file)
            except Exception as remove_err:
                logger.error(f"AICache: Failed to remove corrupted cache file: {remove_err}")
            return None

    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Writes the validated JSON output payload to the cache folder.
        """
        if not settings.AI_CACHE_ENABLED:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"AICache: Successfully cached response in '{cache_file.name}'")
        except Exception as err:
            logger.error(f"AICache: Failed to cache response in '{cache_file.name}': {err}")

ai_cache = AICache()
