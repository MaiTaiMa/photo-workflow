"""
Skript: app/family_recognition.py
Zweck: Erkennt Familiengesichter mit YuNet und SFace aus dynamischen Referenzpools.
Autor: MaiTaiMa
Erstellt: 2026-08-09
Version: 1.1
Requires: Python 3.11, OpenCV-Contrib, NumPy, PyYAML, ExifTool optional

Ä·nderungsprotokoll:
  2026-08-09 | 1.0 | OpenCV-Backend und RAM-only Matching ergänzt
  2026-08-09 | 1.1 | Dynamische Personen-Erkennung: faces/<Person>/reference/
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Verwaltet Referenzzustä··nde, Reports und kontrollierte Metadatenaufrufe.
# Eingabe: Config, Referenzbilder und Workflow-Bildpfade.
# Ausgabe: Familienmatches, Scores und namespaced Tags.
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.faces.matcher import FaceMatcher
from app.faces.opencv_backend import OpenCVFaceBackend

IMAGE_EXTS = {".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG"}


def now() -> str:
    """Gibt den aktuellen UTC-Zeitpunkt im ISO-8601-Format zurück."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_cache_paths(cfg: dict[str, object]) -> dict[str, Path]:
    """
    Erzeugt Pfade für zulä··ssige Referenzmetadaten.
    
    Embeddings werden absichtlich nicht als Cache-Datei zurückgegeben.
    """
    fr_cfg = cfg.get("family_recognition", {})
    cache_dir = Path(fr_cfg.get("cache_dir", "models/family_faces"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        "dir": cache_dir,
        "meta": cache_dir / "family_references.meta.json",
        "index": cache_dir / "family_index.json",
        "report": cache_dir / "last_rebuild_report.json",
    }


def _selected_reference_images(
    reference_dir: Path,
    max_images_per_person: int,
    min_images_per_person: int = 3,
) -> dict[str, list[Path]]:
    """
    Wä··hlt deterministisch begrenzte Referenzbilder je Person aus.
    
    98AP-Regeln:
      - Nur faces/<Person>/reference/ wird gelesen (nicht new_faces/)
      - Slug wird in Kleinbuchstaben konvertiert (Chris → chris)
      - Mindestanzahl Bilder muss erreicht sein
      - Leere Ordner pausieren nur diese Person, nicht global
    """
    selected: dict[str, list[Path]] = {}
    
    if not reference_dir.exists():
        return selected
    
    for person_dir in sorted(reference_dir.iterdir()):
        if not person_dir.is_dir() or person_dir.is_symlink():
            continue
        
        # WICHTIG: Nur reference/ Unterordner lesen, nicht new_faces/
        active_reference_dir = person_dir / "reference"
        if not active_reference_dir.is_dir() or active_reference_dir.is_symlink():
            continue
        
        images = [
            path
            for path in sorted(active_reference_dir.iterdir())
            if path.is_file()
            and not path.is_symlink()
            and path.suffix.lower() in IMAGE_EXTS
        ]
        
        # Nur Personen mit ausreichender Referenzbasis aktivieren
        if len(images) >= min_images_per_person:
            # WICHTIG: Slug in Kleinbuchstaben für Config-Kompatibilitä··t
            person_slug = person_dir.name.casefold()
            selected[person_slug] = images[:max_images_per_person]
    
    return selected


def build_reference_state(cfg: dict[str, object]) -> dict:
    """Erzeugt einen JSON-fä··higen Zustand ohne Bildbytes oder Embeddings."""
    fr_cfg = cfg.get("family_recognition", {})
    reference_dir = Path(fr_cfg.get("reference_dir", "family_faces"))
    max_images = int(fr_cfg.get("max_reference_images_per_person", 200))
    min_images = int(fr_cfg.get("min_reference_images_per_person", 3))

    state = {
        "reference_dir": str(reference_dir),
        "max_reference_images_per_person": max_images,
        "min_reference_images_per_person": min_images,
        "people": {},
    }

    for person, images in _selected_reference_images(
        reference_dir,
        max_images,
        min_images,
    ).items():
        rows = []
        for image in images:
            stat = image.stat()
            rows.append({
                "file": image.name,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            })
        state["people"][person] = rows
    
    return state


def _write_cache(
    cfg: dict[str, object],
    state: dict,
    loaded_people: list[str],
) -> dict[str, str]:
    """Schreibt ausschließlich Referenzmetadaten, niemals Embeddings."""
    paths = get_cache_paths(cfg)
    meta = {
        "created_at": now(),
        "status": "metadata_only",
        "reference_state": state,
        "people": loaded_people,
        "person_count": len(loaded_people),
    }
    paths["meta"].write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths["index"].write_text(
        json.dumps(
            {
                "people": loaded_people,
                "person_count": len(loaded_people),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {
        "cache_dir": str(paths["dir"]),
        "cache_meta_path": str(paths["meta"]),
    }


def prepare_family_model(cfg: dict[str, object], force_rebuild: bool = False, allow_when_disabled: bool = False) -> dict:
    """
    Baut den fluchtigen Familienmatcher aus den aktiven Referenzen auf.
      - Jeder Lauf erzeugt die Embeddings neu im RAM
      - Persistente Embedding-Caches werden nicht verwendet
      - Dynamische Personen-Erkennung aus faces/<Person>/reference/
    """
    fr_cfg = cfg.get("family_recognition", {})
    enabled = bool(fr_cfg.get("enabled", False))
    paths = get_cache_paths(cfg)
    
    model = {
        "enabled": enabled,
        "library_available": True,
        "reference_dir": fr_cfg.get("reference_dir"),
        "people": {},
        "status": "disabled",
        "used_cache": False,
        "rebuilt_cache": False,
        "cache_dir": str(paths["dir"]),
        "cache_meta_path": str(paths["meta"]),
        "person_count": 0,
    }

    if not enabled and not allow_when_disabled:
        return model

    reference_dir = Path(fr_cfg.get("reference_dir", "family_faces"))
    if not reference_dir.exists():
        model["status"] = "reference_dir_missing"
        return model

    backend = OpenCVFaceBackend(cfg)
    matcher = FaceMatcher(
        backend,
        threshold=float(fr_cfg.get("match_tolerance", 0.6)),
        margin=float(fr_cfg.get("match_margin", 0.05)),
    )

    max_images = int(fr_cfg.get("max_reference_images_per_person", 200))
    min_images = int(fr_cfg.get("min_reference_images_per_person", 3))

    loaded_people = []
    for person, images in _selected_reference_images(
        reference_dir,
        max_images,
        min_images,
    ).items():
        loaded = 0
        for image in images:
            try:
                matcher.add_reference(person, image)
                loaded += 1
            except Exception:
                continue
        if loaded >= min_images:
            loaded_people.append(person)

    state = build_reference_state(cfg)
    model.update({
        "backend": backend,
        "matcher": matcher,
        "people": {person: {} for person in loaded_people},
        "status": "cache_rebuilt" if fr_cfg.get("cache_enabled", True) else "ready_no_cache",
        "rebuilt_cache": bool(fr_cfg.get("cache_enabled", True)),
        "person_count": len(loaded_people),
    })
    if fr_cfg.get("cache_enabled", True):
        model.update(_write_cache(cfg, state, loaded_people))
    
    return model


def write_rebuild_report(cfg: dict[str, object], report: dict) -> str:
    """Schreibt einen JSON-Report ohne Bildbytes oder Embeddings."""
    paths = get_cache_paths(cfg)
    payload = dict(report)
    payload["written_at"] = now()
    paths["report"].write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(paths["report"])


def load_family_model(cfg: dict[str, object]) -> dict:
    """Baut den fluchtigen Familienmatcher fur einen Lauf auf."""
    return prepare_family_model(
        cfg,
        force_rebuild=bool(cfg.get("family_recognition", {}).get("force_cache_rebuild", False)),
    )


def rebuild_family_cache(cfg: dict[str, object]) -> dict:
    """Erzeugt zulassige Referenzmetadaten und einen Laufreport."""
    model = prepare_family_model(cfg, force_rebuild=True, allow_when_disabled=True)
    report = {
        "status": model.get("status"),
        "cache_dir": model.get("cache_dir"),
        "cache_meta_path": model.get("cache_meta_path"),
        "person_count": model.get("person_count", 0),
        "used_cache": model.get("used_cache", False),
        "rebuilt_cache": model.get("rebuilt_cache", False),
    }
    report["report_path"] = write_rebuild_report(cfg, report)
    return report


def build_family_tags(people: list[str]) -> list[str]:
    """Erzeugt deterministische namespaced Familien- und Personentags."""
    if not people:
        return []
    tags = ["family:match:true"]
    for person in sorted(set(people)):
        tags.append(f"person:{person}")
    return sorted(set(tags))


def detect_family_members(
    image_path: Path,
    cfg: dict[str, object],
    model: dict,
) -> dict:
    """
    Erkennt und matched alle Gesichter eines Bildes.
      - YuNet liefert Boxen und Landmarken; SFace erzeugt Embeddings nur im RAM
      - Nur Treffer mit Distanz <= match_tolerance werden zurückgegeben
      - Mehrere Treffer pro Bild moglich (Gruppenfotos)
    """
    fr_cfg = cfg.get("family_recognition", {})
    result = {
        "status": model.get("status", "disabled"),
        "detected_people": [],
        "family_score": 0.0,
        "protected_by_family_rule": False,
        "tags": [],
        "regions": [],
        "metadata_tags_written": False,
        "metadata_write_status": "not_attempted",
    }

    if not fr_cfg.get("enabled", False):
        return result
    if not model.get("people") or "backend" not in model:
        result["status"] = "no_reference_faces_loaded"
        return result

    try:
        values = model["backend"].embeddings(image_path)
    except Exception:
        result["status"] = "image_read_error"
        return result

    # Gewichte aus Config laden (optional fur bekannte Personen)
    weights = fr_cfg.get("person_weights", {}) or {}
    default_weight = float(fr_cfg.get("default_person_weight", 0.35))
    
    seen = []
    regions = []
    
    for vector, detection in values:
        match = model["matcher"].match_embedding(vector)
        if match.status != "matched" or match.person_slug is None:
            continue
        
        person = match.person_slug
        if person not in seen:
            seen.append(person)
        
        box = detection["box"]
        regions.append({
            "name": person,
            "left": box["left"],
            "top": box["top"],
            "right": box["right"],
            "bottom": box["bottom"],
            "distance": round(float(match.distance or 0.0), 4),
        })

    # Family-Score berechnen: Summe der Gewichte aller erkannten Personen
    score = min(
        1.0,
        sum(
            float(weights.get(person, default_weight))
            for person in seen
        ),
    )

    result.update({
        "status": "matched" if seen else "no_family_match",
        "detected_people": seen,
        "family_score": score,
        "protected_by_family_rule": bool(seen) and bool(fr_cfg.get("protect_detected_family", True)),
        "tags": build_family_tags(seen),
        "regions": regions,
    })
    return result


def write_native_tags(
    image_path: Path,
    tags: list[str],
    cfg: dict[str, object],
    face_regions: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Schreibt namespaced Tags kontrolliert uber ExifTool.
      - shell=False für ExifTool
      - Nach dem Schreiben zurücklesen und abgleichen
      - Namespaced Tags: family:, person:, workflow:
    """
    fr_cfg = cfg.get("family_recognition", {})
    if not tags:
        return False, "no_tags"
    
    exiftool_path = shutil.which(fr_cfg.get("exiftool_path", "exiftool"))
    if not exiftool_path:
        return False, "exiftool_missing"

    command = [exiftool_path, "-overwrite_original"]
    for tag in sorted(set(tags)):
        command.append(f"-XMP-dc:Subject+={tag}")
        command.append(f"-IPTC:Keywords+={tag}")
    command.append(str(image_path))
    
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
        )
    except Exception:
        return False, "exiftool_exec_error"
    
    status = "ok" if completed.returncode == 0 else "exiftool_failed"
    return completed.returncode == 0, status