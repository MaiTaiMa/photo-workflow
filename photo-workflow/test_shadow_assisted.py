# =============================================================================
# PROJECT:     photo-workflow
# FILE:        test_shadow_assisted.py
# PURPOSE:     Tests fuer shadow/assisted Automation-Modi
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.0.0
# REQUIRES:    Python 3.12+, typing
# CHANGES:
#   2026-09-03 | 1.0.0 | shadow/assisted Modi Tests hinzugefuegt
# =============================================================================

"""
Tests fuer shadow/assisted Modi
===============================
Ausfuehren: .venv/bin/python test_shadow_assisted.py
"""

from app.auto_decision import predict_decision
from app.config_schema import validate_config

print("=" * 70)
print("TESTS: shadow/assisted Modi")
print("=" * 70)

# Test 1: shadow Mode
config_shadow = {
    "automation": {
        "mode": "shadow",
        "keep_score_min": 0.70,
        "reject_score_max": 0.30,
    }
}
decision, reason = predict_decision(
    personal_score=0.95,
    final_score=0.98,
    config=config_shadow,
)
assert decision == "review" and reason == "shadow_mode_learning_only", f"Test 1 failed: {decision}, {reason}"
print("✅ Test 1: shadow Mode -> review")

# Test 2: assisted Mode -> keep
config_assisted = {
    "automation": {
        "mode": "assisted",
        "keep_score_min": 0.70,
        "reject_score_max": 0.30,
    }
}
decision, reason = predict_decision(
    personal_score=0.85,
    final_score=0.88,
    config=config_assisted,
)
assert decision == "keep" and reason == "assisted_confident_keep", f"Test 2 failed: {decision}, {reason}"
print("✅ Test 2: assisted Mode (high scores) -> keep")

# Test 3: assisted Mode -> reject
decision, reason = predict_decision(
    personal_score=0.15,
    final_score=0.18,
    config=config_assisted,
)
assert decision == "reject" and reason == "assisted_confident_reject", f"Test 3 failed: {decision}, {reason}"
print("✅ Test 3: assisted Mode (low scores) -> reject")

# Test 4: assisted Mode -> review
decision, reason = predict_decision(
    personal_score=0.50,
    final_score=0.55,
    config=config_assisted,
)
assert decision == "review" and reason == "assisted_uncertain", f"Test 4 failed: {decision}, {reason}"
print("✅ Test 4: assisted Mode (medium scores) -> review")

# Test 5: Config-Validierung mit invalid mode
invalid_config = {
    "paths": {
        "base_dir": "/tmp/test",
        "temp_sd": "temp",
        "temp_images": "temp_img",
        "temp_done": "temp_done",
        "temp_error": "temp_err",
        "workflow_data_dir": "workflow",
    },
    "runtime": {
        "lock_file": "test.lock",
        "state_dir": "state",
        "quarantine_dir": "quarantine",
        "log_file": "test.log",
        "error_log": "error.log",
        "run_summaries_dir": "summaries",
        "calibration_batches_dir": "calibration",
    },
    "safety": {
        "require_paths_within_base_dir": True,
        "follow_symlinks": False,
        "never_delete_outside_arw_dir": True,
    },
    "automation": {
        "mode": "invalid_mode",
    }
}
is_valid, errors = validate_config(invalid_config)
has_mode_error = any("automation.mode" in e for e in errors)
assert not is_valid and has_mode_error, f"Test 5 failed: {errors}"
print("✅ Test 5: Invalid mode rejected")

print("\n" + "=" * 70)
print("ALLE TESTS BESTANDEN!")
print("=" * 70)
