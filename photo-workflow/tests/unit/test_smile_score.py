"""S1: Smile-Score, Tiebreak-Verhalten, Keyword-Tag."""
from pathlib import Path

import pytest

from app import aesthetic
from app.metadata_writer import build_culling_keywords
from app.photo_workflow import combine_scores


def _cfg(weight=0.05):
    return {'culling': {'component_weights': {'base_score': 0.55, 'smile_score': weight}}}


def _landmarks(mouth_width, eye_dist=100.0):
    top_lip = [(0.0, 0.0)] * 12
    top_lip[6] = (mouth_width, 0.0)
    left = [(0.0, 5.0)] * 6
    right = [(eye_dist, 5.0)] * 6
    return {'top_lip': top_lip, 'left_eye': left, 'right_eye': right}


class _FakeFR:
    faces = []

    @staticmethod
    def load_image_file(path):
        return object()

    @staticmethod
    def face_landmarks(image):
        return _FakeFR.faces


def test_combine_scores_smile_tiebreak():
    low = combine_scores(0.6, None, None, None, _cfg(), smile_score=0.0)
    high = combine_scores(0.6, None, None, None, _cfg(), smile_score=0.9)
    assert high > low


def test_combine_scores_smile_ignored_without_weight():
    low = combine_scores(0.6, None, None, None, _cfg(0.0), smile_score=0.0)
    high = combine_scores(0.6, None, None, None, _cfg(0.0), smile_score=0.9)
    assert high == low


def test_smile_component_wide_mouth_beats_narrow(monkeypatch):
    monkeypatch.setattr(aesthetic, 'face_recognition', _FakeFR)
    cfg = {'culling': {'smile_detection': {'enabled': True}}}
    _FakeFR.faces = [_landmarks(110.0)]
    wide = aesthetic.smile_component(Path('x.jpg'), cfg)
    _FakeFR.faces = [_landmarks(85.0)]
    narrow = aesthetic.smile_component(Path('x.jpg'), cfg)
    assert wide is not None and narrow is not None
    assert wide > narrow


def test_smile_component_none_paths(monkeypatch):
    monkeypatch.setattr(aesthetic, 'face_recognition', _FakeFR)
    cfg = {'culling': {'smile_detection': {'enabled': True}}}
    _FakeFR.faces = []
    assert aesthetic.smile_component(Path('x.jpg'), cfg) is None
    disabled = {'culling': {'smile_detection': {'enabled': False}}}
    assert aesthetic.smile_component(Path('x.jpg'), disabled) is None
    monkeypatch.setattr(aesthetic, 'face_recognition', None)
    assert aesthetic.smile_component(Path('x.jpg'), cfg) is None


def test_smile_keyword_threshold():
    cfg = {'culling': {'smile_detection': {'tag_threshold': 0.65}},
           'metadata_culling': {'write_score_bands': False}}
    row = {'decision': 'keep', 'decision_reason': 'r', 'star_rating': 4,
           'smile_score': 0.8}
    assert 'smile:found:true' in build_culling_keywords(row, cfg)
    row['smile_score'] = 0.3
    assert 'smile:found:true' not in build_culling_keywords(row, cfg)
    row.pop('smile_score')
    assert 'smile:found:true' not in build_culling_keywords(row, cfg)


def test_smile_score_csv_contract():
    src = Path('app/photo_workflow.py').read_text(encoding='utf-8')
    assert "'smile_score',\n        'reference_score'," in src
    assert "'smile_score': components.get('smile')," in src
