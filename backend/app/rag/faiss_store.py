import os
import faiss
import numpy as np
from typing import List, Tuple
from app.core.logger import logger

def create_index(dimension: int) -> faiss.Index:
    """
    Creates a new FAISS Flat Inner Product index (ideal for cosine similarity of normalized vectors).
    """
    logger.info(f"Creating new FAISS IndexFlatIP with dimension: {dimension}")
    return faiss.IndexFlatIP(dimension)

def save_index(index: faiss.Index, filepath: str):
    """
    Persists the FAISS index to the specified file path.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    faiss.write_index(index, filepath)
    logger.info(f"FAISS index saved to {filepath}")

def load_index(filepath: str) -> faiss.Index:
    """
    Loads a FAISS index from the specified file path.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"FAISS index file not found: {filepath}")
    logger.info(f"Loading FAISS index from {filepath}")
    return faiss.read_index(filepath)

def add_to_index(index: faiss.Index, vectors: List[List[float]]):
    """
    Adds a list of float vectors to the index.
    """
    if not vectors:
        return
    vectors_np = np.array(vectors).astype("float32")
    # Vectors must already be normalized for Inner Product index to act as Cosine Similarity
    index.add(vectors_np)

def search_index(index: faiss.Index, query_vector: List[float], k: int) -> Tuple[List[float], List[int]]:
    """
    Searches the index for the top k nearest neighbors.
    Returns: (scores, indices)
    """
    query_np = np.array([query_vector]).astype("float32")
    scores, indices = index.search(query_np, k)
    # Return lists of results for the first (and only) query vector
    return scores[0].tolist(), indices[0].tolist()
