# -*- coding: utf-8 -*-
"""Tests fuer _needs_auto_validation in photo_workflow."""
import os
from pathlib import Path

from app.photo_workflow import _needs_auto_validation


def _setup(runtime: Path, with_review: bool, with_validation: bool):
    review = runtime / "automation" / "reviews" / "b1.json"
    validation = runtime / "automation" / "validation" / "b1.json"
    if with_review:
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text("{}", encoding="utf-8")
    if with_validation:
        validation.parent.mkdir(parents=True, exist_ok=True)
        validation.write_text("{}", encoding="utf-8")
    return review, validation


def test_no_review_means_no_validation(tmp_path):
    _setup(tmp_path, with_review=False, with_validation=False)
    assert _needs_auto_validation(tmp_path, "b1") is False


def test_review_without_validation_needs_run(tmp_path):
    _setup(tmp_path, with_review=True, with_validation=False)
    assert _needs_auto_validation(tmp_path, "b1") is True


def test_newer_review_than_validation_needs_run(tmp_path):
    review, validation = _setup(tmp_path, with_review=True, with_validation=True)
    old = 1_700_000_000
    os.utime(validation, (old, old))
    assert _needs_auto_validation(tmp_path, "b1") is True


def test_current_validation_skips(tmp_path):
    review, validation = _setup(tmp_path, with_review=True, with_validation=True)
    old = 1_700_000_000
    os.utime(review, (old, old))
    assert _needs_auto_validation(tmp_path, "b1") is False
