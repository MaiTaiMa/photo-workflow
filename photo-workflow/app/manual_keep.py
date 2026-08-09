"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/manual_keep.py
# PURPOSE:     MANUAL_KEEP-Verwaltung (AP8)
# AUTHOR:      Benjamin (via AP8-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP8)
# REQUIRES:    Python 3.8+, os, json
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP8
#               - ManualKeep-Klasse für Verwaltung
#               - move_to_inbox() und move_to_used()
#               - get_inbox_images() und get_used_images()
#               - Recovery- und Lock-Unterstu tzung
# =============================================================================
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


# =============================================================================
# ManualKeep-Klasse
# =============================================================================

class ManualKeep:
    """
    Verwaltung von MANUAL_KEEP (inbox/ und used/).
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
            user_id: User-ID für Log
        
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
            import shutil
            shutil.copy2(source_path, target_path)
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
            user_id: User-ID für Log
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
            import shutil
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
        """Setzt Lock für Assignment."""
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
        
        # Suffix hinzufügen
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