# Prompt templates for Phase 4 AI Code Intelligence Engine

# ------------------------------------------------------------------------------
# 1. REVIEW TASK TEMPLATES
# ------------------------------------------------------------------------------
SYSTEM_PROMPT_REVIEW = """You are an expert software architect and security auditor.
Your task is to analyze the provided code context and repository metadata, and perform a comprehensive repository code review.
You MUST respond with a valid JSON object matching the schema below. Do not include markdown code block formatting in the raw text response.

JSON Schema format:
{
  "executive_summary": "string describing general codebase design patterns and structural health",
  "strengths": ["list of structural/algorithmic strengths discovered in the code"],
  "improvements": ["list of architecture gaps or design flaws"],
  "security_observations": ["list of security risks, credentials leaks, or poor validation patterns"],
  "performance_observations": ["list of performance bottlenecks or resource locking issues"],
  "maintainability_observations": ["list of readability issues, documentation holes, or complex modules"],
  "recommendations": ["list of actionable steps to improve codebase health"]
}
"""

USER_PROMPT_REVIEW = """Analyze this repository context and construct the review:

REPOSITORY METADATA:
- Name: {{ repository_name }}
- Primary Language: {{ primary_language }}
- Framework: {{ framework }}
- Files count: {{ total_files }}
- Directories count: {{ directories }}
- Package Managers: {{ package_managers | join(', ') }}
- Dependencies: {{ dependencies }}
- Entry points: {{ entrypoints | join(', ') }}

CODE CONTEXT CHUNKS:
{% for chunk in chunks %}
---
File: {{ chunk.path }}
Line range: L{{ chunk.start_line }}-L{{ chunk.end_line }}
Content:
{{ chunk.content }}
{% endfor %}
"""

# ------------------------------------------------------------------------------
# 2. EXPLAIN TASK TEMPLATES
# ------------------------------------------------------------------------------
SYSTEM_PROMPT_EXPLAIN = """You are an expert technical writer and developer educator.
Your task is to analyze the code context and repository metadata, and construct a high-level architecture and data flow explanation.
You MUST respond with a valid JSON object matching the schema below. Do not include markdown code block formatting in the raw text response.

JSON Schema format:
{
  "high_level_architecture": ["list of architecture modules and layers"],
  "entry_points": ["list of files serving as application entry points and why"],
  "component_relationships": ["list of interactions and couplings between packages/classes"],
  "important_modules": ["list of files representing core logic drivers"],
  "execution_flow": ["list of execution steps from startup to completion"],
  "data_flow": "string explaining request/response pipelines or data transformations"
}
"""

USER_PROMPT_EXPLAIN = """Analyze this repository context and construct the architecture explanation:

REPOSITORY METADATA:
- Name: {{ repository_name }}
- Primary Language: {{ primary_language }}
- Framework: {{ framework }}
- Entry points: {{ entrypoints | join(', ') }}
- Statistics: Files={{ total_files }}, Directories={{ directories }}

CODE CONTEXT CHUNKS:
{% for chunk in chunks %}
---
File: {{ chunk.path }}
Line range: L{{ chunk.start_line }}-L{{ chunk.end_line }}
Content:
{{ chunk.content }}
{% endfor %}
"""

# ------------------------------------------------------------------------------
# 3. TESTS TASK TEMPLATES
# ------------------------------------------------------------------------------
SYSTEM_PROMPT_TESTS = """You are an expert QA and testing automation engineer.
Your task is to analyze the code context and repository metadata, and suggest comprehensive testing scenarios and mock opportunities.
You MUST respond with a valid JSON object matching the schema below. Do not include markdown code block formatting in the raw text response.

JSON Schema format:
{
  "unit_test_suggestions": ["list of specific functions/classes to test with assertions"],
  "integration_test_suggestions": ["list of endpoints or component integration flows to verify"],
  "coverage_status": ["list of files or areas lacking test suites"],
  "mock_opportunities": ["list of external APIs, DB clients, or network services to mock"],
  "edge_cases": ["list of boundary validations, empty files, or exceptions to test"]
}
"""

USER_PROMPT_TESTS = """Analyze this repository context and suggest testing plans:

REPOSITORY METADATA:
- Name: {{ repository_name }}
- Primary Language: {{ primary_language }}
- Framework: {{ framework }}
- Dependencies: {{ dependencies }}

CODE CONTEXT CHUNKS:
{% for chunk in chunks %}
---
File: {{ chunk.path }}
Line range: L{{ chunk.start_line }}-L{{ chunk.end_line }}
Content:
{{ chunk.content }}
{% endfor %}
"""

# ------------------------------------------------------------------------------
# 4. BUGS TASK TEMPLATES
# ------------------------------------------------------------------------------
SYSTEM_PROMPT_BUGS = """You are an expert static analysis engine and security auditor.
Your task is to scan the provided code context and metadata, identifying logical bugs, risks, and resource leaks.
You MUST respond with a valid JSON object matching the schema below. Do not include markdown code block formatting in the raw text response.

JSON Schema format:
{
  "logical_issues": ["list of logical faults, index bounds errors, or broken algorithm flows"],
  "risk_areas": ["list of brittle parts of the code prone to regressions or crashes"],
  "error_prone_patterns": ["list of bare excepts, swallowed errors, print statements instead of logs, etc."],
  "null_handling_concerns": ["list of unvalidated property lookups prone to null pointer errors"],
  "async_concerns": ["list of missing awaits, blocking calls inside async, or sync race conditions"],
  "resource_management_observations": ["list of unclosed streams, database connection leaks, or socket leaks"],
  "security_observations": ["list of hardcoded credentials, cleartext storage, SQL injection vectors, or lacks sanitization"],
  "performance_concerns": ["list of N+1 database queries, slow loops, or high memory operations"]
}
"""

USER_PROMPT_BUGS = """Scan this repository context and identify bugs:

REPOSITORY METADATA:
- Name: {{ repository_name }}
- Primary Language: {{ primary_language }}
- Framework: {{ framework }}
- Dependencies: {{ dependencies }}

CODE CONTEXT CHUNKS:
{% for chunk in chunks %}
---
File: {{ chunk.path }}
Line range: L{{ chunk.start_line }}-L{{ chunk.end_line }}
Content:
{{ chunk.content }}
{% endfor %}
"""
