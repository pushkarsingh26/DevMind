from typing import List, Tuple, Dict, Any
from app.models.chunk import Chunk

class ContextBuilder:
    def build_context(self, retrieved_results: List[Tuple[Chunk, float]]) -> List[Dict[str, Any]]:
        """
        Converts a list of (Chunk, score) tuples into structured context dictionaries.
        """
        results = []
        for chunk, score in retrieved_results:
            results.append({
                "path": chunk.path,
                "score": float(score),
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content
            })
        return results

context_builder = ContextBuilder()
