# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/idempotent_assignment.py
# PURPOSE:     Idempotente Zuordnung (AP8)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, json, hashlib
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP8
#               - IdempotentAssignment-Klasse für Zuordnungen
#               - assign() für idempotente Zuordnung
#               - is_assigned() für Duplikat-Pruefung
#               - Recovery-Unterstu tzung
# =============================================================================


import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional


# =============================================================================
# IdempotentAssignment-Klasse
# =============================================================================

class IdempotentAssignment:
    """
    Idempotente Zuordnung von Bildern.
    """
    
    def __init__(self, base_dir: str, log_path: Optional[str] = None):
        """
        Initialisiert idempotente Zuordnung.
        
        Args:
            base_dir: Basisverzeichnis
            log_path: Pfad zum Assignment-Log (default: .assignments.json)
        """
        self.base_dir = base_dir
        
        if log_path is None:
            manual_keep_dir = os.path.join(base_dir, "MANUAL_KEEP")
            log_path = os.path.join(manual_keep_dir, ".assignments.json")
        
        self.log_path = log_path
        self.assignments: Dict[str, Dict[str, Any]] = {}
        
        # Log laden
        self._load_log()
    
    def _load_log(self) -> None:
        """Laedt Assignment-Log."""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assignments = data.get("assignments", {})
            except (json.JSONDecodeError, IOError):
                self.assignments = {}
    
    def _save_log(self) -> None:
        """Speichert Assignment-Log."""
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        data = {
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "assignments": self.assignments,
        }
        
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def assign(self, source_path: str, target_path: str, 
               user_id: str = "unknown",
               metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, str]:
        """
        Fuhrt idempotente Zuordnung aus.
        
        Args:
            source_path: Quellpfad
            target_path: Zielpfad
            user_id: User-ID
            metadata: Optionale Metadaten
        
        Returns:
            Tuple (success, assignment_id, message)
        """
        # Assignment-ID berechnen
        assignment_id = self._compute_assignment_id(source_path, user_id)
        
        # Pruefen, ob bereits zugewiesen (idempotent)
        if self.is_assigned(assignment_id):
            return False, assignment_id, "Bereits zugewiesen (idempotent)"
        
        # Lock pruefen (optional)
        # TODO: Lock-Mechanismus
        
        # Zuordnung durchfuehren
        try:
            # File-Operation
            import shutil
            shutil.copy2(source_path, target_path)
            if os.path.exists(source_path):
                os.remove(source_path)
            
            # Assignment speichern
            self._record_assignment(assignment_id, source_path, target_path, user_id, metadata)
            
            return True, assignment_id, f"Zugewiesen: {target_path}"
        
        except Exception as e:
            return False, assignment_id, f"Fehler: {e}"
    
    def is_assigned(self, assignment_id: str) -> bool:
        """
        Prueft, ob Assignment bereits existiert.
        
        Args:
            assignment_id: Assignment-ID
        
        Returns:
            True, wenn bereits zugewiesen
        """
        return assignment_id in self.assignments
    
    def get_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt Assignment-Details zurueck.
        
        Args:
            assignment_id: Assignment-ID
        
        Returns:
            Assignment-Details oder None
        """
        return self.assignments.get(assignment_id)
    
    def _compute_assignment_id(self, source_path: str, user_id: str) -> str:
        """
        Berechnet eindeutige Assignment-ID.
        
        Args:
            source_path: Quellpfad
            user_id: User-ID
        
        Returns:
            Assignment-ID (16 Zeichen Hash)
        """
        canonical = f"{os.path.normpath(source_path)}|{user_id}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    
    def _record_assignment(self, assignment_id: str, source_path: str,
                           target_path: str, user_id: str,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Speichert Assignment-Record.
        
        Args:
            assignment_id: Assignment-ID
            source_path: Quellpfad
            target_path: Zielpfad
            user_id: User-ID
            metadata: Optionale Metadaten
        """
        record = {
            "assignment_id": assignment_id,
            "source_path": source_path,
            "target_path": target_path,
            "user_id": user_id,
            "assigned_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
            "metadata": metadata or {},
        }
        
        self.assignments[assignment_id] = record
        self._save_log()


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def compute_assignment_hash(source_path: str, user_id: str) -> str:
    """
    Berechnet Assignment-Hash (Hilfsfunktion).
    
    Args:
        source_path: Quellpfad
        user_id: User-ID
    
    Returns:
        Assignment-ID (16 Zeichen)
    """
    canonical = f"{os.path.normpath(source_path)}|{user_id}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]