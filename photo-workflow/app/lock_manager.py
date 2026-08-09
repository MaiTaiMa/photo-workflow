"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/lock_manager.py
# PURPOSE:     Locking und Recovery (AP8)
# AUTHOR:      Benjamin (via AP8-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP8)
# REQUIRES:    Python 3.8+, os, json
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP8
#               - LockManager-Klasse für Locking
#               - acquire_lock() und release_lock()
#               - Recovery-Log und Wiederaufnahme
# =============================================================================
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional


# =============================================================================
# LockManager-Klasse
# =============================================================================

class LockManager:
    """
    Verwaltung von Locks und Recovery.
    """
    
    def __init__(self, base_dir: str, locks_dir: Optional[str] = None,
                 recovery_log_path: Optional[str] = None):
        """
        Initialisiert Lock-Manager.
        
        Args:
            base_dir: Basisverzeichnis
            locks_dir: Verzeichnis für Lock-Dateien (default: MANUAL_KEEP/.locks)
            recovery_log_path: Pfad zum Recovery-Log (default: MANUAL_KEEP/.recovery_info.json)
        """
        self.base_dir = base_dir
        
        # Pfade
        if locks_dir is None:
            manual_keep_dir = os.path.join(base_dir, "MANUAL_KEEP")
            locks_dir = os.path.join(manual_keep_dir, ".locks")
        
        if recovery_log_path is None:
            manual_keep_dir = os.path.join(base_dir, "MANUAL_KEEP")
            recovery_log_path = os.path.join(manual_keep_dir, ".recovery_info.json")
        
        self.locks_dir = locks_dir
        self.recovery_log_path = recovery_log_path
        
        # Verzeichnisse sicherstellen
        os.makedirs(self.locks_dir, exist_ok=True)
        
        # Recovery-Log laden
        self.recovery_info: Dict[str, Any] = {}
        self._load_recovery_log()
    
    def _load_recovery_log(self) -> None:
        """Laedt Recovery-Log."""
        if os.path.exists(self.recovery_log_path):
            try:
                with open(self.recovery_log_path, "r", encoding="utf-8") as f:
                    self.recovery_info = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.recovery_info = {}
    
    def _save_recovery_log(self) -> None:
        """Speichert Recovery-Log."""
        os.makedirs(os.path.dirname(self.recovery_log_path), exist_ok=True)
        
        self.recovery_info["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        with open(self.recovery_log_path, "w", encoding="utf-8") as f:
            json.dump(self.recovery_info, f, indent=2, ensure_ascii=False)
    
    def acquire_lock(self, resource_id: str, user_id: str,
                     timeout_seconds: int = 300) -> Tuple[bool, str]:
        """
        Setzt Lock für Ressource.
        
        Args:
            resource_id: Ressourcen-ID (z.B. assignment_id)
            user_id: User-ID
            timeout_seconds: Lock-Timeout (default: 300s)
        
        Returns:
            Tuple (success, message)
        """
        lock_path = os.path.join(self.locks_dir, f"{resource_id}.lock")
        
        # Existiert bereits?
        if os.path.exists(lock_path):
            # Timeout pruefen
            try:
                with open(lock_path, "r") as f:
                    data = json.load(f)
                    locked_at = datetime.fromisoformat(data["locked_at"].replace("Z", "+00:00"))
                    elapsed = (datetime.utcnow().replace(tzinfo=locked_at.tzinfo) - locked_at).total_seconds()
                    
                    if elapsed < timeout_seconds:
                        return False, f"Lock bereits gesetzt von {data.get('user_id', 'unknown')}"
                    else:
                        # Stale Lock, ueberschreiben
                        pass
            except (json.JSONDecodeError, IOError, KeyError):
                # Corrupt Lock, ueberschreiben
                pass
        
        # Lock setzen
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        lock_data = {
            "resource_id": resource_id,
            "user_id": user_id,
            "locked_at": datetime.utcnow().isoformat() + "Z",
            "timeout_seconds": timeout_seconds,
        }
        
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, indent=2)
        
        # Recovery-Log aktualisieren
        self._record_in_progress(resource_id, user_id)
        
        return True, "Lock gesetzt"
    
    def release_lock(self, resource_id: str) -> Tuple[bool, str]:
        """
        Gibt Lock frei.
        
        Args:
            resource_id: Ressourcen-ID
        
        Returns:
            Tuple (success, message)
        """
        lock_path = os.path.join(self.locks_dir, f"{resource_id}.lock")
        
        if os.path.exists(lock_path):
            os.remove(lock_path)
            
            # Recovery-Log aktualisieren
            self._mark_completed(resource_id)
            
            return True, "Lock freigegeben"
        else:
            return False, "Lock nicht gefunden"
    
    def is_locked(self, resource_id: str, timeout_seconds: int = 300) -> Tuple[bool, Optional[str]]:
        """
        Prueft, ob Ressource gesperrt ist.
        
        Args:
            resource_id: Ressourcen-ID
            timeout_seconds: Lock-Timeout
        
        Returns:
            Tuple (is_locked, user_id_or_None)
        """
        lock_path = os.path.join(self.locks_dir, f"{resource_id}.lock")
        
        if not os.path.exists(lock_path):
            return False, None
        
        try:
            with open(lock_path, "r") as f:
                data = json.load(f)
                locked_at = datetime.fromisoformat(data["locked_at"].replace("Z", "+00:00"))
                elapsed = (datetime.utcnow().replace(tzinfo=locked_at.tzinfo) - locked_at).total_seconds()
                
                if elapsed < timeout_seconds:
                    return True, data.get("user_id", "unknown")
                else:
                    # Stale Lock
                    return False, None
        except (json.JSONDecodeError, IOError, KeyError):
            return False, None
    
    def _record_in_progress(self, resource_id: str, user_id: str) -> None:
        """Markiert Assignment als 'in_progress' im Recovery-Log."""
        if "in_progress" not in self.recovery_info:
            self.recovery_info["in_progress"] = {}
        
        self.recovery_info["in_progress"][resource_id] = {
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
        }
        
        self._save_recovery_log()
    
    def _mark_completed(self, resource_id: str) -> None:
        """Markiert Assignment als 'completed' im Recovery-Log."""
        if "in_progress" in self.recovery_info:
            if resource_id in self.recovery_info["in_progress"]:
                del self.recovery_info["in_progress"][resource_id]
        
        if "completed" not in self.recovery_info:
            self.recovery_info["completed"] = []
        
        self.recovery_info["completed"].append({
            "resource_id": resource_id,
            "completed_at": datetime.utcnow().isoformat() + "Z",
        })
        
        self._save_recovery_log()
    
    def get_in_progress(self) -> List[Dict[str, Any]]:
        """
        Gibt alle 'in_progress' Assignments zurueck.
        
        Returns:
            Liste von Assignment-Infos
        """
        result = []
        
        for resource_id, info in self.recovery_info.get("in_progress", {}).items():
            result.append({
                "resource_id": resource_id,
                "user_id": info.get("user_id", "unknown"),
                "started_at": info.get("started_at"),
            })
        
        return result
    
    def resume_in_progress(self) -> List[Dict[str, Any]]:
        """
        Setzt 'in_progress' Assignments fort (Recovery).
        
        Returns:
            Liste von wiederhergestellten Assignments
        """
        # TODO: In-Progress-Assignments wiederaufnehmen
        return self.get_in_progress()