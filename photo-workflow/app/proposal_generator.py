"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/proposal_generator.py
# PURPOSE:     Vorschlags-Generierung für new_refs/new_faces (AP5)
# AUTHOR:      Benjamin (via AP5-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP5)
# REQUIRES:    Python 3.8+, pool_limits.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP5
#               - ProposalGenerator-Klasse für Vorschlaege
#               - generate_proposals() für Vorschlags-Generierung
#               - filter_candidates() für Kandidaten-Filterung
#               - prioritize_proposals() für Priorisierung
# =============================================================================
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import hashlib


# =============================================================================
# Konstanten
# =============================================================================

DEFAULT_SCORE_THRESHOLD = 0.7  # Mindest-Score für Vorschlaege
DEFAULT_DIVERSITY_THRESHOLD = 0.3  # Mindest-Diversitaet
DEFAULT_COOLDOWN_DAYS = 7  # Cool-Down für recency


# =============================================================================
# ProposalGenerator-Klasse
# =============================================================================

class ProposalGenerator:
    """
    Generiert Vorschlaege für new_refs/new_faces.
    """
    
    def __init__(self, pool_type: str, limits: Dict[str, int],
                 score_threshold: float = DEFAULT_SCORE_THRESHOLD,
                 diversity_threshold: float = DEFAULT_DIVERSITY_THRESHOLD,
                 cooldown_days: int = DEFAULT_COOLDOWN_DAYS):
        """
        Initialisiert Proposal-Generator.
        
        Args:
            pool_type: Typ des Pools (aesthetic, personal, face)
            limits: Limits-Dict
            score_threshold: Mindest-Score für Vorschlaege
            diversity_threshold: Mindest-Diversitaet
            cooldown_days: Cool-Down-Periode (Tage)
        """
        self.pool_type = pool_type
        self.limits = limits
        self.score_threshold = score_threshold
        self.diversity_threshold = diversity_threshold
        self.cooldown_days = cooldown_days
        
        self.max_new_per_batch = limits.get("max_new_per_batch", 10)
        self.max_new = limits.get("max_new", 50)
    
    def generate_proposals(self, candidates: List[Dict[str, Any]],
                           existing_images: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Generiert Vorschlaege aus Kandidaten.
        
        Args:
            candidates: Liste von Kandidaten-Bildern (mit score, rel_path, etc.)
            existing_images: Bereits existierende Bilder im Pool
        
        Returns:
            Tuple (proposals, warnings)
        """
        warnings = []
        
        # 1. Kandidaten filtern (score, recency, etc.)
        filtered = self.filter_candidates(candidates, existing_images)
        
        # 2. Nach Prioritaet sortieren
        prioritized = self.prioritize_proposals(filtered)
        
        # 3. Auf max_new_per_batch begrenzen
        proposals = prioritized[:self.max_new_per_batch]
        
        # 4. Warnung wenn mehr Kandidaten als Platz
        if len(prioritized) > self.max_new_per_batch:
            warnings.append(f"{len(prioritized) - self.max_new_per_batch} Kandidaten nicht aufgenommen (max_new_per_batch={self.max_new_per_batch})")
        
        # 5. Vorschlaege als "new" markieren
        for proposal in proposals:
            proposal["status"] = "new"
            proposal["added_at"] = datetime.utcnow().isoformat() + "Z"
            proposal["source"] = "auto"
        
        return proposals, warnings
    
    def filter_candidates(self, candidates: List[Dict[str, Any]],
                          existing_images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtert Kandidaten nach Kriterien.
        
        Args:
            candidates: Kandidaten-Bilder
            existing_images: Bereits existierende Bilder
        
        Returns:
            Gefilterte Kandidaten
        """
        filtered = []
        now = datetime.utcnow()
        
        # rel_paths existierender Bilder
        existing_paths = set(img.get("rel_path", "") for img in existing_images)
        
        for candidate in candidates:
            rel_path = candidate.get("rel_path", "")
            
            # 1. Score-Threshold
            score = candidate.get("score", 0)
            if score < self.score_threshold:
                continue
            
            # 2. Nicht bereits im Pool
            if rel_path in existing_paths:
                continue
            
            # 3. Recency-Check (Cool-Down)
            added_at_str = candidate.get("added_at", "")
            if added_at_str:
                try:
                    added_at = datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
                    if now - added_at < timedelta(days=self.cooldown_days):
                        continue  # Zu recently
                except (ValueError, TypeError):
                    pass
            
            # 4. Diversity-Check (Placeholder)
            diversity = candidate.get("diversity", 1.0)
            if diversity < self.diversity_threshold:
                continue
            
            # Kandidat akzeptiert
            filtered.append(candidate)
        
        return filtered
    
    def prioritize_proposals(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sortiert Kandidaten nach Prioritaet.
        
        Args:
            candidates: Kandidaten-Bilder
        
        Returns:
            Sortierte Liste
        """
        def sort_key(candidate: Dict[str, Any]) -> Tuple[float, float, float]:
            score = candidate.get("score", 0)
            diversity = candidate.get("diversity", 0)
            recency = candidate.get("recency", 0)
            
            # Sortierung: score (absteigend), diversity (absteigend), recency (absteigend)
            return (-score, -diversity, -recency)
        
        return sorted(candidates, key=sort_key)


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def compute_proposal_hash(candidate: Dict[str, Any]) -> str:
    """
    Berechnet Hash für einen Vorschlag (zur Duplikat-Erkennung).
    
    Args:
        candidate: Kandidaten-Bild
    
    Returns:
        SHA-256 Hash (erste 12 Zeichen)
    """
    components = [
        candidate.get("rel_path", ""),
        str(candidate.get("score", 0)),
        candidate.get("added_at", ""),
    ]
    
    canonical = "|".join(components)
    hash_hex = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    return hash_hex[:12]


def generate_proposals(pool_type: str, candidates: List[Dict[str, Any]],
                       existing_images: List[Dict[str, Any]],
                       limits: Dict[str, int]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Generiert Vorschlaege (Hilfsfunktion).
    
    Args:
        pool_type: Typ des Pools
        candidates: Kandidaten-Bilder
        existing_images: Bereits existierende Bilder
        limits: Limits-Dict
    
    Returns:
        Tuple (proposals, warnings)
    """
    generator = ProposalGenerator(pool_type, limits)
    return generator.generate_proposals(candidates, existing_images)