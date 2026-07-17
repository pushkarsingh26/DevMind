"""Dataclass models for the Repository Intelligence layer.

These are plain Python dataclasses (no Pydantic dependency) so the
intelligence layer remains independent of the web framework.

All models support ``to_dict()`` for JSON serialization and
``from_dict()`` class methods for deserialization.
"""

from __future__ import annotations

import hashlib
import traceback as _tb
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_symbol_id(lang_prefix: str, file_path: str, name: str, sym_type: str) -> str:
    """Generate a human-readable, deterministic symbol ID.

    Format: ``{lang_prefix}:{file_path}:{name}:{sym_type}``

    Examples
    --------
    ``py:backend/app/main.py:UserService:class``
    ``ts:frontend/src/App.tsx:AppContext:interface``
    ``go:cmd/server/main.go:NewServer:function``
    ``rs:src/lib.rs:Config:struct``
    """
    # Normalise file path separators
    norm_path = file_path.replace("\\", "/")
    return f"{lang_prefix}:{norm_path}:{name}:{sym_type}"


# ---------------------------------------------------------------------------
# SymbolRecord
# ---------------------------------------------------------------------------

@dataclass
class SymbolRecord:
    """A code symbol extracted from a source file."""

    id: str                         # human-readable deterministic ID
    id_hash: str                    # SHA-256 of id (fast equality)
    name: str
    type: str                       # class | function | method | interface | enum | struct | trait | constant | type_alias
    module: str                     # file path (relative to repo root)
    file: str                       # same as module (kept for backward compat)
    language: str
    line_start: int
    line_end: int                   # same as line_start when not computable
    parent: Optional[str] = None
    visibility: str = "unknown"     # public | private | protected | unknown

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SymbolRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def make(
        cls,
        name: str,
        sym_type: str,
        file_path: str,
        language: str,
        line_start: int,
        line_end: Optional[int] = None,
        parent: Optional[str] = None,
        visibility: str = "unknown",
        lang_prefix: Optional[str] = None,
    ) -> "SymbolRecord":
        """Factory that auto-generates id and id_hash."""
        prefix = lang_prefix or language[:2]
        sym_id = _make_symbol_id(prefix, file_path, name, sym_type)
        sym_id_hash = hashlib.sha256(sym_id.encode()).hexdigest()
        return cls(
            id=sym_id,
            id_hash=sym_id_hash,
            name=name,
            type=sym_type,
            module=file_path.replace("\\", "/"),
            file=file_path.replace("\\", "/"),
            language=language,
            line_start=line_start,
            line_end=line_end if line_end is not None else line_start,
            parent=parent,
            visibility=visibility,
        )


# ---------------------------------------------------------------------------
# ImportRecord
# ---------------------------------------------------------------------------

@dataclass
class ImportRecord:
    """An import statement found in a source file."""

    module: str
    name: Optional[str]             # specific name if ``from X import Y``
    alias: Optional[str]            # ``as`` alias
    file: str
    language: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ImportRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# DependencyRecord
# ---------------------------------------------------------------------------

@dataclass
class DependencyRecord:
    """An external package dependency found in a manifest file."""

    name: str
    version: str
    ecosystem: str      # python | npm | go | cargo
    file: str           # manifest file path

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DependencyRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# FileHashRecord
# ---------------------------------------------------------------------------

@dataclass
class FileHashRecord:
    """Hashing and size metadata for a single source file."""

    path: str           # relative to repo root
    sha256: str         # hex digest of file content
    size_bytes: int
    last_modified: float    # Unix timestamp (mtime)
    language: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# ParseResult
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """Result of parsing a single source file."""

    language: str
    file_path: str
    symbols: List[SymbolRecord] = field(default_factory=list)
    imports: List[ImportRecord] = field(default_factory=list)
    file_hash: Optional[str] = None


# ---------------------------------------------------------------------------
# ParseError (categorized)
# ---------------------------------------------------------------------------

@dataclass
class ParseError:
    """A captured parser or IO failure."""

    category: str       # ParserError | IOError | EncodingError | UnsupportedLanguage | Timeout
    file: str
    language: str
    parser: str         # module name of the parser that failed
    exception: str      # str(exc)
    traceback: str      # formatted traceback or ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_exc(
        cls,
        category: str,
        file: str,
        language: str,
        parser: str,
        exc: Exception,
        include_traceback: bool = True,
    ) -> "ParseError":
        tb = _tb.format_exc() if include_traceback else ""
        return cls(
            category=category,
            file=file,
            language=language,
            parser=parser,
            exception=str(exc),
            traceback=tb.strip(),
        )


# ---------------------------------------------------------------------------
# Call Graph Foundation (placeholder)
# ---------------------------------------------------------------------------

@dataclass
class CallGraphNode:
    """Placeholder node for a future call graph."""
    id: str
    name: str
    file: str
    line: int
    language: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CallGraphEdge:
    """Placeholder edge for a future call graph."""
    caller_id: str
    callee_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CallGraphPlaceholder:
    """Serializable placeholder written to call_graph.json.

    The ``status``, ``version``, and ``generated_at`` fields allow future
    builders to detect whether a real call graph exists without migration.
    """
    status: str = "not_built"
    version: str = "v0"
    generated_at: Optional[str] = None
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    message: str = "Call graph will be built in Phase 8.3"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
