import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service
from app.core.logger import logger
from app.services.chunk_service import CodeChunk

class RAGService:
    def index_repository(self, db: Session, repository_id: str, job_id: str, chunks: List[CodeChunk]):
        """
        Coordinates embedding generation, database persistence, and vector indexing for a repository.
        """
        logger.info(f"RAGService: Indexing repository {repository_id} for job {job_id} with {len(chunks)} chunks.")
        
        # 1. Fetch Repository from database to ensure it exists and update its status
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            logger.error(f"Repository {repository_id} not found in database.")
            return

        repo.status = "INDEXING"
        db.commit()

        try:
            # 2. Delete any existing Chunk and Embedding records for this repository if we are re-indexing
            # (This ensures database remains clean and free of duplicates)
            db.query(Embedding).filter(Embedding.repository_id == repository_id).delete()
            db.query(Chunk).filter(Chunk.repository_id == repository_id).delete()
            db.commit()

            if not chunks:
                logger.warn(f"No chunks provided for repository {repository_id}. Skipping embedding generation.")
                repo.status = "READY"
                db.commit()
                # Initialize empty vector store
                vector_store_service.save_vector_store(
                    repository_id=repository_id,
                    dimension=embedding_service.get_embedding_dimension(),
                    vectors=[],
                    embedding_ids=[]
                )
                return

            # 3. Create Chunk models and save to PostgreSQL
            db_chunks = []
            for i, c in enumerate(chunks):
                chunk_id = f"{repository_id}:{c.id}"
                db_chunk = Chunk(
                    id=chunk_id,
                    repository_id=repository_id,
                    analysis_job_id=job_id,
                    path=c.path,
                    language=c.language,
                    chunk_index=i,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    content=c.content
                )
                db_chunks.append(db_chunk)
                db.add(db_chunk)
            
            db.commit()

            # 4. Generate query embeddings
            texts = [c.content for c in chunks]
            vectors = embedding_service.generate_embeddings(texts)

            # 5. Create Embedding records and save to PostgreSQL (without the vector)
            db_embeddings = []
            embedding_ids = []
            for i, db_chunk in enumerate(db_chunks):
                emb_id = f"emb_{uuid.uuid4().hex[:12]}"
                db_emb = Embedding(
                    id=emb_id,
                    repository_id=repository_id,
                    chunk_id=db_chunk.id,
                    embedding_model=embedding_service.get_model_name(),
                    embedding_dimension=embedding_service.get_embedding_dimension()
                )
                db_embeddings.append(db_emb)
                embedding_ids.append(emb_id)
                db.add(db_emb)

            db.commit()

            # 6. Save vectors and corresponding embedding ids to FAISS
            vector_store_service.save_vector_store(
                repository_id=repository_id,
                dimension=embedding_service.get_embedding_dimension(),
                vectors=vectors,
                embedding_ids=embedding_ids
            )

            # 7. Set repository status to READY
            repo.status = "READY"
            db.commit()
            logger.info(f"RAGService: Indexing completed successfully for repository {repository_id}")

        except Exception as e:
            logger.error(f"RAGService: Indexing failed for repository {repository_id}: {e}")
            repo.status = "FAILED"
            db.commit()
            raise e

rag_service = RAGService()
