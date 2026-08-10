import pytest

from app.auto_decision import AutoDecider, predict_decision


def automation_config(mode: str = "shadow") -> dict:
    return {
        "automation": {
            "mode": mode,
            "keep_score_min": 0.90,
            "reject_score_max": 0.15,
        }
    }


def test_shadow_mode_predicts_high_confidence_keep() -> None:
    decision, reason = predict_decision(
        personal_score=0.95,
        final_score=0.92,
        config=automation_config(),
    )

    assert decision == "keep"
    assert reason == "high_confidence_keep"


def test_shadow_mode_predicts_high_confidence_reject() -> None:
    decision, reason = predict_decision(
        personal_score=0.10,
        final_score=0.12,
        config=automation_config(),
    )

    assert decision == "reject"
    assert reason == "high_confidence_reject"


def test_scores_in_middle_zone_require_manual_review() -> None:
    decision, reason = predict_decision(
        personal_score=0.61,
        final_score=0.64,
        config=automation_config(),
    )

    assert decision == "review"
    assert reason == "manual_review_zone"


def test_missing_score_requires_manual_review() -> None:
    decision, reason = predict_decision(
        personal_score=None,
        final_score=0.98,
        config=automation_config(),
    )

    assert decision == "review"
    assert reason == "score_unavailable"


def test_off_mode_never_produces_operational_prediction() -> None:
    decision, reason = predict_decision(
        personal_score=1.0,
        final_score=1.0,
        config=automation_config("off"),
    )

    assert decision == "review"
    assert reason == "automation_off"


def test_invalid_thresholds_are_rejected() -> None:
    config = automation_config()
    config["automation"]["keep_score_min"] = 0.10
    config["automation"]["reject_score_max"] = 0.15

    with pytest.raises(ValueError, match="thresholds"):
        predict_decision(personal_score=0.2, final_score=0.2, config=config)


def test_wrapper_uses_the_same_prediction_contract() -> None:
    decider = AutoDecider(automation_config())

    assert decider.predict_decision(
        personal_score=0.97,
        final_score=0.93,
    ) == ("keep", "high_confidence_keep")
