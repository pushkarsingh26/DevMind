import os
import json
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
from app.rag.faiss_store import create_index, save_index, load_index, add_to_index, search_index
from app.core.logger import logger

# Base directory for FAISS files: backend/vector_store
VECTOR_STORE_BASE_DIR = Path(__file__).resolve().parents[2] / "vector_store"

class VectorStoreService:
    def __init__(self, base_dir: Path = VECTOR_STORE_BASE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        # In-memory caches (Phase 7.3 Cache optimization)
        self._index_cache: Dict[str, Any] = {}
        self._mapping_cache: Dict[str, Dict[str, str]] = {}
        self._stats_cache: Dict[str, Dict[str, Any]] = {}

    def get_repo_dir(self, repository_id: str) -> Path:
        """
        Gets the directory path for a specific repository's vector store.
        """
        return self.base_dir / repository_id

    def index_exists(self, repository_id: str) -> bool:
        """
        Checks if the FAISS index and mapping file exist for the repository.
        """
        repo_dir = self.get_repo_dir(repository_id)
        index_path = repo_dir / "index.faiss"
        mapping_path = repo_dir / "mapping.json"
        return index_path.exists() and mapping_path.exists()

    def invalidate_cache(self, repository_id: str):
        """
        Invalidates all cached data associated with the repository.
        """
        self._index_cache.pop(repository_id, None)
        self._mapping_cache.pop(repository_id, None)
        self._stats_cache.pop(repository_id, None)
        logger.info(f"VectorStoreService: Invalidated cache for repository {repository_id}")

    def get_repository_statistics(self, db, repository_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns cached repository statistics or queries the DB and caches them.
        """
        if repository_id in self._stats_cache:
            logger.info(f"VectorStoreService: Stats cache HIT for repo {repository_id}")
            return self._stats_cache[repository_id]
        
        from app.models.repository import Repository
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            return None
            
        stats = {
            "id": repo.id,
            "name": repo.name,
            "owner": repo.owner,
            "source": repo.source,
            "framework": repo.framework,
            "language": repo.language,
            "repository_hash": repo.repository_hash,
            "status": repo.status,
            "default_branch": repo.default_branch,
            "readme_present": repo.readme_present,
            "license": repo.license,
            "docker_support": repo.docker_support,
            "github_actions": repo.github_actions,
            "cicd": repo.cicd,
            "tests_present": repo.tests_present,
            "total_files": repo.total_files,
            "directories": repo.directories,
            "extensions": repo.extensions,
            "largest_files": repo.largest_files,
            "dependencies": repo.dependencies,
            "package_managers": repo.package_managers,
        }
        self._stats_cache[repository_id] = stats
        logger.info(f"VectorStoreService: Stats cache MISS for repo {repository_id} - loaded & cached")
        return stats

    def set_repository_statistics(self, repository_id: str, stats: Dict[str, Any]):
        """
        Directly populates or updates the cached stats in memory.
        """
        self._stats_cache[repository_id] = stats

    def save_vector_store(self, repository_id: str, dimension: int, vectors: List[List[float]], embedding_ids: List[str]):
        """
        Creates a new FAISS index, adds vectors to it, and saves index.faiss and mapping.json.
        Invalidates in-memory cache.
        """
        self.invalidate_cache(repository_id)
        repo_dir = self.get_repo_dir(repository_id)
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        os.makedirs(repo_dir, exist_ok=True)

        index_path = str(repo_dir / "index.faiss")
        mapping_path = repo_dir / "mapping.json"

        # Create low-level index
        index = create_index(dimension)
        
        if vectors:
            add_to_index(index, vectors)

        # Save index to disk
        save_index(index, index_path)

        # Write mapping.json: maps stringified integer index to embedding UUID
        mapping = {str(i): emb_id for i, emb_id in enumerate(embedding_ids)}
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)

        logger.info(f"Successfully saved FAISS index and mapping for repository {repository_id} ({len(vectors)} vectors)")

    def search(self, repository_id: str, query_vector: List[float], k: int) -> List[Tuple[str, float]]:
        """
        Searches the repository's FAISS index for the top k similar vectors.
        Uses in-memory cached index and mapping to avoid disk I/O.
        """
        if not self.index_exists(repository_id):
            logger.warn(f"Vector store not found for repository: {repository_id}")
            return []

        # Check in-memory cache
        if repository_id in self._index_cache and repository_id in self._mapping_cache:
            index = self._index_cache[repository_id]
            mapping = self._mapping_cache[repository_id]
            logger.info(f"VectorStoreService: FAISS index and mapping cache HIT for repo {repository_id}")
        else:
            repo_dir = self.get_repo_dir(repository_id)
            index_path = str(repo_dir / "index.faiss")
            mapping_path = repo_dir / "mapping.json"

            # Load from disk
            index = load_index(index_path)
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping: Dict[str, str] = json.load(f)
            
            # Cache in memory
            self._index_cache[repository_id] = index
            self._mapping_cache[repository_id] = mapping
            logger.info(f"VectorStoreService: FAISS index and mapping cache MISS for repo {repository_id} - loaded from disk & cached")

        # Query index
        scores, indices = search_index(index, query_vector, k)

        results = []
        for score, idx in zip(scores, indices):
            # FAISS returns -1 index if it cannot find enough matches
            if idx == -1:
                continue
            emb_id = mapping.get(str(idx))
            if emb_id:
                results.append((emb_id, score))

        return results

    def delete_vector_store(self, repository_id: str):
        """
        Deletes the vector store files and directory for a repository.
        Invalidates in-memory cache.
        """
        self.invalidate_cache(repository_id)
        repo_dir = self.get_repo_dir(repository_id)
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
            logger.info(f"Deleted vector store directory for repository {repository_id}")

vector_store_service = VectorStoreService()
