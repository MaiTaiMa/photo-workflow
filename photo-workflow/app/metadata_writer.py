from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _bool(cfg: dict, key: str, default: bool) -> bool:
    return bool(cfg.get('metadata_culling', {}).get(key, default))


def _as_people(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(',') if part.strip()]


def _score_band(value) -> str | None:
    if value is None or value == '':
        return None
    try:
        value = float(value)
    except Exception:
        return None
    if value < 0:
        value = 0.0
    if value > 1:
        value = 1.0
    lo = int(value * 100) // 10 * 10
    hi = min(lo + 9, 99)
    return f'{lo:02d}_{hi:02d}'


def build_culling_keywords(row: dict, cfg: dict) -> list[str]:
    mc = cfg.get('metadata_culling', {})
    schema = str(mc.get('keyword_schema', 'namespaced_v1')).strip().lower()
    if schema != 'namespaced_v1':
        schema = 'namespaced_v1'
    rating = int(row.get('star_rating', 0) or 0)
    keywords = [
        'workflow:ai_cull',
        f"decision:{str(row.get('decision', 'unknown')).lower()}",
        f"decision_reason:{str(row.get('decision_reason', 'unknown')).lower()}",
        f'rating:stars:{rating}',
    ]
    series_id = row.get('series_id')
    if series_id and str(series_id) != 'single':
        keywords.append(f'series:id:{series_id}')
        keywords.append(f"series:size:{int(row.get('series_size', 1) or 1)}")
        keywords.append(f"series:rank:{int(row.get('series_rank', 1) or 1)}")
        keywords.append(f"series:best:{str(bool(row.get('series_best', False))).lower()}")
    elif series_id:
        keywords.append('series:type:single')
    face_status = str(row.get('face_status', '') or '').strip()
    if face_status:
        keywords.append(f'face:status:{face_status}')
    protected = bool(row.get('protected_by_family_rule', False))
    if row.get('family_score') not in (None, ''):
        keywords.append(f'family:match:{str(float(row.get("family_score", 0.0)) > 0.0).lower()}')
    if protected:
        keywords.append('family:protected:true')
    for person in _as_people(row.get('detected_people')):
        keywords.append(f'person:{person}')
    if _bool(cfg, 'write_score_bands', True):
        score_fields = {
            'final': row.get('final_score'),
            'base': row.get('base_score'),
            'reference': row.get('reference_score'),
            'personal': row.get('personal_score'),
            'family': row.get('family_score'),
        }
        for label, value in score_fields.items():
            band = _score_band(value)
            if band:
                keywords.append(f'score_band:{label}:{band}')
    if _bool(cfg, 'write_raw_scores_to_keywords', False):
        score_fields = {
            'final': row.get('final_score'),
            'base': row.get('base_score'),
            'reference': row.get('reference_score'),
            'personal': row.get('personal_score'),
            'family': row.get('family_score'),
        }
        for label, value in score_fields.items():
            if value not in (None, ''):
                keywords.append(f'score:{label}:{float(value):.2f}')
    return sorted(set(keywords))


def write_culling_metadata(path: str | Path, row: dict, cfg: dict) -> tuple[bool, str]:
    mc = cfg.get('metadata_culling', {})
    if not bool(mc.get('enabled', True)):
        return False, 'disabled'
    exiftool = str(mc.get('exiftool_path', 'exiftool'))
    if shutil.which(exiftool) is None:
        return False, 'exiftool_missing'
    target = Path(path)
    rating = int(row.get('star_rating', 0) or 0)
    keywords = build_culling_keywords(row, cfg) if _bool(cfg, 'write_keywords', True) else []
    cmd = [exiftool]
    if not bool(mc.get('keep_backup', False)):
        cmd.append('-overwrite_original')
    if _bool(cfg, 'write_rating', True):
        cmd.append(f'-XMP:Rating={rating}')
    for kw in keywords:
        cmd.append(f'-XMP-dc:Subject+={kw}')
    cmd.append(str(target))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, 'written'
    except subprocess.CalledProcessError as exc:
        msg = (exc.stderr or exc.stdout or '').strip()
        return False, f'failed:{msg[:120]}' if msg else 'failed'
