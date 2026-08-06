from __future__ import annotations

import json
import pickle
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import face_recognition
except Exception:  # pragma: no cover
    face_recognition = None

IMAGE_EXTS = {'.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG'}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def get_cache_paths(cfg: dict) -> dict[str, Path]:
    fr_cfg = cfg.get('family_recognition', {})
    cache_dir = Path(fr_cfg.get('cache_dir', 'models/family_faces'))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        'dir': cache_dir,
        'encodings': cache_dir / 'family_encodings.pkl',
        'meta': cache_dir / 'family_encodings.meta.json',
        'index': cache_dir / 'family_index.json',
        'report': cache_dir / 'last_rebuild_report.json',
    }


def _selected_reference_images(reference_dir: Path, max_images_per_person: int) -> dict[str, list[Path]]:
    selected = {}
    for person_dir in sorted(reference_dir.iterdir()):
        if not person_dir.is_dir():
            continue
        images = [p for p in sorted(person_dir.iterdir()) if p.suffix in IMAGE_EXTS]
        selected[person_dir.name] = images[:max_images_per_person]
    return selected


def build_reference_state(cfg: dict) -> dict:
    fr_cfg = cfg.get('family_recognition', {})
    reference_dir = Path(fr_cfg.get('reference_dir', 'family_faces'))
    max_images = int(fr_cfg.get('max_reference_images_per_person', 200))
    state = {
        'reference_dir': str(reference_dir),
        'max_reference_images_per_person': max_images,
        'people': {},
    }
    if not reference_dir.exists():
        return state
    for person, images in _selected_reference_images(reference_dir, max_images).items():
        rows = []
        for img in images:
            stat = img.stat()
            rows.append({
                'file': img.name,
                'size': stat.st_size,
                'mtime_ns': stat.st_mtime_ns,
            })
        state['people'][person] = rows
    return state


def _cache_matches(cfg: dict, meta: dict) -> bool:
    expected = build_reference_state(cfg)
    return meta.get('reference_state') == expected


def _load_cache(cfg: dict) -> dict | None:
    paths = get_cache_paths(cfg)
    if not paths['encodings'].exists() or not paths['meta'].exists():
        return None
    meta = json.loads(paths['meta'].read_text(encoding='utf-8'))
    if not _cache_matches(cfg, meta):
        return None
    with paths['encodings'].open('rb') as handle:
        payload = pickle.load(handle)
    model = {
        'enabled': True,
        'library_available': face_recognition is not None,
        'reference_dir': cfg.get('family_recognition', {}).get('reference_dir'),
        'people': payload.get('people', {}),
        'tolerance': float(cfg.get('family_recognition', {}).get('match_tolerance', 0.48)),
        'status': 'cache_loaded',
        'used_cache': True,
        'rebuilt_cache': False,
        'cache_dir': str(paths['dir']),
        'cache_meta_path': str(paths['meta']),
        'cache_encodings_path': str(paths['encodings']),
        'person_count': len(payload.get('people', {})),
    }
    return model


def _write_cache(cfg: dict, people: dict, status: str, loaded_people: list[str]) -> dict:
    paths = get_cache_paths(cfg)
    payload = {'people': people}
    meta = {
        'created_at': now(),
        'status': status,
        'reference_state': build_reference_state(cfg),
        'people': loaded_people,
        'person_count': len(loaded_people),
    }
    with paths['encodings'].open('wb') as handle:
        pickle.dump(payload, handle)
    paths['meta'].write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    paths['index'].write_text(json.dumps({'people': loaded_people, 'person_count': len(loaded_people)}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'cache_dir': str(paths['dir']),
        'cache_meta_path': str(paths['meta']),
        'cache_encodings_path': str(paths['encodings']),
    }


def prepare_family_model(cfg: dict, force_rebuild: bool = False, allow_when_disabled: bool = False) -> dict:
    fr_cfg = cfg.get('family_recognition', {})
    model = {
        'enabled': bool(fr_cfg.get('enabled', False)),
        'library_available': face_recognition is not None,
        'reference_dir': fr_cfg.get('reference_dir'),
        'people': {},
        'status': 'disabled',
        'used_cache': False,
        'rebuilt_cache': False,
        'cache_dir': str(get_cache_paths(cfg)['dir']),
        'cache_meta_path': str(get_cache_paths(cfg)['meta']),
        'cache_encodings_path': str(get_cache_paths(cfg)['encodings']),
        'person_count': 0,
    }
    if not model['enabled'] and not allow_when_disabled:
        return model
    if face_recognition is None:
        model['status'] = 'face_library_missing'
        return model

    reference_dir = Path(fr_cfg.get('reference_dir', 'family_faces'))
    if not reference_dir.exists():
        model['status'] = 'reference_dir_missing'
        return model

    cache_enabled = bool(fr_cfg.get('cache_enabled', True))
    if cache_enabled and not force_rebuild:
        cached = _load_cache(cfg)
        if cached is not None:
            return cached

    tolerance = float(fr_cfg.get('match_tolerance', 0.48))
    max_images_per_person = int(fr_cfg.get('max_reference_images_per_person', 200))
    min_images_per_person = int(fr_cfg.get('min_reference_images_per_person', 3))
    people = {}
    loaded_people = []
    for person, images in _selected_reference_images(reference_dir, max_images_per_person).items():
        encodings = []
        for img_path in images:
            try:
                image = face_recognition.load_image_file(str(img_path))
                found = face_recognition.face_encodings(image)
                if found:
                    encodings.append(found[0])
            except Exception:
                continue
        if len(encodings) >= min_images_per_person:
            people[person] = {'encodings': encodings, 'samples': len(encodings)}
            loaded_people.append(person)
    model.update({
        'people': people,
        'tolerance': tolerance,
        'status': 'cache_rebuilt' if cache_enabled else 'ready_no_cache',
        'used_cache': False,
        'rebuilt_cache': cache_enabled,
        'person_count': len(loaded_people),
    })
    if cache_enabled:
        model.update(_write_cache(cfg, people, model['status'], loaded_people))
    return model


def write_rebuild_report(cfg: dict, report: dict) -> str:
    paths = get_cache_paths(cfg)
    payload = dict(report)
    payload['written_at'] = now()
    paths['report'].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return str(paths['report'])


def load_family_model(cfg: dict) -> dict:
    return prepare_family_model(cfg, force_rebuild=bool(cfg.get('family_recognition', {}).get('force_cache_rebuild', False)))


def rebuild_family_cache(cfg: dict) -> dict:
    model = prepare_family_model(cfg, force_rebuild=True, allow_when_disabled=True)
    report = {
        'status': model.get('status'),
        'cache_dir': model.get('cache_dir'),
        'cache_meta_path': model.get('cache_meta_path'),
        'cache_encodings_path': model.get('cache_encodings_path'),
        'person_count': model.get('person_count', 0),
        'used_cache': model.get('used_cache', False),
        'rebuilt_cache': model.get('rebuilt_cache', False),
    }
    report['report_path'] = write_rebuild_report(cfg, report)
    return report


def build_family_tags(people: list[str]) -> list[str]:
    if not people:
        return []
    tags = ['family:match:true']
    for person in sorted(set(people)):
        tags.append(f'person:{person}')
    return sorted(set(tags))


def detect_family_members(image_path: Path, cfg: dict, model: dict) -> dict:
    fr_cfg = cfg.get('family_recognition', {})
    result = {
        'status': model.get('status', 'disabled'),
        'detected_people': [],
        'family_score': 0.0,
        'protected_by_family_rule': False,
        'tags': [],
        'regions': [],
        'metadata_tags_written': False,
        'metadata_write_status': 'not_attempted',
    }
    if not fr_cfg.get('enabled', False):
        return result
    if model.get('status') in {'disabled', 'face_library_missing', 'reference_dir_missing'}:
        return result
    if not model.get('people'):
        result['status'] = 'no_reference_faces_loaded'
        return result
    try:
        image = face_recognition.load_image_file(str(image_path))
        locations = face_recognition.face_locations(image)
        encodings = face_recognition.face_encodings(image, locations)
    except Exception:
        result['status'] = 'image_read_error'
        return result

    weights = fr_cfg.get('person_weights', {}) or {}
    seen = []
    regions = []
    for loc, enc in zip(locations, encodings):
        best_name = None
        best_distance = None
        for person, pdata in model['people'].items():
            distances = face_recognition.face_distance(pdata['encodings'], enc)
            if len(distances) == 0:
                continue
            distance = float(min(distances))
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_name = person
        if best_name is not None and best_distance is not None and best_distance <= float(model['tolerance']):
            if best_name not in seen:
                seen.append(best_name)
            top, right, bottom, left = loc
            regions.append({'name': best_name, 'left': left, 'top': top, 'right': right, 'bottom': bottom, 'distance': round(best_distance, 4)})

    score = 0.0
    for person in seen:
        score += float(weights.get(person, fr_cfg.get('default_person_weight', 0.35)))
    score = min(1.0, score)
    result.update({
        'status': 'matched' if seen else 'no_family_match',
        'detected_people': seen,
        'family_score': score,
        'protected_by_family_rule': bool(seen) and bool(fr_cfg.get('protect_detected_family', True)),
        'tags': build_family_tags(seen),
        'regions': regions,
    })
    return result


def write_native_tags(image_path: Path, tags: list[str], cfg: dict, face_regions: list[dict] | None = None) -> tuple[bool, str]:
    fr_cfg = cfg.get('family_recognition', {})
    if not tags:
        return False, 'no_tags'
    exiftool_path = shutil.which(fr_cfg.get('exiftool_path', 'exiftool'))
    if not exiftool_path:
        return False, 'exiftool_missing'
    cmd = [exiftool_path, '-overwrite_original']
    for tag in sorted(set(tags)):
        cmd.append(f'-XMP-dc:Subject+={tag}')
        cmd.append(f'-IPTC:Keywords+={tag}')
    cmd.append(str(image_path))
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True)
    except Exception:
        return False, 'exiftool_exec_error'
    return completed.returncode == 0, 'ok' if completed.returncode == 0 else 'exiftool_failed'
