# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_clip_scorer_personal_cache.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from pathlib import Path

from app.clip_scorer import CLIPScorer


def test_shadow_mode_personal_score_is_unavailable() -> None:
    scorer = CLIPScorer("/unused", shadow_mode=True)

    assert scorer.compute_personal_score("query.jpg", ["reference.jpg"]) is None
    assert scorer.last_personal_cache_status == "unavailable"


def test_personal_score_uses_cached_reference_vectors(monkeypatch, tmp_path) -> None:
    scorer = CLIPScorer("/unused", shadow_mode=True)
    scorer.shadow_mode = False
    monkeypatch.setattr("app.clip_scorer.TRANSFORMERS_AVAILABLE", True)
    monkeypatch.setattr(scorer, "_embed_image", lambda path: [1.0, 0.0])

    calls = []

    def fake_cache(**kwargs):
        calls.append(kwargs)
        return {"reference.jpg": [1.0, 0.0]}, True

    monkeypatch.setattr("app.clip_scorer.load_or_build_reference_cache", fake_cache)

    score = scorer.compute_personal_score(
        "query.jpg",
        ["reference.jpg"],
        reference_dir=str(tmp_path / "references"),
        cache_path=str(tmp_path / "runtime" / "personal-cache.json"),
        model_id="clip-test-v1",
    )

    assert score == 1.0
    assert scorer.last_personal_cache_status == "hit"
    assert calls[0]["model_id"] == "clip-test-v1"