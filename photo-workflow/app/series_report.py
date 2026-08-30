# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/series_report.py
# PURPOSE:     Report-Generierung für Serien (AP7)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.1.0
# REQUIRES:    Python 3.11+, series_detection.py, best_of_selection.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP7
#   2026-08-13: AP7A – finale Culling-Rows als Batch-Serienreports schreiben
# =============================================================================


from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.best_of_selection import SelectionResult
from app.series_detection import Series


def generate_series_report(
    series: Series,
    selection: SelectionResult,
) -> dict[str, Any]:
    """Generiert einen JSON-Report für den klassischen Best-of-Pfad."""
    selected = [
        {
            'rel_path': image.get('rel_path', ''),
            'rank': image.get('best_of_score', 0),
            'best_of_score': round(image.get('best_of_score', 0), 3),
            'reason': selection.reasons.get(image.get('rel_path', ''), ''),
        }
        for image in selection.selected_images
    ]
    rejected = [
        {
            'rel_path': image.get('rel_path', ''),
            'reason': selection.reasons.get(image.get('rel_path', ''), ''),
        }
        for image in selection.rejected_images
    ]
    protected = [
        {
            'rel_path': image.get('rel_path', ''),
            'reason': image.get('_protected_reason', 'Geschuetzt'),
        }
        for image in selection.protected_images
    ]

    return {
        'series_id': series.series_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_images': series.size,
        'selected_count': len(selection.selected_images),
        'rejected_count': len(selection.rejected_images),
        'protected_count': len(selection.protected_images),
        'series_start_time': (
            series.start_time.isoformat() if series.start_time else None
        ),
        'series_end_time': (
            series.end_time.isoformat() if series.end_time else None
        ),
        'selection': selected,
        'rejection': rejected,
        'protected': protected,
    }


def generate_text_report(series: Series, selection: SelectionResult) -> str:
    """Generiert einen Text-Report für den klassischen Best-of-Pfad."""
    lines = [
        f'Serien-Report: {series.series_id}',
        '=' * 60,
        '',
        f'Generiert: {datetime.now(timezone.utc).isoformat()}',
        f'Zeitraum: {series.start_time} bis {series.end_time}',
        f'Anzahl Bilder: {series.size}',
        '',
        'Zusammenfassung:',
        f'- Ausgewaehlt: {len(selection.selected_images)}',
        f'- Abgelehnt: {len(selection.rejected_images)}',
        f'- Geschuetzt: {len(selection.protected_images)}',
        '',
        'Ausgewaehlt:',
    ]

    for index, image in enumerate(selection.selected_images, 1):
        rel_path = image.get('rel_path', '')
        score = image.get('best_of_score', 0)
        reason = selection.reasons.get(rel_path, '')
        lines.extend([
            f'  {index}. {rel_path}',
            f'     Score: {score:.3f}',
            f'     Grund: {reason}',
        ])

    if selection.rejected_images:
        lines.extend(['', 'Abgelehnt:'])
        for image in selection.rejected_images[:5]:
            rel_path = image.get('rel_path', '')
            reason = selection.reasons.get(rel_path, '')
            lines.extend([f'  - {rel_path}', f'    Grund: {reason}'])
        if len(selection.rejected_images) > 5:
            lines.append(
                f'  ... und {len(selection.rejected_images) - 5} weitere'
            )

    if selection.protected_images:
        lines.extend(['', 'Geschuetzt:'])
        for image in selection.protected_images:
            rel_path = image.get('rel_path', '')
            reason = image.get('_protected_reason', 'Geschuetzt')
            lines.extend([f'  - {rel_path}', f'    Grund: {reason}'])

    lines.extend(['', '=' * 60, 'Ende des Reports'])
    return '\n'.join(lines)


def save_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Speichert einen JSON-Report atomar genug innerhalb eines Batch-Laufs."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def save_text_report(text_report: str, output_path: str | Path) -> None:
    """Speichert einen Text-Report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_report, encoding='utf-8')


def _safe_report_stem(series_id: str) -> str:
    normalized = re.sub(r'[^A-Za-z0-9._-]+', '_', series_id).strip('._-')
    normalized = normalized or 'series'
    digest = hashlib.sha256(series_id.encode('utf-8')).hexdigest()[:10]
    return f'{normalized}-{digest}'


def _row_report_item(row: dict[str, Any]) -> dict[str, Any]:
    decision_reason = str(row.get('decision_reason', ''))
    return {
        'file': str(row.get('file', '')),
        'final_path': str(row.get('final_path', '')),
        'series_rank': row.get('series_rank'),
        'series_best': bool(row.get('series_best', False)),
        'series_margin_to_best': row.get('series_margin_to_best'),
        'final_score': row.get('final_score'),
        'star_rating': row.get('star_rating'),
        'score_decision': row.get('score_decision'),
        'decision': row.get('decision'),
        'decision_reason': decision_reason,
        'manual_keep': decision_reason == 'manual_keep_match',
        'family_protected': bool(row.get('protected_by_family_rule', False)),
        'face_status': row.get('face_status', ''),
    }


def _series_report_from_rows(
    series_id: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    images = sorted(
        (_row_report_item(row) for row in rows),
        key=lambda item: (
            int(item['series_rank'] or 0),
            item['file'],
        ),
    )
    decision_counts = {
        decision: sum(item['decision'] == decision for item in images)
        for decision in ('keep', 'review', 'reject')
    }
    return {
        'schema_version': 'series-report-v1',
        'series_id': series_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'series_size': len(images),
        'decision_counts': decision_counts,
        'manual_keep_count': sum(item['manual_keep'] for item in images),
        'family_protected_count': sum(
            item['family_protected'] for item in images
        ),
        'images': images,
    }


def _batch_text_report(reports: list[dict[str, Any]]) -> str:
    lines = [
        'Batch-Serienreport',
        '=' * 72,
        f'Generiert: {datetime.now(timezone.utc).isoformat()}',
        f'Erkannte Serien: {len(reports)}',
        '',
    ]
    for report in reports:
        counts = report['decision_counts']
        lines.extend([
            f"Serie: {report['series_id']} ({report['series_size']} Bilder)",
            (
                'Entscheidungen: '
                f"keep={counts['keep']}, review={counts['review']}, "
                f"reject={counts['reject']}"
            ),
        ])
        for image in report['images']:
            markers = []
            if image['series_best']:
                markers.append('BEST')
            if image['manual_keep']:
                markers.append('MANUAL_KEEP')
            if image['family_protected']:
                markers.append('FAMILY_PROTECTED')
            marker_text = f" [{', '.join(markers)}]" if markers else ''
            lines.append(
                f"  #{image['series_rank']} {image['file']}: "
                f"{image['decision']} ({image['decision_reason']})"
                f"{marker_text}"
            )
        lines.append('')
    lines.append('Ende des Batch-Serienreports')
    return '\n'.join(lines)


def write_batch_series_reports(
    rows: list[dict[str, Any]],
    save_dir: Path,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Schreibt EINEN kombinierten JSON-Report + Text-Report direkt in save_dir."""
    reporting_cfg = cfg.get('reporting', {})
    enabled = bool(reporting_cfg.get('series_reports_enabled', True))

    result = {
        'enabled': enabled,
        'series_count': 0,
        'reported_image_count': 0,
        'json_report_count': 0,
        'json_report_path': '',
        'text_report_path': '',
    }
    if not enabled:
        return result

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        series_id = str(row.get('series_id', ''))
        if not series_id or series_id == 'single':
            continue
        grouped.setdefault(series_id, []).append(row)

    if not grouped:
        return result

    save_dir.mkdir(parents=True, exist_ok=True)
    reports = [
        _series_report_from_rows(series_id, grouped[series_id])
        for series_id in sorted(grouped)
    ]

    combined_report = {
        'schema_version': 'series-report-v1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'series_count': len(reports),
        'series': reports,
    }
    json_path = save_dir / 'series_report.json'
    save_report(combined_report, json_path)

    text_path = save_dir / 'series_report.txt'
    save_text_report(_batch_text_report(reports), text_path)

    result.update({
        'series_count': len(reports),
        'reported_image_count': sum(
            report['series_size'] for report in reports
        ),
        'json_report_count': 1,
        'json_report_path': str(json_path),
        'text_report_path': str(text_path),
    })
    return result