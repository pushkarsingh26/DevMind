"""
Phase 5 — ChatResponseParser

Parses the LLM's structured JSON chat response into typed Python objects.

Expected LLM output shape:
  {
    "answer": "<markdown string>",
    "citations": [{"path": "...", "start_line": N, "end_line": N}],
    "follow_up_questions": ["...", "..."]
  }

On any parse error the parser returns a safe fallback — it never propagates
an exception to the API layer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logger import logger


@dataclass
class ParsedChatResponse:
    """Structured result of one LLM chat response."""
    answer: str = ""
    citations: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    parse_ok: bool = True  # False when the parser fell back to defaults


# ---------------------------------------------------------------------------
# Compiled regex — strip ```json ... ``` fences (same pattern as Phase 4)
# ---------------------------------------------------------------------------
_FENCE_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)


class ChatResponseParser:
    """
    Converts raw LLM text into a ParsedChatResponse.

    Strategy:
      1. Strip any markdown code fences.
      2. Find the first top-level JSON object in the text.
      3. Parse and extract answer / citations / follow_up_questions.
      4. Validate citations conform to {path, start_line, end_line}.
      5. On any failure return a graceful degraded result (parse_ok=False).
    """

    # Maximum number of follow-up questions to accept from the LLM
    MAX_FOLLOW_UPS = 3

    def parse(self, raw_text: str) -> ParsedChatResponse:
        """
        Parse the raw LLM response string into a ParsedChatResponse.
        Never raises; returns a fallback on any error.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("ChatResponseParser: Received empty LLM response.")
            return self._fallback("The AI returned an empty response.")

        cleaned = self._strip_fences(raw_text.strip())

        try:
            data = self._extract_json(cleaned)
        except Exception as exc:
            logger.warning(f"ChatResponseParser: JSON extraction failed: {exc}")
            # Last resort — treat the entire text as the answer
            return self._fallback(raw_text, parse_ok=False)

        answer = str(data.get("answer") or data.get("text") or "").strip()
        if not answer:
            return self._fallback(raw_text, parse_ok=False)

        citations = self._parse_citations(data.get("citations") or [])
        follow_ups = self._parse_follow_ups(
            data.get("follow_up_questions") or data.get("followUpQuestions") or []
        )

        return ParsedChatResponse(
            answer=answer,
            citations=citations,
            follow_up_questions=follow_ups,
            parse_ok=True,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _strip_fences(self, text: str) -> str:
        """Remove surrounding ```json ... ``` markdown fences if present."""
        match = _FENCE_RE.search(text)
        if match:
            return match.group(1).strip()
        return text

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Try to parse the text as JSON.
        If the text has leading/trailing prose, slice out the first {...} block.
        """
        text = text.strip()

        # Fast path — well-formed JSON object
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Slow path — find the outermost {...} block
        start = text.find("{")
        if start == -1:
            # Try parsing directly with repair
            try:
                from app.utils.json_repair import parse_repaired_json
                return parse_repaired_json(text)
            except Exception:
                raise ValueError("No JSON object found in LLM response.")

        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end == -1:
            # Outer braces unmatched, try to repair the prefix starting at `start`
            try:
                from app.utils.json_repair import parse_repaired_json
                return parse_repaired_json(text[start:])
            except Exception:
                raise ValueError("Unmatched braces in LLM response.")

        try:
            return json.loads(text[start:end])
        except Exception:
            try:
                from app.utils.json_repair import parse_repaired_json
                return parse_repaired_json(text[start:end])
            except Exception as repair_err:
                raise ValueError(f"Failed to parse or repair brace block: {repair_err}")

    def _parse_citations(self, raw: Any) -> List[Dict[str, Any]]:
        """
        Validate and normalise the citations list.
        Each item must have at minimum 'path', 'start_line', 'end_line'.
        Invalid items are silently dropped.
        """
        if not isinstance(raw, list):
            return []

        result = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("file") or ""
            start = item.get("start_line") or item.get("startLine") or 0
            end = item.get("end_line") or item.get("endLine") or 0
            if path and isinstance(start, int) and isinstance(end, int):
                result.append({
                    "path": str(path),
                    "start_line": int(start),
                    "end_line": int(end),
                    "score": float(item["score"]) if "score" in item else None,
                })

        return result

    def _parse_follow_ups(self, raw: Any) -> List[str]:
        """Coerce follow_up_questions to List[str] and cap at MAX_FOLLOW_UPS."""
        if not isinstance(raw, list):
            return []
        result = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            if len(result) >= self.MAX_FOLLOW_UPS:
                break
        return result

    def _fallback(self, message: str, parse_ok: bool = False) -> ParsedChatResponse:
        """
        Last-resort fallback: extract a clean, human-readable answer from raw LLM text.
        Never exposes raw JSON structure, keys, or scaffolding to the user.

        Priority order:
          1. Regex-extract the value of the "answer" or "text" JSON field.
          2. If the text looks like plain prose (no JSON markers), use it as-is.
          3. If the text looks like broken JSON, strip all JSON structure and present what remains.
          4. Absolute last resort: return a friendly error message.
        """
        cleaned_msg = message.strip() if message else ""

        # --- Path 1: JSON-shaped text — try to extract the answer value ---
        if cleaned_msg.startswith("{") or '"answer"' in cleaned_msg or '"text"' in cleaned_msg:

            # Attempt 1a: greedy regex capture of the "answer" string value
            match = re.search(
                r'"(?:answer|text)"\s*:\s*"((?:[^"\\]|\\.)*)"',
                cleaned_msg,
                re.DOTALL,
            )
            if match:
                raw_val = match.group(1)
                try:
                    # Unescape JSON string escapes (\\n → \n, \\" → ", etc.)
                    ans = raw_val.encode("utf-8").decode("unicode_escape")
                except Exception:
                    # Manual unescape of the most common sequences
                    ans = (
                        raw_val
                        .replace(r"\n", "\n")
                        .replace(r"\t", "\t")
                        .replace(r'\"', '"')
                        .replace(r"\\", "\\")
                    )
                ans = ans.strip()
                if ans:
                    return ParsedChatResponse(answer=ans, citations=[], follow_up_questions=[], parse_ok=parse_ok)

            # Attempt 1b: strip all JSON structural characters and key names,
            # leaving only values that look like prose
            stripped = re.sub(
                r'"(?:answer|text|citations|follow_up_questions|followUpQuestions|path|start_line|end_line|score)"\s*:',
                "",
                cleaned_msg,
            )
            # Remove remaining JSON scaffolding characters
            stripped = re.sub(r'[{}[\]"\\]', " ", stripped)
            # Collapse whitespace
            stripped = re.sub(r"\s{2,}", " ", stripped).strip()

            if stripped and len(stripped) > 20:
                return ParsedChatResponse(answer=stripped, citations=[], follow_up_questions=[], parse_ok=False)

        # --- Path 2: Plain prose — use as-is (already clean) ---
        if cleaned_msg and not cleaned_msg.startswith("{"):
            return ParsedChatResponse(answer=cleaned_msg, citations=[], follow_up_questions=[], parse_ok=parse_ok)

        # --- Path 3: Absolute last resort ---
        return ParsedChatResponse(
            answer="I was unable to generate a response for this query. Please try rephrasing your question.",
            citations=[],
            follow_up_questions=[],
            parse_ok=False,
        )


chat_response_parser = ChatResponseParser()
