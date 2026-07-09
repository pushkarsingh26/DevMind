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
        ai_output = result.get("ai_output") or {}
        is_fallback = ai_output.get("is_fallback", True)

        warning_banner = ""
        if is_fallback:
            warning_banner = "> [!WARNING]\n> **AI Reasoning Engine is currently offline or failed back.** Displaying local heuristic static analysis fallback.\n\n"

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
