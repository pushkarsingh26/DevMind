from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from app.models.embedding import Embedding
from app.models.chunk import Chunk
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service
from app.core.logger import logger

class RetrievalService:
    def retrieve_chunks(self, db: Session, repository_id: str, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """
        Performs semantic search across repository chunks and returns a list of (Chunk, similarity_score) tuples.
        """
        logger.info(f"RetrievalService: Querying repository {repository_id} with query='{query}' top_k={top_k}")
        
        # 1. Check if index exists
        if not vector_store_service.index_exists(repository_id):
            logger.warn(f"Vector store index not found for repository: {repository_id}")
            return []

        # 2. Generate embedding for query text
        query_vector = embedding_service.generate_embeddings([query])[0]

        # 3. Query VectorStoreService (this abstracts FAISS)
        search_results = vector_store_service.search(repository_id, query_vector, top_k)
        if not search_results:
            return []

        # 4. Extract embedding IDs
        embedding_ids = [emb_id for emb_id, _ in search_results]

        # 5. Load Embedding and Chunk records in bulk using joinedload to prevent N+1 queries
        embeddings = (
            db.query(Embedding)
            .options(joinedload(Embedding.chunk))
            .filter(Embedding.id.in_(embedding_ids))
            .all()
        )

        # 6. Map embedding ID to its DB record for fast lookup
        emb_map = {emb.id: emb for emb in embeddings}

        # 7. Reconstruct ordered results with scores
        ordered_results = []
        for emb_id, score in search_results:
            emb = emb_map.get(emb_id)
            if emb and emb.chunk:
                # Map score (IP dot product of normalized embeddings is cosine similarity)
                # Keep original float value
                ordered_results.append((emb.chunk, score))

        logger.info(f"RetrievalService: Found {len(ordered_results)} matches for query '{query}'")
        return ordered_results

retrieval_service = RetrievalService()
