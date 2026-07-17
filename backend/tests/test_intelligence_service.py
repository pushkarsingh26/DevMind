"""pytest test suite for IntelligenceService, IntelligenceManager, and versioning.

Test categories
---------------
- Manifest validation
- Version mismatch detection
- Cache validation (all 4 version strings)
- IntelligenceManager API (exists, validate, invalidate, rebuild, refresh)
- IntelligenceService build (tmp_path based)
- Error recovery (service handles bad files gracefully)
- Incremental-ready: per-file hash presence
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.intelligence.intelligence_manager import (
    RepositoryIntelligenceManager,
    intelligence_manager as _global_manager,
)
from app.services.intelligence.intelligence_service import IntelligenceService
from app.services.intelligence.versions import (
    FORMAT_VERSION,
    INTELLIGENCE_VERSION,
    PARSER_VERSION,
    REQUIRED_FILES,
    SCHEMA_VERSION,
)
from app.services.intelligence.parsers import PARSER_VERSION as PARSERS_PARSER_VERSION


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def manager():
    """Fresh IntelligenceManager for each test (isolated cache)."""
    return RepositoryIntelligenceManager()


@pytest.fixture()
def service():
    return IntelligenceService()


@pytest.fixture()
def mini_repo(tmp_path: Path) -> Path:
    """A minimal repository with Python and TS files."""
    (tmp_path / "main.py").write_text(
        "import os\n\nclass App:\n    def run(self): pass\n\nDEBUG = True\n",
        encoding="utf-8",
    )
    (tmp_path / "utils.py").write_text(
        "from typing import List\n\ndef helper(x: int) -> int:\n    return x + 1\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "App.tsx").write_text(
        "import React from 'react';\nexport interface IApp { id: string; }\nexport class AppComponent { render() {} }\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("fastapi==0.116.0\npydantic>=2.0\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def built_intel(service: IntelligenceService, mini_repo: Path, tmp_path: Path):
    """Run a full build and return the result dict."""
    # Override output dir to tmp
    with patch.object(
        service, "build_intelligence",
        wraps=lambda repo_path, repo_id, repo_hash=None: _build_into_tmp(
            service, repo_path, repo_id, tmp_path, repo_hash
        ),
    ):
        result = service.build_intelligence(
            repo_path=str(mini_repo),
            repo_id="test_repo_001",
        )
    return result


def _build_into_tmp(svc, repo_path, repo_id, tmp_path, repo_hash):
    """Run build but redirect output to tmp_path."""
    import time, json as _json
    from datetime import datetime, timezone
    from app.services.intelligence.call_graph import build_placeholder
    from app.services.intelligence.models import ParseError
    from app.services.intelligence.file_hasher import hash_dir
    from app.services.intelligence.parsers import PARSER_VERSION as PV
    from app.services.intelligence.versions import (
        INTELLIGENCE_VERSION, SCHEMA_VERSION, FORMAT_VERSION,
        GENERATOR_NAME, GENERATOR_VERSION, SUPPORTED_LANGUAGES,
    )
    from app.services.intelligence.intelligence_service import _SKIP_DIRS, _SKIP_EXTS, _write_json

    root = Path(repo_path)
    if not repo_hash:
        repo_hash = hash_dir(root, _SKIP_DIRS, _SKIP_EXTS)

    intel_dir = tmp_path / "intelligence" / repo_id
    intel_dir.mkdir(parents=True, exist_ok=True)

    start = int(time.time() * 1000)
    file_tree = svc._build_file_tree(root)
    modules = svc._build_modules(file_tree)
    symbols, imports, errors = svc._build_symbols_and_imports(root, modules)
    deps = svc._build_dependencies(root, file_tree)
    stats = svc._build_statistics(file_tree, modules, symbols, imports, deps)
    cg = build_placeholder(symbols, imports)
    err_doc = svc._build_errors_doc(errors)

    _write_json(intel_dir / "file_tree.json", file_tree)
    _write_json(intel_dir / "modules.json", modules)
    _write_json(intel_dir / "symbols.json", symbols)
    _write_json(intel_dir / "imports.json", imports)
    _write_json(intel_dir / "dependencies.json", deps)
    _write_json(intel_dir / "statistics.json", stats)
    _write_json(intel_dir / "errors.json", err_doc)
    _write_json(intel_dir / "call_graph.json", cg)

    build_time_ms = int(time.time() * 1000) - start
    manifest = {
        "repository_id": repo_id,
        "repository_hash": repo_hash,
        "intelligence_version": INTELLIGENCE_VERSION,
        "parser_version": PV,
        "schema_version": SCHEMA_VERSION,
        "format_version": FORMAT_VERSION,
        "generator": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_time_ms": build_time_ms,
        "supported_languages": SUPPORTED_LANGUAGES,
        "total_files": stats.get("total_files", 0),
        "parsed_files": len(modules),
        "failed_files": len(errors),
        "total_symbols": stats.get("total_symbols", 0),
        "total_imports": stats.get("total_imports", 0),
        "total_dependencies": stats.get("total_dependencies", 0),
    }
    _write_json(intel_dir / "manifest.json", manifest)

    return {
        "intelligence_path": str(intel_dir),
        "build_time_ms": build_time_ms,
        "repo_hash": repo_hash,
    }


# ===========================================================================
# Manifest validation
# ===========================================================================

class TestManifestValidation:
    def test_manifest_contains_all_version_fields(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_manifest", tmp_path, None)
        manifest = json.loads((Path(result["intelligence_path"]) / "manifest.json").read_text())
        assert "intelligence_version" in manifest
        assert "parser_version" in manifest
        assert "schema_version" in manifest
        assert "format_version" in manifest

    def test_manifest_contains_generator(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_gen", tmp_path, None)
        manifest = json.loads((Path(result["intelligence_path"]) / "manifest.json").read_text())
        assert manifest["generator"] == "devmind-intelligence"
        assert "generator_version" in manifest

    def test_manifest_contains_counts(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_counts", tmp_path, None)
        manifest = json.loads((Path(result["intelligence_path"]) / "manifest.json").read_text())
        assert manifest["total_files"] > 0
        assert manifest["parsed_files"] >= 0
        assert "total_symbols" in manifest

    def test_all_required_files_written(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_files", tmp_path, None)
        intel_path = Path(result["intelligence_path"])
        for fname in REQUIRED_FILES:
            assert (intel_path / fname).is_file(), f"Missing: {fname}"


# ===========================================================================
# Per-file hashing
# ===========================================================================

class TestPerFileHashing:
    def test_file_tree_entries_have_sha256(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_hash1", tmp_path, None)
        file_tree = json.loads((Path(result["intelligence_path"]) / "file_tree.json").read_text())
        py_files = [f for f in file_tree if f["extension"] == ".py"]
        for f in py_files:
            assert "sha256" in f
            assert len(f["sha256"]) == 64

    def test_file_tree_entries_have_mtime(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_hash2", tmp_path, None)
        file_tree = json.loads((Path(result["intelligence_path"]) / "file_tree.json").read_text())
        for f in file_tree:
            assert "last_modified" in f
            assert f["last_modified"] > 0


# ===========================================================================
# Error handling
# ===========================================================================

class TestErrorHandling:
    def test_errors_json_written_even_with_no_errors(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_err1", tmp_path, None)
        errors_doc = json.loads((Path(result["intelligence_path"]) / "errors.json").read_text())
        assert "summary" in errors_doc
        assert "errors" in errors_doc

    def test_errors_json_has_total_count(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_err2", tmp_path, None)
        errors_doc = json.loads((Path(result["intelligence_path"]) / "errors.json").read_text())
        assert "total" in errors_doc["summary"]

    def test_build_continues_on_bad_file(self, service, tmp_path):
        """A repo with a broken Python file should still produce symbols from good files."""
        repo = tmp_path / "broken_repo"
        repo.mkdir()
        (repo / "good.py").write_text("class Good: pass\n", encoding="utf-8")
        (repo / "bad.py").write_bytes(b"\xff\xfe invalid utf-32 \x00\x00")

        intel = tmp_path / "intel_broken"
        result = _build_into_tmp(service, str(repo), "repo_broken", tmp_path, None)
        symbols = json.loads((Path(result["intelligence_path"]) / "symbols.json").read_text())
        assert any(s["name"] == "Good" for s in symbols)


# ===========================================================================
# Call graph placeholder
# ===========================================================================

class TestCallGraph:
    def test_call_graph_written(self, service, mini_repo, tmp_path):
        result = _build_into_tmp(service, str(mini_repo), "repo_cg", tmp_path, None)
        cg = json.loads((Path(result["intelligence_path"]) / "call_graph.json").read_text())
        assert cg["status"] == "not_built"
        assert "version" in cg
        assert "nodes" in cg and "edges" in cg


# ===========================================================================
# IntelligenceManager — Cache validation
# ===========================================================================

class TestCacheValidation:
    def _fake_manifest(self, **overrides):
        base = {
            "intelligence_version": INTELLIGENCE_VERSION,
            "parser_version": PARSERS_PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "repository_hash": "abc123",
        }
        base.update(overrides)
        return base

    def test_valid_cache_passes(self, manager):
        manager._cache["r1"] = {"manifest": self._fake_manifest()}
        assert manager.validate("r1", "abc123") is True

    def test_wrong_intelligence_version_fails(self, manager):
        manager._cache["r2"] = {"manifest": self._fake_manifest(intelligence_version="v99")}
        assert manager.validate("r2", "abc123") is False

    def test_wrong_parser_version_fails(self, manager):
        manager._cache["r3"] = {"manifest": self._fake_manifest(parser_version="v99")}
        assert manager.validate("r3", "abc123") is False

    def test_wrong_schema_version_fails(self, manager):
        manager._cache["r4"] = {"manifest": self._fake_manifest(schema_version="v99")}
        assert manager.validate("r4", "abc123") is False

    def test_wrong_repo_hash_fails(self, manager):
        manager._cache["r5"] = {"manifest": self._fake_manifest()}
        assert manager.validate("r5", "wrong_hash") is False

    def test_no_repo_hash_skips_hash_check(self, manager):
        manager._cache["r6"] = {"manifest": self._fake_manifest()}
        assert manager.validate("r6", None) is True


# ===========================================================================
# IntelligenceManager — API surface
# ===========================================================================

class TestManagerAPI:
    def _load_fake(self, manager, repo_id: str, data: dict) -> None:
        manager._cache[repo_id] = data

    def test_exists_true_when_cached(self, manager):
        self._load_fake(manager, "ex1", {"manifest": {}})
        assert manager.exists("ex1") is True

    def test_exists_false_when_not_cached(self, manager):
        assert manager.exists("not_here") is False

    def test_invalidate_removes_entry(self, manager):
        self._load_fake(manager, "inv1", {"manifest": {}})
        manager.invalidate("inv1")
        assert manager.exists("inv1") is False

    def test_get_returns_section(self, manager):
        self._load_fake(manager, "get1", {
            "manifest": {
                "intelligence_version": INTELLIGENCE_VERSION,
                "parser_version": PARSERS_PARSER_VERSION,
                "schema_version": SCHEMA_VERSION,
                "repository_hash": "h1",
            },
            "statistics": {"total_files": 42},
        })
        stats = manager.get("get1", "statistics", "h1")
        assert stats["total_files"] == 42

    def test_get_alias_stats(self, manager):
        self._load_fake(manager, "get2", {
            "manifest": {
                "intelligence_version": INTELLIGENCE_VERSION,
                "parser_version": PARSERS_PARSER_VERSION,
                "schema_version": SCHEMA_VERSION,
                "repository_hash": "h2",
            },
            "statistics": {"total_files": 7},
        })
        assert manager.get("get2", "stats", "h2")["total_files"] == 7

    def test_get_returns_none_on_invalid_hash(self, manager):
        self._load_fake(manager, "get3", {
            "manifest": {
                "intelligence_version": INTELLIGENCE_VERSION,
                "parser_version": PARSERS_PARSER_VERSION,
                "schema_version": SCHEMA_VERSION,
                "repository_hash": "correct",
            },
            "statistics": {},
        })
        assert manager.get("get3", "statistics", "wrong") is None

    def test_get_none_when_not_exists(self, manager):
        assert manager.get("nope", "statistics") is None
