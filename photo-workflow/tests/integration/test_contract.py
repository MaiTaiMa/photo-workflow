# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/integration/test_contract.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

from pathlib import Path

from app.orchestrator import WorkflowOrchestrator
from app.phase3_transfer import transfer_batch
from app.state_store import StateStore


def config(root: Path) -> dict:
    return {
        "paths": {"base_dir": str(root / "base"),
                  "publish_root": str(root / "publish")},
        "safety": {"require_paths_within_base_dir": True,
                   "follow_symlinks": False},
        "finalization": {
            "enabled": True,
            "publish_to_synology_photos": {
                "enabled": True,
                "mode": "copy",
                "dry_run": False,
                "indexing": {"enabled": False},
            },
        },
    }


def test_phase1_to_phase3_dry_run_contract(tmp_path: Path):
    batch = tmp_path / "base" / "batch"
    batch.mkdir(parents=True)
    (batch / "photo.jpg").write_bytes(b"jpg")
    orchestrator = WorkflowOrchestrator(config(tmp_path),
                                         runtime_root=tmp_path / "state")
    context = orchestrator.start_phase1(batch)
    orchestrator.mark_phase1_moving(context)
    orchestrator.complete_phase1(context, manifest_hash="a" * 64)
    orchestrator.gate_phase2(context)
    orchestrator.gate_phase3(context, tmp_path / "publish" / "batch")
    result = transfer_batch(batch, tmp_path / "publish" / "batch", config(tmp_path),
                            batch_id=context.batch_id, dry_run=True)
    assert result["status"] == "planned"
    assert not (tmp_path / "publish" / "batch").exists()
    assert StateStore(tmp_path / "state").read(context.batch_id)["state"] == "phase1_completed"