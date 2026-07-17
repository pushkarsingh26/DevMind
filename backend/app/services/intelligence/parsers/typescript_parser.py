"""TypeScript / TSX source-file parser (regex-based).

Returns the standard parser result dict:
    language   – "typescript"
    file_path  – relative path supplied by the caller
    symbols    – list of SymbolRecord-compatible dicts
    imports    – list of ImportRecord-compatible dicts

Supported symbols: class, interface, enum, type_alias, function, method, constant
Visibility:        "public" if exported, "private" otherwise
IDs:               ``ts:{file_path}:{name}:{type}``
"""

import re
from typing import Any, Dict, List

from app.services.intelligence.models import SymbolRecord, ImportRecord

_LANGUAGE = "typescript"
_LANG_PREFIX = "ts"
PARSER_VERSION = "v1"

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_CLASS_RE       = re.compile(r"^(?P<exp>export\s+)?(?:abstract\s+)?class\s+(?P<n>\w+)", re.M)
_INTERFACE_RE   = re.compile(r"^(?P<exp>export\s+)?interface\s+(?P<n>\w+)", re.M)
_ENUM_RE        = re.compile(r"^(?P<exp>export\s+)?(?:const\s+)?enum\s+(?P<n>\w+)", re.M)
_TYPE_ALIAS_RE  = re.compile(r"^(?P<exp>export\s+)?type\s+(?P<n>\w+)\s*[=<]", re.M)
_FUNCTION_RE    = re.compile(r"^(?P<exp>export\s+)?(?:async\s+)?function\s+(?P<n>\w+)\s*[(<]", re.M)
_ARROW_FN_RE    = re.compile(r"^(?P<exp>export\s+)?(?:const|let|var)\s+(?P<n>\w+)\s*=\s*(?:async\s+)?\(", re.M)
_CONST_RE       = re.compile(r"^(?P<exp>export\s+)?const\s+(?P<n>[A-Z_][A-Z0-9_]{2,})\s*[=:]", re.M)
_METHOD_RE      = re.compile(r"^    (?:(?:public|private|protected|static|async|readonly|override)\s+)*(?P<n>\w+)\s*\(", re.M)

# Import patterns
_IMPORT_FROM_RE        = re.compile(r"^import\s+(?:type\s+)?(?:{[^}]*}|\w+|\*\s+as\s+\w+)\s+from\s+['\"](?P<m>[^'\"]+)['\"]", re.M)
_IMPORT_SIDE_EFFECT_RE = re.compile(r'^import\s+[\'"](?P<m>[^"\']+)[\'"]', re.M)
_REQUIRE_RE            = re.compile(r"require\s*\(\s*['\"](?P<m>[^'\"]+)['\"]\s*\)", re.M)
_EXPORT_FROM_RE        = re.compile(r"^export\s+(?:\*|{[^}]*})\s+from\s+['\"](?P<m>[^'\"]+)['\"]", re.M)

_NOISE_NAMES = frozenset({
    "if", "for", "while", "switch", "catch", "constructor",
    "return", "throw", "await", "yield", "else", "try",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _line_of(source: str, match: re.Match) -> int:
    return source[: match.start()].count("\n") + 1


def _visibility_from_export(match: re.Match) -> str:
    return "public" if match.group("exp") else "private"


def _make(name: str, sym_type: str, file_path: str, line: int, visibility: str) -> Dict[str, Any]:
    return SymbolRecord.make(
        name=name, sym_type=sym_type, file_path=file_path,
        language=_LANGUAGE, lang_prefix=_LANG_PREFIX,
        line_start=line, line_end=line,
        visibility=visibility,
    ).to_dict()


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

def _extract_symbols(source: str, file_path: str) -> List[Dict[str, Any]]:
    symbols: List[Dict[str, Any]] = []

    for m in _CLASS_RE.finditer(source):
        symbols.append(_make(m.group("n"), "class", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _INTERFACE_RE.finditer(source):
        symbols.append(_make(m.group("n"), "interface", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _ENUM_RE.finditer(source):
        symbols.append(_make(m.group("n"), "enum", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _TYPE_ALIAS_RE.finditer(source):
        symbols.append(_make(m.group("n"), "type_alias", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _FUNCTION_RE.finditer(source):
        symbols.append(_make(m.group("n"), "function", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _ARROW_FN_RE.finditer(source):
        name = m.group("n")
        if not name.isupper():
            symbols.append(_make(name, "function", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _CONST_RE.finditer(source):
        symbols.append(_make(m.group("n"), "constant", file_path, _line_of(source, m), _visibility_from_export(m)))

    for m in _METHOD_RE.finditer(source):
        name = m.group("n")
        if name not in _NOISE_NAMES:
            symbols.append(_make(name, "method", file_path, _line_of(source, m), "unknown"))

    return symbols


# ---------------------------------------------------------------------------
# Import extraction (deduplicated)
# ---------------------------------------------------------------------------

def _extract_imports(source: str, file_path: str) -> List[Dict[str, Any]]:
    seen: set = set()  # deduplicate by module name
    imports: List[Dict[str, Any]] = []

    def _add(module: str, line: int) -> None:
        if module in seen:
            return
        seen.add(module)
        imports.append(ImportRecord(
            module=module, name=None, alias=None,
            file=file_path, language=_LANGUAGE, line=line,
        ).to_dict())

    for m in _EXPORT_FROM_RE.finditer(source):
        _add(m.group("m"), _line_of(source, m))
    for m in _IMPORT_FROM_RE.finditer(source):
        _add(m.group("m"), _line_of(source, m))
    for m in _IMPORT_SIDE_EFFECT_RE.finditer(source):
        _add(m.group("m"), _line_of(source, m))
    for m in _REQUIRE_RE.finditer(source):
        _add(m.group("m"), _line_of(source, m))

    return imports


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source_code: str, file_path: str) -> Dict[str, Any]:
    """Parse a TypeScript/TSX source file."""
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
