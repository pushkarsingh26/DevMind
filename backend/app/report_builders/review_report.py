from typing import Dict, Any
from app.report_builders.base_builder import BaseReportBuilder

class ReviewReportBuilder(BaseReportBuilder):
    def build_report(self, result: Dict[str, Any]) -> str:
        repo = result.get("repository", {})
        metadata = result.get("metadata", {})
        stats = result.get("statistics", {})
        chunks = result.get("chunks", [])

        # Format helpers
        pkg_managers = metadata.get("package_managers", [])
        pkg_managers_str = ", ".join(pkg_managers) if pkg_managers else "None detected"

        deps_lines = []
        for name, ver in metadata.get("dependencies", {}).items():
            deps_lines.append(f"- `{name}`: `{ver}`")
        deps_str = "\n".join(deps_lines) if deps_lines else "None parsed"

        largest_files_lines = []
        for f in stats.get("largest_files", []):
            largest_files_lines.append(f"- `{f.get('path')}` ({f.get('size')} bytes)")
        largest_files_str = "\n".join(largest_files_lines) if largest_files_lines else "None recorded"

        extensions_lines = []
        for ext, count in stats.get("extensions", {}).items():
            extensions_lines.append(f"- `{ext}`: {count} files")
        extensions_str = "\n".join(extensions_lines) if extensions_lines else "None"

        # Check AI output and fallback flag
        ai_output = result.get("ai_output")
        is_fallback = ai_output.get("is_fallback", True) if ai_output else True

        warning_banner = ""
        if ai_output and not is_fallback:
            # AI reasoning was successful!
            executive_summary = ai_output.get("executive_summary", "No summary provided.")
            
            s_list = ai_output.get("strengths", [])
            strengths_str = "\n".join(f"- {s}" for s in s_list) if s_list else "No strengths noted."
            
            i_list = ai_output.get("improvements", [])
            improvements_str = "\n".join(f"- {i}" for i in i_list) if i_list else "No improvement areas noted."
            
            sec_list = ai_output.get("security_observations", [])
            security_str = "\n".join(f"- {s}" for s in sec_list) if sec_list else "No security observations."
            
            perf_list = ai_output.get("performance_observations", [])
            performance_str = "\n".join(f"- {p}" for p in perf_list) if perf_list else "No performance observations."
            
            maint_list = ai_output.get("maintainability_observations", [])
            maintainability_str = "\n".join(f"- {m}" for m in maint_list) if maint_list else "No maintainability observations."
            
            r_list = ai_output.get("recommendations", [])
            recs_str = "\n".join(f"- {r}" for r in r_list) if r_list else "No recommendations."
        else:
            # Fallback to local Phase 3 heuristics
            warning_banner = "> [!WARNING]\n> **AI Reasoning Engine is currently offline or failed back.** Displaying local heuristic static analysis fallback.\n\n"
            
            strengths = []
            if metadata.get("docker_support"):
                strengths.append("- Docker support is configured (Dockerfile present).")
            if metadata.get("github_actions"):
                strengths.append("- CI/CD workflow is integrated via GitHub Actions.")
            if metadata.get("cicd"):
                strengths.append("- Other CI/CD configurations are defined in the repository.")
            if metadata.get("tests_present"):
                strengths.append("- Test suite folder/file structure is present.")
            strengths_str = "\n".join(strengths) if strengths else "Information could not be determined from the available repository context."

            improvements = []
            if not metadata.get("tests_present"):
                improvements.append("- Missing unit test coverage structures.")
            if not metadata.get("readme_present"):
                improvements.append("- Missing README documentation at the repository root.")
            if not metadata.get("license") or metadata.get("license") == "None":
                improvements.append("- No open source LICENSE file was detected.")
            improvements_str = "\n".join(improvements) if improvements else "Information could not be determined from the available repository context."

            security_obs = []
            if metadata.get("docker_support"):
                security_obs.append("- Dockerfile and environment configs were parsed. Verify environment credentials security.")
            if metadata.get("dependencies"):
                security_obs.append("- Core dependencies mapped for security scanning.")
            security_str = "\n".join(security_obs) if security_obs else "Information could not be determined from the available repository context."

            performance_obs = []
            largest = stats.get("largest_files", [])
            if largest:
                performance_obs.append(f"- Large code files detected (largest is `{largest[0].get('path')}` at {largest[0].get('size')} bytes).")
            performance_str = "\n".join(performance_obs) if performance_obs else "Information could not be determined from the available repository context."

            maintainability_obs = []
            primary_lang = metadata.get("primary_language")
            framework = metadata.get("framework")
            if primary_lang and primary_lang != "Unknown":
                maintainability_obs.append(f"- Main language determined: `{primary_lang}`.")
            if framework and framework != "None":
                maintainability_obs.append(f"- Framework structure: `{framework}`.")
            maintainability_str = "\n".join(maintainability_obs) if maintainability_obs else "Information could not be determined from the available repository context."

            recs = []
            if not metadata.get("tests_present"):
                recs.append("- Recommendation: Establish automated test coverage by adding test suites.")
            if stats.get("largest_files") and len(stats.get("largest_files", [])) > 0:
                recs.append("- Recommendation: Consider modularizing larger files to optimize code structure.")
            recs_str = "\n".join(recs) if recs else "Information could not be determined from the available repository context."

            executive_summary = "Structured repository assessment generated from repository metadata, scanner outputs, dependency analysis, and retrieved repository context."

        report = f"""{warning_banner}# DevMind Real-Time Workspace Scan — Repository Review
- **Repository Name**: `{repo.get("name")}`
- **Repository Owner**: `{repo.get("owner")}`
- **Default Branch**: `{repo.get("default_branch")}`
- **Status**: `SUCCESS`

---

## 1. Executive Summary
{executive_summary}

## 2. Repository Overview
- **Name**: `{repo.get("name")}`
- **Owner**: `{repo.get("owner")}`
- **Source URL**: `{result.get("source_path_or_url") or "Uploaded zip file"}`

## 3. Codebase Architecture Summary
- **Primary Language**: `{metadata.get("primary_language") or "Unknown"}`
- **Framework**: `{metadata.get("framework") or "None"}`
- **License**: `{metadata.get("license") or "None"}`


## 4. Dependency Summary
- **Package Manager**: `{pkg_managers_str}`

### Core Dependency Details
{deps_str}

## 5. Code Organization
### File Extensions Distribution
{extensions_str}

### Largest Files
{largest_files_str}

## 6. Repository Statistics
- **Total Files**: `{stats.get("total_files")}`
- **Total Folders**: `{stats.get("total_directories")}`
- **Retrieved Chunk Spans**: `{len(chunks)} chunks`

## 7. Strengths
{strengths_str}

## 8. Potential Improvement Areas
{improvements_str}

## 9. Security Observations
{security_str}

## 10. Performance Observations
{performance_str}

## 11. Maintainability Observations
{maintainability_str}

## 12. Recommendations
{recs_str}
"""

        # Append traceability mapping and analysis metadata
        return report + self.build_analysis_metadata_section(result) + self.build_retrieved_context_section(result)
