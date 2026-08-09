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

# =============================================================================
# Konstanten
# =============================================================================

IMAGE_EXTS = {".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG"}


# =============================================================================
# Hilfsfunktionen fur Batch-Erkennung
# =============================================================================

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
    Findet alle Bilder im Batch, die im inbox liegen.
    
    98AP-Regeln:
      - Case-insensitive Vergleiche
      - Nur IMAGE_EXTS berucksichtigen
      - Leere Treffer als leer melden, nicht als Fehler
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
) -> Tuple[List[Path], dict]:
    """
    Erkennt Bilder im Batch, die im MANUAL_KEEP/inbox liegen.
    
    98AP-Regeln:
      - AP2: MANUAL_KEEP hat Vorrang vor automatischer Bewertung
      - Nur Bilder im inbox werden als KEEP markiert
      - Bilder im used wurden bereits verarbeitet (idempotent)
      - Kein Bild darf doppelt verarbeitet werden
    
    Args:
        batch_path: Pfad zum Batch-Ordner
        manual_keep_inbox: Pfad zum MANUAL_KEEP/inbox-Ordner
        manual_keep_used: Pfad zum MANUAL_KEEP/used-Ordner
    
    Returns:
        Tuple (List[Image-Pfade], status_dict)
        status_dict enthaelt:
            - inbox_count: Anzahl Bilder im inbox
            - matched_count: Anzahl Treffer im Batch
            - status: 'ok', 'no_inbox', 'batch_missing'
    """
    status = {
        "inbox_count": 0,
        "matched_count": 0,
        "status": "ok",
    }
    
    # Batch-Pfad pruefen
    if not batch_path.exists() or not batch_path.is_dir():
        status["status"] = "batch_missing"
        return [], status
    
    # Inbox-Pfad pruefen
    if not manual_keep_inbox.exists() or not manual_keep_inbox.is_dir():
        status["status"] = "no_inbox"
        return [], status
    
    # Batch-Namen extrahieren
    batch_name = batch_path.name
    inbox_batch = manual_keep_inbox / batch_name
    
    # Inbox-Batch existiert nicht?
    if not inbox_batch.exists() or not inbox_batch.is_dir():
        status["status"] = "no_inbox"
        return [], status
    
    # Alle Bilddateinamen im inbox sammeln
    inbox_filenames = _collect_inbox_filenames(inbox_batch)
    status["inbox_count"] = len(inbox_filenames)
    
    # Leerer inbox?
    if not inbox_filenames:
        status["status"] = "empty_inbox"
        return [], status
    
    # Treffer im Batch finden
    keep_images = _match_batch_images(batch_path, inbox_filenames)
    status["matched_count"] = len(keep_images)
    
    if keep_images:
        status["status"] = "matched"
    else:
        status["status"] = "no_match"
    
    return keep_images, status


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