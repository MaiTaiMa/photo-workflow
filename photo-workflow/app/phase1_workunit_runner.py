# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/phase1_workunit_runner.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable

from app.family_recognition import write_native_tags
from app.metadata_writer import write_culling_metadata
from app.phase1_analysis_plan import Phase1AnalysisPlanStore
from app.phase1_workunit_executor import ExecutionResult, execute_next_image
from app.workunit_state import WorkUnitStateStore


class Phase1WorkUnitRunner:
    """Runs at most one persisted image step without scheduling a batch."""

    def __init__(self, analysis_plans: Phase1AnalysisPlanStore, workunit_states: WorkUnitStateStore, move_file: Callable[[Path, Path], None] = shutil.move, family_writer: Callable[..., tuple[bool, str]] = write_native_tags, culling_writer: Callable[..., tuple[bool, str]] = write_culling_metadata) -> None:
        self.analysis_plans = analysis_plans
        self.workunit_states = workunit_states
        self.move_file = move_file
        self.family_writer = family_writer
        self.culling_writer = culling_writer

    def run_next(self, *, root: str | Path, batch_id: str, cfg: dict[str, Any]) -> ExecutionResult | None:
        """Load the next unfinished WorkUnit and execute one image from it."""
        workunit = self.workunit_states.next_pending(batch_id)
        if workunit is None:
            return None
        plan = self.analysis_plans.load(batch_id)
        if plan is None:
            raise RuntimeError("analysis plan is not initialized")
        return execute_next_image(root=root, batch_id=batch_id, workunit=workunit, plan_rows=plan["rows"], cfg=cfg, update_execution=self.analysis_plans.update_execution, transition=self.workunit_states.transition, move_file=self.move_file, write_family=self.family_writer, write_culling=self.culling_writer)
