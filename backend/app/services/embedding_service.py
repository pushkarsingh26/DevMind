from typing import List, Dict, Any
from app.rag.embedding_model import encode_texts, get_model_name, get_embedding_dimension

class EmbeddingService:
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings for the provided texts.
        """
        return encode_texts(texts)

    def get_model_name(self) -> str:
        """
        Retrieves the name of the active embedding model.
        """
        return get_model_name()

    def get_embedding_dimension(self) -> int:
        """
        Retrieves the dimension size of the embedding vectors.
        """
        return get_embedding_dimension()

embedding_service = EmbeddingService()
