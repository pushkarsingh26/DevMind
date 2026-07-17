"""JavaScript / JSX source-file parser.

Delegates to the TypeScript parser (JS is a structural subset) and
relabels the language/prefix as "javascript" / "js".

Supported symbols: class, function, method, interface, enum, constant
IDs:               ``js:{file_path}:{name}:{type}``
"""

from typing import Any, Dict

from app.services.intelligence.parsers import typescript_parser as _ts

_LANGUAGE = "javascript"
_LANG_PREFIX = "js"
PARSER_VERSION = "v1"

# Noise names re-exported for test introspection
_NOISE_NAMES = _ts._NOISE_NAMES  # noqa: SLF001


def parse(source_code: str, file_path: str) -> Dict[str, Any]:
    """Parse a JavaScript/JSX source file."""
    result = _ts.parse(source_code, file_path)

    # Relabel language everywhere
    result["language"] = _LANGUAGE
    for sym in result.get("symbols", []):
        sym["language"] = _LANGUAGE
        # Rebuild id with "js" prefix
        sym["id"] = sym["id"].replace("ts:", f"{_LANG_PREFIX}:", 1)
    for imp in result.get("imports", []):
        imp["language"] = _LANGUAGE

    return result
