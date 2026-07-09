import logging
import os
from sentence_transformers import SentenceTransformer
from typing import List
from app.core.logger import logger

_model = None

# Silence the HuggingFace Hub authentication / network warnings at module level.
# The model is cached locally after first download; subsequent startups should be silent.
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.utils").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)


def get_embedding_model() -> SentenceTransformer:
    """
    Lazily loads and returns the SentenceTransformer embedding model.

    Strategy:
      1. Try loading from local cache only (no network call, no HF auth warning).
      2. If the cache does not exist yet, fall back to downloading from the Hub.
         This only happens on first startup; all subsequent loads are silent.
    """
    global _model
    if _model is None:
        model_name = "BAAI/bge-small-en-v1.5"
        logger.info(f"Loading embedding model: {model_name}...")
        try:
            # Prefer local cache — avoids HuggingFace Hub auth/network warnings
            _model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            # First-time download (model not yet cached)
            logger.info(f"Embedding model not found in cache. Downloading {model_name} for the first time...")
            _model = SentenceTransformer(model_name, local_files_only=False)
        logger.info("Embedding model loaded successfully.")
    return _model


def get_embedding_dimension() -> int:
    """
    Returns the dimension of the embedding vectors.
    BAAI/bge-small-en-v1.5 produces 384-dimensional vectors.
    """
    return 384


def get_model_name() -> str:
    """
    Returns the name of the active embedding model.
    """
    return "BAAI/bge-small-en-v1.5"


def encode_texts(texts: List[str]) -> List[List[float]]:
    """
    Encodes a list of text strings into a list of embedding vectors.
    normalize_embeddings=True ensures cosine similarity compatibility.
    """
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
