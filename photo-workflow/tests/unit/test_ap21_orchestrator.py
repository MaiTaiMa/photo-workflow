from __future__ import annotations

from pathlib import Path

import pytest

from app.orchestrator import WorkflowGateError, WorkflowOrchestrator
from app.state_store import StateStore


def make_config(root: Path) -> dict:
    return {"paths": {"base_dir": str(root / "base"),
                       "publish_root": str(root / "publish")},
            "safety": {"require_paths_within_base_dir": True,
                       "follow_symlinks": False}}


def test_phase1_gate_sequence(tmp_path: Path):
    batch = tmp_path / "base" / "batch"
    batch.mkdir(parents=True)
    orchestrator = WorkflowOrchestrator(make_config(tmp_path),
                                         runtime_root=tmp_path / "state")
    context = orchestrator.start_phase1(batch)
    orchestrator.mark_phase1_moving(context)
    with pytest.raises(WorkflowGateError):
        orchestrator.complete_phase1(context, manifest_hash="")
    (batch / "photo.jpg").write_bytes(b"jpg")
    orchestrator.complete_phase1(context, manifest_hash="a" * 64)
    assert StateStore(tmp_path / "state").read(context.batch_id)["state"] == "phase1_completed"


def test_phase3_gate_rejects_uncompleted_phase1(tmp_path: Path):
    batch = tmp_path / "base" / "batch"
    batch.mkdir(parents=True)
    orchestrator = WorkflowOrchestrator(make_config(tmp_path),
                                         runtime_root=tmp_path / "state")
    context = orchestrator.start_phase1(batch)
    with pytest.raises(Exception):
        orchestrator.gate_phase3(context, None)
