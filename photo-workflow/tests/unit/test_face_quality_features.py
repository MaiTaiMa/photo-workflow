# -*- coding: utf-8 -*-
"""Tests fuer _face_box_quality_features in photo_workflow.

face_area_ratio misst die kuerzere Box-Kante relativ zur Crop-Zielgroesse
(1.0 = Box mindestens so gross wie der Ziel-Crop), framing_score die
Zentralitaet der Box im Bild.
"""
from app.photo_workflow import _face_box_quality_features


def test_box_at_crop_size_scores_full_area():
    box = {"left": 0, "top": 0, "right": 256, "bottom": 256}
    area, _ = _face_box_quality_features(box, 2000, 2000)
    assert area == 1.0


def test_box_half_crop_size_scores_half_area():
    box = {"left": 0, "top": 0, "right": 128, "bottom": 128}
    area, _ = _face_box_quality_features(box, 2000, 2000)
    assert area == 0.5


def test_centered_box_scores_full_framing():
    box = {"left": 400, "top": 400, "right": 600, "bottom": 600}
    _, framing = _face_box_quality_features(box, 1000, 1000)
    assert framing == 1.0


def test_corner_box_scores_lower_framing():
    box = {"left": 0, "top": 0, "right": 100, "bottom": 100}
    _, framing = _face_box_quality_features(box, 1000, 1000)
    assert 0.0 <= framing < 1.0


def test_custom_crop_size_respected():
    box = {"left": 0, "top": 0, "right": 128, "bottom": 128}
    area, _ = _face_box_quality_features(box, 2000, 2000, crop_size=128)
    assert area == 1.0


def test_invalid_box_returns_none():
    box = {"left": 0, "top": 0, "right": None, "bottom": 100}
    assert _face_box_quality_features(box, 1000, 1000) is None


def test_zero_image_size_returns_none():
    box = {"left": 0, "top": 0, "right": 10, "bottom": 10}
    assert _face_box_quality_features(box, 0, 0) is None
