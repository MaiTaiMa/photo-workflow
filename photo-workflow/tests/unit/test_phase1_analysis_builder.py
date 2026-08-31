# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase1_analysis_builder.py
# PURPOSE:     Testet den kanonischen Review-/Rejected-Ordnervertrag.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
# =============================================================================


import pytest
from app.phase1_analysis_builder import Phase1AnalysisBuildError, build_persistable_analysis_rows
from app.phase1_analysis_plan import Phase1AnalysisPlanStore

def _row(decision="keep", file_name="a.jpg"):
    return {"file": file_name, "decision": decision, "final_score": 0.5, "_source_path": "/unsafe/a.jpg", "_family_tags": ["family:test"], "_family_regions": []}

@pytest.mark.parametrize(("decision", "target"), [("keep", "a.jpg"), ("review", "Rejected/a.jpg"), ("reject", "Rejected/a.jpg")])
def test_builds_decision_target_and_removes_internal_fields(decision, target):
    result = build_persistable_analysis_rows([_row(decision)], move_files=True)
    assert result[0]["execution"]["target_relative_path"] == target
    assert result[0]["family_tags"] == ["family:test"]
    assert "_source_path" not in result[0]
    assert "_family_tags" not in result[0]

def test_no_moves_keeps_target_in_root():
    assert build_persistable_analysis_rows([_row("reject")], move_files=False)[0]["execution"]["target_relative_path"] == "a.jpg"

def test_result_is_valid_analysis_plan_row(tmp_path):
    rows = build_persistable_analysis_rows([_row("review")], move_files=True)
    store = Phase1AnalysisPlanStore(tmp_path, "test")
    record = store.write(batch_id="batch-1", rows=rows, workunits=[{"workunit_id": "wu-1", "image_names": ["a.jpg"]}], config_fingerprint="cfg")
    assert record["rows"] == rows

@pytest.mark.parametrize("row", [_row("unknown"), _row("keep", "../a.jpg"), {"decision": "keep"}])
def test_rejects_invalid_rows(row):
    with pytest.raises(Phase1AnalysisBuildError):
        build_persistable_analysis_rows([row], move_files=True)