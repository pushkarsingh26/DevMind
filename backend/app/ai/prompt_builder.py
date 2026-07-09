from typing import List, Dict, Any, Tuple
from jinja2 import Template
from app.core.logger import logger
from app.ai.prompt_templates import (
    SYSTEM_PROMPT_REVIEW, USER_PROMPT_REVIEW,
    SYSTEM_PROMPT_EXPLAIN, USER_PROMPT_EXPLAIN,
    SYSTEM_PROMPT_TESTS, USER_PROMPT_TESTS,
    SYSTEM_PROMPT_BUGS, USER_PROMPT_BUGS
)

class PromptBuilder:
    """
    Compiles system and user prompts, performing deduplication and merging of code context chunks.
    """
    def __init__(self):
        self._templates = {
            "review": (SYSTEM_PROMPT_REVIEW, USER_PROMPT_REVIEW),
            "explain": (SYSTEM_PROMPT_EXPLAIN, USER_PROMPT_EXPLAIN),
            "tests": (SYSTEM_PROMPT_TESTS, USER_PROMPT_TESTS),
            "bugs": (SYSTEM_PROMPT_BUGS, USER_PROMPT_BUGS)
        }

    def optimize_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates context chunks and merges contiguous or overlapping spans from the same file.
        """
        if not chunks:
            return []

        # 1. Deduplicate by unique content/id
        seen_contents = set()
        seen_ids = set()
        deduplicated = []
        for chunk in chunks:
            content = chunk.get("content", "").strip()
            chunk_id = chunk.get("id") or chunk.get("chunk_id")
            
            if not content:
                continue
            if content in seen_contents:
                continue
            if chunk_id and chunk_id in seen_ids:
                continue

            seen_contents.add(content)
            if chunk_id:
                seen_ids.add(chunk_id)
            deduplicated.append(chunk)

        # 2. Group and merge contiguous or overlapping spans from the same file
        # Group by path
        grouped_by_path: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in deduplicated:
            path = chunk.get("path", "Unknown")
            grouped_by_path.setdefault(path, []).append(chunk)

        merged_chunks = []

        for path, file_chunks in grouped_by_path.items():
            # Sort by start_line ascending
            file_chunks.sort(key=lambda x: x.get("start_line", 0))
            
            current_merged = file_chunks[0]
            for next_chunk in file_chunks[1:]:
                prev_start = current_merged.get("start_line", 0)
                prev_end = current_merged.get("end_line", 0)
                next_start = next_chunk.get("start_line", 0)
                next_end = next_chunk.get("end_line", 0)
                
                prev_content = current_merged.get("content", "")
                next_content = next_chunk.get("content", "")

                # Merging threshold: overlap or gap <= 5 lines
                if next_start <= prev_end + 5:
                    if next_start <= prev_end:
                        # Overlap: Align line numbers and slice strings
                        lines_prev = prev_content.split("\n")
                        lines_next = next_content.split("\n")
                        
                        overlap_start_index = next_start - prev_start
                        if overlap_start_index >= 0 and overlap_start_index < len(lines_prev):
                            merged_lines = lines_prev[:overlap_start_index] + lines_next
                            new_content = "\n".join(merged_lines)
                        else:
                            # Fallback if line indexing math breaks
                            new_content = prev_content + "\n" + next_content
                    else:
                        # Gap of 1 to 5 lines: Join with placeholder
                        gap_size = next_start - prev_end - 1
                        gap_msg = f"\n[... {gap_size} lines gap ...]\n" if gap_size > 0 else "\n"
                        new_content = prev_content + gap_msg + next_content

                    current_merged = dict(current_merged)
                    current_merged["content"] = new_content
                    current_merged["end_line"] = max(prev_end, next_end)
                else:
                    merged_chunks.append(current_merged)
                    current_merged = next_chunk
            
            merged_chunks.append(current_merged)

        return merged_chunks

    def build_prompts(
        self,
        task_type: str,
        repository_metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """
        Optimizes chunks and renders system/user prompt templates using Jinja.
        """
        task_key = task_type.strip().lower()
        if task_key not in self._templates:
            raise ValueError(f"Unsupported task type: {task_type}")

        system_tmpl_str, user_tmpl_str = self._templates[task_key]

        # Optimize (deduplicate and merge) chunks
        optimized_chunks = self.optimize_chunks(chunks)

        # Prepare context variables for Jinja template rendering
        render_context = {
            "repository_name": repository_metadata.get("repository_name", "Unknown"),
            "primary_language": repository_metadata.get("primary_language", "Unknown"),
            "framework": repository_metadata.get("framework", "None"),
            "total_files": repository_metadata.get("total_files", 0),
            "directories": repository_metadata.get("directories", 0),
            "package_managers": repository_metadata.get("package_managers", []),
            "dependencies": repository_metadata.get("dependencies", {}),
            "entrypoints": repository_metadata.get("entrypoints", []),
            "chunks": optimized_chunks
        }

        # Render prompts
        system_prompt = Template(system_tmpl_str).render(render_context)
        user_prompt = Template(user_tmpl_str).render(render_context)

        return system_prompt, user_prompt

prompt_builder = PromptBuilder()
