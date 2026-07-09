from typing import List, Dict, Any, Tuple
from app.core.logger import logger

class TokenManager:
    """
    Orchestrates token counting and context budgeting. Uses tiktoken cl100k_base 
    when available, with a safe character-to-token approximation as a fallback.
    """
    def __init__(self):
        self._tiktoken_encoder = None
        try:
            import tiktoken
            # Use cl100k_base which matches OpenAI, Groq (Llama), and OpenRouter models well
            self._tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
            logger.info("TokenManager: Successfully initialized tiktoken cl100k_base encoder.")
        except Exception as err:
            logger.warning(
                f"TokenManager: tiktoken is not available. Falling back to character-based "
                f"estimations (4 characters = 1 token + 15% safety buffer). Error: {err}"
            )

    def estimate_tokens(self, text: str) -> int:
        """
        Estimates the token count of a given text.
        """
        if not text:
            return 0

        # Try to count tokens using tiktoken encoder
        if self._tiktoken_encoder:
            try:
                return len(self._tiktoken_encoder.encode(text))
            except Exception as err:
                logger.debug(
                    f"TokenManager: tiktoken encoding failed: {err}. Falling back to character approximation."
                )

        # Fallback ratio: 1 token ~= 4 characters, with 15% safety buffer
        char_count = len(text)
        approx_tokens = int((char_count / 4.0) * 1.15)
        return max(1, approx_tokens)

    def budget_chunks(
        self,
        chunks: List[Dict[str, Any]],
        base_prompt_tokens: int,
        max_budget: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Iterates over a list of chunks, fitting as many as possible within the remaining budget.
        Truncates the last chunk at the boundary if necessary.
        """
        budgeted_chunks = []
        current_tokens = base_prompt_tokens

        # Chunks are expected to be pre-sorted by relevance/similarity score descending
        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_tokens = self.estimate_tokens(content)

            # Check if this chunk exceeds the remaining context budget
            if current_tokens + chunk_tokens > max_budget:
                remaining_tokens = max_budget - current_tokens
                # Truncate content if there are at least 50 tokens left
                if remaining_tokens > 50:
                    chars_to_keep = int(remaining_tokens * 2.5)  # safe boundary multiplier
                    if chars_to_keep > 100:
                        truncated_content = (
                            content[:chars_to_keep] +
                            "\n[... Content truncated to fit context size constraint ...]"
                        )
                        truncated_tokens = self.estimate_tokens(truncated_content)
                        if current_tokens + truncated_tokens <= max_budget:
                            truncated_chunk = dict(chunk)
                            truncated_chunk["content"] = truncated_content
                            budgeted_chunks.append(truncated_chunk)
                            current_tokens += truncated_tokens
                break

            budgeted_chunks.append(chunk)
            current_tokens += chunk_tokens

        return budgeted_chunks, current_tokens

token_manager = TokenManager()
