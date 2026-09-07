# -*- coding: utf-8 -*-
"""Tests fuer save_human_decisions_from_batch (Kontrakt-Schreiber)."""
import json
from pathlib import Path

from app.human_review_store import validate_human_review_batch
from app.review_decision import save_human_decisions_from_batch


def _batch(tmp_path: Path):
    batch = tmp_path / "03_TEMP_DONE" / "2026-01-01"
    (batch / "Review").mkdir(parents=True)
    (batch / "Rejected").mkdir(parents=True)
    (batch / "keep1.jpg").write_bytes(b"k")
    (batch / "Review" / "rev1.jpg").write_bytes(b"r")
    (batch / "Rejected" / "rej1.jpg").write_bytes(b"x")
    return tmp_path / "WORKFLOW_DATA" / "runtime"


def test_save_writes_contract_conformant_batch(tmp_path):
    runtime = _batch(tmp_path)
    result, target = save_human_decisions_from_batch(
        runtime_path=runtime, batch_id="2026-01-01", producer_version="v1.4",
    )
    assert result["status"] == "ok"
    assert result["decision_count"] == 2
    assert "skipped_records" not in result  # Review-Quelle entfernt (Paket 4)
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_human_review_batch(payload)
    decisions = {r["image_id"]: r["human_decision"] for r in payload["reviews"]}
    assert decisions == {"keep1.jpg": "keep", "rej1.jpg": "reject"}


def test_save_missing_batch_is_soft_error(tmp_path):
    result, _ = save_human_decisions_from_batch(
        runtime_path=tmp_path / "WORKFLOW_DATA" / "runtime",
        batch_id="2099-01-01", producer_version="v1.4",
    )
    assert result["status"] == "error"
