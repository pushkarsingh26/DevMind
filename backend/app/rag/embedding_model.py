from sentence_transformers import SentenceTransformer
from typing import List
from app.core.logger import logger

_model = None

def get_embedding_model() -> SentenceTransformer:
    """
    Lazily loads and returns the SentenceTransformer embedding model.
    """
    global _model
    if _model is None:
        model_name = "BAAI/bge-small-en-v1.5"
        logger.info(f"Loading embedding model: {model_name}...")
        # BAAI/bge-small-en-v1.5 is a 384-dimensional model
        _model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully.")
    return _model

def get_embedding_dimension() -> int:
    """
    Returns the dimension of the embedding vectors.
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
    """
    if not texts:
        return []
    model = get_embedding_model()
    # Ensure standard format (normalize_embeddings=True for cosine similarity compatibility)
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
