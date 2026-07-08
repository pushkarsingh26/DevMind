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
