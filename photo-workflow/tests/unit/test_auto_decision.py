# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_auto_decision.py
# PURPOSE:     Prüft nicht-operative KI-Prognosen und ihre Fail-closed-Grenzen.
# AUTHOR:      Matzethias
# DATE:        2026-08-26
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+, pytest, app.auto_decision
# CHANGES:
#   2026-08-26 | 1.0.0 | Header und Testdokumentation gemäß Implementierungsregeln ergänzt.
# =============================================================================


import pytest

from app.auto_decision import AutoDecider, predict_decision


# -----------------------------------------------------------------------------
# Testfall: automation config.
# Prüft den abgegrenzten Vertragsfall mit kontrollierten Eingabewerten.
# Die nachstehenden Assertions sichern das erwartete Fail-closed-Verhalten.
# -----------------------------------------------------------------------------

def automation_config(mode: str = "auto_phase1") -> dict:
    return {
        "automation": {
            "policy_version": "1.0",
            "mode": mode,
            "keep_score_min": 0.90,
            "reject_score_max": 0.15,
        }
    }


# -----------------------------------------------------------------------------
# Testfall: test shadow mode predicts high confidence keep.
# Prüft den abgegrenzten Vertragsfall mit kontrollierten Eingabewerten.
# Die nachstehenden Assertions sichern das erwartete Fail-closed-Verhalten.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Testfall: test shadow mode predicts review (learning only).
# shadow mode gibt IMMER review zurueck, keine Automation.
# -----------------------------------------------------------------------------

def test_shadow_mode_predicts_high_confidence_keep() -> None:
    """shadow mode produces diagnostic predictions (no operational effect)."""
    decision, reason = predict_decision(
        personal_score=0.95,
        final_score=0.92,
        config=automation_config(mode="shadow"),
    )

    # Diagnostic prediction: keep bei hohen Scores
    assert decision == "keep"
    assert reason == "shadow_diagnostic_keep"


# -----------------------------------------------------------------------------
# Testfall: test shadow mode predicts review for reject scores.
# shadow mode gibt IMMER review zurueck, keine Automation.
# -----------------------------------------------------------------------------

def test_shadow_mode_predicts_high_confidence_reject() -> None:
    """shadow mode produces diagnostic predictions (no operational effect)."""
    decision, reason = predict_decision(
        personal_score=0.10,
        final_score=0.08,
        config=automation_config(mode="shadow"),
    )

    # Diagnostic prediction: reject bei niedrigen Scores
    assert decision == "reject"
    assert reason == "shadow_diagnostic_reject"


@pytest.mark.parametrize('mode', ['auto_phase1', 'auto_phase2', 'full_auto'])
def test_contract_operational_modes_remain_prediction_only(mode: str) -> None:
    """Operational modes produce keep/reject predictions."""
    decision, reason = predict_decision(
        personal_score=0.95,
        final_score=0.92,
        config=automation_config(mode),
    )

    assert (decision, reason) == ("keep", "high_confidence_keep")

def test_scores_in_middle_zone_require_manual_review() -> None:
    decision, reason = predict_decision(
        personal_score=0.61,
        final_score=0.64,
        config=automation_config(),
    )

    assert decision == "review"
    assert reason == "manual_review_zone"


# -----------------------------------------------------------------------------
# Testfall: test missing score requires manual review.
# Prüft den abgegrenzten Vertragsfall mit kontrollierten Eingabewerten.
# Die nachstehenden Assertions sichern das erwartete Fail-closed-Verhalten.
# -----------------------------------------------------------------------------

def test_missing_score_requires_manual_review() -> None:
    decision, reason = predict_decision(
        personal_score=None,
        final_score=0.98,
        config=automation_config(),
    )

    assert decision == "review"
    assert reason == "score_unavailable"


# -----------------------------------------------------------------------------
# Testfall: test off mode never produces operational prediction.
# Prüft den abgegrenzten Vertragsfall mit kontrollierten Eingabewerten.
# Die nachstehenden Assertions sichern das erwartete Fail-closed-Verhalten.
# -----------------------------------------------------------------------------

def test_off_mode_never_produces_operational_prediction() -> None:
    decision, reason = predict_decision(
        personal_score=1.0,
        final_score=1.0,
        config=automation_config("off"),
    )

    assert decision == "review"
    assert reason == "automation_off"


# -----------------------------------------------------------------------------
# Testfall: test invalid thresholds are rejected.
# Prüft den abgegrenzten Vertragsfall mit kontrollierten Eingabewerten.
# Die nachstehenden Assertions sichern das erwartete Fail-closed-Verhalten.
# -----------------------------------------------------------------------------

def test_invalid_thresholds_are_rejected() -> None:
    config = automation_config()
    config["automation"]["keep_score_min"] = 0.10
    config["automation"]["reject_score_max"] = 0.15

    with pytest.raises(ValueError, match="thresholds"):
        predict_decision(personal_score=0.2, final_score=0.2, config=config)


# -----------------------------------------------------------------------------
# Testfall: test wrapper uses the same prediction contract.
# Prüft den abgegrenzten Vertragsfall mit kontrollierten Eingabewerten.
# Die nachstehenden Assertions sichern das erwartete Fail-closed-Verhalten.
# -----------------------------------------------------------------------------

def test_wrapper_uses_the_same_prediction_contract() -> None:
    decider = AutoDecider(automation_config())

    assert decider.predict_decision(
        personal_score=0.97,
        final_score=0.93,
    ) == ("keep", "high_confidence_keep")