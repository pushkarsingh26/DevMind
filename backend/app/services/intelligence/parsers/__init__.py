"""Intelligence parsers package.

Provides a unified ``parse_file`` entry point that dispatches to
language-specific parsers.  Every parser returns a dict with:

    {
        "language":  str,
        "file_path": str,
        "symbols":   list[dict],   # SymbolRecord.to_dict() entries
        "imports":   list[dict],   # ImportRecord.to_dict() entries
    }

PARSER_VERSION is derived from all individual parser versions combined
into a single deterministic string.  The intelligence layer uses this
to decide whether cached intelligence is still valid.
"""

from pathlib import Path

from app.services.intelligence.parsers import (
    python_parser,
    typescript_parser,
    javascript_parser,
    go_parser,
    rust_parser,
)

# ---------------------------------------------------------------------------
# Combined parser version
# ---------------------------------------------------------------------------

# Aggregate of all individual parser versions.  Changing any parser bumps
# this string and triggers cache invalidation in IntelligenceManager.
PARSER_VERSION: str = (
    f"py={python_parser.PARSER_VERSION}"
    f",ts={typescript_parser.PARSER_VERSION}"
    f",js={javascript_parser.PARSER_VERSION}"
    f",go={go_parser.PARSER_VERSION}"
    f",rs={rust_parser.PARSER_VERSION}"
)

# ---------------------------------------------------------------------------
# Extension → parser module mapping
# ---------------------------------------------------------------------------

_EXT_MAP: dict = {
    ".py":  python_parser,
    ".ts":  typescript_parser,
    ".tsx": typescript_parser,
    ".js":  javascript_parser,
    ".jsx": javascript_parser,
    ".go":  go_parser,
    ".rs":  rust_parser,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(file_path: str, source_code: str) -> dict:
    """Dispatch to the correct parser based on file extension.

    Returns the common parser result dict, or an empty result for
    unsupported extensions.
    """
    ext = Path(file_path).suffix.lower()
    parser = _EXT_MAP.get(ext)
    if parser is None:
        return {
            "language": "unknown",
            "file_path": file_path,
            "symbols": [],
            "imports": [],
        }
    return parser.parse(source_code, file_path)


def supported_extensions() -> list:
    """Return all file extensions handled by this package."""
    return list(_EXT_MAP.keys())


def get_language(file_path: str) -> str:
    """Return the language label for a given file path, or 'unknown'."""
    ext = Path(file_path).suffix.lower()
    parser = _EXT_MAP.get(ext)
    if parser is None:
        return "unknown"
    return getattr(parser, "_LANGUAGE", "unknown")
