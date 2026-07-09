"""
Phase 5 — ChatPromptBuilder

Builds the OpenAI-compatible messages[] list for multi-turn repository chat.

Reuses:
  - prompt_builder.optimize_chunks()  (Phase 4 deduplication / merging)
  - token_manager.budget_chunks()     (Phase 4 token budgeting)
  - token_manager.estimate_tokens()   (Phase 4 counting)

Token budget strategy:
  Total:   MAX_TOKENS
  Reserve: 600  system prompt + repo metadata block
  Reserve: CHAT_RESPONSE_TOKENS  (800) for the assistant reply
  Remaining split: 60% context chunks | 40% conversation history

History is evicted FIFO (oldest first) until it fits the 40% budget.
The current user message is always the final item in the messages list.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from jinja2 import Template

from app.ai.prompt_builder import prompt_builder
from app.ai.token_manager import token_manager
from app.core.config import settings
from app.core.logger import logger


# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_CHAT = """You are a repository-aware AI assistant embedded in DevMind.

Repository: {{ repository_name }}
Primary Language: {{ primary_language }}
Framework: {{ framework | default("None") }}
Total Files: {{ total_files }} | Directories: {{ directories }}
Package Managers: {{ package_managers | join(", ") if package_managers else "None" }}

--- RETRIEVED CODE CONTEXT ---
{% for chunk in chunks %}
FILE: {{ chunk.path }} (L{{ chunk.start_line }}–L{{ chunk.end_line }})
```
{{ chunk.content }}
```
{% endfor %}
--- END CONTEXT ---

STRICT RULES:
1. Answer ONLY using the retrieved code context shown above and the conversation history.
2. Never invent function names, file paths, or code that are not present in the snippets.
3. Always cite the exact file path and line range you reference in your answer.
4. Format your ENTIRE response as a single JSON object with this exact shape:
   {
     "answer": "<your full markdown answer here>",
     "citations": [
       {"path": "relative/file.py", "start_line": 10, "end_line": 25}
     ],
     "follow_up_questions": [
       "First natural follow-up question?",
       "Second natural follow-up question?"
     ]
   }
5. If the context is insufficient to answer accurately, say so clearly in the "answer"
   field and set citations to [] and follow_up_questions to [].
6. Generate 2–3 follow_up_questions that would naturally arise from your answer.
7. Do not include any text outside the JSON object."""


class ChatPromptBuilder:
    """
    Assembles the messages[] list for a single chat turn.

    Parameters to build_chat_messages:
      history        — list of {role, content} dicts (oldest first)
      repo_metadata  — dict with repository_name, primary_language, etc.
      chunks         — list of raw chunk dicts from RetrievalService
      user_message   — the current user question string

    Returns:
      (messages_list, estimated_tokens, budgeted_chunks)
    """

    def __init__(self) -> None:
        self._system_template = Template(SYSTEM_PROMPT_CHAT)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_chat_messages(
        self,
        history: List[Dict[str, str]],
        repo_metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        user_message: str,
    ) -> Tuple[List[Dict[str, str]], int, List[Dict[str, Any]]]:
        """
        Build the complete messages list for the LLM provider call.

        Returns:
            messages      : [{"role": "system", "content": ...}, ...]
            total_tokens  : estimated total tokens consumed
            budgeted_chunks : the chunks actually included in context
        """
        max_budget = settings.MAX_TOKENS
        response_reserve = settings.CHAT_RESPONSE_TOKENS
        system_reserve = 600  # rough overhead for system prompt metadata

        available = max_budget - response_reserve - system_reserve
        chunk_budget = int(available * 0.60)
        history_budget = int(available * 0.40)

        # 1. Optimise chunks (dedup + merge contiguous spans)
        optimised = prompt_builder.optimize_chunks(chunks)

        # 2. Budget chunks to fit within the context slice
        budgeted_chunks, chunk_tokens = token_manager.budget_chunks(
            optimised,
            base_prompt_tokens=0,
            max_budget=chunk_budget,
        )

        # 3. Render system prompt with repo metadata + context
        render_ctx = {
            "repository_name": repo_metadata.get("repository_name", "Unknown"),
            "primary_language": repo_metadata.get("primary_language", "Unknown"),
            "framework": repo_metadata.get("framework", "None"),
            "total_files": repo_metadata.get("total_files", 0),
            "directories": repo_metadata.get("directories", 0),
            "package_managers": repo_metadata.get("package_managers", []),
            "chunks": budgeted_chunks,
        }
        system_content = self._system_template.render(render_ctx)
        system_tokens = token_manager.estimate_tokens(system_content)

        # 4. Trim history FIFO until it fits the history_budget
        trimmed_history = self._trim_history(history, history_budget)

        # 5. Assemble messages list
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
        messages.extend(trimmed_history)
        messages.append({"role": "user", "content": user_message})

        # 6. Estimate total tokens
        history_tokens = sum(
            token_manager.estimate_tokens(m["content"]) for m in trimmed_history
        )
        user_tokens = token_manager.estimate_tokens(user_message)
        total_tokens = system_tokens + chunk_tokens + history_tokens + user_tokens

        logger.debug(
            f"ChatPromptBuilder: system={system_tokens} chunk={chunk_tokens} "
            f"history={history_tokens} user={user_tokens} total={total_tokens} "
            f"budget={max_budget} chunks_used={len(budgeted_chunks)}"
        )

        return messages, total_tokens, budgeted_chunks

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _trim_history(
        self,
        history: List[Dict[str, str]],
        budget: int,
    ) -> List[Dict[str, str]]:
        """
        Trim oldest messages first until the total token cost fits within budget.
        Always keeps at least the most recent turn if possible.
        """
        if not history:
            return []

        # Work backwards: keep as many recent turns as possible
        kept: List[Dict[str, str]] = []
        used = 0

        for msg in reversed(history):
            tokens = token_manager.estimate_tokens(msg["content"])
            if used + tokens <= budget:
                kept.insert(0, msg)
                used += tokens
            else:
                # No more room — drop older messages
                break

        if len(kept) < len(history):
            logger.debug(
                f"ChatPromptBuilder: History trimmed from {len(history)} "
                f"to {len(kept)} messages to fit {budget}-token budget."
            )

        return kept


chat_prompt_builder = ChatPromptBuilder()
