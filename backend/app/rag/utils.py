from typing import List

def clean_text(text: str) -> str:
    """
    Cleans content string for embedding inputs.
    """
    return text.strip()

def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """
    Splits generic text block into smaller segments.
    """
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
