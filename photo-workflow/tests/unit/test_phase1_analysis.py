# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase1_analysis.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from pathlib import Path
from app.phase1_analysis import analyze_rows, combine_scores
def _score(base): return lambda _: {"generic_score": base, "base_score": base, "personal_score": None, "eye_score": None}
def _family(**values): return lambda _: {"status": "none", "tags": [], "regions": [], "detected_people": [], "family_score": 0.0, "protected_by_family_rule": False, **values}
def _analyze(tmp_path, **kwargs):
 image=tmp_path/"a.jpg"; image.write_text("unchanged"); result=analyze_rows(images=[image],cfg={"culling":{"keep_threshold":0.7,"reject_threshold":0.3,"component_weights":{}},"family_recognition":{"enabled":True}},manual_keep_names=kwargs.get("manual_keep_names",set()),score=kwargs.get("score",_score(0.8)),detect_family=kwargs.get("family",_family()),predict=lambda row:{"predicted_decision":"review","prediction_reason":"shadow"},apply_series=kwargs.get("series",lambda rows:rows)); assert image.read_text()=="unchanged"; return result.rows[0]
def test_score_thresholds_and_shadow_prediction_do_not_change_decision(tmp_path):
 assert _analyze(tmp_path,score=_score(0.8))["decision"]=="keep"; assert _analyze(tmp_path,score=_score(0.5))["decision"]=="review"; row=_analyze(tmp_path,score=_score(0.2)); assert row["decision"]=="reject"; assert row["predicted_decision"]=="review"
def test_family_protection_and_manual_keep_take_precedence(tmp_path):
 assert _analyze(tmp_path,score=_score(0.2),family=_family(protected_by_family_rule=True))["decision"]=="review"; assert _analyze(tmp_path,score=_score(0.2),manual_keep_names={"a.jpg"})["decision"]=="keep"
def test_manual_keep_survives_series_override(tmp_path): assert _analyze(tmp_path,manual_keep_names={"a.jpg"},series=lambda rows:[dict(rows[0],decision="reject")])["decision"]=="keep"
def test_combine_scores_uses_base_when_no_weights(): assert combine_scores(0.4,0.8,0.9,1.0,{"culling":{"component_weights":{}}})==0.4