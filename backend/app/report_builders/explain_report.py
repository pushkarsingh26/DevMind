from typing import Dict, Any
from app.report_builders.base_builder import BaseReportBuilder

class ExplainReportBuilder(BaseReportBuilder):
    def build_report(self, result: Dict[str, Any]) -> str:
        repo = result.get("repository", {})
        metadata = result.get("metadata", {})
        stats = result.get("statistics", {})
        chunks = result.get("chunks", [])

        # File extension distribution format
        extensions_lines = []
        for ext, count in stats.get("extensions", {}).items():
            extensions_lines.append(f"- `{ext}`: {count} files")
        extensions_str = "\n".join(extensions_lines) if extensions_lines else "None"

        # Determine main entrypoints based on scanned metadata and chunks
        # Check AI output and fallback flag
        ai_output = result.get("ai_output") or {}
        is_fallback = ai_output.get("is_fallback", True)

        warning_banner = ""
        if is_fallback:
            warning_banner = "> [!WARNING]\n> **AI Reasoning Engine is currently offline or failed back.** Displaying local heuristic static analysis fallback.\n\n"

        hla_list = ai_output.get("high_level_architecture", [])
        arch_str = "\n".join(f"- {a}" for a in hla_list) if hla_list else "No high-level architecture details."
        
        ep_list = ai_output.get("entry_points", [])
        entrypoints_str = "\n".join(f"- {ep}" for ep in ep_list) if ep_list else "No entry points identified."
        
        cr_list = ai_output.get("component_relationships", [])
        cr_str = "\n".join(f"- {c}" for c in cr_list) if cr_list else "No component relationships identified."
        
        im_list = ai_output.get("important_modules", [])
        important_modules_str = "\n".join(f"- {m}" for m in im_list) if im_list else "No important modules highlighted."
        
        ef_list = ai_output.get("execution_flow", [])
        execution_flow_str = "\n".join(f"- {e}" for e in ef_list) if ef_list else "No execution flow details."
        
        data_flow = ai_output.get("data_flow", "No data flow details.")

        report = f"""{warning_banner}# DevMind Real-Time Workspace Scan — Architecture Explanation
- **Repository Name**: `{repo.get("name")}`
- **Repository Owner**: `{repo.get("owner")}`
- **Default Branch**: `{repo.get("default_branch")}`
- **Language & Framework**: `{metadata.get("primary_language")}` / `{metadata.get("framework")}`
- **Task Objective**: `EXPLAIN`

---

## 1. Folder Structure
- **Total Folders**: `{stats.get("total_directories")}`
- **Total Code Files**: `{stats.get("total_files")}`

### Workspace File Extensions
{extensions_str}

## 2. High-Level Architecture
{arch_str}

## 3. Entry Points
{entrypoints_str}

## 4. Component Relationships (Component Structure (Explanation))
{cr_str}

## 5. Important Modules
{important_modules_str}

## 6. Execution Flow
{execution_flow_str}

## 7. Data Flow
{data_flow}
"""

        # Append traceability mapping and analysis metadata
        return report + self.build_analysis_metadata_section(result) + self.build_retrieved_context_section(result)
