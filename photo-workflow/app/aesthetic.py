from __future__ import annotations

from pathlib import Path
from math import log1p
from typing import Dict, Optional
import json
import statistics

import numpy as np

try:
    from PIL import Image, ImageFilter, ImageStat
except Exception:
    Image = None
    ImageFilter = None
    ImageStat = None

try:
    import face_recognition
except Exception:
    face_recognition = None

IMAGE_EXTS = {'.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG'}
_REFERENCE_PROFILE_CACHE: dict[tuple[str, bool, int], np.ndarray] = {}


def clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _variance(values) -> float:
    if not values:
        return 0.0
    try:
        return statistics.pvariance(values)
    except statistics.StatisticsError:
        return 0.0


def _open_image(path: Path):
    if Image is None:
        raise RuntimeError('Pillow not available')
    return Image.open(path).convert('RGB')


def extract_features(image_path: str | Path) -> Dict[str, float]:
    path = Path(image_path)
    size_bytes = path.stat().st_size if path.exists() else 0
    width = 0
    height = 0
    edge_var = 0.0
    mean_luma = 0.5
    clipped_dark = 0.0
    clipped_bright = 0.0
    contrast = 0.0
    saturation = 0.0

    if Image is not None:
        try:
            with _open_image(path) as img:
                width, height = img.size
                gray = img.convert('L')
                edges = gray.filter(ImageFilter.FIND_EDGES)
                stat = ImageStat.Stat(edges)
                edge_var = float(stat.var[0]) if stat.var else 0.0
                gray_arr = np.asarray(gray, dtype=np.float32)
                hsv = np.asarray(img.convert('HSV'), dtype=np.float32)
                mean_luma = float(gray_arr.mean() / 255.0) if gray_arr.size else 0.5
                clipped_dark = float((gray_arr < 5).mean()) if gray_arr.size else 0.0
                clipped_bright = float((gray_arr > 250).mean()) if gray_arr.size else 0.0
                contrast = float(gray_arr.std() / 64.0) if gray_arr.size else 0.0
                saturation = float(hsv[:, :, 1].mean() / 255.0) if hsv.size else 0.0
        except Exception:
            width = 0
            height = 0
            edge_var = 0.0
            mean_luma = 0.5
            clipped_dark = 0.0
            clipped_bright = 0.0
            contrast = 0.0
            saturation = 0.0

    megapixels = (width * height) / 1_000_000 if width and height else 0.0
    aspect = (width / height) if width and height else 1.0
    aspect_targets = [1.5, 1.3333, 1.7777]
    aspect_score = 1.0 - min(abs(aspect - target) for target in aspect_targets)
    aspect_score = clip01(aspect_score)
    portrait = 1.0 if height > width else 0.0
    filesize_mb = size_bytes / (1024 * 1024) if size_bytes else 0.0

    return {
        'width': float(width),
        'height': float(height),
        'megapixels': float(megapixels),
        'aspect_ratio': float(aspect),
        'aspect_score': float(aspect_score),
        'portrait': float(portrait),
        'filesize_mb': float(filesize_mb),
        'edge_var': float(edge_var),
        'mean_luma': float(mean_luma),
        'clipped_dark': float(clipped_dark),
        'clipped_bright': float(clipped_bright),
        'contrast': float(contrast),
        'saturation': float(saturation),
    }


def generic_aesthetic_score(image_path: str | Path) -> float:
    f = extract_features(image_path)
    resolution_score = clip01(f['megapixels'] / 24.0)
    size_score = clip01(log1p(f['filesize_mb']) / log1p(12.0))
    sharpness_score = clip01(log1p(f['edge_var']) / log1p(8000.0))
    score = (
        0.35 * resolution_score
        + 0.25 * size_score
        + 0.25 * sharpness_score
        + 0.15 * f['aspect_score']
    )
    return clip01(score)


def sharpness_component(image_path: str | Path) -> float:
    f = extract_features(image_path)
    return clip01(log1p(f['edge_var']) / log1p(8000.0))


def exposure_component(image_path: str | Path) -> float:
    f = extract_features(image_path)
    clip_penalty = min(1.0, (f['clipped_dark'] + f['clipped_bright']) * 5.0)
    balance_penalty = abs(f['mean_luma'] - 0.5) * 1.2
    return clip01(1.0 - (0.6 * clip_penalty + 0.4 * balance_penalty))


def classic_aesthetic_component(image_path: str | Path) -> float:
    f = extract_features(image_path)
    score = (
        0.35 * clip01(f['contrast'])
        + 0.25 * clip01(f['saturation'])
        + 0.20 * (1 - abs(f['mean_luma'] - 0.5) * 2)
        + 0.20 * clip01(log1p(f['edge_var']) / log1p(8000.0))
    )
    return clip01(score)


def _simple_embedding(image_path: str | Path, size: int = 32) -> np.ndarray:
    with _open_image(Path(image_path)) as img:
        img = img.resize((size, size))
        gray = img.convert('L')
        edges = gray.filter(ImageFilter.FIND_EDGES)
        rgb = np.asarray(img, dtype=np.float32) / 255.0
        gray_arr = np.asarray(gray, dtype=np.float32) / 255.0
        edge_arr = np.asarray(edges, dtype=np.float32) / 255.0
    feat = np.concatenate([rgb.mean(axis=(0, 1)), rgb.std(axis=(0, 1)), gray_arr.reshape(-1), edge_arr.reshape(-1)])
    norm = float(np.linalg.norm(feat))
    return feat if norm <= 1e-12 else (feat / norm)


def _reference_images(folder: Path, recursive: bool) -> list[Path]:
    iterator = folder.rglob('*') if recursive else folder.glob('*')
    return [p for p in sorted(iterator) if p.is_file() and p.suffix in IMAGE_EXTS]



def _reference_cfg(cfg: dict) -> dict:
    ref_cfg = cfg.get('culling', {}).get('reference_scoring', {}) or {}
    base_dir = Path(cfg.get('paths', {}).get('base_dir', '.'))
    folder = Path(ref_cfg.get('folder', base_dir / 'reference_images'))
    preview_size = int(ref_cfg.get('preview_size', 32))
    cache_dir = Path(ref_cfg.get('cache_dir', base_dir / 'models' / 'reference_scoring'))
    return {
        'enabled': bool(ref_cfg.get('enabled', False)),
        'folder': folder,
        'recursive': bool(ref_cfg.get('recursive', False)),
        'preview_size': preview_size,
        'cache_enabled': bool(ref_cfg.get('cache_enabled', True)),
        'cache_dir': cache_dir,
        'force_cache_rebuild': bool(ref_cfg.get('force_cache_rebuild', False)),
    }


def _reference_cache_paths(cfg: dict) -> dict:
    ref = _reference_cfg(cfg)
    cache_dir = Path(ref['cache_dir'])
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        'dir': cache_dir,
        'profile': cache_dir / 'reference_profile.npy',
        'meta': cache_dir / 'reference_profile_meta.json',
        'report': cache_dir / 'last_reference_profile_report.json',
    }


def build_reference_profile_state(cfg: dict) -> dict:
    ref = _reference_cfg(cfg)
    folder = Path(ref['folder'])
    refs = _reference_images(folder, ref['recursive']) if folder.exists() and folder.is_dir() else []
    return {
        'folder': str(folder),
        'recursive': ref['recursive'],
        'preview_size': ref['preview_size'],
        'images': [
            {
                'relative_path': str(p.relative_to(folder)),
                'size': p.stat().st_size,
                'mtime_ns': p.stat().st_mtime_ns,
            }
            for p in refs
        ],
    }


def _write_reference_report(cfg: dict, payload: dict) -> None:
    paths = _reference_cache_paths(cfg)
    paths['report'].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def ensure_reference_profile(cfg: dict) -> tuple[Optional[np.ndarray], dict]:
    ref = _reference_cfg(cfg)
    info = {
        'status': 'disabled' if not ref['enabled'] else 'missing',
        'used_cache': False,
        'rebuilt_cache': False,
        'reference_image_count': 0,
        'folder': str(ref['folder']),
        'cache_dir': str(ref['cache_dir']),
        'preview_size': ref['preview_size'],
    }
    if not ref['enabled']:
        return None, info
    folder = Path(ref['folder'])
    if not str(folder) or not folder.exists() or not folder.is_dir() or Image is None:
        info['status'] = 'reference_dir_missing' if not folder.exists() else 'pillow_missing'
        _write_reference_report(cfg, info)
        return None, info
    state = build_reference_profile_state(cfg)
    info['reference_image_count'] = len(state['images'])
    if not state['images']:
        info['status'] = 'no_reference_images'
        _write_reference_report(cfg, info | {'reference_state': state})
        return None, info
    key = (str(folder.resolve()), ref['recursive'], ref['preview_size'])
    paths = _reference_cache_paths(cfg)
    rebuild = bool(ref['force_cache_rebuild'])
    meta = {}
    if paths['meta'].exists():
        try:
            meta = json.loads(paths['meta'].read_text(encoding='utf-8'))
        except Exception:
            meta = {}
    if key in _REFERENCE_PROFILE_CACHE and not rebuild:
        info['status'] = 'memory_cache_used'
        info['used_cache'] = True
        _write_reference_report(cfg, info | {'reference_state': state})
        return _REFERENCE_PROFILE_CACHE[key], info
    if ref['cache_enabled'] and paths['profile'].exists() and meta.get('reference_state') == state and not rebuild:
        try:
            profile = np.load(paths['profile'])
            _REFERENCE_PROFILE_CACHE[key] = profile
            info['status'] = 'cache_used'
            info['used_cache'] = True
            _write_reference_report(cfg, info | {'reference_state': state})
            return profile, info
        except Exception:
            rebuild = True
    refs = _reference_images(folder, ref['recursive'])
    emb = np.stack([_simple_embedding(p, size=ref['preview_size']) for p in refs])
    profile = emb.mean(axis=0)
    norm = float(np.linalg.norm(profile))
    profile = profile if norm <= 1e-12 else (profile / norm)
    _REFERENCE_PROFILE_CACHE[key] = profile
    if ref['cache_enabled']:
        np.save(paths['profile'], profile)
        meta_payload = {'reference_state': state, 'preview_size': ref['preview_size'], 'status': 'cache_rebuilt'}
        paths['meta'].write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False), encoding='utf-8')
    info['status'] = 'cache_rebuilt'
    info['rebuilt_cache'] = True
    _write_reference_report(cfg, info | {'reference_state': state})
    return profile, info


def reference_score_component(image_path: str | Path, cfg: dict) -> Optional[float]:
    ref = _reference_cfg(cfg)
    if not ref['enabled']:
        return None
    runtime_profile = cfg.get('culling', {}).get('reference_scoring', {}).get('_runtime_profile')
    profile = runtime_profile
    if profile is None:
        profile, _ = ensure_reference_profile(cfg)
    if profile is None:
        return None
    img_emb = _simple_embedding(image_path, size=ref['preview_size'])
    return clip01((float(np.dot(img_emb, profile)) + 1.0) / 2.0)


def eye_open_component(image_path: str | Path, cfg: dict) -> Optional[float]:
    eye_cfg = cfg.get('culling', {}).get('eye_detection', {})
    if not bool(eye_cfg.get('enabled', True)):
        return None
    if face_recognition is None:
        return None
    try:
        image = face_recognition.load_image_file(str(image_path))
        faces = face_recognition.face_landmarks(image)
    except Exception:
        return None
    if not faces:
        return None

    def eye_score(points) -> float:
        if len(points) < 6:
            return 0.5
        pts = np.asarray(points[:6], dtype=np.float32)
        d1 = np.linalg.norm(pts[1] - pts[5])
        d2 = np.linalg.norm(pts[2] - pts[4])
        d3 = np.linalg.norm(pts[0] - pts[3])
        ear = (d1 + d2) / (2.0 * d3 + 1e-6)
        return clip01((ear - 0.16) / 0.18)

    scores = []
    for face in faces:
        left = face.get('left_eye')
        right = face.get('right_eye')
        if not left or not right:
            continue
        scores.append((eye_score(left) + eye_score(right)) / 2.0)
    if not scores:
        return None
    return clip01(sum(scores) / len(scores))


def _normalized_active_weights(weight_map: dict[str, float], active: dict[str, Optional[float]]) -> dict[str, float]:
    valid = {k: float(weight_map.get(k, 0.0)) for k, v in active.items() if v is not None and float(weight_map.get(k, 0.0)) > 0}
    total = sum(valid.values()) or 1.0
    return {k: v / total for k, v in valid.items()}


def base_score_components(image_path: str | Path, cfg: dict) -> Dict[str, Optional[float]]:
    return {
        'sharp': sharpness_component(image_path),
        'aesth': classic_aesthetic_component(image_path),
        'exposure': exposure_component(image_path),
        'eyes': eye_open_component(image_path, cfg),
        'reference': reference_score_component(image_path, cfg),
    }


def weighted_base_score(components: Dict[str, Optional[float]], cfg: dict) -> float:
    weights = cfg.get('culling', {}).get('base_weights', {})
    normalized = _normalized_active_weights(weights, components)
    if not normalized:
        return clip01(generic_aesthetic_score(''))
    total = 0.0
    for key, weight in normalized.items():
        value = components.get(key)
        if value is not None:
            total += float(weight) * float(value)
    return clip01(total)


def load_personal_model(model_path: str | Path) -> Optional[dict]:
    path = Path(model_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def personal_model_score(image_path: str | Path, model: Optional[dict]) -> Optional[float]:
    if not model:
        return None
    f = extract_features(image_path)
    generic = generic_aesthetic_score(image_path)
    feature_map = {
        'bias': 1.0,
        'generic_score': generic,
        'megapixels': f['megapixels'],
        'aspect_score': f['aspect_score'],
        'portrait': f['portrait'],
        'filesize_mb': f['filesize_mb'],
        'edge_var': f['edge_var'],
    }
    if model.get('model_type') == 'prototype_v1':
        stats = model.get('feature_stats', {}) or {}
        distances = []
        for name, payload in stats.items():
            if name not in feature_map:
                continue
            mean_value = float(payload.get('mean', 0.0))
            std_value = max(float(payload.get('std', 0.0)), 1e-6)
            z_distance = abs(float(feature_map[name]) - mean_value) / (std_value * 2.5)
            distances.append(min(1.0, z_distance))
        if not distances:
            return None
        return clip01(1.0 - (sum(distances) / len(distances)))
    weights = model.get('weights', {})
    score = 0.0
    for name, weight in weights.items():
        score += float(weight) * float(feature_map.get(name, 0.0))
    scale = float(model.get('score_scale', 1.0)) or 1.0
    offset = float(model.get('score_offset', 0.0))
    normalized = (score + offset) / scale
    return clip01(normalized)
