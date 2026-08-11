from pathlib import Path
from app.photo_workflow import score_image


def test_clip_scores_none_when_disabled(tmp_path) -> None:
    cfg = {'clip_scoring': {'enabled': False}}
    result = score_image(tmp_path / 'dummy.jpg', cfg, model=None)
    assert result['clip_personal_score'] is None
    assert result['clip_aesthetic_score'] is None


def test_clip_scores_none_when_references_missing(tmp_path) -> None:
    cfg = {
        'clip_scoring': {
            'enabled': True,
            'model_dir': str(tmp_path / 'clip'),
            'personal_reference_dir': str(tmp_path / 'refs'),
            'cache_dir': str(tmp_path / 'cache'),
            'shadow_mode': True,
        }
    }
    (tmp_path / 'clip').mkdir()
    (tmp_path / 'refs').mkdir()
    (tmp_path / 'cache').mkdir()

    result = score_image(tmp_path / 'dummy.jpg', cfg, model=None)
    assert result['clip_personal_score'] is None