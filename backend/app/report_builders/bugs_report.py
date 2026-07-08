from typing import Dict, Any
from app.report_builders.base_builder import BaseReportBuilder

class BugsReportBuilder(BaseReportBuilder):
    def build_report(self, result: Dict[str, Any]) -> str:
        repo = result.get("repository", {})
        metadata = result.get("metadata", {})
        stats = result.get("statistics", {})
        chunks = result.get("chunks", [])

        logical_issues = []
        risk_areas = []
        error_prone = []
        null_concerns = []
        async_concerns = []
        resource_obs = []
        security_obs = []
        perf_concerns = []

        # Real evidence-based chunk analysis
        for chunk in chunks:
            path = chunk.get("path", "")
            content = chunk.get("content", "")
            start = chunk.get("start_line", 1)

            # 1. Error-prone patterns (silent exceptions, pass)
            if "except:" in content or "except Exception:" in content:
                if "pass" in content or "continue" in content:
                    error_prone.append(f"- Silent exception handling (bare except block with `pass` or `continue`) in `{path}` near line {start}.")
            
            # 2. Resource management observations (open/close)
            if "open(" in content and "with " not in content:
                resource_obs.append(f"- Resource acquisition without context manager (`open()` called outside `with`) in `{path}` near line {start}.")
            
            # 3. Async concerns (async/await mismatch)
            if "async " in content and "await " not in content and ".ts" in path:
                async_concerns.append(f"- Async function definition without explicit `await` expression in `{path}` near line {start}.")

            # 4. Null handling concerns
            if " == null" in content or " != null" in content:
                null_concerns.append(f"- Explicit null validation checks in `{path}` near line {start}; verify safety of property dereferencing.")

        # Performance concerns (file sizes)
        largest = stats.get("largest_files", [])
        if largest and largest[0].get("size", 0) > 10000:
            perf_concerns.append(f"- Large source file `{largest[0].get('path')}` ({largest[0].get('size')} bytes) may degrade parsing and memory usage.")

        # Formatting
        logical_str = "\n".join(logical_issues) if logical_issues else "Information could not be determined from the available repository context."
        risk_str = "\n".join(risk_areas) if risk_areas else "Information could not be determined from the available repository context."
        error_str = "\n".join(error_prone) if error_prone else "Information could not be determined from the available repository context."
        null_str = "\n".join(null_concerns) if null_concerns else "Information could not be determined from the available repository context."
        async_str = "\n".join(async_concerns) if async_concerns else "Information could not be determined from the available repository context."
        resource_str = "\n".join(resource_obs) if resource_obs else "Information could not be determined from the available repository context."
        security_str = "\n".join(security_obs) if security_obs else "Information could not be determined from the available repository context."
        perf_str = "\n".join(perf_concerns) if perf_concerns else "Information could not be determined from the available repository context."

        report = f"""# DevMind Real-Time Workspace Scan — Bug Finder Report
- **Repository Name**: `{repo.get("name")}`
- **Repository Owner**: `{repo.get("owner")}`
- **Default Branch**: `{repo.get("default_branch")}`
- **Language & Framework**: `{metadata.get("primary_language")}` / `{metadata.get("framework")}`
- **Task Objective**: `BUGS`

---

## 1. Potential Logical Issues
{logical_str}

## 2. Risk Areas
{risk_str}

## 3. Error-Prone Patterns (Hotspots & Logic Defects)
{error_str}


## 4. Null Handling Concerns
{null_str}

## 5. Async Concerns
{async_str}

## 6. Resource Management Observations
{resource_str}

## 7. Security Observations
{security_str}

## 8. Performance Concerns
{perf_str}
"""

        # Append traceability mapping
        return report + self.build_retrieved_context_section(result)
