from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.embedding import Embedding
from app.models.chunk import Chunk
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service
from app.core.logger import logger

# ---------------------------------------------------------------------------
# File patterns that should be excluded from retrieval or heavily deprioritized.
# These are lockfiles, generated artifacts, minified bundles, and build outputs
# that carry no meaningful semantic signal for code intelligence tasks.
# ---------------------------------------------------------------------------
_EXCLUDE_PATH_PATTERNS = (
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "composer.lock",
    "pipfile.lock",
    "gemfile.lock",
    "cargo.lock",
    ".min.js",
    ".min.css",
    ".bundle.js",
    "dist/",
    "build/",
    ".cache/",
    "__pycache__/",
    ".pyc",
    ".map",           # Source maps
    "coverage/",
    ".next/",
    ".nuxt/",
    "vendor/",
    "generated/",
    "auto-generated",
    "migrations/",    # DB migration files — usually auto-generated
)

# Boost factors for high-signal paths
_BOOST_README      = 0.25
_BOOST_ARCH        = 0.20
_BOOST_CORE_SRC    = 0.15
_BOOST_DOCS        = 0.10
_PENALTY_TEST      = -0.10
_PENALTY_GENERATED = -0.30   # Heavy penalty for lockfiles / generated files


class RetrievalService:
    def retrieve_chunks(
        self,
        db: Session,
        repository_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[Chunk, float]]:
        """
        Performs semantic search across repository chunks and returns a list of
        (Chunk, boosted_similarity_score) tuples.

        Improvements vs. original:
          - Bulk-loads Embedding + Chunk in a single JOIN query (no N+1)
          - Excludes lockfiles, generated files, and build artifacts entirely
          - Applies path-based score boosting for high-signal files
          - Only warns when the index is genuinely missing
        """
        # 1. Guard: check index exists before attempting search
        if not vector_store_service.index_exists(repository_id):
            logger.warning(f"RetrievalService: Vector store index not found for repository: {repository_id}")
            return []

        # 2. Generate query embedding
        query_vector = embedding_service.generate_embeddings([query])[0]

        # 3. Search FAISS with an over-sized candidate pool for reranking
        candidate_k = max(20, top_k * 3)
        search_results = vector_store_service.search(repository_id, query_vector, candidate_k)
        if not search_results:
            return []

        # 4. Bulk-load Embedding + Chunk records (single JOIN, no N+1)
        embedding_ids = [emb_id for emb_id, _ in search_results]
        embeddings = (
            db.query(Embedding)
            .options(joinedload(Embedding.chunk))
            .filter(Embedding.id.in_(embedding_ids))
            .all()
        )

        # 5. Build fast lookup map
        emb_map = {emb.id: emb for emb in embeddings}

        # 6. Apply path-based boosting and exclusion filters
        boosted_results = []
        excluded_count = 0

        for emb_id, score in search_results:
            emb = emb_map.get(emb_id)
            if not emb or not emb.chunk:
                continue

            path_lower = emb.chunk.path.lower()

            # Hard-exclude lockfiles, generated files, build artifacts
            if any(pat in path_lower for pat in _EXCLUDE_PATH_PATTERNS):
                excluded_count += 1
                continue

            # Compute path boost
            boost = 0.0
            if "readme" in path_lower:
                boost += _BOOST_README
            elif any(p in path_lower for p in ("architecture", "arch/")):
                boost += _BOOST_ARCH
            elif any(p in path_lower for p in (
                "src/", "app/", "components/", "services/", "controllers/",
                "models/", "routes/", "routing/", "backend/", "logic/", "core/",
                "api/", "handlers/", "middleware/",
            )):
                boost += _BOOST_CORE_SRC
            elif any(p in path_lower for p in ("doc/", "docs/", "documentation/")):
                boost += _BOOST_DOCS

            # Deprioritize test files unless query explicitly asks about tests
            if any(p in path_lower for p in ("test_", "_test", "tests/", "spec/", ".spec.", ".test.")):
                if "test" not in query.lower():
                    boost += _PENALTY_TEST

            boosted_results.append((emb.chunk, score + boost))

        if excluded_count:
            logger.info(
                f"RetrievalService: Excluded {excluded_count} generated/lockfile chunks from results"
            )

        # 7. Re-sort by boosted score (descending) and take top_k
        boosted_results.sort(key=lambda x: x[1], reverse=True)
        final_results = boosted_results[:top_k]

        logger.info(
            f"RetrievalService: Selected {len(final_results)} chunks "
            f"(from {len(boosted_results)} candidates, excluded {excluded_count}) "
            f"for query '{query[:60]}'"
        )
        return final_results


retrieval_service = RetrievalService()
