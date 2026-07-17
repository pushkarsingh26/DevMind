"""Repository Intelligence Service.

Responsibilities
----------------
- Build file tree (with per-file SHA-256, size, mtime)
- Build module index
- Build symbol index (via language parsers — rich metadata)
- Build import graph
- Build dependency graph (pip, npm, go, cargo)
- Build repository statistics
- Build call graph placeholder
- Capture and categorize parser/IO errors
- Generate self-describing manifest
- Save all JSON artifacts to disk

This service intentionally does NOT:
- Generate embeddings
- Chunk files
- Execute RAG
- Call any LLM

Output directory layout
-----------------------
backend/data/repositories/{repository_id}/intelligence/
    manifest.json      – self-describing build metadata
    file_tree.json     – all repository files with hashes
    modules.json       – parseable source files only
    symbols.json       – all extracted symbols (rich metadata)
    imports.json       – all import statements
    dependencies.json  – external package dependencies
    statistics.json    – aggregated counts and lists
    errors.json        – categorized parse / IO errors
    call_graph.json    – call graph placeholder (Phase 8.3)
"""

from __future__ import annotations

import json
import os
import re as _re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.intelligence.call_graph import build_placeholder as _build_call_graph
from app.services.intelligence.file_hasher import hash_dir, hash_source
from app.services.intelligence.models import ParseError
from app.services.intelligence.parsers import (
    PARSER_VERSION,
    get_language,
    parse_file,
    supported_extensions,
)
from app.services.intelligence.versions import (
    FORMAT_VERSION,
    GENERATOR_NAME,
    GENERATOR_VERSION,
    INTELLIGENCE_VERSION,
    REQUIRED_FILES,
    SCHEMA_VERSION,
    SUPPORTED_LANGUAGES,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_LANG_MAP: Dict[str, str] = {
    ".py":  "python",
    ".ts":  "typescript",
    ".tsx": "typescript",
    ".js":  "javascript",
    ".jsx": "javascript",
    ".go":  "go",
    ".rs":  "rust",
}

_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".next", ".nuxt",
    "target",
}

_SKIP_EXTS = {
    ".pyc", ".pyo", ".class", ".o", ".a", ".so", ".dll", ".exe",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".lock",
}

_LARGEST_FILES_N = 10
_MAX_PARSE_BYTES = 1_000_000   # 1 MB per file


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    logger.debug(f"[IntelligenceService] Wrote {path.name} ({path})")


def _read_source(path: Path) -> Optional[str]:
    """Read a source file respecting size limit. Returns None on failure."""
    try:
        if path.stat().st_size > _MAX_PARSE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _dedup_deps(deps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate dependency records by (name, ecosystem)."""
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for d in deps:
        key = (d.get("name", "").lower(), d.get("ecosystem", ""))
        if key not in seen:
            seen.add(key)
            result.append(d)
    return result


# ---------------------------------------------------------------------------
# IntelligenceService
# ---------------------------------------------------------------------------

class IntelligenceService:
    """Build and persist repository intelligence JSON files.

    Public interface
    ----------------
    build_intelligence(repo_path, repo_id, repo_hash) → dict
        Run the full build and return metadata about the output.

    No other methods are public.  IntelligenceManager is the only
    authorised consumer of the output artifacts.
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def build_intelligence(
        self,
        repo_path: str,
        repo_id: str,
        repo_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the full intelligence build for a repository.

        Parameters
        ----------
        repo_path:
            Absolute path to the repository root on disk.
        repo_id:
            Unique repository identifier (DB primary key).
        repo_hash:
            Pre-computed repository hash.  If not provided, one is
            computed from the directory contents.

        Returns
        -------
        dict with keys:
            intelligence_path  – absolute path to the output directory
            build_time_ms      – elapsed build time in milliseconds
            repo_hash          – the hash embedded in manifest.json
        """
        start_ms = int(time.time() * 1000)
        root = Path(repo_path).resolve()

        if not root.is_dir():
            raise ValueError(f"Repository path does not exist: {root}")

        if not repo_hash:
            repo_hash = hash_dir(root, _SKIP_DIRS, _SKIP_EXTS)

        intel_dir = (
            Path("backend") / "data" / "repositories" / repo_id / "intelligence"
        ).resolve()
        intel_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[IntelligenceService] Building intelligence for {repo_id} → {intel_dir}")

        # --- Build steps ---
        file_tree = self._build_file_tree(root)
        modules = self._build_modules(file_tree)
        symbols, imports, errors = self._build_symbols_and_imports(root, modules)
        dependencies = self._build_dependencies(root, file_tree)
        statistics = self._build_statistics(file_tree, modules, symbols, imports, dependencies)
        call_graph = _build_call_graph(symbols, imports)
        errors_doc = self._build_errors_doc(errors)

        # --- Persist ---
        _write_json(intel_dir / "file_tree.json", file_tree)
        _write_json(intel_dir / "modules.json", modules)
        _write_json(intel_dir / "symbols.json", symbols)
        _write_json(intel_dir / "imports.json", imports)
        _write_json(intel_dir / "dependencies.json", dependencies)
        _write_json(intel_dir / "statistics.json", statistics)
        _write_json(intel_dir / "errors.json", errors_doc)
        _write_json(intel_dir / "call_graph.json", call_graph)

        build_time_ms = int(time.time() * 1000) - start_ms

        manifest = self._build_manifest(
            repo_id=repo_id,
            repo_hash=repo_hash,
            build_time_ms=build_time_ms,
            statistics=statistics,
            parsed_files=len(modules),
            failed_files=len(errors),
        )
        _write_json(intel_dir / "manifest.json", manifest)

        logger.info(
            f"[IntelligenceService] Done – {repo_id} in {build_time_ms} ms "
            f"| files={len(file_tree)} symbols={len(symbols)} "
            f"errors={len(errors)}"
        )

        return {
            "intelligence_path": str(intel_dir),
            "build_time_ms": build_time_ms,
            "repo_hash": repo_hash,
        }

    # ------------------------------------------------------------------
    # Build steps (private)
    # ------------------------------------------------------------------

    def _build_file_tree(self, root: Path) -> List[Dict[str, Any]]:
        """Walk repository and return file entries with per-file hash metadata."""
        entries: List[Dict[str, Any]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
            for name in sorted(filenames):
                full = Path(dirpath) / name
                ext = full.suffix.lower()
                if ext in _SKIP_EXTS:
                    continue
                rel = full.relative_to(root).as_posix()
                language = _LANG_MAP.get(ext, "other")

                # Per-file metadata
                try:
                    stat = full.stat()
                    size = stat.st_size
                    mtime = stat.st_mtime
                except OSError:
                    size = 0
                    mtime = 0.0

                # SHA-256 only for source files (skip binaries, etc.)
                sha256 = ""
                if ext in _LANG_MAP or ext in {".json", ".yaml", ".yml", ".toml", ".md"}:
                    try:
                        sha256 = hash_source(full.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        pass

                entries.append({
                    "path": rel,
                    "extension": ext,
                    "size_bytes": size,
                    "last_modified": mtime,
                    "sha256": sha256,
                    "language": language,
                })
        return entries

    def _build_modules(self, file_tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter file_tree to parseable source files only."""
        supported = set(supported_extensions())
        return [f for f in file_tree if f["extension"] in supported]

    def _build_symbols_and_imports(
        self,
        root: Path,
        modules: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[ParseError]]:
        """Parse every module file; collect symbols, imports, and errors."""
        all_symbols: List[Dict[str, Any]] = []
        all_imports: List[Dict[str, Any]] = []
        errors: List[ParseError] = []

        for mod in modules:
            full_path = root / mod["path"]
            lang = mod.get("language", "unknown")
            parser_name = f"{lang}_parser"

            # --- IO / encoding errors ---
            try:
                if full_path.stat().st_size > _MAX_PARSE_BYTES:
                    errors.append(ParseError.from_exc(
                        category="UnsupportedLanguage",
                        file=mod["path"],
                        language=lang,
                        parser=parser_name,
                        exc=Exception(f"File too large: {full_path.stat().st_size} bytes"),
                        include_traceback=False,
                    ))
                    continue
                source = full_path.read_text(encoding="utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                errors.append(ParseError.from_exc(
                    category="EncodingError",
                    file=mod["path"], language=lang,
                    parser=parser_name, exc=exc,
                ))
                continue
            except OSError as exc:
                errors.append(ParseError.from_exc(
                    category="IOError",
                    file=mod["path"], language=lang,
                    parser=parser_name, exc=exc,
                ))
                continue

            # --- Parser errors ---
            try:
                result = parse_file(mod["path"], source)
            except Exception as exc:
                errors.append(ParseError.from_exc(
                    category="ParserError",
                    file=mod["path"], language=lang,
                    parser=parser_name, exc=exc,
                ))
                continue

            all_symbols.extend(result.get("symbols", []))
            all_imports.extend(result.get("imports", []))

        return all_symbols, all_imports, errors

    def _build_dependencies(
        self,
        root: Path,
        file_tree: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Parse dependency manifests; return deduplicated list."""
        deps: List[Dict[str, Any]] = []
        manifest_files = {f["path"] for f in file_tree}

        # Python: requirements*.txt
        REQ_LINE = _re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*([=<>!~^,][^\s#]*)?\s*(?:#.*)?$")
        for path_str in sorted(manifest_files):
            fname = Path(path_str).name.lower()
            if fname == "requirements.txt" or (fname.startswith("requirements") and fname.endswith(".txt")):
                try:
                    for line in (root / path_str).read_text(encoding="utf-8", errors="replace").splitlines():
                        m = REQ_LINE.match(line)
                        if m and not line.strip().startswith("-"):
                            deps.append({"name": m.group(1), "version": (m.group(2) or "").strip(),
                                         "ecosystem": "python", "file": path_str})
                except OSError:
                    pass

        # Python: pyproject.toml
        if "pyproject.toml" in manifest_files:
            tomllib = _try_import_tomllib()
            if tomllib:
                try:
                    with (root / "pyproject.toml").open("rb") as fh:
                        data = tomllib.load(fh)
                    for dep in data.get("project", {}).get("dependencies", []):
                        name = _re.split(r"[>=<!^~\s]", dep)[0].strip()
                        if name:
                            deps.append({"name": name, "version": "", "ecosystem": "python", "file": "pyproject.toml"})
                except Exception:
                    pass

        # Node: package.json
        if "package.json" in manifest_files:
            try:
                pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
                for section in ("dependencies", "devDependencies", "peerDependencies"):
                    for name, ver in pkg.get(section, {}).items():
                        deps.append({"name": name, "version": ver, "ecosystem": "npm", "file": "package.json"})
            except Exception:
                pass

        # Go: go.mod
        if "go.mod" in manifest_files:
            REQUIRE_LINE = _re.compile(r"^\s*([^\s]+)\s+([^\s]+)")
            in_require = False
            try:
                for line in (root / "go.mod").read_text(encoding="utf-8", errors="replace").splitlines():
                    stripped = line.strip()
                    if stripped in {"require (", "require("}:
                        in_require = True
                        continue
                    if in_require:
                        if stripped == ")":
                            in_require = False
                            continue
                        m = REQUIRE_LINE.match(stripped)
                        if m:
                            deps.append({"name": m.group(1), "version": m.group(2), "ecosystem": "go", "file": "go.mod"})
                    elif stripped.startswith("require "):
                        m = REQUIRE_LINE.match(stripped[8:])
                        if m:
                            deps.append({"name": m.group(1), "version": m.group(2), "ecosystem": "go", "file": "go.mod"})
            except OSError:
                pass

        # Rust: Cargo.toml
        if "Cargo.toml" in manifest_files:
            tomllib = _try_import_tomllib()
            if tomllib:
                try:
                    with (root / "Cargo.toml").open("rb") as fh:
                        cargo = tomllib.load(fh)
                    for name, ver in cargo.get("dependencies", {}).items():
                        if isinstance(ver, dict):
                            ver = ver.get("version", "")
                        deps.append({"name": name, "version": str(ver), "ecosystem": "cargo", "file": "Cargo.toml"})
                except Exception:
                    pass

        return _dedup_deps(deps)

    def _build_statistics(
        self,
        file_tree: List[Dict[str, Any]],
        modules: List[Dict[str, Any]],
        symbols: List[Dict[str, Any]],
        imports: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        lang_counts: Dict[str, int] = defaultdict(int)
        for f in modules:
            lang_counts[f["language"]] += 1

        languages = sorted(lang_counts.keys())
        largest = sorted(modules, key=lambda f: f["size_bytes"], reverse=True)[:_LARGEST_FILES_N]
        entry_names = {"main.py", "main.go", "main.rs", "index.js", "index.ts", "app.py", "server.py"}
        entry_points = [f["path"] for f in file_tree if Path(f["path"]).name.lower() in entry_names]

        return {
            "languages": languages,
            "language_file_counts": dict(lang_counts),
            "total_files": len(file_tree),
            "source_files": len(modules),
            "classes": sum(1 for s in symbols if s.get("type") == "class"),
            "functions": sum(1 for s in symbols if s.get("type") == "function"),
            "methods": sum(1 for s in symbols if s.get("type") == "method"),
            "structs": sum(1 for s in symbols if s.get("type") == "struct"),
            "interfaces": sum(1 for s in symbols if s.get("type") == "interface"),
            "enums": sum(1 for s in symbols if s.get("type") == "enum"),
            "traits": sum(1 for s in symbols if s.get("type") == "trait"),
            "constants": sum(1 for s in symbols if s.get("type") == "constant"),
            "total_symbols": len(symbols),
            "total_imports": len(imports),
            "total_dependencies": len(dependencies),
            "largest_files": [f["path"] for f in largest],
            "entry_points": entry_points,
        }

    def _build_errors_doc(self, errors: List[ParseError]) -> Dict[str, Any]:
        """Produce the categorized errors.json structure."""
        by_category: Dict[str, int] = defaultdict(int)
        for e in errors:
            by_category[e.category] += 1
        return {
            "summary": {
                "total": len(errors),
                "by_category": dict(by_category),
            },
            "errors": [e.to_dict() for e in errors],
        }

    def _build_manifest(
        self,
        repo_id: str,
        repo_hash: str,
        build_time_ms: int,
        statistics: Dict[str, Any],
        parsed_files: int,
        failed_files: int,
    ) -> Dict[str, Any]:
        return {
            "repository_id": repo_id,
            "repository_hash": repo_hash,
            "intelligence_version": INTELLIGENCE_VERSION,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "format_version": FORMAT_VERSION,
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "build_time_ms": build_time_ms,
            "supported_languages": SUPPORTED_LANGUAGES,
            "total_files": statistics.get("total_files", 0),
            "parsed_files": parsed_files,
            "failed_files": failed_files,
            "total_symbols": statistics.get("total_symbols", 0),
            "total_imports": statistics.get("total_imports", 0),
            "total_dependencies": statistics.get("total_dependencies", 0),
        }


# ---------------------------------------------------------------------------
# TOML loader (optional dependency)
# ---------------------------------------------------------------------------

def _try_import_tomllib():
    try:
        import tomllib
        return tomllib
    except ImportError:
        pass
    try:
        import tomli as tomllib  # type: ignore[no-redef]
        return tomllib
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

intelligence_service = IntelligenceService()
