from __future__ import annotations

from statistics import mean, pstdev

from pathlib import Path
import csv
import json
from datetime import datetime
from typing import List, Dict
import numpy as np

from metadata_rating import read_rating
from aesthetic import extract_features, generic_aesthetic_score


IMAGE_EXTS = {'.jpg', '.jpeg', '.JPG', '.JPEG'}


def collect_labeled_images(images_dir: str | Path) -> List[Dict[str, float]]:
    rows = []
    for path in sorted(Path(images_dir).rglob('*')):
        if path.suffix not in IMAGE_EXTS or not path.is_file():
            continue
        rating = read_rating(path)
        if rating is None:
            continue
        features = extract_features(path)
        rows.append({
            'path': str(path),
            'rating': float(rating),
            'generic_score': generic_aesthetic_score(path),
            'megapixels': features['megapixels'],
            'aspect_score': features['aspect_score'],
            'portrait': features['portrait'],
            'filesize_mb': features['filesize_mb'],
            'edge_var': features['edge_var'],
        })
    return rows


def fit_personal_model(rows: List[Dict[str, float]]) -> Dict:
    feature_names = ['bias', 'generic_score', 'megapixels', 'aspect_score', 'portrait', 'filesize_mb', 'edge_var']
    X = []
    y = []
    for row in rows:
        X.append([
            1.0,
            row['generic_score'],
            row['megapixels'],
            row['aspect_score'],
            row['portrait'],
            row['filesize_mb'],
            row['edge_var'],
        ])
        y.append(row['rating'] / 5.0)
    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)
    weights, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ weights
    score_min = float(pred.min()) if len(pred) else 0.0
    score_max = float(pred.max()) if len(pred) else 1.0
    scale = score_max - score_min if score_max != score_min else 1.0
    return {
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'feature_names': feature_names,
        'weights': {name: float(value) for name, value in zip(feature_names, weights)},
        'score_offset': -score_min,
        'score_scale': scale,
        'training_rows': len(rows),
    }


def export_labels(rows: List[Dict[str, float]], csv_path: str | Path) -> None:
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ['path', 'rating'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def train_from_directory(images_dir: str | Path, model_out: str | Path, labels_out: str | Path, min_images: int = 20) -> Dict:
    rows = collect_labeled_images(images_dir)
    if len(rows) < int(min_images):
        raise ValueError(f'Not enough labeled images: found {len(rows)}, need at least {min_images}.')
    model = fit_personal_model(rows)
    export_labels(rows, labels_out)
    model_out = Path(model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    model_out.write_text(json.dumps(model, indent=2), encoding='utf-8')
    return model


PERSONAL_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.JPG', '.JPEG', '.PNG', '.WEBP', '.BMP', '.TIF', '.TIFF'}


def _personal_cfg(cfg: dict) -> dict:
    section = cfg.get('personal_scoring', {}) or {}
    source_dir = section.get('source_dir') or cfg.get('training', {}).get('sample_images_dir')
    model_path = section.get('model_path') or cfg.get('paths', {}).get('personal_model')
    cache_dir = section.get('cache_dir') or str(Path(model_path).parent)
    return {
        'enabled': bool(section.get('enabled', True)),
        'source_dir': str(source_dir),
        'model_path': str(model_path),
        'cache_dir': str(cache_dir),
        'cache_enabled': bool(section.get('cache_enabled', True)),
        'cache_rebuild_mode': str(section.get('cache_rebuild_mode', 'incremental')),
        'force_cache_rebuild': bool(section.get('force_cache_rebuild', False)),
        'auto_train_on_change': bool(section.get('auto_train_on_change', True)),
        'recursive': bool(section.get('recursive', False)),
        'min_reference_images': int(section.get('min_reference_images', 5)),
    }


def _iter_personal_images(source_dir: Path, recursive: bool) -> list[Path]:
    if not source_dir.exists():
        return []
    iterator = source_dir.rglob('*') if recursive else source_dir.iterdir()
    return sorted([p for p in iterator if p.is_file() and p.suffix in PERSONAL_IMAGE_EXTS])


def _personal_cache_paths(cfg: dict) -> dict:
    pcfg = _personal_cfg(cfg)
    cache_dir = Path(pcfg['cache_dir'])
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = Path(pcfg['model_path'])
    return {
        'dir': cache_dir,
        'model': model_path,
        'meta': cache_dir / 'personal_model_meta.json',
        'report': cache_dir / 'last_personal_rebuild_report.json',
    }


def build_personal_reference_state(cfg: dict) -> dict:
    pcfg = _personal_cfg(cfg)
    source_dir = Path(pcfg['source_dir'])
    images = _iter_personal_images(source_dir, pcfg['recursive'])
    return {
        'source_dir': str(source_dir),
        'recursive': pcfg['recursive'],
        'images': [
            {
                'relative_path': str(p.relative_to(source_dir)),
                'size': p.stat().st_size,
                'mtime_ns': p.stat().st_mtime_ns,
            }
            for p in images
        ],
    }


def build_personal_model_from_directory(images_dir: str | Path, model_out: str | Path, recursive: bool = False) -> dict:
    from aesthetic import extract_features, generic_aesthetic_score
    images_dir = Path(images_dir)
    model_out = Path(model_out)
    rows = []
    for image_path in _iter_personal_images(images_dir, recursive):
        feats = extract_features(image_path)
        rows.append({
            'generic_score': float(generic_aesthetic_score(image_path)),
            'megapixels': float(feats['megapixels']),
            'aspect_score': float(feats['aspect_score']),
            'portrait': float(feats['portrait']),
            'filesize_mb': float(feats['filesize_mb']),
            'edge_var': float(feats['edge_var']),
        })
    if not rows:
        raise ValueError('No usable sample images found for personal model.')
    feature_names = list(rows[0].keys())
    stats = {}
    for name in feature_names:
        values = [float(r[name]) for r in rows]
        stats[name] = {
            'mean': mean(values),
            'std': pstdev(values) if len(values) > 1 else 0.05,
        }
    model = {
        'model_type': 'prototype_v1',
        'feature_stats': stats,
        'training_rows': len(rows),
        'source_dir': str(images_dir),
    }
    model_out.parent.mkdir(parents=True, exist_ok=True)
    model_out.write_text(json.dumps(model, indent=2), encoding='utf-8')
    return model


def _write_personal_report(cfg: dict, report: dict) -> None:
    paths = _personal_cache_paths(cfg)
    paths['report'].write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')


def load_or_rebuild_personal_model(cfg: dict):
    from aesthetic import load_personal_model
    pcfg = _personal_cfg(cfg)
    paths = _personal_cache_paths(cfg)
    info = {
        'status': 'disabled' if not pcfg['enabled'] else 'missing',
        'used_cache': False,
        'rebuilt_cache': False,
        'source_dir': pcfg['source_dir'],
        'source_image_count': 0,
        'model_path': str(paths['model']),
    }
    if not pcfg['enabled']:
        return None, info
    source_dir = Path(pcfg['source_dir'])
    state = build_personal_reference_state(cfg)
    images = state['images']
    info['source_image_count'] = len(images)
    if not source_dir.exists():
        info['status'] = 'reference_dir_missing'
        _write_personal_report(cfg, info | {'reference_state': state})
        return None, info
    if len(images) < pcfg['min_reference_images']:
        info['status'] = 'not_enough_reference_images'
        _write_personal_report(cfg, info | {'reference_state': state})
        return None, info
    rebuild = bool(pcfg['force_cache_rebuild']) or not paths['model'].exists()
    meta = {}
    if paths['meta'].exists():
        try:
            meta = json.loads(paths['meta'].read_text(encoding='utf-8'))
        except Exception:
            meta = {}
    if pcfg['auto_train_on_change'] and meta.get('reference_state') != state:
        rebuild = True
    if rebuild:
        model = build_personal_model_from_directory(source_dir, paths['model'], recursive=pcfg['recursive'])
        info['status'] = 'cache_rebuilt'
        info['rebuilt_cache'] = True
        payload = {'reference_state': state, 'status': info['status'], 'source_image_count': info['source_image_count']}
        paths['meta'].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        _write_personal_report(cfg, info | payload)
        return model, info
    model = load_personal_model(paths['model'])
    info['status'] = 'cache_used' if model else 'model_missing'
    info['used_cache'] = bool(model)
    _write_personal_report(cfg, info | {'reference_state': state})
    return model, info
