from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseReportBuilder(ABC):
    @abstractmethod
    def build_report(self, result: Dict[str, Any]) -> str:
        """
        Builds task-specific report from repository metadata and chunk context.
        """
        pass

    def build_retrieved_context_section(self, result: Dict[str, Any]) -> str:
        """
        Compiles the mandatory 'Retrieved Context' section for debugging and traceability.
        """
        chunks = result.get("chunks", [])
        if not chunks:
            return "\n## Retrieved Context\n*No context chunks were retrieved or stored for this repository.*\n"

        lines = [
            "\n## Retrieved Context",
            "This report is generated from the following retrieved context chunks:",
            "",
            "| Source File | Line Range | Chunk ID | Similarity Score |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for chunk in chunks:
            path = chunk.get("path", "Unknown")
            start = chunk.get("start_line", "Unknown")
            end = chunk.get("end_line", "Unknown")
            # Chunk ID parsing
            chunk_id = chunk.get("id", "N/A")
            # Similarity score: if we run a retrieve query, it has score, otherwise N/A
            score = chunk.get("score")
            score_str = f"{score:.4f}" if score is not None else "N/A (Full Index)"

            lines.append(f"| `{path}` | L{start}-L{end} | `{chunk_id}` | {score_str} |")

        return "\n".join(lines) + "\n"

    def build_analysis_metadata_section(self, result: Dict[str, Any]) -> str:
        """
        Compiles the 'Analysis Metadata' section detailing provider model, latencies, cache, and failover status.
        """
        ai_output = result.get("ai_output")
        if not ai_output:
            return (
                "\n## Analysis Metadata\n"
                "- **AI Reasoning Engine**: Offline (Pre-Phase 4 Legacy / Direct Heuristic Execution)\n"
                "- **Fallback Status**: Heuristic Fallback Active\n"
            )

        meta = ai_output.get("ai_metadata", {})
        if not meta:
            return "\n## Analysis Metadata\n- *No analysis metadata available.*\n"

        provider = meta.get("provider", "Unknown")
        failover_provider = meta.get("provider_used_after_failover")
        model = meta.get("model", "Unknown")
        latency = meta.get("latency", 0.0)
        cache_hit = meta.get("cache_hit", False)
        fallback_flag = meta.get("fallback_flag", False)
        completed_ts = meta.get("completed_timestamp")

        import datetime
        timestamp_str = (
            datetime.datetime.fromtimestamp(completed_ts).strftime("%Y-%m-%d %H:%M:%S UTC")
            if completed_ts
            else "N/A"
        )

        provider_str = f"{provider} -> {failover_provider}" if failover_provider else provider
        cache_status = "Hit" if cache_hit else "Miss"
        fallback_status = "Heuristic Fallback Active" if (fallback_flag or ai_output.get("is_fallback", False)) else "AI Successful"
        chunk_count = len(result.get("chunks", []))

        lines = [
            "\n## Analysis Metadata",
            f"- **Provider Chain**: `{provider_str}`",
            f"- **Model Used**: `{model}`",
            f"- **Latency**: `{latency:.3f} seconds`",
            f"- **Retrieved Context Chunks**: `{chunk_count}`",
            f"- **Cache Status**: `{cache_status}`",
            f"- **Fallback Status**: `{fallback_status}`",
            f"- **Generation Timestamp**: `{timestamp_str}`",
            ""
        ]
        return "\n".join(lines)

