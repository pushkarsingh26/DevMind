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
        entrypoints = []
        largest_files = stats.get("largest_files", [])
        for f in largest_files:
            path = f.get("path", "")
            basename = path.split("/")[-1].split("\\")[-1]
            if basename in ("main.py", "app.py", "index.js", "App.tsx", "server.js", "manage.py", "index.ts"):
                entrypoints.append(f"- Entrypoint detected: `{path}` ({f.get('size')} bytes)")
        
        # Fallback if no specific entrypoint name matched
        if not entrypoints and largest_files:
            entrypoints.append(f"- Primary candidate entrypoint: `{largest_files[0].get('path')}` ({largest_files[0].get('size')} bytes)")
        
        entrypoints_str = "\n".join(entrypoints) if entrypoints else "Information could not be determined from the available repository context."

        # Architecture and relationships
        primary_lang = metadata.get("primary_language")
        framework = metadata.get("framework")
        
        arch_lines = []
        if primary_lang and primary_lang != "Unknown":
            arch_lines.append(f"- Built primarily using `{primary_lang}` codebase structures.")
        if framework and framework != "None":
            arch_lines.append(f"- Structured around a `{framework}` application architecture layout.")
        arch_str = "\n".join(arch_lines) if arch_lines else "Information could not be determined from the available repository context."

        # Component relationships & modules
        important_modules = []
        for f in largest_files[:3]:
            important_modules.append(f"- Module: `{f.get('path')}`")
        important_modules_str = "\n".join(important_modules) if important_modules else "Information could not be determined from the available repository context."

        # Data Flow
        data_flow = "Information could not be determined from the available repository context."
        if framework in ("FastAPI", "Express", "Next.js", "Django", "Flask"):
            data_flow = f"- As a `{framework}` application, incoming data flows through API route declarations, mapping request payloads directly to handler functions before returning database/JSON results."

        report = f"""# DevMind Real-Time Workspace Scan — Architecture Explanation
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
- Core library imports and package declarations specify project boundaries.

- Database dependencies (if any) link relational structures with codebase modules.

## 5. Important Modules
{important_modules_str}

## 6. Execution Flow
- Starts at detected entry points and invokes helper libraries and model modules sequentially.

## 7. Data Flow
{data_flow}
"""

        # Append traceability mapping
        return report + self.build_retrieved_context_section(result)
