import json

from app.series_report import write_batch_series_reports


def _row(
    file_name: str,
    series_id: str = 'series_0',
    rank: int = 1,
    decision: str = 'keep',
    reason: str = 'series_best_confirmed',
    **extra,
) -> dict:
    row = {
        'file': file_name,
        'series_id': series_id,
        'series_size': 2,
        'series_rank': rank,
        'series_best': rank == 1,
        'series_margin_to_best': 0.0 if rank == 1 else 0.12,
        'final_score': 0.91 if rank == 1 else 0.79,
        'star_rating': 5 if rank == 1 else 4,
        'score_decision': 'keep',
        'decision': decision,
        'decision_reason': reason,
        'protected_by_family_rule': False,
        'face_status': 'ok',
        '_source_path': '/not/persisted/IMG.jpg',
        '_family_tags': ['not:persisted'],
    }
    row.update(extra)
    return row


def test_no_real_series_writes_no_reports(tmp_path):
    result = write_batch_series_reports(
        rows=[_row('IMG_0001.JPG', series_id='single')],
        save_dir=tmp_path,
        cfg={},
    )

    assert result['enabled'] is True
    assert result['series_count'] == 0
    assert result['json_report_count'] == 0
    assert not (tmp_path / 'series_reports').exists()


def test_writes_json_and_text_report_from_final_rows(tmp_path):
    rows = [
        _row('IMG_0001.JPG', rank=1),
        _row(
            'IMG_0002.JPG',
            rank=2,
            decision='review',
            reason='series_near_best',
        ),
    ]

    result = write_batch_series_reports(rows, tmp_path, {})

    assert result['series_count'] == 1
    assert result['reported_image_count'] == 2
    assert result['json_report_count'] == 1
    report_dir = tmp_path / 'series_reports'
    json_paths = list(report_dir.glob('*.json'))
    assert len(json_paths) == 1
    assert (report_dir / 'series_report.txt').is_file()

    report = json.loads(json_paths[0].read_text(encoding='utf-8'))
    assert report['series_id'] == 'series_0'
    assert report['decision_counts'] == {
        'keep': 1,
        'review': 1,
        'reject': 0,
    }
    assert report['images'][0]['file'] == 'IMG_0001.JPG'
    assert report['images'][0]['series_best'] is True
    assert report['images'][1]['decision_reason'] == 'series_near_best'
    assert '_source_path' not in json.dumps(report)
    assert '_family_tags' not in json.dumps(report)


def test_multiple_series_get_separate_collision_safe_files(tmp_path):
    rows = [
        _row('IMG_0001.JPG', series_id='series/a', rank=1),
        _row('IMG_0002.JPG', series_id='series:a', rank=1),
    ]

    result = write_batch_series_reports(rows, tmp_path, {})

    assert result['series_count'] == 2
    json_paths = list((tmp_path / 'series_reports').glob('*.json'))
    assert len(json_paths) == 2
    assert len({path.name for path in json_paths}) == 2


def test_manual_keep_and_family_protection_are_visible(tmp_path):
    rows = [
        _row(
            'IMG_0001.JPG',
            reason='manual_keep_match',
            protected_by_family_rule=True,
        ),
        _row('IMG_0002.JPG', rank=2, decision='reject'),
    ]

    write_batch_series_reports(rows, tmp_path, {})
    json_path = next((tmp_path / 'series_reports').glob('*.json'))
    report = json.loads(json_path.read_text(encoding='utf-8'))

    assert report['manual_keep_count'] == 1
    assert report['family_protected_count'] == 1
    assert report['images'][0]['manual_keep'] is True
    assert report['images'][0]['family_protected'] is True


def test_disabled_reporting_writes_nothing(tmp_path):
    result = write_batch_series_reports(
        rows=[_row('IMG_0001.JPG'), _row('IMG_0002.JPG', rank=2)],
        save_dir=tmp_path,
        cfg={'reporting': {'series_reports_enabled': False}},
    )

    assert result['enabled'] is False
    assert result['series_count'] == 0
    assert not (tmp_path / 'series_reports').exists()