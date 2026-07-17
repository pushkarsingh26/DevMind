"""Go source-file parser (regex-based).

Returns the standard parser result dict:
    language   – "go"
    file_path  – relative path supplied by the caller
    symbols    – list of SymbolRecord-compatible dicts
    imports    – list of ImportRecord-compatible dicts

Supported symbols: struct, interface, function, method
Visibility:        "public" if name starts with uppercase, "private" otherwise
IDs:               ``go:{file_path}:{name}:{type}``
"""

import re
from typing import Any, Dict, List

from app.services.intelligence.models import SymbolRecord, ImportRecord

_LANGUAGE = "go"
_LANG_PREFIX = "go"
PARSER_VERSION = "v1"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_STRUCT_RE    = re.compile(r"^type\s+(?P<n>\w+)\s+struct\s*{", re.M)
_INTERFACE_RE = re.compile(r"^type\s+(?P<n>\w+)\s+interface\s*{", re.M)
# Methods: func (recv *Type) MethodName(
_METHOD_RE    = re.compile(r"^func\s+\(\s*\w+\s+\*?\w+\s*\)\s+(?P<n>\w+)\s*\(", re.M)
# Top-level functions: func FuncName(
_FUNCTION_RE  = re.compile(r"^func\s+(?P<n>\w+)\s*\(", re.M)

# Imports
_IMPORT_SINGLE_RE = re.compile(r'^import\s+"(?P<m>[^"]+)"', re.M)
_IMPORT_BLOCK_PKG = re.compile(r'"(?P<m>[^"]+)"')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _line_of(source: str, match: re.Match) -> int:
    return source[: match.start()].count("\n") + 1


def _go_visibility(name: str) -> str:
    """In Go, exported names start with an uppercase letter."""
    return "public" if name and name[0].isupper() else "private"


def _make(name: str, sym_type: str, file_path: str, line: int) -> Dict[str, Any]:
    return SymbolRecord.make(
        name=name, sym_type=sym_type, file_path=file_path,
        language=_LANGUAGE, lang_prefix=_LANG_PREFIX,
        line_start=line, line_end=line,
        visibility=_go_visibility(name),
    ).to_dict()


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

def _extract_symbols(source: str, file_path: str) -> List[Dict[str, Any]]:
    symbols: List[Dict[str, Any]] = []

    for m in _STRUCT_RE.finditer(source):
        symbols.append(_make(m.group("n"), "struct", file_path, _line_of(source, m)))

    for m in _INTERFACE_RE.finditer(source):
        symbols.append(_make(m.group("n"), "interface", file_path, _line_of(source, m)))

    method_starts = {m.start() for m in _METHOD_RE.finditer(source)}

    for m in _METHOD_RE.finditer(source):
        symbols.append(_make(m.group("n"), "method", file_path, _line_of(source, m)))

    for m in _FUNCTION_RE.finditer(source):
        if m.start() not in method_starts:
            symbols.append(_make(m.group("n"), "function", file_path, _line_of(source, m)))

    return symbols


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------

def _extract_imports(source: str, file_path: str) -> List[Dict[str, Any]]:
    seen: set = set()
    imports: List[Dict[str, Any]] = []

    def _add(module: str, line: int) -> None:
        if module in seen:
            return
        seen.add(module)
        imports.append(ImportRecord(
            module=module, name=None, alias=None,
            file=file_path, language=_LANGUAGE, line=line,
        ).to_dict())

    # Block imports: import ( "pkg1"\n "pkg2" )
    block_re = re.compile(r"import\s*\((?P<body>[^)]+)\)", re.S)
    for block_m in block_re.finditer(source):
        block_line = source[: block_m.start()].count("\n") + 1
        for pkg_m in _IMPORT_BLOCK_PKG.finditer(block_m.group("body")):
            offset_line = block_m.group("body")[: pkg_m.start()].count("\n")
            _add(pkg_m.group("m"), block_line + offset_line)

    # Single-line imports
    for m in _IMPORT_SINGLE_RE.finditer(source):
        _add(m.group("m"), _line_of(source, m))

    return imports


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source_code: str, file_path: str) -> Dict[str, Any]:
    """Parse a Go source file."""
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
