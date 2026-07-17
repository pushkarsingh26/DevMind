"""Python source-file parser using the standard ``ast`` module.

Returns the standard parser result dict:
    language   – "python"
    file_path  – relative path supplied by the caller
    symbols    – list of SymbolRecord-compatible dicts
    imports    – list of ImportRecord-compatible dicts

Supported symbols: class, function, method, constant
Visibility:        public (no leading underscore) | private (_ prefix)
IDs:               human-readable deterministic format
                   ``py:{file_path}:{name}:{type}``
"""

import ast
from typing import Any, Dict, List, Optional

from app.services.intelligence.models import SymbolRecord, ImportRecord

_LANGUAGE = "python"
_LANG_PREFIX = "py"
PARSER_VERSION = "v1"

# ---------------------------------------------------------------------------
# Visibility detection
# ---------------------------------------------------------------------------

def _visibility(name: str) -> str:
    if name.startswith("__") and name.endswith("__"):
        return "public"   # dunder methods are part of the public protocol
    if name.startswith("_"):
        return "private"
    return "public"


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

def _extract_symbols(
    node: ast.AST,
    file_path: str,
    parent: Optional[str] = None,
) -> List[Dict[str, Any]]:
    symbols: List[Dict[str, Any]] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            r = SymbolRecord.make(
                name=child.name,
                sym_type="class",
                file_path=file_path,
                language=_LANGUAGE,
                lang_prefix=_LANG_PREFIX,
                line_start=child.lineno,
                line_end=getattr(child, "end_lineno", child.lineno),
                parent=parent,
                visibility=_visibility(child.name),
            )
            symbols.append(r.to_dict())
            symbols.extend(_extract_symbols(child, file_path, parent=child.name))

        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sym_type = "method" if parent else "function"
            r = SymbolRecord.make(
                name=child.name,
                sym_type=sym_type,
                file_path=file_path,
                language=_LANGUAGE,
                lang_prefix=_LANG_PREFIX,
                line_start=child.lineno,
                line_end=getattr(child, "end_lineno", child.lineno),
                parent=parent,
                visibility=_visibility(child.name),
            )
            symbols.append(r.to_dict())
            symbols.extend(_extract_symbols(child, file_path, parent=parent))

        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    r = SymbolRecord.make(
                        name=target.id,
                        sym_type="constant",
                        file_path=file_path,
                        language=_LANGUAGE,
                        lang_prefix=_LANG_PREFIX,
                        line_start=child.lineno,
                        line_end=getattr(child, "end_lineno", child.lineno),
                        parent=parent,
                        visibility="public",
                    )
                    symbols.append(r.to_dict())
        else:
            symbols.extend(_extract_symbols(child, file_path, parent=parent))
    return symbols


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------

def _extract_imports(node: ast.AST, file_path: str) -> List[Dict[str, Any]]:
    imports: List[Dict[str, Any]] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                r = ImportRecord(
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    file=file_path,
                    language=_LANGUAGE,
                    line=child.lineno,
                )
                imports.append(r.to_dict())
        elif isinstance(child, ast.ImportFrom):
            module = child.module or ""
            for alias in child.names:
                r = ImportRecord(
                    module=module,
                    name=alias.name,
                    alias=alias.asname,
                    file=file_path,
                    language=_LANGUAGE,
                    line=child.lineno,
                )
                imports.append(r.to_dict())
    return imports


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source_code: str, file_path: str) -> Dict[str, Any]:
    """Parse a Python source file.

    Returns
    -------
    dict with keys: language, file_path, symbols, imports
    """
    try:
        tree = ast.parse(source_code, filename=file_path)
        symbols = _extract_symbols(tree, file_path)
        imports = _extract_imports(tree, file_path)
    except SyntaxError:
        symbols = []
        imports = []

    return {
        "language": _LANGUAGE,
        "file_path": file_path,
        "symbols": symbols,
        "imports": imports,
    }
