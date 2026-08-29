# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_automation_config_schema.py
# PURPOSE:     Prüft die strikte Akzeptanz des kanonischen Automation-Blocks.
# AUTHOR:      Matzethias
# DATE:        2026-08-20
# VERSION:     1.0.0
# REQUIRES:    Python 3.11, pytest
# CHANGES:
#   2026-08-20 | 1.0.0 | A1: Schema-Test für die Automation-Top-Level-Sektion.
# =============================================================================


from app.config_schema import get_test_config, validate_config


def test_strict_schema_accepts_automation_section(tmp_path) -> None:
    config = get_test_config(str(tmp_path))
    config["automation"] = {
        "policy_version": "1.0",
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
    config["pipeline"] = {
        "phases": ["phase1", "phase2"],
        "stop_on_error": True,
    }
    config["phase2"] = {
        "cleanup_review_rejected": False,
    }

    valid, errors = validate_config(config)

    assert valid is True
    assert errors == []


def test_strict_schema_rejects_unknown_top_level_section(tmp_path) -> None:
    config = get_test_config(str(tmp_path))
    config["unknown_section"] = {}

    valid, errors = validate_config(config)

    assert valid is False
    assert "Unbekannte Sektion 'unknown_section' in config" in errors