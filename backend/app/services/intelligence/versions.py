"""Central version constants for the Repository Intelligence layer.

Versioning strategy
-------------------
Four independent version strings govern cache validity.

INTELLIGENCE_VERSION
    Bumped when the overall build pipeline changes (new build steps,
    new output files, new directory layout).

PARSER_VERSION
    Bumped when any parser changes the symbols or imports it extracts
    (new symbol types, changed field names, new language support).

SCHEMA_VERSION
    Bumped when the JSON schema for symbols, imports, or dependencies
    changes in a breaking way (field renamed/removed, type changed).

FORMAT_VERSION
    Bumped when the file layout / storage format changes (new files
    added to or removed from the output directory, directory structure
    changes). Separating FORMAT from SCHEMA avoids unnecessary cache
    rebuilds when storage changes but the symbol schema does not.

A cached intelligence bundle is ONLY valid when ALL FOUR version strings
match the constants defined here.  A repository-hash match alone is not
sufficient for reuse.

Generator metadata
------------------
GENERATOR_NAME and GENERATOR_VERSION are embedded in every manifest.json
for auditing and debugging purposes.
"""

# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------

INTELLIGENCE_VERSION: str = "v2"
"""Bumped v1 → v2 in Phase 8.1.1 (per-file hashing, errors.json,
call_graph.json, richer manifest, 4-version cache validation)."""

PARSER_VERSION: str = "v1"
"""Bumped when any language parser changes its extraction logic."""

SCHEMA_VERSION: str = "v1"
"""Bumped when the JSON schema for symbols/imports/dependencies changes."""

FORMAT_VERSION: str = "v1"
"""Bumped when the output file layout changes (new/removed JSON files)."""

# ---------------------------------------------------------------------------
# Generator metadata
# ---------------------------------------------------------------------------

GENERATOR_NAME: str = "devmind-intelligence"
GENERATOR_VERSION: str = "0.2.0"

# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: list = ["python", "typescript", "javascript", "go", "rust"]

# ---------------------------------------------------------------------------
# Required output files (all must exist for a build to be considered valid)
# ---------------------------------------------------------------------------

REQUIRED_FILES: list = [
    "manifest.json",
    "file_tree.json",
    "modules.json",
    "symbols.json",
    "imports.json",
    "dependencies.json",
    "statistics.json",
    "errors.json",
    "call_graph.json",
]

# ---------------------------------------------------------------------------
# Error categories (used in errors.json)
# ---------------------------------------------------------------------------

ERROR_CATEGORIES: list = [
    "ParserError",
    "IOError",
    "EncodingError",
    "UnsupportedLanguage",
    "Timeout",
]
