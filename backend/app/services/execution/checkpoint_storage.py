"""Checkpoint and Execution Event Storage.

Manages persistence under backend/data/workflows/{workflow_id}/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.execution.execution_models import (
    ExecutionCheckpoint,
    ExecutionState,
    ExecutionMetrics,
    ExecutionBudget,
    ExecutionEvent,
)


class CheckpointStorage:
    """Handles serialization and corruption recovery of checkpoints and events."""

    def _get_workflow_dir(self, workflow_id: str) -> Path:
        """Returns the workflows dir for execution state."""
        wf_dir = Path("backend/data/workflows") / workflow_id
        wf_dir.mkdir(parents=True, exist_ok=True)
        return wf_dir

    def save_checkpoint(self, workflow_id: str, checkpoint: ExecutionCheckpoint) -> None:
        """Saves a checkpoint list and its backup to disk."""
        wf_dir = self._get_workflow_dir(workflow_id)
        cp_file = wf_dir / "checkpoints.json"
        bak_file = wf_dir / "checkpoints.json.bak"

        # Load existing checkpoints
        checkpoints = self.load_checkpoints(workflow_id)
        
        # Remove if already exists (updating step status)
        checkpoints = [cp for cp in checkpoints if cp.step_id != checkpoint.step_id]
        checkpoints.append(checkpoint)

        data = [cp.to_dict() for cp in checkpoints]
        
        try:
            # Write backup first if main file exists and is valid
            if cp_file.is_file():
                try:
                    with cp_file.open("r", encoding="utf-8") as f:
                        json.load(f)
                    # Copy to backup
                    bak_file.write_text(cp_file.read_text(encoding="utf-8"), encoding="utf-8")
                except Exception:
                    pass

            with cp_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[CheckpointStorage] Failed to save checkpoint for {workflow_id}: {e}")

    def load_checkpoints(self, workflow_id: str) -> List[ExecutionCheckpoint]:
        """Loads checkpoints from disk, falling back to backup if corrupted."""
        wf_dir = self._get_workflow_dir(workflow_id)
        cp_file = wf_dir / "checkpoints.json"
        bak_file = wf_dir / "checkpoints.json.bak"

        if not cp_file.is_file() and not bak_file.is_file():
            return []

        # Try reading main file
        if cp_file.is_file():
            try:
                with cp_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return [ExecutionCheckpoint.from_dict(cp) for cp in data]
            except Exception as e:
                logger.warning(f"[CheckpointStorage] Main checkpoints file corrupted: {e}. Attempting backup recovery...")
                
        # Try reading backup file
        if bak_file.is_file():
            try:
                with bak_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return [ExecutionCheckpoint.from_dict(cp) for cp in data]
            except Exception as e:
                logger.error(f"[CheckpointStorage] Backup checkpoints file also corrupted: {e}. Resetting checkpoints.")

        return []

    def save_state(
        self,
        workflow_id: str,
        state: ExecutionState,
        metrics: ExecutionMetrics,
        budget: ExecutionBudget,
    ) -> None:
        """Saves execution state, metrics, and budget to state.json."""
        wf_dir = self._get_workflow_dir(workflow_id)
        state_file = wf_dir / "state.json"
        
        data = {
            "state": state.to_dict(),
            "metrics": metrics.to_dict(),
            "budget": budget.to_dict(),
        }
        
        try:
            with state_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[CheckpointStorage] Failed to save state for {workflow_id}: {e}")

    def load_state(
        self,
        workflow_id: str,
    ) -> Tuple[Optional[ExecutionState], Optional[ExecutionMetrics], Optional[ExecutionBudget]]:
        """Loads state, metrics, and budget from disk. Handles corruption."""
        wf_dir = self._get_workflow_dir(workflow_id)
        state_file = wf_dir / "state.json"
        
        if not state_file.is_file():
            return None, None, None
            
        try:
            with state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            state = ExecutionState.from_dict(data.get("state", {}))
            metrics = ExecutionMetrics.from_dict(data.get("metrics", {}))
            budget = ExecutionBudget.from_dict(data.get("budget", {}))
            return state, metrics, budget
        except Exception as e:
            logger.warning(f"[CheckpointStorage] State file corrupted for {workflow_id}: {e}. Returning default states.")
            return None, None, None

    def log_event(self, workflow_id: str, event: ExecutionEvent) -> None:
        """Appends an execution event to execution_events.json."""
        wf_dir = self._get_workflow_dir(workflow_id)
        events_file = wf_dir / "execution_events.json"
        
        events = self.load_events(workflow_id)
        events.append(event)
        
        try:
            with events_file.open("w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in events], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[CheckpointStorage] Failed to log event for {workflow_id}: {e}")

    def load_events(self, workflow_id: str) -> List[ExecutionEvent]:
        """Loads timeline events from disk, recovering if corrupted."""
        wf_dir = self._get_workflow_dir(workflow_id)
        events_file = wf_dir / "execution_events.json"
        
        if not events_file.is_file():
            return []
            
        try:
            with events_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return [ExecutionEvent.from_dict(e) for e in data]
        except Exception as e:
            logger.warning(f"[CheckpointStorage] Events log file corrupted: {e}. Resetting events log.")
            return []


checkpoint_storage = CheckpointStorage()
