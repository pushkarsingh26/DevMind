from typing import List, Dict, Any, Tuple, Optional
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
    Optionally injects structured knowledge-graph context before RAG chunks.
    """
    def __init__(self):
        self._templates = {
            "review": (SYSTEM_PROMPT_REVIEW, USER_PROMPT_REVIEW),
            "explain": (SYSTEM_PROMPT_EXPLAIN, USER_PROMPT_EXPLAIN),
            "tests": (SYSTEM_PROMPT_TESTS, USER_PROMPT_TESTS),
            "bugs": (SYSTEM_PROMPT_BUGS, USER_PROMPT_BUGS)
        }

    def optimize_chunks(self, chunks: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
        """
        Deduplicates context chunks, merges contiguous file ranges, and applies Context Compression
        to ensure minimal token consumption (preserves imports, decorators, and declarations).
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
        grouped_by_path: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in deduplicated:
            path = chunk.get("path", "Unknown")
            grouped_by_path.setdefault(path, []).append(chunk)

        merged_chunks = []

        for path, file_chunks in grouped_by_path.items():
            file_chunks.sort(key=lambda x: x.get("start_line", 0))
            
            current_merged = file_chunks[0]
            for next_chunk in file_chunks[1:]:
                prev_start = current_merged.get("start_line", 0)
                prev_end = current_merged.get("end_line", 0)
                next_start = next_chunk.get("start_line", 0)
                next_end = next_chunk.get("end_line", 0)
                
                prev_content = current_merged.get("content", "")
                next_content = next_chunk.get("content", "")

                if next_start <= prev_end + 5:
                    if next_start <= prev_end:
                        lines_prev = prev_content.split("\n")
                        lines_next = next_content.split("\n")
                        
                        overlap_start_index = next_start - prev_start
                        if overlap_start_index >= 0 and overlap_start_index < len(lines_prev):
                            merged_lines = lines_prev[:overlap_start_index] + lines_next
                            new_content = "\n".join(merged_lines)
                        else:
                            new_content = prev_content + "\n" + next_content
                    else:
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

        # 3. Context Compression (Targeting 30-40% fewer tokens on large chunks)
        query_words = [w.lower() for w in query.split() if len(w) > 3] if query else []
        for chunk in merged_chunks:
            content = chunk.get("content", "")
            lines = content.split("\n")
            if len(lines) <= 50:
                continue

            # Preserve imports/header declarations (first 15 lines)
            keep_indices = set(range(min(len(lines), 15)))
            
            for idx, line in enumerate(lines):
                line_lower = line.lower()
                is_import = "import " in line_lower or "require(" in line_lower or "from " in line_lower
                is_package = "package " in line_lower or "module " in line_lower or "namespace " in line_lower
                is_decorator = line.strip().startswith("@")
                is_declaration = any(k in line_lower for k in ("def ", "class ", "function", "const ", "let ", "export "))
                is_query_match = any(w in line_lower for w in query_words)
                
                if is_import or is_package or is_decorator or is_declaration or is_query_match:
                    # Keep matched line and a window of 1 line before and after
                    for i in range(max(0, idx - 1), min(len(lines), idx + 2)):
                        keep_indices.add(i)

            # Keep the last 10 lines
            for idx in range(max(0, len(lines) - 10), len(lines)):
                keep_indices.add(idx)

            # Reconstruct compressed content
            compressed_lines = []
            in_gap = False
            for idx in range(len(lines)):
                if idx in keep_indices:
                    if in_gap:
                        compressed_lines.append("[... compressed/trimmed ...]")
                        in_gap = False
                    compressed_lines.append(lines[idx])
                else:
                    in_gap = True

            if len(compressed_lines) >= len(lines) * 0.8:
                chunk["content"] = "\n".join(lines[:20]) + "\n[... compressed/trimmed ...]\n" + "\n".join(lines[-20:])
            else:
                chunk["content"] = "\n".join(compressed_lines)

        return merged_chunks

    def build_prompts(
        self,
        task_type: str,
        repository_metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        graph_context: Optional[str] = None,
        goal: Optional[str] = None,
        analysis_context: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Optimizes chunks and renders system/user prompt templates using Jinja.
        Injects graph_context before RAG chunks when available.
        """
        task_key = task_type.strip().lower()
        if task_key not in self._templates:
            raise ValueError(f"Unsupported task type: {task_type}")

        system_tmpl_str, user_tmpl_str = self._templates[task_key]

        # Optimize (deduplicate and merge) chunks
        optimized_chunks = self.optimize_chunks(chunks, query=goal or "")

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
            "chunks": optimized_chunks,
            "graph_context": graph_context or "",
            "analysis_context": analysis_context or "",
        }

        # Render prompts
        system_prompt = Template(system_tmpl_str).render(render_context)
        user_prompt = Template(user_tmpl_str).render(render_context)

        # Prepend graph context and analysis context to user prompt when available
        extra_ctx = []
        if analysis_context:
            extra_ctx.append(analysis_context)
        if graph_context:
            extra_ctx.append(graph_context)

        if extra_ctx:
            user_prompt = "\n\n---\n\n".join(extra_ctx) + "\n\n---\n\n" + user_prompt

        return system_prompt, user_prompt

prompt_builder = PromptBuilder()
