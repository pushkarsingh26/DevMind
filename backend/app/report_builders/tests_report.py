from typing import Dict, Any
from app.report_builders.base_builder import BaseReportBuilder

class TestsReportBuilder(BaseReportBuilder):
    def build_report(self, result: Dict[str, Any]) -> str:
        repo = result.get("repository", {})
        metadata = result.get("metadata", {})
        stats = result.get("statistics", {})
        chunks = result.get("chunks", [])

        primary_lang = metadata.get("primary_language")
        framework = metadata.get("framework")
        tests_present = metadata.get("tests_present")

        # Mock opportunities based on dependencies
        # Check AI output and fallback flag
        ai_output = result.get("ai_output")
        is_fallback = ai_output.get("is_fallback", True) if ai_output else True

        warning_banner = ""
        if ai_output and not is_fallback:
            # AI reasoning was successful!
            ut_list = ai_output.get("unit_test_suggestions", [])
            unit_recs_str = "\n".join(f"- {u}" for u in ut_list) if ut_list else "No unit test recommendations."
            
            it_list = ai_output.get("integration_test_suggestions", [])
            integration_recs_str = "\n".join(f"- {i}" for i in it_list) if it_list else "No integration test recommendations."
            
            cov_list = ai_output.get("coverage_status", [])
            coverage_recs_str = "\n".join(f"- {c}" for c in cov_list) if cov_list else "No coverage status details."
            
            mo_list = ai_output.get("mock_opportunities", [])
            mock_suggestions_str = "\n".join(f"- {m}" for m in mo_list) if mo_list else "No mock opportunities highlighted."
            
            ec_list = ai_output.get("edge_cases", [])
            edge_cases_str = "\n".join(f"- {e}" for e in ec_list) if ec_list else "No edge case testing recommendations."
        else:
            # Fallback block to local Phase 3 heuristics
            warning_banner = "> [!WARNING]\n> **AI Reasoning Engine is currently offline or failed back.** Displaying local heuristic static analysis fallback.\n\n"
            
            dependencies = metadata.get("dependencies", {})
            mock_suggestions = []
            for dep in dependencies.keys():
                if dep in ("axios", "requests", "httpx"):
                    mock_suggestions.append(f"- Mock HTTP requests made by `{dep}` library.")
                elif dep in ("pg", "sqlalchemy", "pymongo", "redis"):
                    mock_suggestions.append(f"- Mock database/cache client queries for `{dep}`.")
            
            mock_suggestions_str = "\n".join(mock_suggestions) if mock_suggestions else "Information could not be determined from the available repository context."

            unit_recs = []
            largest_files = stats.get("largest_files", [])
            for f in largest_files[:2]:
                unit_recs.append(f"- Write unit tests covering logical blocks of `{f.get('path')}`.")

            unit_recs_str = "\n".join(unit_recs) if unit_recs else "Information could not be determined from the available repository context."

            integration_recs = []
            if framework == "FastAPI":
                integration_recs.append("- Use `fastapi.testclient.TestClient` to perform request/response integration checks on routes.")
            elif framework == "Express":
                integration_recs.append("- Use `supertest` to verify HTTP endpoint status codes and JSON payloads.")
            elif framework and framework != "None":
                integration_recs.append(f"- Set up API client integration suites matching the `{framework}` configuration.")
            else:
                integration_recs.append("Information could not be determined from the available repository context.")

            integration_recs_str = "\n".join(integration_recs)

            coverage_recs = []
            if not tests_present:
                coverage_recs.append("- No dedicated `/tests` or `/test` directory was found. 100% of codebase lacks coverage.")
            else:
                coverage_recs.append("- Existing test file structure was detected, but detailed block-level execution metrics are not parsed.")
            coverage_recs_str = "\n".join(coverage_recs)

            edge_cases = []
            if largest_files:
                edge_cases.append(f"- Check parameter validation, boundary values, and exception handling for operations in `{largest_files[0].get('path')}`.")
            edge_cases_str = "\n".join(edge_cases) if edge_cases else "Information could not be determined from the available repository context."

        report = f"""{warning_banner}# DevMind Real-Time Workspace Scan — Test Generation Recommendations
- **Repository Name**: `{repo.get("name")}`
- **Repository Owner**: `{repo.get("owner")}`
- **Default Branch**: `{repo.get("default_branch")}`
- **Language & Framework**: `{primary_lang}` / `{framework}`
- **Task Objective**: `TESTS`

---

## 1. Unit Testing Suggestions
{unit_recs_str}

## 2. Integration Testing Suggestions
{integration_recs_str}

## 3. Test Suite Coverage Status
{coverage_recs_str}

## 4. Mock Opportunities
{mock_suggestions_str}

## 5. Edge Cases
{edge_cases_str}
"""

        # Append traceability mapping and analysis metadata
        return report + self.build_analysis_metadata_section(result) + self.build_retrieved_context_section(result)
