"""Repository Analysis Storage — Cache validation, load, and save.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.logger import logger
from app.services.repository_analysis.analysis_models import (
    AnalysisSummary,
    ImpactResult,
    DependencyChain,
    CircularDependency,
    DeadCodeReport,
    HotspotReport,
    ArchitectureIssue,
)

ANALYSIS_VERSION = "v1"


class AnalysisStorage:
    """Manages the persistence of Repository Analysis artifacts to disk."""

    def _get_analysis_dir(self, intelligence_path: str) -> Path:
        """Returns the analysis folder adjacent to intelligence."""
        # e.g., backend/data/repositories/{repository_id}/intelligence -> backend/data/repositories/{repository_id}/analysis
        intel_dir = Path(intelligence_path)
        analysis_dir = intel_dir.parent / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        return analysis_dir

    def is_valid_cache(
        self,
        intelligence_path: str,
        repo_hash: Optional[str],
        graph_version: str = "v1",
    ) -> bool:
        """Determines if the cached analysis is valid based on versions and repo hash."""
        analysis_dir = self._get_analysis_dir(intelligence_path)
        summary_file = analysis_dir / "summary.json"
        
        if not summary_file.is_file():
            return False
            
        try:
            with summary_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Check version markers
            if data.get("analysis_version") != ANALYSIS_VERSION:
                return False
            if data.get("graph_version") != graph_version:
                return False
            if repo_hash and data.get("repository_hash") != repo_hash:
                return False
                
            # Verify other files exist
            for name in ["impact.json", "dependency_report.json", "dead_code.json", "hotspots.json", "architecture.json"]:
                if not (analysis_dir / name).is_file():
                    return False
                    
            return True
        except Exception:
            return False

    def load_summary(self, intelligence_path: str) -> Optional[Dict[str, Any]]:
        return self._load_file(intelligence_path, "summary.json")

    def load_impact(self, intelligence_path: str) -> Optional[Dict[str, Any]]:
        return self._load_file(intelligence_path, "impact.json")

    def load_dependencies(self, intelligence_path: str) -> Optional[Dict[str, Any]]:
        return self._load_file(intelligence_path, "dependency_report.json")

    def load_dead_code(self, intelligence_path: str) -> Optional[Dict[str, Any]]:
        return self._load_file(intelligence_path, "dead_code.json")

    def load_hotspots(self, intelligence_path: str) -> Optional[Dict[str, Any]]:
        return self._load_file(intelligence_path, "hotspots.json")

    def load_architecture(self, intelligence_path: str) -> Optional[Dict[str, Any]]:
        return self._load_file(intelligence_path, "architecture.json")

    def save_analysis(
        self,
        intelligence_path: str,
        summary: AnalysisSummary,
        impacts: Dict[str, Any],
        dependencies: Dict[str, Any],
        dead_code: DeadCodeReport,
        hotspots: HotspotReport,
        issues: List[ArchitectureIssue],
        graph_version: str = "v1",
    ) -> None:
        """Saves all analysis reports atomically to disk."""
        analysis_dir = self._get_analysis_dir(intelligence_path)
        
        # Save summary
        summary_dict = summary.to_dict()
        summary_dict["analysis_version"] = ANALYSIS_VERSION
        summary_dict["graph_version"] = graph_version
        self._write_file(analysis_dir / "summary.json", summary_dict)
        
        # Save other reports
        self._write_file(analysis_dir / "impact.json", {"impacts": impacts})
        self._write_file(analysis_dir / "dependency_report.json", {"dependency_report": dependencies})
        self._write_file(analysis_dir / "dead_code.json", dead_code.to_dict())
        self._write_file(analysis_dir / "hotspots.json", hotspots.to_dict())
        self._write_file(analysis_dir / "architecture.json", {"issues": [i.to_dict() for i in issues]})
        
        logger.info(f"[AnalysisStorage] Saved all analysis reports to {analysis_dir}")

    def _load_file(self, intelligence_path: str, filename: str) -> Optional[Dict[str, Any]]:
        analysis_dir = self._get_analysis_dir(intelligence_path)
        file_path = analysis_dir / filename
        if not file_path.is_file():
            return None
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[AnalysisStorage] Failed to load {filename}: {e}")
            return None

    def _write_file(self, path: Path, data: Any) -> None:
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[AnalysisStorage] Failed to write file {path}: {e}")


analysis_storage = AnalysisStorage()
