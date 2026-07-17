# Repository Intelligence Layer — Architecture

## Overview

The Repository Intelligence Layer builds and caches a structured knowledge
model of a repository.  It runs once after repository ingestion and is
reused across all subsequent workflow executions.

---

## Data Flow Rule (enforced)

```
WorkflowEngine
       │
       ▼
IntelligenceManager   ← ONLY authorised entry point
       │
       ▼
PromptBuilder
       │
       ▼
LLM
```

**No component other than `IntelligenceManager` should read intelligence
JSON files directly.**  All JSON loading, caching, and version validation
happens inside `IntelligenceManager`.

---

## Versioning Strategy

Four independent version constants govern cache validity:

| Constant | Module | Triggers rebuild when… |
|---|---|---|
| `INTELLIGENCE_VERSION` | `versions.py` | Build pipeline changes |
| `PARSER_VERSION` | `parsers/__init__.py` | Any parser changes extraction |
| `SCHEMA_VERSION` | `versions.py` | Symbol/import/dep JSON schema changes |
| `FORMAT_VERSION` | `versions.py` | Output file layout changes |

All four must match for a cached bundle to be reused.
`repository_hash` is validated separately for content freshness.

`FORMAT_VERSION` is stored in the manifest but is **not** checked against
the cache.  It describes storage layout for future tooling, not runtime
cache validity.

---

## Output Files

Every build writes 9 JSON files to:

```
backend/data/repositories/{repository_id}/intelligence/
```

| File | Content |
|---|---|
| `manifest.json` | Self-describing build metadata |
| `file_tree.json` | All repository files with hash, size, mtime |
| `modules.json` | Parseable source files only |
| `symbols.json` | All extracted symbols (rich metadata) |
| `imports.json` | All import statements |
| `dependencies.json` | External package dependencies (deduplicated) |
| `statistics.json` | Aggregated counts |
| `errors.json` | Categorized parse / IO errors |
| `call_graph.json` | Call graph placeholder (Phase 8.3) |

---

## Symbol ID Format

```
{lang_prefix}:{file_path}:{name}:{type}
```

Examples:
```
py:backend/app/main.py:UserService:class
ts:frontend/src/App.tsx:IUser:interface
go:cmd/server/main.go:NewServer:function
rs:src/lib.rs:Config:struct
```

- Human-readable and debuggable
- Deterministic (same input → same ID)
- `id_hash` (SHA-256 of the id string) stored separately for fast equality

---

## Parser Architecture

```
parsers/
├── __init__.py         parse_file() dispatcher + PARSER_VERSION
├── python_parser.py    AST-based extraction
├── typescript_parser.py Regex-based
├── javascript_parser.py Delegates to TS parser (relabels language)
├── go_parser.py        Regex-based
└── rust_parser.py      Regex-based
```

Every parser exposes `parse(source_code: str, file_path: str) -> dict`.
The return dict always contains: `language`, `file_path`, `symbols`, `imports`.

---

## Per-File Hashing

Every source file in `file_tree.json` stores:

```json
{
  "path": "...",
  "sha256": "...",
  "size_bytes": 4096,
  "last_modified": 1721168000.0,
  "language": "python"
}
```

`last_modified` + `sha256` are the foundation for future incremental rebuilds.

---

## Error Handling

Parser failures are captured and categorized in `errors.json`:

```json
{
  "summary": {"total": 2, "by_category": {"ParserError": 1, "EncodingError": 1}},
  "errors": [...]
}
```

Error categories: `ParserError`, `IOError`, `EncodingError`, `UnsupportedLanguage`, `Timeout`

A build **always** completes successfully even if multiple files fail.
Failures are reported in `errors.json`; they never throw exceptions.

---

## Call Graph Placeholder

`call_graph.json` reserves the file for Phase 8.3:

```json
{
  "status": "not_built",
  "version": "v0",
  "generated_at": null,
  "nodes": [],
  "edges": [],
  "message": "Call graph will be built in Phase 8.3"
}
```

`status`, `version`, `generated_at` ensure future builders need no
migration logic.

---

## IntelligenceManager API

| Method | Description |
|---|---|
| `load(repo_id, intel_path, repo_hash)` | Load files into cache |
| `get(repo_id, section, repo_hash)` | Retrieve a section |
| `exists(repo_id)` | Check if any entry is cached |
| `validate(repo_id, repo_hash)` | Full 4-version + hash validation |
| `invalidate(repo_id)` | Evict from cache |
| `rebuild(repo_id, repo_path, intel_path, repo_hash)` | Force rebuild + reload |
| `refresh(repo_id, repo_path, intel_path, repo_hash)` | Validate first; rebuild if stale |
| `ensure_loaded(...)` | Backward-compat alias for `refresh()` |

Section aliases accepted by `get()`:
`manifest`, `file_tree` / `tree`, `modules`, `symbols`, `imports`,
`dependencies`, `statistics` / `stats`, `errors`, `call_graph` / `graph`.

---

## Future: Incremental Parsing (Phase 8.X)

With per-file `sha256` + `last_modified` already stored, incremental
rebuilds become straightforward:

1. Compute current `sha256` of each file.
2. Compare against stored `sha256` in `file_tree.json`.
3. Re-parse only changed files.
4. Merge results into existing JSON artifacts.
5. Update manifest hash and `generated_at`.

No architectural changes are required — the metadata is already there.

---

## Dependency Manifest Support

| File | Ecosystem |
|---|---|
| `requirements*.txt` | python |
| `pyproject.toml` | python |
| `package.json` | npm |
| `go.mod` | go |
| `Cargo.toml` | cargo |

Dependencies are deduplicated by `(name, ecosystem)`.
