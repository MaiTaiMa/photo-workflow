"""
Skript: app/manual_keep.py
Zweck: MANUAL_KEEP-Verwaltung (AP8) - inbox/ und used/ fur manuell geschutzte Bilder.
Autor: Benjamin (via AP8-Implementierung)
Erstellt: 2026-08-09
Version: 1.1
Requires: Python 3.8+, os, json, pathlib

Ä·nderungsprotokoll:
  2026-08-09 | 1.0 | Initiale Implementierung fur AP8
  2026-08-09 | 1.1 | Robustere Pfadprufung, Batch-Erkennung, Terminal-Ausgabe

98AP-Vertrag:
  - AP2: MANUAL_KEEP hat Vorrang vor jeder automatischen Bewertung
  - AP7: Entscheidungen mussen nachvollziehbar und reversibel sein
  - AP8: Inbox/Used-Logik fur idempotente Zuordnung
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Set
from pathlib import Path
from review_validation import ReviewValidator

# =============================================================================
# Konstanten
# =============================================================================

IMAGE_EXTS = {".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".tif", ".tiff", ".webp"}
JPG_EXTS = {".jpg", ".jpeg"}

# =============================================================================
# Hilfsfunktionen fur Batch-Erkennung
# =============================================================================

def now():
    """ISO-8601 Zeitstempel für Logs."""
    return datetime.now().isoformat()

def _normalize_filename(filename: str) -> str:
    """Normalisiert Dateinamen fur case-insensitive Vergleiche."""
    return filename.upper()


def _collect_inbox_filenames(inbox_batch: Path) -> Set[str]:
    """
    Sammelt alle Bilddateinamen im inbox-Batch.
    
    98AP-Regeln:
      - Case-insensitive Vergleiche (.JPG == .jpg)
      - Nur IMAGE_EXTS berucksichtigen
      - Leeren inbox als leer melden, nicht als Fehler
    """
    filenames: Set[str] = set()
    
    if not inbox_batch.exists() or not inbox_batch.is_dir():
        return filenames
    
    for pattern in ["*.JPG", "*.jpg", "*.JPEG", "*.jpeg", "*.PNG", "*.png"]:
        for img in inbox_batch.glob(pattern):
            if img.is_file() and not img.is_symlink():
                filenames.add(_normalize_filename(img.name))
    
    return filenames


def _match_batch_images(batch_path: Path, inbox_filenames: Set[str]) -> List[Path]:
    """
    Returns supported image files directly in folder (no subfolders).
    Sorted by name for reproducible ordering.
    
    Excludes:
      - Symlinks
      - Hidden files (starting with '.')
      - Non-image files
    """
    keep_images: List[Path] = []
    
    if not batch_path.exists() or not batch_path.is_dir():
        return keep_images
    
    for pattern in ["*.JPG", "*.jpg", "*.JPEG", "*.jpeg", "*.PNG", "*.png"]:
        for img in batch_path.glob(pattern):
            if img.is_file() and not img.is_symlink():
                if _normalize_filename(img.name) in inbox_filenames:
                    if img not in keep_images:
                        keep_images.append(img)
    
    return keep_images

def top_level_images(folder: Path) -> List[Path]:
    """Returns supported image files directly in folder (no subfolders)."""
    if not folder.is_dir():
        return []
    
    return sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and not path.name.startswith('.')
            and path.suffix.lower() in IMAGE_EXTS
        ),
        key=lambda path: path.name.lower(),
    )


def top_level_jpgs(folder: Path) -> List[Path]:
    """
    Returns only .JPG/.jpeg files directly in folder (no subfolders).
    Sorted by name for reproducible ordering.
    
    Excludes:
      - Symlinks
      - Hidden files (starting with '.')
      - Non-JPG files
    """
    if not folder.is_dir():
        return []
    
    return sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and not path.name.startswith('.')
            and path.suffix.lower() in {".jpg", ".jpeg"}
        ),
        key=lambda path: path.name.lower(),
    )

def is_image_file(path: Path) -> bool:
    """Check if path is a supported image file."""
    return path.is_file() and not path.is_symlink() and path.suffix.lower() in IMAGE_EXTS


def is_jpg_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and path.suffix.lower() in JPG_EXTS

# =============================================================================
# Feature-Extraktion (unterhalb der Imports, vor ManualKeep-Klasse)
# =============================================================================

def extract_visual_features(image_path: Path, preview_size: int = 32) -> list[float]:
    """
    Extrahiert Feature-Vektor für ein Bild (ähnlich wie series_detection).
    
    98AP-Regeln:
      - Keine Bildbytes speichern, nur Features
      - Preview-Size konfigurierbar (Default 32px)
      - Feature-Vektor als Liste von Floats
    
    Args:
        image_path: Pfad zum Bild
        preview_size: Kantenlänge für Feature-Extraktion
    
    Returns:
        Liste von Floats (Feature-Vektor)
    """
    try:
        from PIL import Image
        import numpy as np
        
        # Bild laden und auf preview_size skalieren
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            img = img.resize((preview_size, preview_size), Image.Resampling.LANCZOS)
            
            # In numpy Array konvertieren und normalisieren
            arr = np.array(img, dtype=np.float32) / 255.0
            
            # Flattened Feature-Vektor (RGB * preview_size^2)
            features = arr.flatten().tolist()
            
            return features
    
    except Exception as e:
        # Bei Fehler leeren Vektor zurückgeben
        return [0.0] * (3 * preview_size * preview_size)


def cosine_similarity(features_a: list[float], features_b: list[float]) -> float:
    """
    Berechnet Kosinus-Ähnlichkeit zwischen zwei Feature-Vektoren.
    
    Args:
        features_a: Erster Feature-Vektor
        features_b: Zweiter Feature-Vektor
    
    Returns:
        Ähnlichkeit von 0.0 (unähnlich) bis 1.0 (identisch)
    """
    import numpy as np
    
    # In numpy Arrays konvertieren
    vec_a = np.array(features_a, dtype=np.float32)
    vec_b = np.array(features_b, dtype=np.float32)
    
    # Kosinus-Ähnlichkeit berechnen
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))


def load_or_extract_features(image_path: Path) -> dict:
    """
    Lädt gespeicherte Features oder extrahiert sie neu.
    
    98AP-Regeln:
      - Features werden als JSON neben dem Bild gespeichert
      - Bei Änderung des Bildes (mtime) neu extrahieren
    
    Args:
        image_path: Pfad zum Bild
    
    Returns:
        dict mit 'features', 'path', 'filename', 'mtime_ns'
    """
    features_path = image_path.with_suffix(image_path.suffix + '.features.json')
    
    # Features existieren?
    if features_path.exists():
        try:
            features = json.loads(features_path.read_text(encoding='utf-8'))
            
            # Prüfen, ob Bild unverändert ist
            stat = image_path.stat()
            if features.get('mtime_ns') == stat.st_mtime_ns:
                return features
        except Exception:
            pass  # Bei Fehler neu extrahieren
    
    # Neu extrahieren
    stat = image_path.stat()
    features = {
        'path': str(image_path),
        'filename': image_path.name,
        'size': stat.st_size,
        'mtime_ns': stat.st_mtime_ns,
        'features': extract_visual_features(image_path),
        'created_at': now(),
    }
    
    # Speichern
    try:
        features_path.write_text(json.dumps(features, indent=2), encoding='utf-8')
    except Exception:
        pass  # Speichern optional, nicht kritisch
    
    return features

# =============================================================================
# ManualKeep-Klasse (AP8)
# =============================================================================

class ManualKeep:
    """
    Verwaltung von MANUAL_KEEP (inbox/ und used/).
    
    98AP-Regeln:
      - AP2: MANUAL_KEEP hat Vorrang vor automatischer Bewertung
      - AP7: Entscheidungen mussen nachvollziehbar sein
      - AP8: Inbox/Used-Logik fur idempotente Zuordnung
    """

    def __init__(self, base_dir: str):
        """
        Initialisiert MANUAL_KEEP.
        
        Args:
            base_dir: Basisverzeichnis (z.B. /path/to/NAS_EXAMPLE)
        """
        self.base_dir = base_dir
        self.manual_keep_dir = os.path.join(base_dir, "MANUAL_KEEP")
        self.inbox_dir = os.path.join(self.manual_keep_dir, "inbox")
        self.used_dir = os.path.join(self.manual_keep_dir, "used")
        self.locks_dir = os.path.join(self.manual_keep_dir, ".locks")
        self.recovery_log_path = os.path.join(self.manual_keep_dir, ".recovery_info.json")

        # Verzeichnisse sicherstellen
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Stellt sicher, dass alle Verzeichnisse existieren."""
        for dir_path in [self.inbox_dir, self.used_dir, self.locks_dir]:
            os.makedirs(dir_path, exist_ok=True)

        # .gitkeep-Dateien
        for dir_path in [self.inbox_dir, self.used_dir]:
            gitkeep_path = os.path.join(dir_path, ".gitkeep")
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, "w") as f:
                    f.write("")

    def move_to_inbox(self, source_path: str, user_id: str = "unknown") -> Tuple[bool, str]:
        """
        Verschiebt Bild nach inbox/.
        
        Args:
            source_path: Quellpfad
            user_id: User-ID fur Log
        
        Returns:
            Tuple (success, message)
        """
        # Ziel-Pfad
        filename = os.path.basename(source_path)
        target_path = os.path.join(self.inbox_dir, filename)

        # Verschieben
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Copy then delete (sicherer als move)
            shutil.copy2(source_path, target_path)
            if os.path.exists(source_path):
                os.remove(source_path)

            # Log
            self._log_assignment("inbox", source_path, target_path, user_id)

            return True, f"Verschoben nach inbox: {target_path}"

        except Exception as e:
            return False, f"Fehler: {e}"

    def move_to_used(self, source_path: str, user_id: str = "unknown",
                     metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Verschiebt Bild nach used/ (idempotent).
        
        Args:
            source_path: Quellpfad
            user_id: User-ID fur Log
            metadata: Optionale Metadaten
        
        Returns:
            Tuple (success, message)
        """
        # Assignment-ID berechnen
        assignment_id = self._compute_assignment_id(source_path, user_id)

        # Pruefen, ob bereits zugewiesen (idempotent)
        if self._is_already_assigned(assignment_id):
            return False, f"Bereits zugewiesen (idempotent): {assignment_id}"

        # Lock setzen
        if not self._acquire_lock(assignment_id, user_id):
            return False, "Lock nicht erhalten (Konflikt)"

        try:
            # Ziel-Pfad
            filename = os.path.basename(source_path)
            target_path = os.path.join(self.used_dir, filename)

            # Kollision vermeiden
            if os.path.exists(target_path):
                target_path = self._get_unique_path(target_path)

            # Verschieben
            shutil.copy2(source_path, target_path)
            if os.path.exists(source_path):
                os.remove(source_path)

            # Assignment speichern
            self._record_assignment(assignment_id, source_path, target_path, user_id, metadata)

            # Lock freigeben
            self._release_lock(assignment_id)

            # Log
            self._log_assignment("used", source_path, target_path, user_id)

            return True, f"Verschoben nach used: {target_path}"

        except Exception as e:
            # Lock freigeben bei Fehler
            self._release_lock(assignment_id)
            return False, f"Fehler: {e}"

    def get_inbox_images(self) -> List[Dict[str, Any]]:
        """
        Gibt alle Bilder in inbox/ zurueck.
        
        Returns:
            Liste von Bild-Infos (rel_path, size, mtime, etc.)
        """
        images = []

        for filename in os.listdir(self.inbox_dir):
            if filename.startswith("."):
                continue

            file_path = os.path.join(self.inbox_dir, filename)

            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                images.append({
                    "rel_path": os.path.relpath(file_path, self.base_dir),
                    "filename": filename,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "location": "inbox",
                })

        return images

    def get_used_images(self) -> List[Dict[str, Any]]:
        """
        Gibt alle Bilder in used/ zurueck.
        
        Returns:
            Liste von Bild-Infos (rel_path, size, mtime, assignment_id, etc.)
        """
        images = []

        for filename in os.listdir(self.used_dir):
            if filename.startswith("."):
                continue

            file_path = os.path.join(self.used_dir, filename)

            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                assignment_id = self._compute_assignment_id(file_path, "unknown")

                images.append({
                    "rel_path": os.path.relpath(file_path, self.base_dir),
                    "filename": filename,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "location": "used",
                    "assignment_id": assignment_id,
                })

        return images

    def _compute_assignment_id(self, file_path: str, user_id: str) -> str:
        """Berechnet eindeutige Assignment-ID."""
        import hashlib
        canonical = f"{os.path.normpath(file_path)}|{user_id}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def _is_already_assigned(self, assignment_id: str) -> bool:
        """Prueft, ob Assignment bereits existiert."""
        # TODO: In Datenbank/JSON-Log nachschauen
        return False

    def _acquire_lock(self, assignment_id: str, user_id: str, timeout_seconds: int = 300) -> bool:
        """Setzt Lock fur Assignment."""
        lock_path = os.path.join(self.locks_dir, f"{assignment_id}.lock")

        # Existiert bereits?
        if os.path.exists(lock_path):
            # Timeout pruefen
            try:
                with open(lock_path, "r") as f:
                    lines = f.readlines()
                if len(lines) >= 2:
                    locked_at = datetime.fromisoformat(lines[1].strip().replace("Z", "+00:00"))
                    elapsed = (datetime.utcnow().replace(tzinfo=locked_at.tzinfo) - locked_at).total_seconds()
                    if elapsed < timeout_seconds:
                        return False  # Lock noch aktiv
            except:
                pass

        # Lock setzen
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with open(lock_path, "w") as f:
            f.write(f"{user_id}\n{datetime.utcnow().isoformat()}Z\n")

        return True

    def _release_lock(self, assignment_id: str) -> None:
        """Gibt Lock frei."""
        lock_path = os.path.join(self.locks_dir, f"{assignment_id}.lock")
        if os.path.exists(lock_path):
            os.remove(lock_path)

    def _get_unique_path(self, base_path: str) -> str:
        """Generiert eindeutigen Pfad (bei Kollision)."""
        if not os.path.exists(base_path):
            return base_path

        # Suffix hinzufugen
        base, ext = os.path.splitext(base_path)
        counter = 1

        while True:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def _record_assignment(self, assignment_id: str, source_path: str,
                           target_path: str, user_id: str,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """Speichert Assignment-Record."""
        # TODO: In Datenbank/JSON-Log speichern
        pass

    def _log_assignment(self, location: str, source: str, target: str, user_id: str) -> None:
        """Loggt Assignment."""
        # TODO: In Log-Datei schreiben
        pass

# =============================================================================
# Funktion fur Phase-1-Integration (AP2)
# =============================================================================

def detect_manual_keep_images(
    batch_path: Path,
    manual_keep_inbox: Path,
    manual_keep_used: Path,
    similarity_threshold: float = 0.85,
) -> Tuple[List[Path], dict]:
    """
    Erkennt Bilder im Batch, die MANUAL_KEEP-Bildern ähneln.
    
    98AP-Regeln:
      - Feature-Vektor-basiertes Matching (nicht Dateiname)
      - Threshold-configurierbar (Default 0.85)
      - inbox kann flach oder mit Batch-Unterordnern sein
      - Keine Bildbytes persistieren, nur Features
    
    Args:
        batch_path: Pfad zum Batch-Ordner
        manual_keep_inbox: Pfad zum MANUAL_KEEP/inbox-Ordner
        manual_keep_used: Pfad zum MANUAL_KEEP/used-Ordner
        similarity_threshold: Minimale Ähnlichkeit für Match (0.0-1.0)
    
    Returns:
        Tuple (List[Image-Pfade im Batch], status_dict)
        status_dict enthält:
            - inbox_count: Anzahl Bilder im inbox
            - matched_count: Anzahl Treffer im Batch
            - status: 'ok', 'no_inbox', 'empty_inbox', 'matched', 'no_match'
    """
    status = {
        'inbox_count': 0,
        'matched_count': 0,
        'matched_source_count': 0,
        'matched_source_paths': [],
        'status': 'ok',
    }
    
    # Batch-Pfad prüfen
    if not batch_path.exists() or not batch_path.is_dir():
        status['status'] = 'batch_missing'
        return [], status
    
    # Inbox-Pfad prüfen
    if not manual_keep_inbox.exists() or not manual_keep_inbox.is_dir():
        status['status'] = 'no_inbox'
        return [], status
    
    # 1. Alle MANUAL_KEEP-Bilder im inbox laden (flach + Unterordner)
    inbox_features: list[dict] = []
    
    # Flache Struktur: inbox/*.JPG
    for pattern in ['*.JPG', '*.jpg', '*.JPEG', '*.jpeg']:
        for img in manual_keep_inbox.glob(pattern):
            if img.is_file() and not img.is_symlink():
                features = load_or_extract_features(img)
                inbox_features.append(features)
                status['inbox_count'] += 1
    
    # Unterordner-Struktur: inbox/BATCH_NAME/*.JPG
    for batch_dir in manual_keep_inbox.iterdir():
        if batch_dir.is_dir() and not batch_dir.name.startswith('.'):
            for pattern in ['*.JPG', '*.jpg', '*.JPEG', '*.jpeg']:
                for img in batch_dir.glob(pattern):
                    if img.is_file() and not img.is_symlink():
                        features = load_or_extract_features(img)
                        inbox_features.append(features)
                        status['inbox_count'] += 1
    
    # Leerer inbox?
    if not inbox_features:
        status['status'] = 'empty_inbox'
        return [], status
    
    # 2. Alle Batch-Bilder mit inbox-Features vergleichen
    keep_images: List[Path] = []
    matched_source_paths: set[str] = set()
    
    for batch_img in top_level_images(batch_path):
        batch_features = extract_visual_features(batch_img)

        best_similarity = 0.0
        best_inbox_feature = None

        for inbox_feature in inbox_features:
            similarity = cosine_similarity(
                batch_features,
                inbox_feature['features'],
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_inbox_feature = inbox_feature

        if best_similarity >= similarity_threshold:
            keep_images.append(batch_img)
            status['matched_count'] += 1

            if best_inbox_feature is not None:
                matched_source_paths.add(best_inbox_feature['path'])

    status['matched_source_paths'] = sorted(matched_source_paths)
    status['matched_source_count'] = len(matched_source_paths)
    
    # Status setzen
    if keep_images:
        status['status'] = 'matched'
    else:
        status['status'] = 'no_match'
    
    return keep_images, status

def move_manual_keep_sources_to_used(
    matched_source_paths: list[str],
    manual_keep_inbox: Path,
    manual_keep_used: Path,
) -> dict:
    """
    Verschiebt erfolgreich verwendete MANUAL_KEEP-Quellbilder von inbox nach used.

    Die Quelldateien stammen aus dem Feature-Matching. Deshalb erfolgt keine
    Zuordnung über Batch-Dateinamen.

    Unterordner relativ zu inbox bleiben unter used erhalten. Das verhindert
    Namenskollisionen bei mehrfach vorkommenden Dateinamen.
    """
    result = {
        'moved_count': 0,
        'already_used_count': 0,
        'failed_count': 0,
        'errors': [],
        'status': 'ok',
    }

    inbox_root = manual_keep_inbox.resolve()
    used_root = manual_keep_used.resolve()
    used_root.mkdir(parents=True, exist_ok=True)

    for source_path_text in sorted(set(matched_source_paths)):
        source = Path(source_path_text)

        try:
            resolved_source = source.resolve()
            relative_path = resolved_source.relative_to(inbox_root)
        except (FileNotFoundError, ValueError) as exc:
            result['failed_count'] += 1
            result['errors'].append(
                f'Ungültige MANUAL_KEEP-Quelle: {source_path_text} ({exc})'
            )
            continue

        target = used_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        features_source = source.with_suffix(source.suffix + '.features.json')
        features_target = target.with_suffix(target.suffix + '.features.json')

        try:
            if target.exists():
                result['already_used_count'] += 1
            else:
                shutil.move(str(source), str(target))
                result['moved_count'] += 1

            if features_source.exists() and not features_target.exists():
                shutil.move(str(features_source), str(features_target))

        except OSError as exc:
            result['failed_count'] += 1
            result['errors'].append(f'{source} -> {target}: {exc}')

    if result['failed_count']:
        result['status'] = 'partial' if result['moved_count'] else 'failed'
    elif result['moved_count']:
        result['status'] = 'moved'
    elif result['already_used_count']:
        result['status'] = 'already_used'
    else:
        result['status'] = 'nothing_to_move'

    return result

def mark_manual_keep_used(
    batch_path: Path,
    manual_keep_inbox: Path,
    manual_keep_used: Path,
) -> int:
    """
    Verschiebt MANUAL_KEEP-Markierungen von inbox nach used.
    
    98AP-Regeln:
      - AP7: Idempotente Zuordnung (used/ verhindert Doppelverarbeitung)
      - Verschieben nach Abschluss von Phase 1
      - Fehlerhafte Verschiebe-Operationen mussen nachvollziehbar sein
    
    Args:
        batch_path: Pfad zum Batch-Ordner
        manual_keep_inbox: Pfad zum MANUAL_KEEP/inbox-Ordner
        manual_keep_used: Pfad zum MANUAL_KEEP/used-Ordner
    
    Returns:
        Anzahl verschobener Bilder
    """
    batch_name = batch_path.name
    inbox_batch = manual_keep_inbox / batch_name
    used_batch = manual_keep_used / batch_name
    
    # Inbox-Batch existiert nicht?
    if not inbox_batch.exists() or not inbox_batch.is_dir():
        return 0
    
    # Used-Batch existiert bereits? (idempotent)
    if used_batch.exists() and used_batch.is_dir():
        return 0
    
    # Used-Batch erstellen
    used_batch.mkdir(parents=True, exist_ok=True)
    
    # Alle Bilder von inbox nach used verschieben
    moved = 0
    errors = []
    
    for img in inbox_batch.iterdir():
        if img.is_file() and not img.is_symlink():
            try:
                shutil.move(str(img), str(used_batch / img.name))
                moved += 1
            except Exception as e:
                errors.append(f"{img.name}: {e}")
    
    # Inbox-Bereinigung (nur bei Erfolg)
    if moved > 0 and not errors:
        try:
            for img in inbox_batch.iterdir():
                if img.is_file():
                    img.unlink()
            inbox_batch.rmdir()
        except Exception:
            pass  # Fehler hier nicht kritisch
    
    return moved


def get_manual_keep_status(
    batch_path: Path,
    manual_keep_inbox: Path,
    manual_keep_used: Path,
) -> dict:
    """
    Ermittelt den MANUAL_KEEP-Status fur einen Batch.
    
    98AP-Regeln:
      - AP7: Status muss nachvollziehbar sein
      - Inbox/Used-Status muss klar erkennbar sein
    
    Returns:
        dict mit:
            - in_inbox: bool
            - in_used: bool
            - inbox_count: int
            - used_count: int
    """
    batch_name = batch_path.name
    inbox_batch = manual_keep_inbox / batch_name
    used_batch = manual_keep_used / batch_name
    
    status = {
        "in_inbox": inbox_batch.exists() and inbox_batch.is_dir(),
        "in_used": used_batch.exists() and used_batch.is_dir(),
        "inbox_count": 0,
        "used_count": 0,
    }
    
    if status["in_inbox"]:
        status["inbox_count"] = sum(
            1 for f in inbox_batch.iterdir() if f.is_file() and not f.is_symlink()
        )
    
    if status["in_used"]:
        status["used_count"] = sum(
            1 for f in used_batch.iterdir() if f.is_file() and not f.is_symlink()
        )
    
    return status
    
    
def validate_batch_decisions(batch_id: str, runtime_path: Path):
    """
    Validiert Entscheidungen eines Batches nach Abschluss.
    
    Wird nach jeder manuellen Entscheidung aufgerufen.
    """
    validator = ReviewValidator(runtime_path)
    report = validator.validate_decisions(batch_id, window_days=30)
    
    output_path = runtime_path / "validation" / f"validation_{batch_id}.json"
    validator.save_validation_report(report, output_path)
    
    return report