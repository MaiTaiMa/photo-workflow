import pytest

from app.automation_config import validate_automation_config


def config() -> dict:
    return {
        "automation": {
            "mode": "shadow",
            "keep_score_min": 0.90,
            "reject_score_max": 0.15,
            "evaluation_window_days": 90,
            "min_evaluated_batches": 10,
            "min_evaluated_images": 500,
            "min_overall_agreement": 0.85,
            "min_keep_precision": 0.95,
            "min_reject_precision": 0.98,
        }
    }


def test_valid_automation_config_is_normalized() -> None:
    validated = validate_automation_config(config())

    assert validated["mode"] == "shadow"
    assert validated["keep_score_min"] == 0.90


def test_missing_automation_block_is_rejected() -> None:
    with pytest.raises(ValueError, match="mapping"):
        validate_automation_config({})


def test_unknown_mode_is_rejected() -> None:
    value = config()
    value["automation"]["mode"] = "enabled"

    with pytest.raises(ValueError, match="unsupported"):
        validate_automation_config(value)


def test_reject_threshold_must_be_lower_than_keep_threshold() -> None:
    value = config()
    value["automation"]["reject_score_max"] = 0.90

    with pytest.raises(ValueError, match="lower"):
        validate_automation_config(value)


def test_scores_must_stay_inside_unit_interval() -> None:
    value = config()
    value["automation"]["min_keep_precision"] = 1.01

    with pytest.raises(ValueError, match="between"):
        validate_automation_config(value)


def test_minimum_counts_must_be_positive_integers() -> None:
    value = config()
    value["automation"]["min_evaluated_images"] = 0

    with pytest.raises(ValueError, match="positive integer"):
        validate_automation_config(value)
