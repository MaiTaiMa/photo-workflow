# -*- coding: utf-8 -*-
"""Tests fuer den Qualitaets-Grund im Face-Proposal-Status."""
from app.faces.face_proposal_reporting import build_registration_status


def test_reason_quality_threshold_when_all_skipped_by_quality():
    result = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [], "registered_count": 0, "skipped_count": 0},
        known_matches=3,
        skipped_quality=3,
    )
    assert result["status"] == "no_candidates"
    assert result["reason"] == "all_candidates_below_quality_threshold"


def test_reason_no_known_faces_when_no_matches():
    result = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [], "registered_count": 0, "skipped_count": 0},
        known_matches=0,
        skipped_quality=0,
    )
    assert result["reason"] == "no_eligible_known_faces"


def test_reason_limits_take_priority_over_quality():
    result = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [], "registered_count": 0, "skipped_count": 2},
        known_matches=3,
        skipped_quality=1,
    )
    assert result["reason"] == "all_candidates_skipped"
