import os
import json
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
from app.rag.faiss_store import create_index, save_index, load_index, add_to_index, search_index
from app.core.logger import logger

# Base directory for FAISS files: backend/vector_store
VECTOR_STORE_BASE_DIR = Path(__file__).resolve().parents[2] / "vector_store"

class VectorStoreService:
    def __init__(self, base_dir: Path = VECTOR_STORE_BASE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

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

    def save_vector_store(self, repository_id: str, dimension: int, vectors: List[List[float]], embedding_ids: List[str]):
        """
        Creates a new FAISS index, adds vectors to it, and saves index.faiss and mapping.json.
        """
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
        Returns a list of tuples: (embedding_id, similarity_score)
        """
        if not self.index_exists(repository_id):
            logger.warn(f"Vector store not found for repository: {repository_id}")
            return []

        repo_dir = self.get_repo_dir(repository_id)
        index_path = str(repo_dir / "index.faiss")
        mapping_path = repo_dir / "mapping.json"

        # Load index and mapping
        index = load_index(index_path)
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping: Dict[str, str] = json.load(f)

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
        """
        repo_dir = self.get_repo_dir(repository_id)
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
            logger.info(f"Deleted vector store directory for repository {repository_id}")

vector_store_service = VectorStoreService()
