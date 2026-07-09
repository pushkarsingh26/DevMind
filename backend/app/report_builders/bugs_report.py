from typing import Dict, Any
from app.report_builders.base_builder import BaseReportBuilder

class BugsReportBuilder(BaseReportBuilder):
    def build_report(self, result: Dict[str, Any]) -> str:
        repo = result.get("repository", {})
        metadata = result.get("metadata", {})
        stats = result.get("statistics", {})
        chunks = result.get("chunks", [])

        # Check AI output and fallback flag
        ai_output = result.get("ai_output") or {}
        is_fallback = ai_output.get("is_fallback", True)

        warning_banner = ""
        if is_fallback:
            warning_banner = "> [!WARNING]\n> **AI Reasoning Engine is currently offline or failed back.** Displaying local heuristic static analysis fallback.\n\n"

        log_list = ai_output.get("logical_issues", [])
        logical_str = "\n".join(f"- {l}" for l in log_list) if log_list else "No significant issues detected."
        
        risk_list = ai_output.get("risk_areas", [])
        risk_str = "\n".join(f"- {r}" for r in risk_list) if risk_list else "No significant issues detected."
        
        ep_list = ai_output.get("error_prone_patterns", [])
        error_str = "\n".join(f"- {e}" for e in ep_list) if ep_list else "No significant issues detected."
        
        null_list = ai_output.get("null_handling_concerns", [])
        null_str = "\n".join(f"- {n}" for n in null_list) if null_list else "No significant issues detected."
        
        async_list = ai_output.get("async_concerns", [])
        async_str = "\n".join(f"- {a}" for a in async_list) if async_list else "No async execution concerns."
        
        res_list = ai_output.get("resource_management_observations", [])
        resource_str = "\n".join(f"- {r}" for r in res_list) if res_list else "No significant issues detected."
        
        sec_list = ai_output.get("security_observations", [])
        security_str = "\n".join(f"- {s}" for s in sec_list) if sec_list else "No significant issues detected."
        
        perf_list = ai_output.get("performance_concerns", [])
        perf_str = "\n".join(f"- {p}" for p in perf_list) if perf_list else "No significant issues detected."

        report = f"""{warning_banner}# DevMind Real-Time Workspace Scan — Bug Finder Report
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

        # Append traceability mapping and analysis metadata
        return report + self.build_analysis_metadata_section(result) + self.build_retrieved_context_section(result)
