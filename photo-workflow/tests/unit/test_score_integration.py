# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_score_integration.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from app.score_integration import compute_final_score


def test_final_score_reweights_when_personal_score_is_missing() -> None:
    generic = 0.8
    aesthetic = 0.6
    personal = None

    final = compute_final_score(
        generic_score=generic,
        aesthetic_score=aesthetic,
        personal_score=personal,
        weights={"generic": 0.3, "aesthetic": 0.3, "personal": 0.4},
    )

    expected = (generic * 0.5 + aesthetic * 0.5)
    assert final is not None
    assert abs(final - expected) < 1e-9


def test_final_score_none_when_all_components_missing() -> None:
    assert compute_final_score() is None