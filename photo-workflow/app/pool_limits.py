# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/pool_limits.py
# PURPOSE:     Limit-Validierung und Ueberwachung (AP5)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, selection_schema.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP5
# =============================================================================


from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class LimitStatus:
    """Status der Pool-Limits."""
    active_count: int
    new_count: int
    unknown_count: int
    max_active: int
    min_active: int
    target_active: int
    max_new: int
    max_new_per_batch: int
    
    @property
    def is_max_active_reached(self) -> bool:
        return self.active_count >= self.max_active
    
    @property
    def is_min_active_violated(self) -> bool:
        return self.active_count < self.min_active
    
    @property
    def is_max_new_reached(self) -> bool:
        return self.new_count >= self.max_new
    
    @property
    def needs_attention(self) -> bool:
        return self.is_min_active_violated or self.is_max_active_reached or self.is_max_new_reached
    
    @property
    def available_slots_active(self) -> int:
        return max(0, self.max_active - self.active_count)
    
    @property
    def available_slots_new(self) -> int:
        return max(0, self.max_new - self.new_count)


# =============================================================================
# PoolLimits-Klasse
# =============================================================================

class PoolLimits:
    """
    Limit-Validierung und Ueberwachung für Referenzpools.
    """
    
    def __init__(self, limits: Dict[str, int]):
        """
        Initialisiert Pool-Limits.
        
        Args:
            limits: Limits-Dict (max_active, min_active, target_active, max_new, max_new_per_batch)
        """
        self.max_active = limits.get("max_active", 100)
        self.min_active = limits.get("min_active", 50)
        self.target_active = limits.get("target_active", 80)
        self.max_new = limits.get("max_new", 50)
        self.max_new_per_batch = limits.get("max_new_per_batch", 10)
        
        # Validierung
        self._validate_limits()
    
    def _validate_limits(self) -> None:
        """Validiert Limits auf Konsistenz."""
        if self.min_active > self.max_active:
            raise ValueError(f"min_active ({self.min_active}) darf max_active ({self.max_active}) nicht ueberschreiten")
        
        if self.target_active > self.max_active:
            raise ValueError(f"target_active ({self.target_active}) darf max_active ({self.max_active}) nicht ueberschreiten")
        
        if self.max_new_per_batch > self.max_new:
            raise ValueError(f"max_new_per_batch ({self.max_new_per_batch}) darf max_new ({self.max_new}) nicht ueberschreiten")
    
    def check_limits(self, active_count: int, new_count: int) -> Tuple[bool, List[str]]:
        """
        Prueft aktuelle Counts gegen Limits.
        
        Args:
            active_count: Anzahl aktiver Bilder
            new_count: Anzahl neuer Vorschlaege
        
        Returns:
            Tuple (is_valid, warnings)
        """
        warnings = []
        is_valid = True
        
        # max_active
        if active_count >= self.max_active:
            warnings.append(f"max_active erreicht: {active_count}/{self.max_active}")
            is_valid = False
        
        # min_active
        if active_count < self.min_active:
            warnings.append(f"min_active unterschritten: {active_count}/{self.min_active}")
            is_valid = False
        
        # max_new
        if new_count >= self.max_new:
            warnings.append(f"max_new erreicht: {new_count}/{self.max_new}")
            is_valid = False
        
        # target_active (nur Warning)
        if active_count != self.target_active:
            if active_count < self.target_active:
                warnings.append(f"target_active noch nicht erreicht: {active_count}/{self.target_active}")
            else:
                warnings.append(f"target_active ueberschritten: {active_count}/{self.target_active}")
        
        return is_valid, warnings
    
    def can_add_new(self, new_count: int, count: int = 1) -> bool:
        """
        Prueft, ob neue Vorschlaege hinzugefuegt werden koennen.
        
        Args:
            new_count: Aktuelle Anzahl neuer Vorschlaege
            count: Anzahl der hinzuzufuegenden Vorschlaege
        
        Returns:
            True, wenn hinzugefuegt werden kann
        """
        # max_new prüfen
        if new_count + count > self.max_new:
            return False
        
        # max_new_per_batch prüfen
        if count > self.max_new_per_batch:
            return False
        
        return True
    
    def get_batch_limit(self, new_count: int) -> int:
        """
        Berechnet maximale Anzahl neuer Vorschlaege für naechsten Batch.
        
        Args:
            new_count: Aktuelle Anzahl neuer Vorschlaege
        
        Returns:
            Maximale Anzahl (0, wenn Queue voll)
        """
        # Verbleibende Slots in max_new
        remaining_max = self.max_new - new_count
        
        # Minimum von remaining_max und max_new_per_batch
        return min(remaining_max, self.max_new_per_batch)
    
    def get_status(self, active_count: int, new_count: int, unknown_count: int = 0) -> LimitStatus:
        """
        Gibt ausfue hrlichen Status zurueck.
        
        Args:
            active_count: Anzahl aktiver Bilder
            new_count: Anzahl neuer Vorschlaege
            unknown_count: Anzahl unbekannter Bilder
        
        Returns:
            LimitStatus-Objekt
        """
        return LimitStatus(
            active_count=active_count,
            new_count=new_count,
            unknown_count=unknown_count,
            max_active=self.max_active,
            min_active=self.min_active,
            target_active=self.target_active,
            max_new=self.max_new,
            max_new_per_batch=self.max_new_per_batch,
        )


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def check_pool_limits(selection: Dict[str, Any]) -> Tuple[bool, List[str], LimitStatus]:
    """
    Prueft Limits einer selection.json.
    
    Args:
        selection: Geladene selection.json
    
    Returns:
        Tuple (is_valid, warnings, status)
    """
    limits = selection.get("limits", {})
    images = selection.get("images", [])
    
    # Counts berechnen
    active_count = len([img for img in images if img.get("status") == "active"])
    new_count = len([img for img in images if img.get("status") == "new"])
    unknown_count = len([img for img in images if img.get("status") == "unknown"])
    
    # Limits pruefen
    pool_limits = PoolLimits(limits)
    is_valid, warnings = pool_limits.check_limits(active_count, new_count)
    status = pool_limits.get_status(active_count, new_count, unknown_count)
    
    return is_valid, warnings, status