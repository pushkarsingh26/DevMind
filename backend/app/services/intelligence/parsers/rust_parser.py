"""Rust source-file parser (regex-based).

Returns the standard parser result dict:
    language   – "rust"
    file_path  – relative path supplied by the caller
    symbols    – list of SymbolRecord-compatible dicts
    imports    – list of ImportRecord-compatible dicts

Supported symbols: struct, enum, trait, function, method, constant
Visibility:        "public" if prefixed with ``pub``, otherwise "private"
IDs:               ``rs:{file_path}:{name}:{type}``
"""

import re
from typing import Any, Dict, List

from app.services.intelligence.models import SymbolRecord, ImportRecord

_LANGUAGE = "rust"
_LANG_PREFIX = "rs"
PARSER_VERSION = "v1"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# pub(crate) / pub(super) / pub(in ...) all count as some form of public
_PUB = r"(?:pub(?:\s*\([^)]*\))?\s+)?"

_STRUCT_RE   = re.compile(rf"^\s*{_PUB}struct\s+(?P<n>\w+)", re.M)
_ENUM_RE     = re.compile(rf"^\s*{_PUB}enum\s+(?P<n>\w+)", re.M)
_TRAIT_RE    = re.compile(rf"^\s*{_PUB}trait\s+(?P<n>\w+)", re.M)
_CONST_RE    = re.compile(rf"^\s*{_PUB}const\s+(?P<n>[A-Z_][A-Z0-9_]*)\s*:", re.M)

# Methods inside impl blocks (indented with 4 spaces)
_METHOD_RE   = re.compile(rf"^    {_PUB}(?:async\s+)?fn\s+(?P<n>\w+)\s*[(<]", re.M)

# Top-level functions
_FUNCTION_RE = re.compile(rf"^\s*{_PUB}(?:async\s+)?fn\s+(?P<n>\w+)\s*[(<]", re.M)

# Imports
_USE_RE      = re.compile(r"^\s*use\s+(?P<m>[^;]+);", re.M)
_EXTERN_RE   = re.compile(r"^\s*extern\s+crate\s+(?P<m>\w+)", re.M)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _line_of(source: str, match: re.Match) -> int:
    return source[: match.start()].count("\n") + 1


_PUB_CHECK = re.compile(r"\bpub\b|\bpub\s*\(")


def _rust_visibility(raw_line: str) -> str:
    return "public" if _PUB_CHECK.search(raw_line) else "private"


def _make(name: str, sym_type: str, file_path: str, line: int, source: str, match: re.Match) -> Dict[str, Any]:
    # Use the full matched text to determine visibility
    vis = _rust_visibility(match.group(0))
    return SymbolRecord.make(
        name=name, sym_type=sym_type, file_path=file_path,
        language=_LANGUAGE, lang_prefix=_LANG_PREFIX,
        line_start=line, line_end=line,
        visibility=vis,
    ).to_dict()


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

def _extract_symbols(source: str, file_path: str) -> List[Dict[str, Any]]:
    symbols: List[Dict[str, Any]] = []

    for m in _STRUCT_RE.finditer(source):
        symbols.append(_make(m.group("n"), "struct", file_path, _line_of(source, m), source, m))

    for m in _ENUM_RE.finditer(source):
        symbols.append(_make(m.group("n"), "enum", file_path, _line_of(source, m), source, m))

    for m in _TRAIT_RE.finditer(source):
        symbols.append(_make(m.group("n"), "trait", file_path, _line_of(source, m), source, m))

    for m in _CONST_RE.finditer(source):
        symbols.append(_make(m.group("n"), "constant", file_path, _line_of(source, m), source, m))

    method_starts = {m.start() for m in _METHOD_RE.finditer(source)}

    for m in _METHOD_RE.finditer(source):
        symbols.append(_make(m.group("n"), "method", file_path, _line_of(source, m), source, m))

    for m in _FUNCTION_RE.finditer(source):
        if m.start() not in method_starts:
            symbols.append(_make(m.group("n"), "function", file_path, _line_of(source, m), source, m))

    return symbols


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------

def _normalize_use(raw: str) -> str:
    """Normalize a Rust use path by stripping trailing whitespace/braces."""
    return raw.strip().rstrip(";")


def _extract_imports(source: str, file_path: str) -> List[Dict[str, Any]]:
    seen: set = set()
    imports: List[Dict[str, Any]] = []

    def _add(module: str, line: int) -> None:
        key = module
        if key in seen:
            return
        seen.add(key)
        imports.append(ImportRecord(
            module=module, name=None, alias=None,
            file=file_path, language=_LANGUAGE, line=line,
        ).to_dict())

    for m in _USE_RE.finditer(source):
        _add(_normalize_use(m.group("m")), _line_of(source, m))

    for m in _EXTERN_RE.finditer(source):
        _add(m.group("m"), _line_of(source, m))

    return imports


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source_code: str, file_path: str) -> Dict[str, Any]:
    """Parse a Rust source file."""
    try:
        symbols = _extract_symbols(source_code, file_path)
        imports = _extract_imports(source_code, file_path)
    except Exception:
        symbols = []
        imports = []

    return {
        "language": _LANGUAGE,
        "file_path": file_path,
        "symbols": symbols,
        "imports": imports,
    }
