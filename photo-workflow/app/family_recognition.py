# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/family_recognition.py
# PURPOSE:     Erkennt Familiengesichter mit YuNet und SFace aus dynamischen Referenzpools.
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.1
# REQUIRES:    Python 3.11, OpenCV-Contrib, NumPy, PyYAML, ExifTool optional
# CHANGES:
#   2026-08-09 | 1.0 | OpenCV-Backend und RAM-only Matching ergänzt
#   2026-08-09 | 1.1 | Dynamische Personen-Erkennung: faces/<Person>/reference/
# =============================================================================


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
    Schreibt namespaced Tags kontrolliert über ExifTool.

    Schreibt XMP-dc:Subject und IPTC:Keywords. Wenn
    family_recognition.write_face_regions aktiviert ist, werden erkannte
    Face-Bounding-Boxes zusätzlich als XMP-mwg-rs:RegionInfo geschrieben.

    Die Region-Quelle verwendet Pixelkoordinaten left/top/right/bottom.
    MWG-RS verwendet normalisierte Mittelpunktkoordinaten X/Y und W/H.
    person:<id> bleibt der technische Keyword-Schlüssel. RegionName verwendet
    den lesbaren Namen aus family_recognition.persons, mit id als Fallback.
    """
    import json
    import shutil
    import subprocess

    def _display_name(person_id: str, persons: object) -> str:
        # -----------------------------------------------------------------------
        # Liefert den lesbaren Namen zu einer technischen Personen-ID.
        # Eingabe: persons = optionale Liste aus config.yaml.
        # Fallback: person_id, damit die dynamische Ordner-Erkennung unverändert
        #           funktioniert, wenn kein Mapping gepflegt wurde.
        # -----------------------------------------------------------------------
        if not isinstance(persons, list):
            return person_id
        for person in persons:
            if not isinstance(person, dict):
                continue
            if str(person.get("id", "")) == person_id:
                name = str(person.get("name", "")).strip()
                return name or person_id
        return person_id

    def _read_regions(exiftool_path: str) -> list[dict]:
        # -----------------------------------------------------------------------
        # Liest MWG-RS-Regionen strukturiert per ExifTool zurück.
        # Ausgabe: RegionList oder leere Liste, falls keine Region existiert.
        # -----------------------------------------------------------------------
        readback = subprocess.run(
            [
                exiftool_path,
                "-j",
                "-struct",
                "-XMP-mwg-rs:RegionInfo",
                str(image_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        region_info = json.loads(readback.stdout)[0].get("RegionInfo", {})
        if not isinstance(region_info, dict):
            return []
        region_list = region_info.get("RegionList", [])
        return region_list if isinstance(region_list, list) else []

    def _canonical_regions(regions: list[dict]) -> list[dict]:
        # -----------------------------------------------------------------------
        # Reduziert Regionen auf die fachlich relevanten, vergleichbaren Felder.
        # Rundung entspricht der ExifTool-Schreibgenauigkeit von sechs Stellen.
        # -----------------------------------------------------------------------
        result = []
        for region in regions:
            area = region.get("Area", {}) if isinstance(region, dict) else {}
            result.append({
                "Name": str(region.get("Name", "")),
                "Type": str(region.get("Type", "")),
                "W": round(float(area.get("W", -1)), 6),
                "H": round(float(area.get("H", -1)), 6),
                "X": round(float(area.get("X", -1)), 6),
                "Y": round(float(area.get("Y", -1)), 6),
                "Unit": str(area.get("Unit", "")),
            })
        return result

    fr_cfg = cfg.get("family_recognition", {})
    if not tags:
        return False, "no_tags"

    exiftool_path = shutil.which(fr_cfg.get("exiftool_path", "exiftool"))
    if not exiftool_path:
        return False, "exiftool_missing"

    write_regions = bool(fr_cfg.get("write_face_regions", False))
    desired_regions: list[dict] = []

    # ======================================================================
    # SCHRITT 1: Regionen vollständig vorbereiten und validieren.
    # Keine Metadaten werden verändert, bevor alle Boxen valide sind.
    # ======================================================================
    if write_regions and face_regions:
        try:
            from PIL import Image
            with Image.open(image_path) as image:
                image_width, image_height = image.size
        except Exception:
            return False, "regions_image_read_failed"

        if image_width <= 0 or image_height <= 0:
            return False, "regions_invalid_image_size"

        try:
            for region in face_regions:
                left = float(region["left"])
                top = float(region["top"])
                right = float(region["right"])
                bottom = float(region["bottom"])

                width = right - left
                height = bottom - top
                if width <= 0 or height <= 0:
                    return False, "regions_invalid_box"

                x_normalized = (left + right) / (2.0 * image_width)
                y_normalized = (top + bottom) / (2.0 * image_height)
                width_normalized = width / image_width
                height_normalized = height / image_height

                if not all(
                    0.0 <= value <= 1.0
                    for value in (
                        x_normalized,
                        y_normalized,
                        width_normalized,
                        height_normalized,
                    )
                ):
                    return False, "regions_out_of_bounds"

                person_id = str(region.get("name", "unknown"))
                display_name = _display_name(
                    person_id,
                    fr_cfg.get("persons", []),
                )
                desired_regions.append({
                    "Name": display_name,
                    "Type": "Face",
                    "Area": {
                        "W": round(width_normalized, 6),
                        "H": round(height_normalized, 6),
                        "X": round(x_normalized, 6),
                        "Y": round(y_normalized, 6),
                        "Unit": "normalized",
                    },
                })
        except (KeyError, TypeError, ValueError):
            return False, "regions_invalid_input"

        # ==================================================================
        # SCHRITT 2: Vorhandene Regionen vor dem Schreiben prüfen.
        # Identischer Bestand: idempotent erfolgreich.
        # Abweichender Bestand: nicht überschreiben, sauber abbrechen.
        # ==================================================================
        try:
            existing_regions = _read_regions(exiftool_path)
        except Exception:
            return False, "regions_preflight_readback_failed"

        if existing_regions:
            if _canonical_regions(existing_regions) != _canonical_regions(desired_regions):
                return False, "regions_existing_conflict"
            existing_regions_match = True
        else:
            existing_regions_match = False
    else:
        existing_regions_match = False

    # ======================================================================
    # SCHRITT 3: Bestehende Keywords schreiben.
    # ======================================================================
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

    if completed.returncode != 0:
        return False, "exiftool_failed"

    # ======================================================================
    # SCHRITT 4: Keyword-Readback.
    # ======================================================================
    try:
        readback = subprocess.run(
            [exiftool_path, "-j", "-XMP-dc:Subject", str(image_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        subject = json.loads(readback.stdout)[0].get("Subject", [])
    except Exception:
        return False, "tags_readback_failed"

    written_tags = subject if isinstance(subject, list) else [subject]
    missing_tags = set(tags) - set(written_tags)
    if missing_tags:
        return False, f"tags_readback_mismatch:{sorted(missing_tags)[:3]}"

    # Keine Regionsfunktion aktiv oder keine Treffer vorhanden.
    if not desired_regions:
        return True, "ok"

    # Idempotenter Wiederholungslauf: Regionen bestehen bereits exakt.
    if existing_regions_match:
        return True, "ok"

    # ======================================================================
    # SCHRITT 5: Neue MWG-RS-Regionen schreiben.
    # ======================================================================
    command = [
        exiftool_path,
        "-overwrite_original",
        f"-XMP-mwg-rs:RegionAppliedToDimensionsW={image_width}",
        f"-XMP-mwg-rs:RegionAppliedToDimensionsH={image_height}",
        "-XMP-mwg-rs:RegionAppliedToDimensionsUnit=pixel",
    ]

    for region in desired_regions:
        area = region["Area"]
        command.extend([
            f"-XMP-mwg-rs:RegionAreaW+={area['W']:.6f}",
            f"-XMP-mwg-rs:RegionAreaH+={area['H']:.6f}",
            f"-XMP-mwg-rs:RegionAreaX+={area['X']:.6f}",
            f"-XMP-mwg-rs:RegionAreaY+={area['Y']:.6f}",
            "-XMP-mwg-rs:RegionAreaUnit+=normalized",
            f"-XMP-mwg-rs:RegionName+={region['Name']}",
            "-XMP-mwg-rs:RegionType+=Face",
        ])
    command.append(str(image_path))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
        )
    except Exception:
        return False, "regions_exiftool_exec_error"

    if completed.returncode != 0:
        return False, "regions_exiftool_failed"

    # ======================================================================
    # SCHRITT 6: Region-Readback.
    # ======================================================================
    try:
        written_regions = _read_regions(exiftool_path)
    except Exception:
        return False, "regions_readback_failed"

    if _canonical_regions(written_regions) != _canonical_regions(desired_regions):
        return False, "regions_readback_mismatch"

    return True, "ok"
